"""R2 trainer."""
from models.r2_above_average_sales.feature_engineering import FEATURE_COLS
from models.shared.base_trainer import BaseTrainer


class Trainer(BaseTrainer):
    def __init__(self) -> None:
        super().__init__(rupture_code="R2", feature_cols=FEATURE_COLS, target_col="target")
