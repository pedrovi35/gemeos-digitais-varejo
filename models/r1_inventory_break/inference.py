"""R1 inference."""
from models.r1_inventory_break.feature_engineering import FeatureEngineering
from models.r1_inventory_break.predictor       import Predictor
from models.r1_inventory_break.shap_explainer  import ShapExplainer
from models.shared.base_inference              import BaseInference


class Inference(BaseInference):
    rupture_code = "R1"
    output_col   = "inventory_break_risk"
    entity_cols  = ("store_id", "sku_id")

    def __init__(self) -> None:
        super().__init__()
        self.feature_engineer = FeatureEngineering()
        self.predictor        = Predictor()
        self.explainer        = ShapExplainer()
