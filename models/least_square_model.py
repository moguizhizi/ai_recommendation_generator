import numpy as np
import joblib

from .base_model import BaseModel


class LeastSquareModel(BaseModel):
    """
    最小二乘线性回归模型
    """

    def __init__(self):
        self.coef_ = None
        self.intercept_ = None

    # --------------------------------------------------
    # 训练
    # --------------------------------------------------

    def fit(self, X, y):

        X = np.asarray(X)
        y = np.asarray(y)

        # 添加 bias 列
        ones = np.ones((X.shape[0], 1))
        X_aug = np.hstack([ones, X])

        # 最小二乘解
        coef = np.linalg.pinv(X_aug) @ y

        self.intercept_ = coef[0]
        self.coef_ = coef[1:]

        return self

    # --------------------------------------------------
    # 预测
    # --------------------------------------------------

    def predict(self, X):

        if self.coef_ is None:
            raise RuntimeError("Model not fitted yet.")

        X = np.asarray(X)

        return X @ self.coef_ + self.intercept_

    # --------------------------------------------------
    # 保存模型
    # --------------------------------------------------

    def save(self, path):

        joblib.dump(
            {
                "coef": self.coef_,
                "intercept": self.intercept_,
            },
            path,
        )

    # --------------------------------------------------
    # 加载模型
    # --------------------------------------------------

    def load(self, path):

        data = joblib.load(path)

        self.coef_ = data["coef"]
        self.intercept_ = data["intercept"]

        return self