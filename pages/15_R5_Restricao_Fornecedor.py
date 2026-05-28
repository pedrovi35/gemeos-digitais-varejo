"""R5 · Supplier Billing Restriction Center."""
import streamlit as st
st.set_page_config(page_title="R5 · Restrição de Fornecedor", page_icon="assets/favicon.svg", layout="wide")
from components.rupture_center import render_rupture_center
from models.shared.registry import RuptureCode
render_rupture_center(RuptureCode.R5, eyebrow="R5 · RESTRIÇÃO DE FORNECEDOR",
    title="Supplier Restriction Center", subtitle="Bloqueios comerciais e restrição de faturamento")
