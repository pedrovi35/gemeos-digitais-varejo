"""R5 predictor."""
from models.r5_supplier_billing_restriction.feature_engineering import FEATURE_COLS
from models.shared.base_predictor import BasePredictor


class Predictor(BasePredictor):
    def __init__(self) -> None:
        super().__init__(rupture_code="R5", feature_cols=FEATURE_COLS)
