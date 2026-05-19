"""R3 · Promotion Intelligence."""
import streamlit as st
st.set_page_config(page_title="R3 · Promotion Intel", page_icon="assets/favicon.svg", layout="wide")
from components.rupture_center import render_rupture_center
from models.shared.registry import RuptureCode
render_rupture_center(RuptureCode.R3, eyebrow="R3 · PROMOTION INTEL",
    title="Promotion Intelligence", subtitle="Ofertas sem sinalização ao abastecimento")
