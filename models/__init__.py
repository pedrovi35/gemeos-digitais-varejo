"""
Predictive Operational Intelligence Layer
==========================================

Five rupture-risk models:

   R1 · Quebra de Inventário              (inventory_break)
   R2 · Venda Acima da Média              (above_average_sales)
   R3 · Produto Ofertado Sem Sinalização  (unsignaled_promotion)
   R4 · Tempo de Compra e Entrega         (purchase_delivery_time)
   R5 · Fornecedores Restrição Faturamento (supplier_billing_restriction)

Each model package exposes a uniform interface through shared base classes:

    from models.r1_inventory_break.inference import R1Inference
    scores = R1Inference().score_batch()          # → DataFrame
"""
from models.shared.registry import MODEL_CATALOG, RuptureCode, get_model

__all__ = ["MODEL_CATALOG", "RuptureCode", "get_model"]
