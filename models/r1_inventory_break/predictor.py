"""R1 predictor."""
from models.r1_inventory_break.feature_engineering import FEATURE_COLS
from models.shared.base_predictor import BasePredictor


class Predictor(BasePredictor):
    def __init__(self) -> None:
        super().__init__(rupture_code="R1", feature_cols=FEATURE_COLS)
