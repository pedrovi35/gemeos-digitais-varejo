"""R4 inference."""
from models.r4_purchase_delivery_time.feature_engineering import FeatureEngineering
from models.r4_purchase_delivery_time.predictor import Predictor
from models.r4_purchase_delivery_time.shap_explainer import ShapExplainer
from models.shared.base_inference import BaseInference


class Inference(BaseInference):
    rupture_code = "R4"
    output_col   = "purchase_delivery_risk"
    entity_cols  = ("store_id", "sku_id")

    def __init__(self) -> None:
        super().__init__()
        self.feature_engineer = FeatureEngineering()
        self.predictor        = Predictor()
        self.explainer        = ShapExplainer()
