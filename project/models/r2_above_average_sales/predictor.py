"""R2 predictor."""
from models.r2_above_average_sales.feature_engineering import FEATURE_COLS
from models.shared.base_predictor import BasePredictor


class Predictor(BasePredictor):
    def __init__(self) -> None:
        super().__init__(rupture_code="R2", feature_cols=FEATURE_COLS)
