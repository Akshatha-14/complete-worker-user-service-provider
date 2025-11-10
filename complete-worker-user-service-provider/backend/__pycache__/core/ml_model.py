import lightgbm as lgb
import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../ml_models/lgb_ranker.txt")
FEATURES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../ml_models/feature_cols.pkl")

recommendation_model = lgb.Booster(model_file=MODEL_PATH)
feature_cols = joblib.load(FEATURES_PATH)
