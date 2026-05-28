"""R2 · Demand Spike Observatory."""
import streamlit as st
st.set_page_config(page_title="R2 · Pico de Demanda", page_icon="assets/favicon.svg", layout="wide")
from components.rupture_center import render_rupture_center
from models.shared.registry import RuptureCode
render_rupture_center(RuptureCode.R2, eyebrow="R2 · PICO DE DEMANDA",
    title="Demand Spike Observatory", subtitle="Detecção de picos anormais de demanda")
