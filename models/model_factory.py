from .lightgbm_model import LightGBMModel
from .xgboost_model import XGBoostModel
from .mlp_model import MLPModel


def build_model(model_name, params=None):

    if model_name == "lightgbm":
        return LightGBMModel(params)

    if model_name == "xgboost":
        return XGBoostModel(params)

    if model_name == "mlp":
        return MLPModel(params)

    raise ValueError(f"Unknown model: {model_name}")
