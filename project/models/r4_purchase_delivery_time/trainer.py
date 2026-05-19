"""R4 trainer."""
from models.r4_purchase_delivery_time.feature_engineering import FEATURE_COLS
from models.shared.base_trainer import BaseTrainer


class Trainer(BaseTrainer):
    def __init__(self) -> None:
        super().__init__(rupture_code="R4", feature_cols=FEATURE_COLS, target_col="target")
