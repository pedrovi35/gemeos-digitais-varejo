"""R1 · Quebra de Inventário Center."""
import streamlit as st
st.set_page_config(page_title="R1 · Inventory Break", page_icon="assets/favicon.svg", layout="wide")
from components.rupture_center import render_rupture_center
from models.shared.registry import RuptureCode
render_rupture_center(RuptureCode.R1, eyebrow="R1 · INVENTORY BREAK",
    title="Inventory Break Center", subtitle="Inconsistência estoque sistêmico vs real")
