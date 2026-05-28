"""Themed st.dataframe wrapper with sane defaults."""
from __future__ import annotations

import pandas as pd
import streamlit as st


def render_data_grid(df: pd.DataFrame, *, height: int = 420,
                     column_config: dict | None = None, use_container_width: bool = True) -> None:
    st.dataframe(
        df,
        height=height,
        use_container_width=use_container_width,
        column_config=column_config,
        hide_index=True,
    )
