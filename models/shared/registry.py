"""Rupture model catalog — single source of truth."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuptureCode(str, Enum):
    R1 = "R1"   # Quebra de Inventário
    R2 = "R2"   # Venda Acima da Média
    R3 = "R3"   # Produto Ofertado Sem Sinalização
    R4 = "R4"   # Tempo de Compra e Entrega
    R5 = "R5"   # Fornecedores Restrição Faturamento


@dataclass(frozen=True)
class RuptureSpec:
    code:     RuptureCode
    name:     str
    long_name:str
    output:   str          # column name returned by the predictor
    package:  str          # python package path
    entity:   str          # 'store_sku', 'supplier', 'composite'


MODEL_CATALOG: dict[RuptureCode, RuptureSpec] = {
    RuptureCode.R1: RuptureSpec(
        code=RuptureCode.R1, name="R1 · Quebra de Inventário",
        long_name="Inconsistência entre estoque sistêmico e real",
        output="inventory_break_risk",
        package="models.r1_inventory_break", entity="store_sku",
    ),
    RuptureCode.R2: RuptureSpec(
        code=RuptureCode.R2, name="R2 · Venda Acima da Média",
        long_name="Aumento anormal de demanda sobre baseline rolante",
        output="above_average_sales_risk",
        package="models.r2_above_average_sales", entity="store_sku",
    ),
    RuptureCode.R3: RuptureSpec(
        code=RuptureCode.R3, name="R3 · Promoção Não Sinalizada",
        long_name="Uplift de venda sem registro de promoção",
        output="unsignaled_promotion_risk",
        package="models.r3_unsignaled_promotion", entity="store_sku",
    ),
    RuptureCode.R4: RuptureSpec(
        code=RuptureCode.R4, name="R4 · Lead Time de Reposição",
        long_name="Risco operacional por tempo de compra/entrega",
        output="purchase_delivery_risk",
        package="models.r4_purchase_delivery_time", entity="store_sku",
    ),
    RuptureCode.R5: RuptureSpec(
        code=RuptureCode.R5, name="R5 · Restrição de Faturamento",
        long_name="Bloqueio comercial / restrição financeira de fornecedor",
        output="supplier_billing_restriction_risk",
        package="models.r5_supplier_billing_restriction", entity="supplier",
    ),
}


def get_model(code: RuptureCode | str):
    """Return the inference object for a given rupture code."""
    code = RuptureCode(code) if not isinstance(code, RuptureCode) else code
    spec = MODEL_CATALOG[code]
    mod = __import__(f"{spec.package}.inference", fromlist=["Inference"])
    return mod.Inference()
