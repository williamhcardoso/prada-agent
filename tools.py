"""
Implementações de todas as ferramentas do Agente PRADA.
Cada função retorna um dict com chave 'resultado' ou 'erro'.
"""

import json
import os
import re
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# Caminho do pandoc instalado via winget (adicionado ao PATH após reiniciar shell)
_PANDOC_PATHS = [
    "pandoc",  # se estiver no PATH após reiniciar
    r"C:\Users\WILLIAM\AppData\Local\Microsoft\WinGet\Packages\JohnMacFarlane.Pandoc_Microsoft.Winget.Source_8wekyb3d8bbwe\pandoc-3.9.0.2\pandoc.exe",
]

def _find_pandoc() -> str | None:
    for p in _PANDOC_PATHS:
        try:
            subprocess.run([p, "--version"], capture_output=True, check=True)
            return p
        except Exception:
            continue
    return None

# ---------------------------------------------------------------------------
# DEFINIÇÕES DAS FERRAMENTAS (schema para o SDK Anthropic)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "ler_arquivos_projeto",
        "description": (
            "Escaneia o diretório de trabalho em busca de arquivos .shp e .pdf "
            "(Relatórios SIMCAR). Retorna lista de arquivos encontrados."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "diretorio": {
                    "type": "string",
                    "description": "Caminho do diretório a escanear."
                }
            },
            "required": ["diretorio"]
        }
    },
    {
        "name": "ler_shapefile",
        "description": (
            "Lê um arquivo .shp e extrai: atributos cadastrais (CAR, proprietário, "
            "município, áreas), IDs dos polígonos, centroide e bounding box."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "caminho": {"type": "string", "description": "Caminho completo do arquivo .shp."}
            },
            "required": ["caminho"]
        }
    },
    {
        "name": "ler_pdf_simcar",
        "description": (
            "Extrai texto de um relatório SIMCAR em PDF. Identifica dados cadastrais, "
            "quadro de áreas consolidadas e passivos (APPD, AURD, ARLD)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "caminho": {"type": "string", "description": "Caminho completo do arquivo .pdf."}
            },
            "required": ["caminho"]
        }
    },
    {
        "name": "ler_demonstrativo_car",
        "description": (
            "Lê o PDF 'Demonstrativo de Informações do CAR' (SEMA-MT). "
            "Extrai todas as áreas declaradas (ATP, ARL, ARLR, APP, APPD, AURD, etc.) "
            "e identifica automaticamente os passivos ambientais a recuperar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "caminho": {"type": "string", "description": "Caminho completo do arquivo .pdf."}
            },
            "required": ["caminho"]
        }
    },
    {
        "name": "consultar_mapbiomas_alerta",
        "description": (
            "Consulta o MapBiomas Alerta via GraphQL enviando o código CAR ou geometria WKT. "
            "Retorna: ano de desmatamento, tipologia, sobreposições restritivas e marco temporal "
            "(pré ou pós 22/07/2008)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "car_codigo": {
                    "type": "string",
                    "description": "Código do CAR estadual ou federal (ex.: MT-5100250-...)."
                },
                "geometria_wkt": {
                    "type": "string",
                    "description": "Geometria da propriedade em formato WKT (opcional, se disponível)."
                }
            },
            "required": ["car_codigo"]
        }
    },
    {
        "name": "consultar_gbif",
        "description": (
            "Busca ocorrências de espécies nativas arbóreas/arbustivas via GBIF API "
            "num raio de ~50km a partir do centroide da propriedade. "
            "Retorna lista de espécies com família e coordenadas."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude do centroide (decimal, negativo para Sul)."},
                "lon": {"type": "number", "description": "Longitude do centroide (decimal, negativo para Oeste)."},
                "raio_graus": {
                    "type": "number",
                    "description": "Raio de busca em graus decimais (0.45 ≈ 50km). Padrão: 0.45.",
                    "default": 0.45
                }
            },
            "required": ["lat", "lon"]
        }
    },
    {
        "name": "consultar_flora_brasil",
        "description": (
            "Verifica hábito (arbóreo/arbustivo) e informações taxonômicas de uma espécie "
            "via API da Flora do Brasil 2020 (JBRJ)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_cientifico": {
                    "type": "string",
                    "description": "Nome científico da espécie (ex.: 'Dipteryx alata')."
                }
            },
            "required": ["nome_cientifico"]
        }
    },
    {
        "name": "salvar_draft",
        "description": (
            "Salva os dados estruturados do projeto em prada_draft.json no diretório de trabalho. "
            "Deve ser chamado ANTES de gerar o documento final."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dados": {
                    "type": "object",
                    "description": "Objeto JSON completo seguindo o schema do PRADA (versao_schema 1.1)."
                }
            },
            "required": ["dados"]
        }
    },
    {
        "name": "ler_draft",
        "description": "Lê e retorna o conteúdo atual do prada_draft.json.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "pausar_para_revisao",
        "description": (
            "Exibe o resumo do diagnóstico no terminal e aguarda confirmação do usuário "
            "antes de prosseguir com a geração do documento final. "
            "DEVE ser chamada após salvar_draft e ANTES de gerar_documento_final."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "resumo": {
                    "type": "object",
                    "description": "Objeto com os campos: passivo_total_ha, appd_ha, arld_ha, aurd_ha, marco_temporal, compensacao, total_especies, percentual_pioneiras, percentual_zoocoricas, custo_estimado_R$, docs_pendentes, pendencias, alertas."
                }
            },
            "required": ["resumo"]
        }
    },
    {
        "name": "gerar_documento_final",
        "description": (
            "Lê o prada_draft.json e gera o documento PRADA completo em Markdown "
            "seguindo os 11 tópicos do Termo de Referência SEMA-MT, e converte "
            "automaticamente para .docx via pandoc. "
            "Só pode ser chamado após confirmação do usuário via pausar_para_revisao."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nome_arquivo_saida": {
                    "type": "string",
                    "description": "Nome do arquivo de saída sem extensão (ex.: 'PRADA_Fazenda_Rio_Verde'). O agente gerará o .md e o .docx."
                }
            },
            "required": ["nome_arquivo_saida"]
        }
    }
]


# ---------------------------------------------------------------------------
# DESPACHANTE CENTRAL
# ---------------------------------------------------------------------------

def execute_tool(name: str, inputs: dict, diretorio: str) -> dict:
    """Despacha a chamada para a função correspondente."""
    funcs = {
        "ler_arquivos_projeto": _ler_arquivos_projeto,
        "ler_shapefile": _ler_shapefile,
        "ler_pdf_simcar": _ler_pdf_simcar,
        "ler_demonstrativo_car": _ler_demonstrativo_car,
        "consultar_mapbiomas_alerta": _consultar_mapbiomas_alerta,
        "consultar_gbif": _consultar_gbif,
        "consultar_flora_brasil": _consultar_flora_brasil,
        "salvar_draft": _salvar_draft,
        "ler_draft": _ler_draft,
        "pausar_para_revisao": _pausar_para_revisao,
        "gerar_documento_final": _gerar_documento_final,
    }
    fn = funcs.get(name)
    if fn is None:
        return {"erro": f"Ferramenta desconhecida: {name}"}
    try:
        return fn(inputs, diretorio)
    except Exception as exc:
        return {"erro": str(exc)}


# ---------------------------------------------------------------------------
# IMPLEMENTAÇÕES
# ---------------------------------------------------------------------------

def _ler_arquivos_projeto(inputs: dict, diretorio: str) -> dict:
    base = Path(inputs.get("diretorio", diretorio))
    if not base.exists():
        return {"erro": f"Diretório não encontrado: {base}"}

    shp_files = list(base.glob("**/*.shp"))
    pdf_files = list(base.glob("**/*.pdf"))

    return {
        "resultado": {
            "shapefiles": [str(f) for f in shp_files],
            "pdfs": [str(f) for f in pdf_files],
            "total_shp": len(shp_files),
            "total_pdf": len(pdf_files)
        }
    }


def _detectar_e_reprojetar(caminho_shp: str):
    """
    Lê o arquivo .prj junto ao shapefile.
    Se for CRS projetado (UTM, etc.), retorna um Transformer para WGS84.
    Retorna (transformer_ou_None, epsg_origem).
    """
    prj_path = Path(caminho_shp).with_suffix(".prj")
    if not prj_path.exists():
        return None, None
    try:
        from pyproj import CRS, Transformer
        crs = CRS.from_wkt(prj_path.read_text())
        if crs.is_geographic:
            return None, crs.to_epsg()
        transformer = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
        return transformer, crs.to_epsg()
    except Exception:
        return None, None


def _ler_shapefile(inputs: dict, diretorio: str) -> dict:
    caminho = inputs["caminho"]
    try:
        import shapefile
        from shapely.geometry import shape
    except ImportError:
        return {"erro": "Dependências pyshp e shapely não instaladas. Execute: pip install pyshp shapely"}

    try:
        sf = shapefile.Reader(caminho)
    except Exception as e:
        return {"erro": f"Falha ao abrir shapefile: {e}"}

    transformer, epsg_origem = _detectar_e_reprojetar(caminho)

    fields = [f[0] for f in sf.fields[1:]]
    records = []
    centroides_wgs84 = []
    areas_m2 = []

    for sr in sf.shapeRecords():
        rec = dict(zip(fields, sr.record))
        records.append(rec)
        try:
            geom = shape(sr.shape.__geo_interface__)
            if transformer:
                # Reprojetar cada vértice e reconstruir geometria
                from shapely.ops import transform as shp_transform
                geom_wgs84 = shp_transform(
                    lambda x, y: transformer.transform(x, y), geom
                )
                c = geom_wgs84.centroid
                areas_m2.append(geom.area)  # área em m² (UTM)
            else:
                geom_wgs84 = geom
                c = geom.centroid
            centroides_wgs84.append({"lat": c.y, "lon": c.x})
        except Exception:
            pass

    # Centroide geral (média dos centroides)
    if centroides_wgs84:
        centroide_geral = {
            "lat": sum(c["lat"] for c in centroides_wgs84) / len(centroides_wgs84),
            "lon": sum(c["lon"] for c in centroides_wgs84) / len(centroides_wgs84),
        }
    else:
        centroide_geral = {"lat": 0, "lon": 0}

    # Bbox em WGS84 (reprojetado)
    bbox_orig = sf.bbox
    if transformer:
        lon_min, lat_min = transformer.transform(bbox_orig[0], bbox_orig[1])
        lon_max, lat_max = transformer.transform(bbox_orig[2], bbox_orig[3])
    else:
        lon_min, lat_min, lon_max, lat_max = bbox_orig

    resultado = {
        "campos": fields,
        "registros": records,
        "num_poligonos": len(records),
        "centroide_wgs84": centroide_geral,
        "bbox_wgs84": {
            "lon_min": lon_min, "lat_min": lat_min,
            "lon_max": lon_max, "lat_max": lat_max
        },
        "epsg_origem": epsg_origem or "desconhecido",
        "reprojection_aplicada": transformer is not None,
    }
    if areas_m2:
        resultado["areas_m2"] = areas_m2
        resultado["area_total_m2"] = sum(areas_m2)
        resultado["area_total_ha"] = round(sum(areas_m2) / 10000, 4)

    return {"resultado": resultado}


def _ler_pdf_simcar(inputs: dict, diretorio: str) -> dict:
    caminho = inputs["caminho"]
    try:
        import pdfplumber
    except ImportError:
        return {"erro": "Dependência pdfplumber não instalada. Execute: pip install pdfplumber"}

    try:
        with pdfplumber.open(caminho) as pdf:
            paginas_texto = [p.extract_text() or "" for p in pdf.pages]
            todas_tabelas = []
            for p in pdf.pages:
                try:
                    tabs = p.extract_tables() or []
                    todas_tabelas.extend(tabs)
                except Exception:
                    pass
    except Exception as e:
        return {"erro": f"Falha ao ler PDF: {e}"}

    texto_completo = "\n".join(paginas_texto)
    extraidos = {}

    # ── 1. Extração via tabelas (formato SIMCAR Demonstrativo) ────────────────
    _extrair_tabelas_simcar(todas_tabelas, texto_completo, extraidos)

    # ── 2. Padrões regex de fallback ─────────────────────────────────────────
    padroes_fallback = {
        "car_estadual": [
            # formato estadual MT: MT105380/2017 ou MT-510XXXX
            r"N[°º\s]+CAR\s+Estadual[^\n]*\n([A-Z]{2}[\d/\-]+\d)",
            r"CAR\s*Estadual[:\s]+([A-Z]{2}[\d/\-]+)",
            r"C[oó]digo\s+CAR[:\s]+([A-Z]{2}[\d/\-]+)",
        ],
        "car_federal": [
            # formato federal: MT-5103858-HEX (N° Recibo Federal)
            r"N[°º\s]+Recibo\s+Federal[^\n]*\n([A-Z]{2}-\d[\w\-]+)",
            r"Recibo\s+Federal[:\s]+([A-Z]{2}-\d[\w\-]+)",
            r"CAR\s*Federal[:\s]+([A-Z]{2}-\d[\w\-]+)",
            r"\b([A-Z]{2}-\d{7,}-[A-F0-9]{8,})\b",  # UF-NUMEROS-HEX
        ],
        "cnpj": [
            r"CNPJ[:\s]+([\d]{2}\.[\d]{3}\.[\d]{3}/[\d]{4}-[\d]{2})",
        ],
        "cpf": [
            r"CPF[:\s]+([\d]{3}\.[\d]{3}\.[\d]{3}-[\d]{2})",
        ],
        "proprietario": [
            r"Propriet[áa]rios\s+Nome\s+([^\n]+)",
            r"Propriet[áa]rio(?:s)?[:\s]+([^\n\r]+)",
            r"Respons[áa]vel[:\s]+([^\n\r]+)",
        ],
        "imovel": [
            # Linha isolada antes de "UF  Município" na tabela de dados da propriedade
            r"Dados\s+da\s+Propriedade[^\n]*\n[^\n]+\n([^\n]+?)\s+MT\s+",
            r"Denomina[çc][ãa]o[:\s]+([^\n\r]+)",
            r"Nome\s+da\s+Propriedade[:\s]+([^\n\r]+)",
        ],
        "municipio": [
            # "Fazenda X  MT  Gaúcha do Norte"
            r"\bMT\s+([A-ZÀ-Úa-zà-ú][A-ZÀ-Úa-zà-ú\s]+?)(?:\n|$)",
            r"Munic[íi]pio\s+de\s+([A-ZÀ-Úa-zà-ú][A-ZÀ-Úa-zà-ú\s]+)",
        ],
        "area_total": [
            r"[Áá]rea\s+Total\s+da\s+Propriedade\s*[–\-]\s*ATP\s+([\d.,]+)",
            r"[Áá]rea\s+Total\s+do\s+Im[oó]vel[^0-9]+([\d.,]+)",
            r"[Áá]rea\s+[Tt]otal[:\s]+([\d.,]+)\s*ha",
        ],
        "area_appd": [
            # "Área de Preservação Permanente Degradada – APPD 9,3177"
            r"Permanente\s+Degradada\s*[–\-]\s*APPD\s+([\d.,]+)",
            r"\bAPPD\s+([\d.,]+)",
            r"APPD[:\s]+([\d.,]+)",
        ],
        "area_aurd": [
            r"Uso\s+Restrito\s+Degradada\s*[–\-]\s*AURD\s+([\d.,]+)",
            r"\bAURD\s+([\d.,]+)",
            r"AURD[:\s]+([\d.,]+)",
        ],
        "area_arld": [
            # No SIMCAR é chamado ARLR (Área de Reserva Legal a Recompor)
            r"Reserva\s+Legal\s+a\s+Recompor\s*[–\-]\s*ARLR\s+([\d.,]+)",
            r"\bARLR\s+([\d.,]+)",
            r"\bARLD\s+([\d.,]+)",
            r"ARLD[:\s]+([\d.,]+)",
            r"Reserva\s+Legal\s+Degradada[:\s]+([\d.,]+)",
        ],
    }

    SEMA_CNPJ = "03.507.415/0023-50"

    for campo, lista_padroes in padroes_fallback.items():
        if campo in extraidos:
            continue
        for padrao in lista_padroes:
            m = re.search(padrao, texto_completo, re.IGNORECASE | re.MULTILINE)
            if m:
                valor = m.group(1).strip().rstrip(".")
                valor = re.sub(r"\s{2,}", " ", valor)
                # Não captura o CNPJ da SEMA-MT do rodapé
                if valor == SEMA_CNPJ:
                    continue
                extraidos[campo] = valor
                break

    return {
        "resultado": {
            "texto_bruto_truncado": texto_completo[:4000],
            "campos_extraidos": extraidos,
            "paginas": len(paginas_texto),
            "tabelas_encontradas": len(todas_tabelas),
        }
    }


def _detectar_documento(texto: str) -> tuple:
    """Detecta CPF ou CNPJ em texto. Retorna (tipo, valor) ou (None, None)."""
    m = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', texto)
    if m:
        return "cnpj", m.group(0)
    m = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', texto)
    if m:
        return "cpf", m.group(0)
    return None, None


def _extrair_tabelas_simcar(tabelas: list, texto: str, extraidos: dict) -> None:
    """
    Extrai campos do SIMCAR (Demonstrativo e Digital).
    Suporta células mescladas e células separadas.
    """
    SEMA_CNPJ = "03.507.415/0023-50"  # CNPJ da SEMA-MT — ignorar

    for tab in tabelas:
        if not tab:
            continue
        linhas = [[str(c or "").strip() for c in row] for row in tab]

        for i, linha in enumerate(linhas):
            linha_lower = [c.lower() for c in linha]
            cel0 = linha[0] if linha else ""
            cel0_low = cel0.lower()

            # ── PROPRIETÁRIO formato digital: header "Nome/Razão Social | CPF/CNPJ"
            if any("nome" in c and "raz" in c for c in linha_lower) and \
               any("cpf" in c for c in linha_lower):
                if i + 1 < len(linhas):
                    dado = " ".join(c for c in linhas[i + 1] if c)
                    tipo_doc, doc_val = _detectar_documento(dado)
                    if doc_val and doc_val != SEMA_CNPJ:
                        # Nome = tudo antes do documento
                        nome = re.sub(r'\s+\d[\d\.\-/]{10,}$', '', dado).strip()
                        extraidos.setdefault("proprietario", nome)
                        extraidos.setdefault(tipo_doc, doc_val)

            # ── PROPRIETÁRIO formato demonstrativo: header "Nome" sozinho
            if len(linha) == 1 and cel0_low == "nome":
                if i + 1 < len(linhas):
                    dado = linhas[i + 1][0]
                    primeiro = dado.split("\n")[0].strip()
                    if primeiro:
                        extraidos.setdefault("proprietario", primeiro)
                        # Pode ter CPF/CNPJ junto
                        tipo_doc, doc_val = _detectar_documento(dado)
                        if doc_val and doc_val != SEMA_CNPJ:
                            extraidos.setdefault(tipo_doc, doc_val)

            # ── CAR ESTADUAL
            if any("car estadual" in c or "n° car" in c or "nº car" in c
                   or "n°car" in c for c in linha_lower):
                if i + 1 < len(linhas):
                    dado = linhas[i + 1][0]
                    m = re.match(r"([A-Z]{2}[\d]+/\d{4})", dado)
                    if m:
                        extraidos.setdefault("car_estadual", m.group(1))

            # ── CAR FEDERAL
            if any("recibo federal" in c for c in linha_lower):
                if i + 1 < len(linhas):
                    dado = linhas[i + 1][0]
                    m = re.match(r"([A-Z]{2}-[\d]+-[A-F0-9]+)", dado)
                    if m:
                        extraidos.setdefault("car_federal", m.group(1))

            # ── IMÓVEL + MUNICÍPIO
            if "propriedade" in cel0_low and any("munic" in c for c in linha_lower):
                if i + 1 < len(linhas):
                    dado = linhas[i + 1][0]
                    m = re.match(r"(.+?)\s+MT\s+(.+)", dado, re.IGNORECASE)
                    if m:
                        extraidos.setdefault("imovel",    m.group(1).strip())
                        extraidos.setdefault("municipio", m.group(2).strip())

            # ── ARL A RECOMPOR (ARLD) — tabela "Tipo da Área | Área (ha)"
            if "tipo da" in cel0_low and any("rea" in c for c in linha_lower):
                for j in range(i + 1, len(linhas)):
                    row = linhas[j]
                    desc = (row[0] or "").replace("\n", " ").lower()
                    if "recompor" in desc or "arlr" in desc or "arld" in desc:
                        val = row[1] if len(row) > 1 and row[1] else None
                        if not val:
                            nums = re.findall(r"\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+", row[0])
                            val = nums[-1] if nums else None
                        if val:
                            extraidos.setdefault("area_arld", val)

            # ── TABELA DE ÁREAS: "Legenda | Identificação da Área | Área (ha)"
            # ou "Identificação | Área (ha)"
            if any("identifica" in c for c in linha_lower):
                for j in range(i + 1, len(linhas)):
                    row = linhas[j]
                    # Tenta extrair desc da coluna 1 (índice 1) e valor da coluna 2
                    desc_cel = (row[1] if len(row) > 1 and row[1] else row[0] or "")
                    val_cel  = (row[2] if len(row) > 2 and row[2] else
                                row[1] if len(row) > 1 and row[1] and row[1] != desc_cel else "")
                    desc_norm = desc_cel.replace("\n", " ").lower()

                    # Se valor não encontrado nas colunas, procura na célula mesclada
                    if not val_cel or not re.search(r"\d", val_cel):
                        cel_full = row[0].replace("\n", " ") if row else ""
                        desc_norm = cel_full.lower()
                        nums = re.findall(r"\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+", cel_full)
                        val_cel = max(nums, key=len) if nums else ""

                    if not val_cel:
                        continue

                    if "total da propriedade" in desc_norm or "atp" in desc_norm:
                        extraidos.setdefault("area_total", val_cel)
                    elif "appd" in desc_norm or \
                         ("preserva" in desc_norm and "permanente" in desc_norm and "degradada" in desc_norm):
                        extraidos.setdefault("area_appd", val_cel)
                    elif "aurd" in desc_norm or \
                         ("uso restrito" in desc_norm and "degradada" in desc_norm):
                        extraidos.setdefault("area_aurd", val_cel)
                    elif "arlr" in desc_norm or \
                         ("reserva legal" in desc_norm and ("recompor" in desc_norm or "degradada" in desc_norm)):
                        extraidos.setdefault("area_arld", val_cel)

            # ── CPF/CNPJ em qualquer célula — exclui CNPJ da SEMA-MT (rodapé)
            for cel in linha:
                tipo_doc, doc_val = _detectar_documento(cel)
                if doc_val and doc_val != SEMA_CNPJ:
                    if tipo_doc == "cpf" and "cpf" not in extraidos:
                        extraidos["cpf"] = doc_val
                    elif tipo_doc == "cnpj" and "cnpj" not in extraidos:
                        extraidos["cnpj"] = doc_val


def _ler_demonstrativo_car(inputs: dict, diretorio: str) -> dict:
    """
    Lê o 'Demonstrativo de Informações do CAR' (SEMA-MT).
    Extrai as 4 seções de áreas e identifica passivos automaticamente.
    """
    caminho = inputs["caminho"]
    try:
        import pdfplumber
    except ImportError:
        return {"erro": "pdfplumber não instalada. Execute: pip install pdfplumber"}

    try:
        with pdfplumber.open(caminho) as pdf:
            todas_tabelas = []
            for p in pdf.pages:
                try:
                    tabs = p.extract_tables() or []
                    todas_tabelas.extend(tabs)
                except Exception:
                    pass
    except Exception as e:
        return {"erro": f"Falha ao ler PDF: {e}"}

    def _parse_br(s: str) -> float:
        s = re.sub(r'\.(?=\d{3})', '', str(s or "").strip())
        s = s.replace(',', '.')
        try:
            return round(float(s), 4)
        except (ValueError, TypeError):
            return 0.0

    # label normalizado → chave interna
    MAPA = {
        "área total da propriedade": "atp",
        "total da propriedade": "atp",
        "atp": "atp",
        "massa d'água": "massa_dagua",
        "massa dagua": "massa_dagua",
        "massa dágua": "massa_dagua",
        "área de vegetação nativa": "avn",
        "avn": "avn",
        "área de vegetação nativa preservada": "avnp",
        "avnp": "avnp",
        "área de vegetação nativa remanescente": "avnr",
        "avnr": "avnr",
        "área consolidada": "consolidada",
        "área de uso antropizado do solo": "auas",
        "auas": "auas",
        "área de reserva legal": "arl",
        "arl": "arl",
        "arl preservada": "arlp",
        "arlp": "arlp",
        "arl a recompor": "arlr",
        "área de reserva legal a recompor": "arlr",
        "arlr": "arlr",
        "área de preservação permanente": "app",
        "app": "app",
        "área de preservação permanente em reserva legal": "app_em_rl",
        "app em reserva legal": "app_em_rl",
        "preservação permanente em reserva legal": "app_em_rl",
        "área de preservação permanente preservada": "appp",
        "app preservada": "appp",
        "appp": "appp",
        "área de preservação permanente degradada": "appd",
        "app degradada": "appd",
        "appd": "appd",
        "área de uso restrito": "aur",
        "área uso restrito": "aur",
        "aur": "aur",
        "área de uso restrito degradada": "aurd",
        "uso restrito degradada": "aurd",
        "aurd": "aurd",
        "área de uso restrito preservada": "aurp",
        "aurp": "aurp",
    }

    # Rótulos legíveis para exibição ao usuário
    ROTULOS = {
        "atp":       "Área Total da Propriedade",
        "massa_dagua": "Massa D'água",
        "avn":       "Área de Vegetação Nativa",
        "avnp":      "AVN Preservada",
        "avnr":      "AVN Remanescente",
        "consolidada": "Área Consolidada",
        "auas":      "Área de Uso Antropizado",
        "arl":       "Área de Reserva Legal",
        "arlp":      "ARL Preservada",
        "arlr":      "ARL a Recompor (ARLR)",
        "app":       "Área de Preservação Permanente",
        "app_em_rl": "APP em Reserva Legal",
        "appp":      "APP Preservada",
        "appd":      "APP Degradada (APPD)",
        "aur":       "Área de Uso Restrito",
        "aurd":      "Uso Restrito Degradado (AURD)",
        "aurp":      "Uso Restrito Preservado",
    }

    areas: dict[str, float] = {}

    for tab in todas_tabelas:
        if not tab:
            continue
        for row in tab:
            cells = [str(c or "").replace('\n', ' ').strip() for c in row]

            # Rótulo: primeira célula não vazia
            label = next((c for c in cells if c), "")
            if not label:
                continue

            # Pula cabeçalhos de seção ("1- Identificação...", "Área (ha)", etc.)
            if re.match(r'\d+[-–]', label) or label.lower() in ('área (ha)', 'identificação',
                                                                  'legenda', 'área (ha)'):
                continue

            # Valor: última célula com número decimal brasileiro (ex.: 266,6166)
            valor_str = ""
            for c in reversed(cells):
                if re.search(r'\d+,\d+', c):
                    valor_str = c
                    break
            if not valor_str:
                continue

            # Normaliza rótulo
            label_norm = re.sub(r'^[-–•\s]+', '', label.lower()).strip()
            label_norm = re.sub(r'\s+', ' ', label_norm)

            chave = MAPA.get(label_norm)
            # Fallback: busca parcial (chaves com ≥6 chars)
            if not chave:
                for k, v in MAPA.items():
                    if len(k) >= 6 and (k in label_norm or label_norm in k):
                        chave = v
                        break

            if chave and chave not in areas:
                nums = re.findall(r'\d{1,3}(?:\.\d{3})*,\d+|\d+,\d+', valor_str)
                if nums:
                    areas[chave] = _parse_br(max(nums, key=len))

    # ── Calcula APPD se não declarado diretamente ─────────────────────────────
    appd_calculado = False
    if "appd" not in areas:
        app_t = areas.get("app", 0.0)
        appp  = areas.get("appp", 0.0)
        app_rl = areas.get("app_em_rl", 0.0)
        if app_t > 0:
            calc = round(app_t - appp - app_rl, 4)
            if calc > 0:
                areas["appd"] = calc
                appd_calculado = True

    # ── Identificação automática de passivos ──────────────────────────────────
    passivos = []

    arlr = areas.get("arlr", 0.0)
    if arlr > 0:
        passivos.append({
            "tipo": "ARLD",
            "area_ha": arlr,
            "descricao": "Reserva Legal a Recompor",
            "base_legal": "Art. 66, Lei 12.651/2012",
            "urgencia": "alta",
        })

    appd = areas.get("appd", 0.0)
    if appd > 0:
        nota = " (calculado: APP − APPp − APP em RL)" if appd_calculado else ""
        passivos.append({
            "tipo": "APPD",
            "area_ha": appd,
            "descricao": f"Preservação Permanente Degradada{nota}",
            "base_legal": "Art. 61-A, Lei 12.651/2012",
            "urgencia": "alta",
        })

    aurd = areas.get("aurd", 0.0)
    if aurd > 0:
        passivos.append({
            "tipo": "AURD",
            "area_ha": aurd,
            "descricao": "Uso Restrito Degradado",
            "base_legal": "Art. 10 c/c Art. 48, Lei 12.651/2012",
            "urgencia": "media",
        })

    total_passivo = round(sum(p["area_ha"] for p in passivos), 4)

    # Monta lista de todas as áreas para exibição com rótulo legível
    areas_display = [
        {"campo": chave, "rotulo": ROTULOS.get(chave, chave),
         "area_ha": val, "passivo": chave in ("arlr", "appd", "aurd")}
        for chave, val in areas.items()
    ]

    return {
        "resultado": {
            "areas": areas,
            "areas_display": areas_display,
            "passivos_identificados": passivos,
            "total_passivo_ha": total_passivo,
            "appd_calculado": appd_calculado,
            "conforme": total_passivo == 0,
        }
    }


def _consultar_mapbiomas_alerta(inputs: dict, diretorio: str) -> dict:
    car = inputs["car_codigo"]
    geometria = inputs.get("geometria_wkt", "")

    query = """
    query GetAlertsByCAR($car: String!) {
      allAlerts(filters: { carCode: $car }) {
        alertCode
        areaHa
        detectedAt
        source
        alertType
        territory {
          name
          geoformType
        }
      }
    }
    """
    url = "https://plataforma.alerta.mapbiomas.org/api"
    headers = {"Content-Type": "application/json"}
    payload = {"query": query, "variables": {"car": car}}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {
            "erro": "timeout",
            "mapbiomas_status": "indisponível",
            "instrucao": "Informe manualmente: ano do desmatamento, tipologia e sobreposições restritivas."
        }
    except Exception as e:
        return {
            "erro": str(e),
            "mapbiomas_status": "indisponível",
            "instrucao": "Informe manualmente: ano do desmatamento, tipologia e sobreposições restritivas."
        }

    alertas = data.get("data", {}).get("allAlerts", [])
    if not alertas:
        return {
            "resultado": {
                "mapbiomas_status": "ok",
                "alertas": [],
                "marco_temporal": "indefinido",
                "aviso": "Nenhum alerta encontrado para este CAR. Verifique se o código está correto."
            }
        }

    # Determina marco temporal
    anos = []
    for a in alertas:
        det = a.get("detectedAt", "")
        if det:
            try:
                anos.append(int(det[:4]))
            except ValueError:
                pass

    marco = "indefinido"
    if anos:
        if min(anos) < 2008:
            marco = "pré-2008" if max(anos) < 2008 else "misto"
        else:
            marco = "pós-2008"

    return {
        "resultado": {
            "mapbiomas_status": "ok",
            "total_alertas": len(alertas),
            "alertas": alertas,
            "anos_desmatamento": sorted(set(anos)),
            "marco_temporal": marco,
        }
    }


def _consultar_gbif(inputs: dict, diretorio: str) -> dict:
    lat = inputs["lat"]
    lon = inputs["lon"]
    raio = inputs.get("raio_graus", 0.45)

    # GBIF occurrence/search aceita basisOfRecord como params repetidos
    params = [
        ("taxonKey", 6),          # Plantae
        ("hasCoordinate", "true"),
        ("decimalLatitude",  f"{lat - raio},{lat + raio}"),
        ("decimalLongitude", f"{lon - raio},{lon + raio}"),
        ("basisOfRecord", "HUMAN_OBSERVATION"),
        ("basisOfRecord", "PRESERVED_SPECIMEN"),
        ("limit", 300),
    ]

    try:
        resp = requests.get(
            "https://api.gbif.org/v1/occurrence/search",
            params=params,
            timeout=40
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {
            "erro": "timeout",
            "instrucao": "GBIF indisponível. Não prossiga com lista de espécies. Informe o usuário."
        }
    except Exception as e:
        return {"erro": str(e)}

    # Deduplica por nome científico; mantém apenas nível de espécie
    especies = {}
    for occ in data.get("results", []):
        nome = occ.get("species") or occ.get("scientificName", "")
        familia = occ.get("family", "")
        genero = occ.get("genus", "")
        # Descarta registros sem epíteto específico
        if not nome or len(nome.split()) < 2:
            continue
        if nome not in especies:
            especies[nome] = {
                "nome_cientifico": nome,
                "familia": familia,
                "genero": genero,
                "ocorrencias": 0
            }
        especies[nome]["ocorrencias"] += 1

    lista = sorted(especies.values(), key=lambda x: -x["ocorrencias"])

    return {
        "resultado": {
            "fonte": "GBIF",
            "total_ocorrencias": data.get("count", 0),
            "total_especies_unicas": len(lista),
            "especies": lista[:80]  # top 80 por frequência
        }
    }


def _consultar_flora_brasil(inputs: dict, diretorio: str) -> dict:
    nome = inputs["nome_cientifico"].strip()
    nome_encoded = requests.utils.quote(nome)

    url = (
        f"https://floradobrasil.jbrj.gov.br/reflora/listaBrasil/listaBrasilService/"
        f"ConsultaPublicaService/obterDadosEspecie?nomeCompleto={nome_encoded}"
    )

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return {"erro": "Flora do Brasil indisponível (timeout)."}
    except Exception:
        # Tenta endpoint alternativo simplificado
        try:
            url2 = f"https://floradobrasil.jbrj.gov.br/reflora/listaBrasil/listaBrasilService/ConsultaPublicaService/busca?termo={nome_encoded}&limit=1"
            resp2 = requests.get(url2, timeout=20)
            data = resp2.json()
        except Exception as e2:
            return {"erro": f"Flora do Brasil indisponível: {e2}"}

    return {
        "resultado": {
            "nome_cientifico": nome,
            "dados_raw": data,
            "aviso": "Verifique hábito (árv./arb.) e grupo sucessional na resposta."
        }
    }


def _salvar_draft(inputs: dict, diretorio: str) -> dict:
    dados = inputs["dados"]
    dados["data_geracao"] = datetime.now().isoformat()
    caminho = Path(diretorio) / "prada_draft.json"

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    return {
        "resultado": {
            "caminho": str(caminho),
            "tamanho_bytes": caminho.stat().st_size,
            "mensagem": "Draft salvo com sucesso."
        }
    }


def _ler_draft(inputs: dict, diretorio: str) -> dict:
    caminho = Path(diretorio) / "prada_draft.json"
    if not caminho.exists():
        return {"erro": "prada_draft.json não encontrado. Execute salvar_draft primeiro."}

    with open(caminho, "r", encoding="utf-8") as f:
        dados = json.load(f)

    return {"resultado": dados}


def _pausar_para_revisao(inputs: dict, diretorio: str) -> dict:
    """
    Exibe o resumo no terminal. O agente (agent.py) captura a entrada do usuário
    e a injeta como tool_result. Esta função apenas formata a saída.
    """
    r = inputs.get("resumo", {})

    linhas = [
        "━" * 60,
        "  DIAGNÓSTICO CONCLUÍDO — prada_draft.json gerado.",
        "",
        "  RESUMO:",
        f"  • Passivo total   : {r.get('passivo_total_ha', '?')} ha",
        f"    ├ APPD           : {r.get('appd_ha', '?')} ha",
        f"    ├ ARLD           : {r.get('arld_ha', '?')} ha",
        f"    └ AURD           : {r.get('aurd_ha', '?')} ha",
        f"  • Marco temporal  : {r.get('marco_temporal', '?')}",
        f"  • Compensação     : {r.get('compensacao', 'não aplicável')}",
        f"  • Espécies        : {r.get('total_especies', '?')} "
        f"({r.get('percentual_pioneiras', '?')}% pioneiras | "
        f"{r.get('percentual_zoocoricas', '?')}% zoocóricas)",
        f"  • Custo estimado  : R$ {r.get('custo_estimado_R$', '?')}",
        f"  • Docs pendentes  : {r.get('docs_pendentes', '?')}/6",
    ]

    pendencias = r.get("pendencias", [])
    if pendencias:
        linhas.append(f"  • Pendências      : {len(pendencias)}")
        for p in pendencias:
            linhas.append(f"    - {p}")

    alertas = r.get("alertas", [])
    if alertas:
        linhas.append(f"  • Alertas técnicos: {len(alertas)}")
        for a in alertas:
            linhas.append(f"    ⚠ {a}")

    linhas += [
        "",
        "  Por favor, revise o prada_draft.json.",
        "  Deseja alterar algum parâmetro manualmente antes",
        "  da geração do PRADA oficial?",
        "━" * 60,
    ]

    print("\n" + "\n".join(linhas))

    # Retorna marcador — agent.py coleta a resposta real do stdin
    return {"aguardando_usuario": True, "resumo_exibido": True}


def _gerar_documento_final(inputs: dict, diretorio: str) -> dict:
    nome_saida = inputs["nome_arquivo_saida"]
    caminho_draft = Path(diretorio) / "prada_draft.json"

    if not caminho_draft.exists():
        return {"erro": "prada_draft.json não encontrado."}

    with open(caminho_draft, "r", encoding="utf-8") as f:
        d = json.load(f)

    cad = d.get("cadastro", {})
    geo = d.get("diagnostico_geoespacial", {})
    abas = d.get("abas_simcar", {})
    flor = d.get("floristica", {})
    orc = d.get("orcamento_preliminar", {})
    passivos = geo.get("passivos", {})

    doc = f"""# PROJETO DE REGULARIZAÇÃO AMBIENTAL (PRADA)
**Gerado em:** {d.get('data_geracao', datetime.now().isoformat())[:10]}

---

## 1. IDENTIFICAÇÃO DO EMPREENDEDOR E DO IMÓVEL

| Campo | Valor |
|-------|-------|
| Proprietário | {cad.get('proprietario', '')} |
| CPF/CNPJ | {cad.get('cpf_cnpj', '')} |
| Nome do Imóvel | {cad.get('imovel', '')} |
| Município | {cad.get('municipio', '')} |
| CAR Estadual | {cad.get('car_estadual', '')} |
| CAR Federal | {cad.get('car_federal', '')} |
| Área Total | {cad.get('area_total_ha', '')} ha |
| Módulos Fiscais | {cad.get('modulos_fiscais', '')} |

---

## 2. LOCALIZAÇÃO E CARACTERIZAÇÃO DA ÁREA

Imóvel rural localizado no município de {cad.get('municipio', '___')}, Estado de Mato Grosso.
Coordenadas do centroide: a serem inseridas conforme shapefile.
Bioma: Cerrado / Amazônia (conforme localização).

---

## 3. DIAGNÓSTICO AMBIENTAL

| Passivo | Área (ha) |
|---------|-----------|
| APPD — Área de Preservação Permanente Degradada | {passivos.get('appd_ha', 0)} |
| ARLD — Área de Reserva Legal Degradada | {passivos.get('arld_ha', 0)} |
| AURD — Área de Uso Restrito Degradada | {passivos.get('aurd_ha', 0)} |
| **TOTAL** | **{sum([passivos.get(k, 0) for k in ['appd_ha','arld_ha','aurd_ha']])}** |

**Marco temporal:** {geo.get('marco_temporal', '').upper()}

**Tipologia do desmatamento:** {geo.get('tipologia_desmatamento', '')}

**Sobreposições restritivas:** {', '.join(geo.get('sobreposicoes_restritivas', [])) or 'Nenhuma identificada.'}

---

## 4. FUNDAMENTAÇÃO LEGAL

- Lei Federal nº 12.651/2012 — Arts. 59, 61-A, 65, 66 e 78-A (Código Florestal).
- Resolução CONAMA nº 429/2011 — Metodologias de restauração ecológica.
- Lei Complementar MT nº 592/2017 e Decreto Estadual MT nº 1.031/2017.
- Termos de Referência SEMA-MT para PRADA (versão vigente).

---

## 5. METODOLOGIA DE RECUPERAÇÃO

### 5.1 APPD — Recuperação de Área de Preservação Permanente

Área total: **{passivos.get('appd_ha', 0)} ha**

"""
    def _lista_md(items: list) -> str:
        return "".join(f"  - {x}\n" for x in items) if items else "  — não informado\n"

    aba3 = abas.get("aba3_appd", {})
    doc += f"""**Fitoecologia:** {aba3.get('fitoecologia', '')}
**Fitofisionomia:** {aba3.get('fitofisionomia', '')}
**Método de recuperação:** {aba3.get('metodo', '')}
**Faixa de recuperação:** {aba3.get('faixa_recuperacao_m') or aba3.get('faixa_m', '')} m
**Justificativa:** {aba3.get('justificativa', '')}

**Características da Área:**
{_lista_md(aba3.get('caracteristicas_area', []))}
**Técnicas a serem utilizadas:**
{_lista_md(aba3.get('tecnicas', []))}
"""
    for grupo in aba3.get("grupos", []):
        doc += f"**{grupo.get('nome', '')}** — Polígonos: {', '.join(str(p) for p in grupo.get('poligonos', []))}\n\n"

    aba5 = abas.get("aba5_arld", {})
    doc += f"""### 5.2 ARLD — Recuperação de Reserva Legal

Área total: **{passivos.get('arld_ha', 0)} ha**
**Fitoecologia:** {aba5.get('fitoecologia', '')}
**Fitofisionomia:** {aba5.get('fitofisionomia', '')}
**Alternativa legal adotada (Art. 66, Lei 12.651/2012):** {aba5.get('alternativa_legal', '')}
**Prazo de execução:** {aba5.get('prazo_anos', 20)} anos (mínimo de 1/10 da área a cada 2 anos).
**Justificativa:** {aba5.get('justificativa', '')}

**Características da Área:**
{_lista_md(aba5.get('caracteristicas_area', []))}
**Técnicas a serem utilizadas:**
{_lista_md(aba5.get('tecnicas', []))}

### 5.3 AURD — Recuperação de Área de Uso Restrito

Área total: **{passivos.get('aurd_ha', 0)} ha**
**Fitoecologia:** {abas.get('aba4_aurd', {}).get('fitoecologia', '')}
**Fitofisionomia:** {abas.get('aba4_aurd', {}).get('fitofisionomia', '')}
**Tipo de restrição:** {abas.get('aba4_aurd', {}).get('tipo_restricao', '')}
**Método:** Manejo sustentável / Regeneração natural (vedado corte raso).

**Características da Área:**
{_lista_md(abas.get('aba4_aurd', {}).get('caracteristicas_area', []))}
**Técnicas a serem utilizadas:**
{_lista_md(abas.get('aba4_aurd', {}).get('tecnicas', []))}
"""

    aba6 = abas.get("aba6_compensacao")
    if aba6:
        doc += f"""### 5.4 Compensação (Aba 6 SIMCAR)

Tipo: {aba6.get('tipo', '')}
Área compensada: {aba6.get('area_ha', '')} ha
Localização: {aba6.get('localizacao', '')}
Status: {aba6.get('status_aprovacao', '')}

"""

    doc += f"""---

## 6. LISTA FLORÍSTICA

Fonte dos dados: {flor.get('fonte_dados', '')}
Total de espécies: {flor.get('total_especies', 0)}
Pioneiras: {flor.get('percentual_pioneiras', 0)}%
Zoocóricas: {flor.get('percentual_zoocoricas', 0)}%

| Nº | Nome Científico | Nome Popular | Família | Grupo Suc. | Dispersão |
|----|----------------|--------------|---------|-----------|-----------|
"""
    for i, sp in enumerate(flor.get("lista_especies", []), 1):
        doc += (
            f"| {i} | *{sp.get('nome_cientifico','')}* "
            f"| {sp.get('nome_popular','')} "
            f"| {sp.get('familia','')} "
            f"| {sp.get('grupo_sucessional','')} "
            f"| {sp.get('dispersao','')} |\n"
        )

    cronograma = abas.get("aba7_prazos", {}).get("cronograma", [])
    doc += f"""

---

## 7. CRONOGRAMA FÍSICO-FINANCEIRO

Todas as operações de plantio estritamente no período chuvoso de Mato Grosso (outubro a março).

| Ano | Semestre | Período | Atividade | Área (ha) | % Acumulado |
|-----|----------|---------|-----------|-----------|-------------|
"""
    for linha in cronograma:
        doc += (
            f"| {linha.get('ano','')} "
            f"| {linha.get('semestre','')} "
            f"| {linha.get('periodo','')} "
            f"| {linha.get('atividade','')} "
            f"| {linha.get('area_ha','')} "
            f"| {linha.get('percentual_acumulado','')}% |\n"
        )

    doc += f"""

---

## 8. ESTIMATIVA DE CUSTOS

Referência de preços: {orc.get('referencia_precos', 'IMEA-MT')}

| Item | Valor (R$) |
|------|-----------|
| Mudas ({orc.get('mudas_total', 0)} unid.) | {orc.get('custo_mudas_R$', 0):,.2f} |
| Insumos de Solo | {orc.get('custo_insumos_solo_R$', 0):,.2f} |
| Cercamento (mourões/arame) | {orc.get('custo_cercamento_R$', 0):,.2f} |
| Horas-Máquina | {orc.get('custo_horas_maquina_R$', 0):,.2f} |
| Monitoramento | {orc.get('custo_monitoramento_R$', 0):,.2f} |
| **TOTAL ESTIMADO** | **{orc.get('total_estimado_R$', 0):,.2f}** |

---

## 9. PROGRAMA DE MONITORAMENTO

- **Indicadores de sucesso:** Percentual de cobertura vegetal, taxa de sobrevivência
  das mudas (≥ 80% no 1º ano), diversidade florística.
- **Periodicidade de relatórios:** Semestrais no 1º ano; anuais do 2º ao 20º ano.
- **Entrega:** Relatórios técnicos de monitoramento à SEMA-MT conforme cronograma (Aba 7 SIMCAR).

---

## 10. RESPONSÁVEL TÉCNICO

Nome: _______________________________________________
Número CREA/CFBio: ___________________________________
Número da ART: ______________________________________

---

## 11. ANEXOS

"""
    checklist = abas.get("aba8_documentacao", {}).get("checklist", [])
    for item in checklist:
        s = item.get("status", "")
        status = "[ ]" if s == "pendente" else ("[-]" if s == "n/a" else "[x]")
        doc += f"- {status} {item.get('documento','')}\n"

    # Salva o arquivo
    nome_saida_limpo = re.sub(r'[^\w\-_]', '_', nome_saida)
    caminho_saida = Path(diretorio) / f"{nome_saida_limpo}.md"
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(doc)

    resultado = {
        "arquivo_md": str(caminho_saida),
        "tamanho_md_bytes": caminho_saida.stat().st_size,
    }

    # Converte para .docx via pandoc automaticamente
    pandoc = _find_pandoc()
    if pandoc:
        caminho_docx = caminho_saida.with_suffix(".docx")
        try:
            subprocess.run(
                [pandoc, str(caminho_saida), "-o", str(caminho_docx),
                 "--from", "markdown", "--to", "docx"],
                capture_output=True, check=True
            )
            resultado["arquivo_docx"] = str(caminho_docx)
            resultado["tamanho_docx_bytes"] = caminho_docx.stat().st_size
            resultado["mensagem"] = (
                f"PRADA gerado com sucesso:\n"
                f"  .md   -> {caminho_saida.name}\n"
                f"  .docx -> {caminho_docx.name}"
            )
        except subprocess.CalledProcessError as e:
            resultado["aviso_docx"] = f"pandoc encontrado mas falhou: {e.stderr.decode()}"
            resultado["mensagem"] = f"PRADA .md gerado. Converta manualmente: pandoc {caminho_saida.name} -o {nome_saida_limpo}.docx"
    else:
        resultado["mensagem"] = (
            f"PRADA .md gerado: {caminho_saida.name}\n"
            "pandoc não encontrado no PATH. Converta com:\n"
            f"  pandoc {caminho_saida.name} -o {nome_saida_limpo}.docx"
        )

    return {"resultado": resultado}
