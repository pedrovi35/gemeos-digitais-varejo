"""R4 predictor."""
from models.r4_purchase_delivery_time.feature_engineering import FEATURE_COLS
from models.shared.base_predictor import BasePredictor


class Predictor(BasePredictor):
    def __init__(self) -> None:
        super().__init__(rupture_code="R4", feature_cols=FEATURE_COLS)
