"""R3 SHAP explainer."""
from models.r3_unsignaled_promotion.feature_engineering import FEATURE_COLS
from models.shared.base_shap_explainer import BaseShapExplainer


class ShapExplainer(BaseShapExplainer):
    def __init__(self) -> None:
        super().__init__(rupture_code="R3", feature_cols=FEATURE_COLS)
