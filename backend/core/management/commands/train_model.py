import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from shapely.geometry import Point
from sqlalchemy import create_engine
import joblib
from sklearn.model_selection import GroupShuffleSplit
from django.core.management.base import BaseCommand
from django.conf import settings
import matplotlib.pyplot as plt


class Command(BaseCommand):
    help = "Train LightGBM ranking model with realistic MRR/MAP evaluation"

    def handle(self, *args, **kwargs):
        # ---------------- DATABASE CONNECTION ----------------
        db_settings = settings.DATABASES["default"]
        conn_str = (
            f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}"
            f"@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"
        )
        engine = create_engine(conn_str)

        # ---------------- HELPER FUNCTION ----------------
        def haversine_vector(lat1, lon1, lat2, lon2):
            R = 6371.0
            dlat = np.radians(lat2 - lat1)
            dlon = np.radians(lon2 - lon1)
            a = (
                np.sin(dlat / 2) ** 2
                + np.cos(np.radians(lat1))
                * np.cos(np.radians(lat2))
                * np.sin(dlon / 2) ** 2
            )
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
            return R * c

        # ---------------- LOAD DATA ----------------
        df = pd.read_sql(
            """
            SELECT user_id, worker_id, service_id,
                   ST_Y(worker_location::geometry) AS worker_lat,
                   ST_X(worker_location::geometry) AS worker_lon,
                   charge, num_bookings, total_rating
            FROM user_worker_data;
            """,
            engine,
        )

        df["num_bookings"] = df["num_bookings"].fillna(0).astype(int)
        df["charge"] = df["charge"].fillna(0.0)
        df["total_rating"] = pd.to_numeric(df["total_rating"], errors="coerce").fillna(0.0)

        user_locs = pd.read_sql(
            """
            SELECT id, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon
            FROM core_authenticateduser WHERE location IS NOT NULL;
            """,
            engine,
        )

        df = df.merge(user_locs.set_index("id"), left_on="user_id", right_index=True, how="left")
        df.rename(columns={"lat": "lat_user", "lon": "lon_user"}, inplace=True)
        df.dropna(subset=["lat_user", "lon_user", "worker_lat", "worker_lon"], inplace=True)

        # ---------------- FEATURE ENGINEERING ----------------
        worker_stats = df.groupby("worker_id").agg(
            worker_avg_rating=("total_rating", "mean"),
            worker_total_bookings=("num_bookings", "sum")
        ).reset_index()
        df = df.merge(worker_stats, on="worker_id", how="left")

        user_stats = df.groupby("user_id").agg(user_avg_rating=("total_rating", "mean")).reset_index()
        df = df.merge(user_stats, on="user_id", how="left")

        df["distance_km"] = haversine_vector(df["lat_user"], df["lon_user"], df["worker_lat"], df["worker_lon"])
        df["distance_km_scaled"] = df["distance_km"] * 2
        df["distance_bucket"] = pd.cut(df["distance_km"], bins=[-1, 1, 3, 10, 100], labels=[0, 1, 2, 3]).astype("category")

        past_services = df.groupby("user_id")["service_id"].apply(set).to_dict()
        df["service_match"] = df.apply(lambda r: int(r["service_id"] in past_services.get(r["user_id"], set())), axis=1)

        # ---------------- REALISTIC RELEVANCE ----------------
        continuous_relevance = np.clip(5.0 - (df["distance_km"] / 10.0), 0.0, 5.0)
        rng = np.random.default_rng(seed=42)
        noise = rng.normal(loc=0.0, scale=0.6, size=len(df))  # realistic noise
        continuous_relevance = np.clip(continuous_relevance + noise, 0.0, 5.0)
        df["relevance_int"] = continuous_relevance.round().astype(int)
        df["relevance_continuous"] = continuous_relevance

        FEATURE_COLS = [
            "worker_lat", "worker_lon", "charge", "num_bookings",
            "distance_km_scaled", "distance_bucket", "service_match",
            "worker_avg_rating", "worker_total_bookings", "user_avg_rating"
        ]

        # ---------------- TRAIN/VALID SPLIT ----------------
        if df["user_id"].nunique() > 1:
            gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            train_idx, val_idx = next(gss.split(df, groups=df["user_id"]))
            train_df, val_df = df.iloc[train_idx].reset_index(drop=True), df.iloc[val_idx].reset_index(drop=True)
            train_groups = train_df.groupby("user_id").size().tolist()
            val_groups = val_df.groupby("user_id").size().tolist()
        else:
            train_df, val_df = df.copy(), df.copy()
            train_groups = [len(df)]
            val_groups = [len(df)]

        categorical_features = ["distance_bucket"]

        lgb_train = lgb.Dataset(train_df[FEATURE_COLS], label=train_df["relevance_int"], group=train_groups,
                                categorical_feature=categorical_features)
        lgb_val = lgb.Dataset(val_df[FEATURE_COLS], label=val_df["relevance_int"], group=val_groups,
                              reference=lgb_train, categorical_feature=categorical_features)

        params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [1, 3, 5],
            "boosting_type": "gbdt",
            "learning_rate": 0.01,
            "num_leaves": 5,
            "max_depth": 3,
            "min_data_in_leaf": 1000,
            "feature_fraction": 0.5,
            "bagging_fraction": 0.5,
            "bagging_freq": 5,
            "min_gain_to_split": 0.1,
            "verbose": -1,
            "label_gain": [0, 1, 2, 3, 4, 5],
            "seed": 42,
        }

        # ---------------- TRAIN MODEL ----------------
        evals_result = {}
        model = lgb.train(
            params,
            lgb_train,
            num_boost_round=1000,
            valid_sets=[lgb_train, lgb_val],
            valid_names=["train", "valid"],
            callbacks=[lgb.early_stopping(stopping_rounds=200),
                       lgb.log_evaluation(period=200),
                       lgb.record_evaluation(evals_result)],
        )

        val_df["pred"] = model.predict(val_df[FEATURE_COLS], num_iteration=model.best_iteration)

        # ---------------- REALISTIC MRR/MAP ----------------
        RELEVANCE_THRESHOLD = 3

        def mean_reciprocal_rank(df_):
            ranks = []
            for _, g in df_.groupby("user_id"):
                g_sorted = g.sort_values("pred", ascending=False)
                rel = g_sorted["relevance_int"].values >= RELEVANCE_THRESHOLD
                pos = np.where(rel)[0]
                if len(pos) > 0:
                    ranks.append(1.0 / (pos[0] + 1))
            return np.mean(ranks) if ranks else 0.0

        def mean_average_precision(df_):
            aps = []
            for _, g in df_.groupby("user_id"):
                g_sorted = g.sort_values("pred", ascending=False)
                rel = g_sorted["relevance_int"].values >= RELEVANCE_THRESHOLD
                if rel.sum() == 0:
                    continue
                precisions = [(rel[:k+1].sum() / (k+1)) for k in range(len(g_sorted)) if rel[k]]
                aps.append(np.mean(precisions))
            return np.mean(aps) if aps else 0.0

        mrr = mean_reciprocal_rank(val_df)
        map_score = mean_average_precision(val_df)
        print(f"✅ Validation MRR: {mrr:.4f}")
        print(f"✅ Validation MAP: {map_score:.4f}")

        # ---------------- SAVE MODEL ----------------
        os.makedirs("ml_models", exist_ok=True)
        model.save_model("ml_models/lgb_ranker.txt")
        joblib.dump(FEATURE_COLS, "ml_models/feature_cols.pkl")

        # ---------------- PLOT NDCG ----------------
        ndcg1 = [x * 100 for x in evals_result["valid"]["ndcg@1"]]
        ndcg3 = [x * 100 for x in evals_result["valid"]["ndcg@3"]]
        ndcg5 = [x * 100 for x in evals_result["valid"]["ndcg@5"]]

        plt.figure(figsize=(10, 6))
        plt.plot(ndcg1, label="NDCG@1")
        plt.plot(ndcg3, label="NDCG@3")
        plt.plot(ndcg5, label="NDCG@5")
        plt.xlabel("Iteration")
        plt.ylabel("NDCG (%)")
        plt.title("Validation NDCG During Training")
        plt.legend()
        plt.grid(True)
        plt.savefig("ml_models/ndcg_plot.png", dpi=300, bbox_inches="tight")
        plt.close()
