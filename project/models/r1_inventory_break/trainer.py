"""R1 trainer."""
from models.r1_inventory_break.feature_engineering import FEATURE_COLS
from models.shared.base_trainer import BaseTrainer


class Trainer(BaseTrainer):
    def __init__(self) -> None:
        super().__init__(rupture_code="R1", feature_cols=FEATURE_COLS, target_col="target")
