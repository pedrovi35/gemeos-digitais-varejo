"""R5 SHAP explainer."""
from models.r5_supplier_billing_restriction.feature_engineering import FEATURE_COLS
from models.shared.base_shap_explainer import BaseShapExplainer


class ShapExplainer(BaseShapExplainer):
    def __init__(self) -> None:
        super().__init__(rupture_code="R5", feature_cols=FEATURE_COLS)
