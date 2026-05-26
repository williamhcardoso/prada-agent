"""
Pipeline principal do Agente PRADA — sem IA.
Lê SHP + PDF SIMCAR, consulta APIs, cruza dados, monta draft.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

import db
import rules
from tools import execute_tool


# ── Tipo para callbacks de progresso ─────────────────────────────────────────
ProgressFn = Callable[[str, str], None]  # (mensagem, status) → None


def _noop(msg: str, status: str = "info") -> None:
    pass


# ── Etapa 1 — Leitura de arquivos ─────────────────────────────────────────────

def extrair_shapefile(shp_path: str, diretorio: str) -> dict:
    r = execute_tool("ler_shapefile", {"caminho": shp_path}, diretorio)
    return r.get("resultado", {})


def extrair_pdf(pdf_path: str, diretorio: str) -> dict:
    r = execute_tool("ler_pdf_simcar", {"caminho": pdf_path}, diretorio)
    return r.get("resultado", {})


# ── Etapa 2 — Montagem do cadastro ────────────────────────────────────────────

def montar_cadastro(shp_dados: dict, pdf_dados: dict) -> dict:
    """
    Cruza os dados do shapefile e do PDF SIMCAR para montar o cadastro.
    O PDF é a fonte primária para dados textuais; o SHP para geometria/área.
    """
    campos_pdf = pdf_dados.get("campos_extraidos", {})

    # CPF e CNPJ separados — compatibilidade com campo legado cpf_cnpj
    cpf  = campos_pdf.get("cpf", "")
    cnpj = campos_pdf.get("cnpj", "")

    cadastro = {
        "proprietario":    campos_pdf.get("proprietario", ""),
        "cpf":             cpf,
        "cnpj":            cnpj,
        "cpf_cnpj":        cpf or cnpj,  # campo legado
        "imovel":          campos_pdf.get("imovel", ""),
        "municipio":       campos_pdf.get("municipio", ""),
        "car_estadual":    campos_pdf.get("car_estadual", ""),
        "car_federal":     campos_pdf.get("car_federal", ""),
        "area_total_ha":   shp_dados.get("area_total_ha") or
                           _parse_float(campos_pdf.get("area_total", "")),
        "modulos_fiscais": 1,
        "centroide_lat":   shp_dados.get("centroide_wgs84", {}).get("lat"),
        "centroide_lon":   shp_dados.get("centroide_wgs84", {}).get("lon"),
    }

    passivos = {
        "appd_ha": _parse_float(campos_pdf.get("area_appd", "0")),
        "aurd_ha": _parse_float(campos_pdf.get("area_aurd", "0")),
        "arld_ha": _parse_float(campos_pdf.get("area_arld", "0")),
    }

    return {**cadastro, **passivos}


def _parse_float(s: str) -> float:
    try:
        return float(str(s).replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0


# ── Etapa 3 — Consulta MapBiomas (com cache) ─────────────────────────────────

def consultar_mapbiomas(car: str, diretorio: str,
                         progress: ProgressFn = _noop) -> dict:
    cached = db.get_mapbiomas_cache(car)
    if cached:
        progress("MapBiomas: dados do cache local.", "success")
        return cached

    progress("Consultando MapBiomas Alerta...", "info")
    r = execute_tool("consultar_mapbiomas_alerta", {"car_codigo": car}, diretorio)

    if "erro" in r:
        progress(f"MapBiomas indisponível: {r['erro']}", "warning")
        return {"marco_temporal": "indefinido", "status": "indisponível",
                "alertas": [], "tipologia": ""}

    res = r.get("resultado", {})
    dados_cache = {
        "marco_temporal": res.get("marco_temporal", "indefinido"),
        "tipologia":      "",
        "alertas":        res.get("alertas", []),
        "status":         res.get("mapbiomas_status", "ok"),
    }
    db.set_mapbiomas_cache(car, dados_cache)
    progress("MapBiomas: OK.", "success")
    return dados_cache


# ── Etapa 4 — Consulta GBIF (com cache) ──────────────────────────────────────

def consultar_gbif(lat: float, lon: float, diretorio: str,
                   raio: float = 0.45,
                   progress: ProgressFn = _noop) -> list[dict]:
    cached = db.get_gbif_cache(lat, lon, raio)
    if cached:
        progress(f"GBIF: {len(cached)} espécies do cache local.", "success")
        return cached

    progress("Consultando GBIF...", "info")
    r = execute_tool("consultar_gbif", {"lat": lat, "lon": lon, "raio_graus": raio},
                     diretorio)

    if "erro" in r:
        progress(f"GBIF indisponível: {r['erro']}", "warning")
        return []

    especies = r.get("resultado", {}).get("especies", [])
    db.set_gbif_cache(lat, lon, especies, raio)
    progress(f"GBIF: {len(especies)} espécies encontradas.", "success")
    return especies


# ── Etapa 5 — Enriquecimento florístico (Flora do Brasil) ────────────────────

def enriquecer_especies(especies: list[dict], diretorio: str,
                         progress: ProgressFn = _noop) -> list[dict]:
    """
    Para cada espécie, tenta obter hábito e grupo sucessional via Flora do Brasil.
    Usa cache SQLite para evitar re-consultas.
    """
    enriquecidas = []
    total = len(especies)

    for i, sp in enumerate(especies):
        nome = sp.get("nome_cientifico", "")
        if not nome:
            enriquecidas.append(sp)
            continue

        cached = db.get_flora_cache(nome)
        if cached:
            sp = {**sp,
                  "grupo_sucessional": cached.get("grupo_sucessional", "indefinida"),
                  "dispersao":         cached.get("dispersao", "indefinida"),
                  "habito":            cached.get("habito", "")}
        else:
            r = execute_tool("consultar_flora_brasil",
                              {"nome_cientifico": nome}, diretorio)
            dados_flora = {}
            if "resultado" in r:
                dados_flora = _extrair_flora(r["resultado"])
            db.set_flora_cache(nome, dados_flora)
            sp = {**sp,
                  "grupo_sucessional": dados_flora.get("grupo_sucessional", "indefinida"),
                  "dispersao":         dados_flora.get("dispersao", "indefinida"),
                  "habito":            dados_flora.get("habito", "")}

        enriquecidas.append(sp)

        if (i + 1) % 10 == 0:
            progress(f"Flora do Brasil: {i+1}/{total} espécies processadas.", "info")

    progress(f"Flora do Brasil: enriquecimento concluído ({total} espécies).", "success")
    return enriquecidas


def _extrair_flora(dados_raw: dict) -> dict:
    """Extrai campos relevantes da resposta da Flora do Brasil."""
    texto = json.dumps(dados_raw, ensure_ascii=False).lower()

    habito = ""
    if any(t in texto for t in ["árvore", "arborea", "arbórea", "tree"]):
        habito = "árvore"
    elif any(t in texto for t in ["arbusto", "shrub", "arbustiva"]):
        habito = "arbusto"

    grupo = "indefinida"
    if any(t in texto for t in ["pioneira", "pioneer", "inicial"]):
        grupo = "pioneira"
    elif any(t in texto for t in ["clímax", "climax", "secundária tardia", "não-pioneira"]):
        grupo = "não-pioneira"

    dispersao = "indefinida"
    if any(t in texto for t in ["zoocórica", "zoochory", "zoochoric", "fruto", "semente carnosa"]):
        dispersao = "zoocórica"
    elif any(t in texto for t in ["anemocórica", "anemochory", "ala", "samaroide"]):
        dispersao = "anemocórica"
    elif any(t in texto for t in ["autocórica", "autochory", "explosão"]):
        dispersao = "autocórica"

    return {"habito": habito, "grupo_sucessional": grupo, "dispersao": dispersao}


# ── Etapa 6 — Montar draft JSON ───────────────────────────────────────────────

def montar_draft(cadastro: dict, mapbiomas: dict, especies: list[dict],
                 metodologia: dict | None = None) -> dict:
    """
    Monta o prada_draft.json completo a partir dos dados coletados e das regras.
    """
    appd_ha = cadastro.get("appd_ha", 0)
    aurd_ha = cadastro.get("aurd_ha", 0)
    arld_ha = cadastro.get("arld_ha", 0)
    mf      = cadastro.get("modulos_fiscais", 1)
    marco   = mapbiomas.get("marco_temporal", "indefinido")

    # Metodologia padrão se não fornecida
    if not metodologia:
        metodologia = {
            "aba3_appd": {
                "metodo": rules.metodo_appd(marco),
                "faixa_m": rules.faixa_recuperacao_appd(mf),
                "justificativa": f"Imóvel com {mf} MF (Art. 61-A)",
            },
            "aba4_aurd": {
                "metodo": "Manejo sustentável / Regeneração natural",
                "tipo_restricao": "a verificar",
            },
            "aba5_arld": {
                "alternativa_legal": "recomposição",
                "justificativa": "Área com condições de plantio.",
                "prazo_anos": rules.prazo_arld_anos(arld_ha),
            },
            "aba6_compensacao": None,
        }

    cronograma = rules.gerar_cronograma(appd_ha, arld_ha)
    orcamento  = rules.calcular_orcamento(appd_ha, arld_ha, aurd_ha)
    consorcio  = rules.validar_consorcio(especies)

    checklist = [
        {"documento": "PRADA assinado pelo RT",           "status": "pendente"},
        {"documento": "ART CREA/CFBio",                   "status": "pendente"},
        {"documento": "Mapas temáticos georreferenciados", "status": "pendente"},
        {"documento": "Lista florística com fichas técnicas","status": "pendente"},
        {"documento": "Orçamento IMEA-MT/SEAF-MT",         "status": "pendente"},
        {"documento": "Comprovante CRA (se aplicável)",    "status": "n/a"},
    ]

    return {
        "versao_schema": "2.0",
        "cadastro": cadastro,
        "diagnostico_geoespacial": {
            "mapbiomas_status": mapbiomas.get("status", "indefinido"),
            "marco_temporal":   marco,
            "tipologia_desmatamento": mapbiomas.get("tipologia", ""),
            "sobreposicoes_restritivas": [],
            "passivos": {
                "appd_ha": appd_ha,
                "aurd_ha": aurd_ha,
                "arld_ha": arld_ha,
            },
        },
        "abas_simcar": {
            "aba3_appd": {
                "area_ha":       appd_ha,
                "poligonos_ids": [],
                "grupos":        [{
                    "nome":             "Grupo 1",
                    "poligonos":        [],
                    "metodo":           metodologia["aba3_appd"]["metodo"],
                    "faixa_recuperacao_m": metodologia["aba3_appd"]["faixa_m"],
                    "justificativa":    metodologia["aba3_appd"]["justificativa"],
                }],
            },
            "aba4_aurd": {
                "area_ha":       aurd_ha,
                "poligonos_ids": [],
                "grupos":        [],
                "tipo_restricao": metodologia["aba4_aurd"]["tipo_restricao"],
            },
            "aba5_arld": {
                "area_ha":       arld_ha,
                "poligonos_ids": [],
                "grupos":        [],
                "alternativa_legal": metodologia["aba5_arld"]["alternativa_legal"],
                "justificativa":     metodologia["aba5_arld"]["justificativa"],
                "prazo_anos":        metodologia["aba5_arld"]["prazo_anos"],
            },
            "aba6_compensacao": metodologia.get("aba6_compensacao"),
            "aba7_prazos":       {"cronograma": cronograma},
            "aba8_documentacao": {"checklist": checklist},
        },
        "floristica": {
            "fonte_dados":          "GBIF + Flora do Brasil",
            "total_especies":       consorcio["total_especies"],
            "percentual_pioneiras": consorcio["percentual_pioneiras"],
            "percentual_zoocoricas": consorcio["percentual_zoocoricas"],
            "conforme_sema_mt":     consorcio["conforme"],
            "alertas_consorcio":    consorcio["alertas"],
            "lista_especies":       especies,
        },
        "orcamento_preliminar": orcamento,
        "pendencias":      [],
        "alertas_tecnicos": consorcio["alertas"],
    }


# ── Pipeline completo ─────────────────────────────────────────────────────────

def executar(shp_path: str, pdf_path: str, diretorio: str,
             progress: ProgressFn = _noop) -> tuple[dict, int]:
    """
    Executa o pipeline completo.
    Retorna (draft_dict, projeto_id).
    """
    progress("Lendo shapefile...", "info")
    shp = extrair_shapefile(shp_path, diretorio)

    progress("Lendo PDF SIMCAR...", "info")
    pdf = extrair_pdf(pdf_path, diretorio)

    progress("Montando cadastro...", "info")
    cadastro = montar_cadastro(shp, pdf)

    # Salva projeto no banco
    projeto_id = db.salvar_projeto({
        **cadastro,
        "shp_path": shp_path,
        "pdf_path": pdf_path,
    })
    progress(f"Projeto #{projeto_id} salvo no banco.", "success")

    # MapBiomas
    car = cadastro.get("car_estadual") or cadastro.get("car_federal", "")
    mapbiomas = {}
    if car:
        mapbiomas = consultar_mapbiomas(car, diretorio, progress)
    else:
        progress("CAR não identificado — MapBiomas ignorado.", "warning")

    # GBIF
    lat = cadastro.get("centroide_lat")
    lon = cadastro.get("centroide_lon")
    especies = []
    if lat and lon:
        especies = consultar_gbif(lat, lon, diretorio, progress=progress)
        if especies:
            progress("Enriquecendo espécies com Flora do Brasil...", "info")
            especies = enriquecer_especies(especies[:40], diretorio, progress)
    else:
        progress("Centroide não disponível — GBIF ignorado.", "warning")

    progress("Montando draft PRADA...", "info")
    draft = montar_draft(cadastro, mapbiomas, especies)

    db.salvar_draft(projeto_id, draft)
    progress("Draft salvo no banco SQLite.", "success")

    return draft, projeto_id
