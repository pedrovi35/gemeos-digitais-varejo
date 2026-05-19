"""R5 inference."""
from models.r5_supplier_billing_restriction.feature_engineering import FeatureEngineering
from models.r5_supplier_billing_restriction.predictor import Predictor
from models.r5_supplier_billing_restriction.shap_explainer import ShapExplainer
from models.shared.base_inference import BaseInference


class Inference(BaseInference):
    rupture_code = "R5"
    output_col   = "supplier_billing_restriction_risk"
    entity_cols  = ("supplier_id",)

    def __init__(self) -> None:
        super().__init__()
        self.feature_engineer = FeatureEngineering()
        self.predictor        = Predictor()
        self.explainer        = ShapExplainer()
