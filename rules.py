"""
Regras do SIMCAR-MT codificadas.
Sem IA — lógica pura baseada na legislação vigente.
"""

from __future__ import annotations


# ── Art. 61-A — Faixa de recuperação de APP ───────────────────────────────────

def faixa_recuperacao_appd(modulos_fiscais: float,
                            largura_rio_m: float | None = None) -> int:
    """
    Retorna a faixa mínima de recuperação em metros conforme o Art. 61-A
    da Lei 12.651/2012 e LC MT 592/2017.
    """
    if modulos_fiscais <= 1:
        return 5
    if modulos_fiscais <= 2:
        return 8
    if modulos_fiscais <= 4:
        return 15
    # Acima de 4 MF: faixa integral baseada na largura do curso d'água
    if largura_rio_m is None:
        return 30
    if largura_rio_m <= 10:
        return 30
    if largura_rio_m <= 50:
        return 50
    if largura_rio_m <= 200:
        return 100
    if largura_rio_m <= 600:
        return 200
    return 500


def metodo_appd(marco_temporal: str) -> str:
    if "pós" in marco_temporal.lower():
        return "Plantio de Espécies Nativas"
    return "Condução de Regeneração Natural Assistida"


# ── Art. 66 — Alternativa ARLD ────────────────────────────────────────────────

ALTERNATIVAS_ARLD = [
    "recomposição",
    "regeneração natural",
    "compensação via CRA",
]


def prazo_arld_anos(area_ha: float) -> int:
    """Prazo máximo legal: 20 anos (Art. 66, Lei 12.651/2012)."""
    return 20


# ── Cronograma físico-financeiro ──────────────────────────────────────────────

def gerar_cronograma(area_appd_ha: float, area_arld_ha: float,
                     prazo_arld: int = 20) -> list[dict]:
    """
    Gera o cronograma semestral respeitando:
    - Plantio APPD no 1º ano (período chuvoso out-mar)
    - ARLD: 1/10 da área a cada 2 anos
    - Monitoramento semestral no 1º ano, anual a partir do 2º
    """
    cronograma = []

    # APPD — ano 1, semestre 1
    if area_appd_ha > 0:
        cronograma.append({
            "ano": 1, "semestre": 1, "periodo": "out-mar",
            "atividade": "Isolamento + preparo de solo + plantio APPD",
            "area_ha": round(area_appd_ha, 4),
            "percentual_acumulado": 0,
            "entrega_relatorio": False,
        })

    # Monitoramento 1º ano semestre 2
    cronograma.append({
        "ano": 1, "semestre": 2, "periodo": "abr-set",
        "atividade": "Monitoramento + replantio de falhas",
        "area_ha": 0,
        "percentual_acumulado": 0,
        "entrega_relatorio": True,
    })

    # ARLD — 1/10 a cada 2 anos
    if area_arld_ha > 0:
        etapas = prazo_arld // 2
        area_etapa = round(area_arld_ha / etapas, 4)
        acumulado_pct = 0

        for i, ano_inicio in enumerate(range(2, prazo_arld + 1, 2), start=1):
            acumulado_pct = round((i / etapas) * 100)
            cronograma.append({
                "ano": ano_inicio, "semestre": 1, "periodo": "out-mar",
                "atividade": f"Plantio ARLD — etapa {i}/{etapas} (10%)",
                "area_ha": area_etapa,
                "percentual_acumulado": acumulado_pct,
                "entrega_relatorio": False,
            })
            cronograma.append({
                "ano": ano_inicio, "semestre": 2, "periodo": "abr-set",
                "atividade": "Monitoramento + relatório técnico SEMA-MT",
                "area_ha": 0,
                "percentual_acumulado": acumulado_pct,
                "entrega_relatorio": True,
            })

    return cronograma


# ── Orçamento ─────────────────────────────────────────────────────────────────

# Preços de referência IMEA-MT / SEAF-MT (atualizar anualmente)
PRECO_MUDA_R = 8.50          # R$/muda
PRECO_INSUMOS_R = 650.00     # R$/ha (calcário, adubo cova)
PRECO_CERCAMENTO_R = 12.00   # R$/m linear (mourão + arame)
PRECO_HORA_MAQUINA_R = 180.00  # R$/hora
HORAS_MAQUINA_POR_HA = 2.0
PRECO_MONITORAMENTO_R = 800.00  # R$/ha/ano


def calcular_mudas(area_ha: float, espacamento_m: tuple[float, float] = (3.0, 2.0)) -> int:
    mudas_por_ha = 10_000 / (espacamento_m[0] * espacamento_m[1])
    return int(area_ha * mudas_por_ha)


def calcular_perimetro_estimado(area_ha: float) -> float:
    """Estimativa do perímetro de um polígono quadrado equivalente (m)."""
    lado = (area_ha * 10_000) ** 0.5
    return round(lado * 4, 1)


def calcular_orcamento(area_appd_ha: float, area_arld_ha: float,
                       area_aurd_ha: float = 0,
                       anos_monitoramento: int = 5) -> dict:
    area_plantio = area_appd_ha + area_arld_ha + area_aurd_ha
    mudas = calcular_mudas(area_plantio)
    perimetro = calcular_perimetro_estimado(area_plantio)

    custo_mudas        = round(mudas * PRECO_MUDA_R, 2)
    custo_insumos      = round(area_plantio * PRECO_INSUMOS_R, 2)
    custo_cercamento   = round(perimetro * PRECO_CERCAMENTO_R, 2)
    custo_maquina      = round(area_plantio * HORAS_MAQUINA_POR_HA * PRECO_HORA_MAQUINA_R, 2)
    custo_monitoramento = round(area_plantio * PRECO_MONITORAMENTO_R * anos_monitoramento, 2)
    total              = round(custo_mudas + custo_insumos + custo_cercamento +
                               custo_maquina + custo_monitoramento, 2)

    return {
        "area_plantio_ha":          area_plantio,
        "mudas_total":              mudas,
        "espacamento":              "3m x 2m",
        "custo_mudas_R$":           custo_mudas,
        "custo_insumos_solo_R$":    custo_insumos,
        "custo_cercamento_R$":      custo_cercamento,
        "custo_horas_maquina_R$":   custo_maquina,
        "custo_monitoramento_R$":   custo_monitoramento,
        "total_estimado_R$":        total,
        "referencia_precos":        "IMEA-MT / SEAF-MT",
    }


# ── Consórcio florístico mínimo SEMA-MT ───────────────────────────────────────

def validar_consorcio(especies: list[dict]) -> dict:
    """
    Valida se o consórcio atende ao padrão SEMA-MT:
    - >= 20 espécies/ha
    - >= 50% pioneiras
    - >= 30% zoocóricas
    """
    total = len(especies)
    pioneiras = sum(1 for e in especies
                    if str(e.get("grupo_sucessional","")).lower() == "pioneira")
    zoocoricas = sum(1 for e in especies
                     if str(e.get("dispersao","")).lower() == "zoocórica")

    pct_pioneiras  = round(pioneiras / total * 100, 1) if total else 0
    pct_zoocoricas = round(zoocoricas / total * 100, 1) if total else 0

    alertas = []
    if total < 20:
        alertas.append(f"Mínimo 20 espécies exigido (atual: {total})")
    if pct_pioneiras < 50:
        alertas.append(f"Mínimo 50% de pioneiras (atual: {pct_pioneiras}%)")
    if pct_zoocoricas < 30:
        alertas.append(f"Mínimo 30% de zoocóricas (atual: {pct_zoocoricas}%)")

    return {
        "total_especies":       total,
        "percentual_pioneiras": pct_pioneiras,
        "percentual_zoocoricas": pct_zoocoricas,
        "conforme":             len(alertas) == 0,
        "alertas":              alertas,
    }


# ── Marco temporal ────────────────────────────────────────────────────────────

def classificar_marco_temporal(anos_desmatamento: list[int]) -> str:
    if not anos_desmatamento:
        return "indefinido"
    if max(anos_desmatamento) < 2008:
        return "pré-2008"
    if min(anos_desmatamento) >= 2008:
        return "pós-2008"
    return "misto"
