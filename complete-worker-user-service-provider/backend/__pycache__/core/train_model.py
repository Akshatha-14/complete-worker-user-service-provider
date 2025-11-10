import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sqlalchemy import create_engine
import joblib
from sklearn.model_selection import GroupShuffleSplit
from django.core.management.base import BaseCommand
from django.conf import settings
import matplotlib.pyplot as plt

class Command(BaseCommand):
    help = "Train LightGBM ranking model, calculate MRR/MAP, save model, features, NDCG plot, top-5 recommendations"

    def handle(self, *args, **kwargs):
        # --- Database connection ---
        db_settings = settings.DATABASES['default']
        conn_str = f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"
        engine = create_engine(conn_str)

        # --- Haversine distance ---
        def haversine_vector(lat1, lon1, lat2, lon2):
            R = 6371.0
            dlat = np.radians(lat2 - lat1)
            dlon = np.radians(lon2 - lon1)
            a = np.sin(dlat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
            return R * c

        # --- Load user-worker data ---
        df = pd.read_sql("""
        SELECT 
            user_id,
            worker_id,
            service_id,
            ST_Y(worker_location::geometry) AS worker_lat,
            ST_X(worker_location::geometry) AS worker_lon,
            charge,
            num_bookings,
            total_rating
        FROM user_worker_data;
        """, engine)

        df.fillna({'num_bookings': 0, 'total_rating': 0.0, 'charge': 0.0}, inplace=True)
        df['num_bookings'] = df['num_bookings'].astype(int)

        # --- Load user locations ---
        user_locs = pd.read_sql("""
        SELECT id, ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon
        FROM core_authenticateduser
        WHERE location IS NOT NULL;
        """, engine)
        df = df.merge(user_locs.set_index('id'), left_on='user_id', right_index=True, how='left')
        df.rename(columns={'lat': 'lat_user', 'lon': 'lon_user'}, inplace=True)

        # --- Worker stats ---
        worker_stats = df.groupby('worker_id').agg(
            worker_avg_rating=('total_rating', 'mean'),
            worker_total_bookings=('num_bookings', 'sum')
        ).reset_index()
        df = df.merge(worker_stats, on='worker_id', how='left')

        # --- User stats ---
        user_stats = df.groupby('user_id').agg(user_avg_rating=('total_rating', 'mean')).reset_index()
        df = df.merge(user_stats, on='user_id', how='left')

        # --- Distance features ---
        df['distance_km'] = haversine_vector(df['lat_user'], df['lon_user'], df['worker_lat'], df['worker_lon'])
        df['distance_bucket'] = pd.cut(df['distance_km'], bins=[-1,1,3,10,100], labels=[0,1,2,3])
        df['distance_bucket'] = df['distance_bucket'].astype('category')

        # --- Service match ---
        past_services = df.groupby('user_id')['service_id'].apply(set).to_dict()
        df['service_match'] = df.apply(lambda r: int(r['service_id'] in past_services.get(r['user_id'], set())), axis=1)

        # --- User-level rating normalization ---
        df['rating_norm'] = df.groupby('user_id')['total_rating'].transform(
            lambda x: (x - x.min()) / (x.max() - x.min() + 1e-6)
        )

        # --- Relevance and sample weights ---
        df['relevant'] = (df['total_rating'] >= 3).astype(int)
        df['weight'] = df['relevant'].apply(lambda x: 5 if x==1 else 1)

        FEATURE_COLS = [
            "worker_lat", "worker_lon", "charge", "num_bookings",
            "distance_km", "distance_bucket", "service_match",
            "worker_avg_rating", "worker_total_bookings", "user_avg_rating"
        ]

        print(f"Dataset size: {len(df)}, Unique users: {df['user_id'].nunique()}")

        # --- Train/validation split ---
        if df['user_id'].nunique() > 1:
            gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            train_idx, val_idx = next(gss.split(df, groups=df['user_id']))
            train_df, val_df = df.iloc[train_idx].reset_index(drop=True), df.iloc[val_idx].reset_index(drop=True)
            train_groups = train_df.groupby('user_id').size().tolist()
            val_groups = val_df.groupby('user_id').size().tolist()
        else:
            train_df, val_df = df.copy(), df.copy()
            train_groups = [len(train_df)]
            val_groups = [len(val_df)]

        categorical_features = ['distance_bucket']

        lgb_train = lgb.Dataset(
            train_df[FEATURE_COLS],
            label=train_df['rating_norm'],
            group=train_groups,
            weight=train_df['weight'],
            categorical_feature=categorical_features
        )
        lgb_val = lgb.Dataset(
            val_df[FEATURE_COLS],
            label=val_df['rating_norm'],
            group=val_groups,
            reference=lgb_train,
            categorical_feature=categorical_features
        )

        params = {
            'objective': 'lambdarank',
            'metric': 'map',
            'boosting_type': 'gbdt',
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': 6,
            'min_data_in_leaf': 50,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'lambda_l1': 1.0,
            'lambda_l2': 1.0,
            'min_gain_to_split': 0.01,
            'verbose': -1
        }

        evals_result = {}
        model = lgb.train(
            params,
            lgb_train,
            num_boost_round=2000,
            valid_sets=[lgb_train, lgb_val],
            valid_names=['train','valid'],
            callbacks=[lgb.early_stopping(stopping_rounds=50),
                       lgb.log_evaluation(period=50),
                       lgb.record_evaluation(evals_result)]
        )

        print(f"Best iteration: {model.best_iteration}")

        # --- Predictions ---
        val_df['pred'] = np.clip(model.predict(val_df[FEATURE_COLS], num_iteration=model.best_iteration), 0, 1)

        # --- Optional rerank by worker rating ---
        val_df['pred_rerank'] = val_df['pred'] + 0.1 * val_df['worker_avg_rating'].fillna(0)

        # --- Compute MRR & MAP ---
        mrr, map_score = 0.0, 0.0
        for user_id, group in val_df.groupby('user_id'):
            group_sorted = group.sort_values('pred_rerank', ascending=False)
            rel_idx = group_sorted.index[group_sorted['relevant']==1].tolist()
            if rel_idx:
                mrr += 1 / (rel_idx[0] - group_sorted.index[0] + 1)
                hits, ap = 0, 0
                for i, idx in enumerate(rel_idx, start=1):
                    hits += 1
                    ap += hits / (idx - group_sorted.index[0] + 1)
                map_score += ap / len(rel_idx)
        user_count = val_df['user_id'].nunique()
        mrr /= user_count
        map_score /= user_count
        print(f"✅ Validation MRR: {mrr:.4f}, MAP: {map_score:.4f}")

        # --- Save model & features ---
        os.makedirs("ml_models", exist_ok=True)
        model.save_model("ml_models/lgb_ranker.txt")
        joblib.dump(FEATURE_COLS, "ml_models/feature_cols.pkl")

        # --- Save top-5 per user ---
        os.makedirs("ml_models/top_recommendations", exist_ok=True)
        top5 = val_df.groupby('user_id').apply(lambda g: g.nlargest(5,'pred_rerank')).reset_index(drop=True)
        top5.to_csv("ml_models/top_recommendations/top5_per_user.csv", index=False)
        print("✅ Top-5 recommendations saved!")

        # --- NDCG plot ---
        plt.figure(figsize=(10,6))
        if 'ndcg@1' in evals_result['valid']:
            plt.plot([x*100 for x in evals_result['valid']['ndcg@1']], label='NDCG@1', color='navy')
            plt.plot([x*100 for x in evals_result['valid']['ndcg@3']], label='NDCG@3', color='royalblue')
            plt.plot([x*100 for x in evals_result['valid']['ndcg@5']], label='NDCG@5', color='deepskyblue')
            plt.xlabel('Iteration')
            plt.ylabel('NDCG (%)')
            plt.title('Validation NDCG during training')
            plt.grid(True)
            plt.legend()
            plt.savefig("ml_models/ndcg_plot.png", dpi=300, bbox_inches='tight')
            plt.close()
            print("✅ NDCG plot saved")

        self.stdout.write(self.style.SUCCESS(
            "✅ Model trained, MRR/MAP calculated, NDCG plotted, top-5 recommendations saved!"
        ))
