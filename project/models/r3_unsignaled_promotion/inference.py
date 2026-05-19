"""R3 inference."""
from models.r3_unsignaled_promotion.feature_engineering import FeatureEngineering
from models.r3_unsignaled_promotion.predictor import Predictor
from models.r3_unsignaled_promotion.shap_explainer import ShapExplainer
from models.shared.base_inference import BaseInference


class Inference(BaseInference):
    rupture_code = "R3"
    output_col   = "unsignaled_promotion_risk"
    entity_cols  = ("store_id", "sku_id")

    def __init__(self) -> None:
        super().__init__()
        self.feature_engineer = FeatureEngineering()
        self.predictor        = Predictor()
        self.explainer        = ShapExplainer()
