"""R3 trainer."""
from models.r3_unsignaled_promotion.feature_engineering import FEATURE_COLS
from models.shared.base_trainer import BaseTrainer


class Trainer(BaseTrainer):
    def __init__(self) -> None:
        super().__init__(rupture_code="R3", feature_cols=FEATURE_COLS, target_col="target")
