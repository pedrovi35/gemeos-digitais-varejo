"""R4 · Lead Time Risk Center."""
import streamlit as st
st.set_page_config(page_title="R4 · Lead Time Risk", page_icon="assets/favicon.svg", layout="wide")
from components.rupture_center import render_rupture_center
from models.shared.registry import RuptureCode
render_rupture_center(RuptureCode.R4, eyebrow="R4 · LEAD TIME",
    title="Lead Time Risk Center", subtitle="Risco operacional de compra e entrega")
