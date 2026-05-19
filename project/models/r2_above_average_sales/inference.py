"""R2 inference."""
from models.r2_above_average_sales.feature_engineering import FeatureEngineering
from models.r2_above_average_sales.predictor import Predictor
from models.r2_above_average_sales.shap_explainer import ShapExplainer
from models.shared.base_inference import BaseInference


class Inference(BaseInference):
    rupture_code = "R2"
    output_col   = "above_average_sales_risk"
    entity_cols  = ("store_id", "sku_id")

    def __init__(self) -> None:
        super().__init__()
        self.feature_engineer = FeatureEngineering()
        self.predictor        = Predictor()
        self.explainer        = ShapExplainer()
