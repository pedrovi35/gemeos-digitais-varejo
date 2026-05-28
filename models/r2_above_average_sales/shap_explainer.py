"""R2 SHAP explainer."""
from models.r2_above_average_sales.feature_engineering import FEATURE_COLS
from models.shared.base_shap_explainer import BaseShapExplainer


class ShapExplainer(BaseShapExplainer):
    def __init__(self) -> None:
        super().__init__(rupture_code="R2", feature_cols=FEATURE_COLS)
