"""R3 predictor."""
from models.r3_unsignaled_promotion.feature_engineering import FEATURE_COLS
from models.shared.base_predictor import BasePredictor


class Predictor(BasePredictor):
    def __init__(self) -> None:
        super().__init__(rupture_code="R3", feature_cols=FEATURE_COLS)
