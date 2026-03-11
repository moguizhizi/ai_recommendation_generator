import joblib
import xgboost as xgb
import numpy as np

from .base_model import BaseModel


class XGBoostModel(BaseModel):
    """
    XGBoost 回归模型

    继承 BaseModel，统一 fit / predict / save / load 接口
    """

    def __init__(self, params: dict | None = None):

        default_params = {
            "n_estimators": 500,
            "learning_rate": 0.05,
            "max_depth": 6,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "objective": "reg:squarederror",
            "n_jobs": -1,
            "random_state": 42,
        }

        if params:
            default_params.update(params)

        self.params = default_params
        self.model = xgb.XGBRegressor(**self.params)

    # --------------------------------------------------
    # 训练
    # --------------------------------------------------

    def fit(self, X, y):
        """
        训练模型
        """

        self.model.fit(X, y)

        return self

    # --------------------------------------------------
    # 预测
    # --------------------------------------------------

    def predict(self, X) -> np.ndarray:
        """
        预测
        """

        return self.model.predict(X)

    # --------------------------------------------------
    # 保存模型
    # --------------------------------------------------

    def save(self, path):
        """
        保存模型
        """

        joblib.dump(self.model, path)

    # --------------------------------------------------
    # 加载模型
    # --------------------------------------------------

    def load(self, path):
        """
        加载模型
        """

        self.model = joblib.load(path)

        return self
