import lightgbm as lgb
from .base_model import BaseModel


class LightGBMModel(BaseModel):

    def __init__(self, params=None):
        self.params = params or {}
        self.model = lgb.LGBMRegressor(**self.params)

    def fit(self, X, y):
        self.model.fit(X, y)

    def predict(self, X):
        return self.model.predict(X)

    def save(self, path):
        import joblib

        joblib.dump(self.model, path)

    def load(self, path):
        import joblib

        self.model = joblib.load(path)
