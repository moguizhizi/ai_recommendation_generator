from pathlib import Path
from typing import Dict, Any

from utils.logger import get_logger
from models.lightgbm_model import LightGBMModel
from models.mlp_model import MLPModel
from models.xgboost_model import XGBoostModel

logger = get_logger(__name__)


class ModelManager:

    def __init__(self):
        self.models: Dict[str, object] = {}

    def load_models(self, config: Dict[str, Any]) -> None:
        """
        根据 config.yaml 加载所有分数预测模型
        """

        score_cfg = config.get("score_prediction")

        if not score_cfg:
            logger.info("No score_prediction config found, skip loading models")
            return

        model_type = score_cfg.get("type")

        if not model_type:
            raise ValueError("score_prediction.type not configured")

        logger.info(f"Loading score prediction models: {model_type}")

        model_cfg = score_cfg.get(model_type)

        if not model_cfg:
            raise ValueError(f"No config found for model type: {model_type}")

        checkpoints = model_cfg.get("checkpoints")

        if not checkpoints:
            raise ValueError(f"No checkpoints configured for {model_type}")

        for name, path in checkpoints.items():

            path = Path(path)

            if not path.exists():
                raise FileNotFoundError(f"Model checkpoint not found: {path}")

            logger.info(f"Loading model [{name}] from {path}")

            model = self.build_model(model_type)

            model.load(path)

            self.models[name] = model

        logger.info(f"{len(self.models)} models loaded successfully")

    def get(self, name: str):
        """
        获取指定能力的模型
        """
        if name not in self.models:
            raise KeyError(f"Model '{name}' not found")

        return self.models[name]

    @staticmethod
    def build_model(model_name, params=None):

        if model_name == "lightgbm":
            return LightGBMModel(params)

        if model_name == "xgboost":
            return XGBoostModel(params)

        if model_name == "mlp":
            return MLPModel(params)

        raise ValueError(f"Unknown model: {model_name}")
