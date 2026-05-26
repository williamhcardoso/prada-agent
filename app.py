"""
Interface Streamlit para o Agente PRADA — SIMCAR MT
Sem IA: SHP + PDF → APIs → SQLite → Formulários editáveis → PRADA .docx
Execute: streamlit run app.py
"""

import json
import os
import sys
import threading
import queue
from pathlib import Path


def _abrir_seletor(titulo: str, tipos: list[tuple]) -> str:
    """Abre o seletor de arquivo nativo do Windows via tkinter."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    path = filedialog.askopenfilename(title=titulo, filetypes=tipos)
    root.destroy()
    return path or ""


def _abrir_seletor_pasta(titulo: str = "Selecionar pasta") -> str:
    """Abre o seletor de pasta nativo do Windows via tkinter."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    path = filedialog.askdirectory(title=titulo)
    root.destroy()
    return path or ""

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
import db
import pipeline
import rules
from tools import execute_tool

# ── Configuração ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Agente PRADA — SIMCAR MT",
    page_icon="🌿",
    layout="wide",
)

st.markdown("""
<style>
  section[data-testid="stSidebar"] { min-width: 240px; max-width: 260px; }
  .step-title { font-size: 1.15rem; font-weight: 700; margin-bottom: 0.2rem; }
  div[data-testid="stMetricValue"] { font-size: 1.4rem; }
</style>
""", unsafe_allow_html=True)

ETAPAS = [
    "📁 Arquivos",
    "📋 Cadastro",
    "🌍 APIs",
    "🌿 Florística",
    "⚙️  Metodologia",
    "💰 Orçamento",
    "📄 Gerar PRADA",
]

# ── Session state ─────────────────────────────────────────────────────────────

def _init():
    defaults = {
        "etapa":       0,
        "shp_path":    "",
        "pdf_path":    "",
        "dem_path":    "",
        "diretorio":   "",
        "shp_dados":   {},
        "pdf_dados":   {},
        "dem_dados":   {},
        "cadastro":    {},
        "mapbiomas":   {},
        "especies":    [],
        "draft":       {},
        "projeto_id":  None,
        "progress_q":  queue.Queue(),
        "progress_log": [],
        "rodando":     False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()
S = st.session_state


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🌿 PRADA Agent")
    st.caption("SIMCAR-MT · Sem IA · SQLite")
    st.divider()

    st.markdown("**Progresso:**")
    for i, nome in enumerate(ETAPAS):
        cor = "🟢" if i < S.etapa else ("🔵" if i == S.etapa else "⚪")
        st.caption(f"{cor} {nome}")

    st.divider()

    if S.projeto_id:
        st.caption(f"Projeto #{S.projeto_id} ativo")

    if st.button("🔄 Novo projeto", use_container_width=True):
        for k in list(S.keys()):
            del st.session_state[k]
        st.rerun()

    st.divider()

    # Histórico
    with st.expander("📂 Projetos anteriores"):
        projetos = db.listar_projetos()
        if projetos:
            for p in projetos[:10]:
                label = p.get("imovel") or p.get("car_estadual") or f"#{p['id']}"
                st.caption(f"#{p['id']} — {label} ({p.get('area_total_ha','?')} ha)")
        else:
            st.caption("Nenhum projeto salvo.")


# ── Cabeçalho ─────────────────────────────────────────────────────────────────

st.title("🌿 Agente PRADA — SIMCAR MT")
st.caption("Projeto de Regularização Ambiental · Fluxo 8 Abas · Formulários Editáveis")
st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 0 — Arquivos de entrada
# ══════════════════════════════════════════════════════════════════════════════

if S.etapa == 0:
    st.markdown('<p class="step-title">📁 Selecionar arquivos do projeto</p>',
                unsafe_allow_html=True)
    st.caption("Clique nos botões abaixo para selecionar os arquivos.")

    col_shp_card, col_pdf_card, col_dem_card = st.columns(3)

    # ── Card Shapefile ─────────────────────────────────────────────────────
    with col_shp_card:
        st.markdown("##### 🗺️ Shapefile (.shp)")
        if S.shp_path and Path(S.shp_path).exists():
            st.success(f"✅  {Path(S.shp_path).name}")
        elif S.shp_path:
            st.error("Arquivo não encontrado")
        else:
            st.caption("Nenhum arquivo selecionado")

        if st.button("📂  Selecionar Shapefile", key="btn_shp", use_container_width=True):
            caminho = _abrir_seletor(
                "Selecionar Shapefile",
                [("Shapefile", "*.shp"), ("Todos os arquivos", "*.*")]
            )
            if caminho:
                S.shp_path = caminho
                st.rerun()

    # ── Card PDF SIMCAR ────────────────────────────────────────────────────
    with col_pdf_card:
        st.markdown("##### 📄 Demonstrativo SIMCAR (.pdf)")
        if S.pdf_path and Path(S.pdf_path).exists():
            st.info(f"📄  {Path(S.pdf_path).name}")
        elif S.pdf_path:
            st.error("Arquivo não encontrado")
        else:
            st.caption("Nenhum arquivo selecionado")

        if st.button("📂  Selecionar PDF SIMCAR", key="btn_pdf", use_container_width=True):
            caminho = _abrir_seletor(
                "Selecionar Demonstrativo SIMCAR",
                [("PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
            )
            if caminho:
                S.pdf_path = caminho
                st.rerun()

    # ── Card Demonstrativo CAR ─────────────────────────────────────────────
    with col_dem_card:
        st.markdown("##### 📊 Demonstrativo do CAR (.pdf)")
        st.caption("Identifica passivos automaticamente")
        if S.dem_path and Path(S.dem_path).exists():
            st.success(f"✅  {Path(S.dem_path).name}")
        elif S.dem_path:
            st.error("Arquivo não encontrado")
        else:
            st.caption("Nenhum arquivo selecionado")

        if st.button("📂  Selecionar Demonstrativo CAR", key="btn_dem",
                     use_container_width=True):
            caminho = _abrir_seletor(
                "Selecionar Demonstrativo de Informações do CAR",
                [("PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
            )
            if caminho:
                S.dem_path = caminho
                st.rerun()

    # ── Detecção automática por pasta (oculta por padrão) ─────────────────
    with st.expander("🔍 Detectar arquivos automaticamente por pasta"):
        col_d, col_pasta_btn, col_detect_btn = st.columns([4, 1, 1])
        with col_d:
            dirpath = st.text_input("dir_input", label_visibility="collapsed",
                                     placeholder=r"C:\projetos\fazenda",
                                     value=S.diretorio, key="input_dir")
        with col_pasta_btn:
            if st.button("📂", key="btn_dir", use_container_width=True, help="Selecionar pasta"):
                pasta = _abrir_seletor_pasta("Selecionar pasta do projeto")
                if pasta:
                    S.diretorio = pasta
                    st.rerun()
        with col_detect_btn:
            if st.button("🔍", key="btn_detect", use_container_width=True, help="Detectar na pasta"):
                pasta_busca = dirpath or S.diretorio
                r = execute_tool("ler_arquivos_projeto", {"diretorio": pasta_busca}, pasta_busca)
                if "resultado" in r:
                    shps = r["resultado"]["shapefiles"]
                    pdfs = r["resultado"]["pdfs"]
                    if shps:
                        S.shp_path = shps[0]
                    if pdfs:
                        S.pdf_path = pdfs[0]
                    if not shps and not pdfs:
                        st.warning("Nenhum arquivo .shp ou .pdf encontrado na pasta.")
                    st.rerun()

    ok_shp = bool(S.shp_path and Path(S.shp_path).exists())
    ok_pdf = bool(S.pdf_path and Path(S.pdf_path).exists())
    ok_dem = bool(S.dem_path and Path(S.dem_path).exists())

    st.divider()
    if st.button("▶  Extrair dados e continuar", type="primary",
                  use_container_width=True, disabled=not (ok_shp or ok_pdf or ok_dem)):
        ref_path = S.shp_path if ok_shp else (S.pdf_path if ok_pdf else S.dem_path)
        S.diretorio = str(Path(ref_path).parent)

        with st.spinner("Lendo arquivos..."):
            if ok_shp:
                r = execute_tool("ler_shapefile", {"caminho": S.shp_path}, S.diretorio)
                S.shp_dados = r.get("resultado", {})
            if ok_pdf:
                r = execute_tool("ler_pdf_simcar", {"caminho": S.pdf_path}, S.diretorio)
                S.pdf_dados = r.get("resultado", {})
            if ok_dem:
                r = execute_tool("ler_demonstrativo_car", {"caminho": S.dem_path},
                                 S.diretorio)
                S.dem_dados = r.get("resultado", {})

        S.cadastro = pipeline.montar_cadastro(S.shp_dados, S.pdf_dados)

        # Auto-preenche passivos a partir do Demonstrativo CAR (se disponível)
        if S.dem_dados.get("passivos_identificados"):
            for p in S.dem_dados["passivos_identificados"]:
                if p["tipo"] == "ARLD":
                    S.cadastro["arld_ha"] = p["area_ha"]
                elif p["tipo"] == "APPD":
                    S.cadastro["appd_ha"] = p["area_ha"]
                elif p["tipo"] == "AURD":
                    S.cadastro["aurd_ha"] = p["area_ha"]

        S.etapa = 1
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 1 — Cadastro (editável)
# ══════════════════════════════════════════════════════════════════════════════

elif S.etapa == 1:
    st.markdown('<p class="step-title">📋 Etapa 2 — Dados cadastrais</p>',
                unsafe_allow_html=True)
    st.caption("Dados extraídos automaticamente. Corrija o que for necessário.")

    c = S.cadastro

    col1, col2 = st.columns(2)
    with col1:
        c["proprietario"] = st.text_input("Proprietário / Razão Social",
                                           value=c.get("proprietario",""))
        # CPF e CNPJ separados com auto-detecção
        col_cpf, col_cnpj = st.columns(2)
        with col_cpf:
            c["cpf"] = st.text_input("CPF", value=c.get("cpf",""),
                                      placeholder="000.000.000-00")
        with col_cnpj:
            c["cnpj"] = st.text_input("CNPJ", value=c.get("cnpj",""),
                                       placeholder="00.000.000/0000-00")
        c["imovel"]   = st.text_input("Nome do imóvel", value=c.get("imovel",""))
        c["municipio"] = st.text_input("Município — MT", value=c.get("municipio",""))
    with col2:
        c["car_estadual"]    = st.text_input("CAR Estadual",   value=c.get("car_estadual",""))
        c["car_federal"]     = st.text_input("CAR Federal",    value=c.get("car_federal",""))
        c["area_total_ha"]   = st.number_input("Área total (ha)",
                                                value=float(c.get("area_total_ha") or 0),
                                                min_value=0.0, step=0.01)
        c["modulos_fiscais"] = st.number_input("Módulos Fiscais",
                                                value=int(c.get("modulos_fiscais") or 1),
                                                min_value=1, step=1)

    # Indicador do tipo de pessoa
    if c.get("cnpj"):
        st.caption("🏢 Pessoa Jurídica detectada pelo CNPJ")
    elif c.get("cpf"):
        st.caption("👤 Pessoa Física detectada pelo CPF")

    # ── Painel do Demonstrativo CAR ────────────────────────────────────────
    if S.dem_dados.get("areas"):
        st.divider()
        _dem = S.dem_dados
        passivos_dem = _dem.get("passivos_identificados", [])
        total_passivo = _dem.get("total_passivo_ha", 0)

        if passivos_dem:
            st.markdown("**📊 Demonstrativo CAR — Passivos identificados automaticamente:**")
            _pcols = st.columns(len(passivos_dem))
            _COR = {"APPD": "🔴", "ARLD": "🟠", "AURD": "🟡"}
            for _i, _p in enumerate(passivos_dem):
                with _pcols[_i]:
                    st.metric(
                        f"{_COR.get(_p['tipo'], '⚠️')} {_p['tipo']}",
                        f"{_p['area_ha']} ha",
                        help=f"{_p['descricao']} — {_p['base_legal']}"
                    )
            st.caption(f"Passivo total: **{total_passivo} ha**")
        else:
            st.success("✅ Demonstrativo CAR: nenhum passivo identificado.")

        with st.expander("📋 Ver todas as áreas declaradas no Demonstrativo"):
            import pandas as pd
            _df_areas = pd.DataFrame([
                {"Descrição": row["rotulo"],
                 "Área (ha)": row["area_ha"],
                 "Passivo": "⚠️ Sim" if row["passivo"] else ""}
                for row in _dem.get("areas_display", [])
            ])
            st.dataframe(_df_areas, use_container_width=True, hide_index=True)
            if _dem.get("appd_calculado"):
                st.caption("ℹ️ APPD calculada como: APP total − APP Preservada − APP em RL")

    st.divider()
    st.markdown("**Passivos a recuperar:**")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        c["appd_ha"] = st.number_input("APPD (ha)", value=float(c.get("appd_ha") or 0), min_value=0.0, step=0.01)
    with col_b:
        c["arld_ha"] = st.number_input("ARLD (ha)", value=float(c.get("arld_ha") or 0), min_value=0.0, step=0.01)
    with col_c:
        c["aurd_ha"] = st.number_input("AURD (ha)", value=float(c.get("aurd_ha") or 0), min_value=0.0, step=0.01)

    if S.shp_dados.get("centroide_wgs84"):
        ct = S.shp_dados["centroide_wgs84"]
        st.caption(f"Centroide WGS84: lat {ct['lat']:.5f} · lon {ct['lon']:.5f}  "
                   f"({S.shp_dados.get('epsg_origem','?')} → EPSG:4326)")
        c["centroide_lat"] = ct["lat"]
        c["centroide_lon"] = ct["lon"]

    S.cadastro = c

    # ── Salvar proprietário e imóvel no banco ──────────────────────────────
    st.divider()
    with st.expander("💾 Salvar proprietário e imóvel no banco de dados"):
        st.caption("Salva os dados cadastrais no banco local para reuso futuro.")

        # Verifica se já existem no banco
        imovel_existente = db.buscar_imovel_por_car(c.get("car_estadual","")) \
                           if c.get("car_estadual") else None
        prop_existente = db.buscar_proprietario(c.get("cpf",""), c.get("cnpj","")) \
                         if (c.get("cpf") or c.get("cnpj")) else None

        if imovel_existente:
            st.info(f"Imóvel já cadastrado: **{imovel_existente.get('nome_imovel')}** "
                    f"(CAR {imovel_existente.get('car_estadual')})")
        if prop_existente:
            st.info(f"Proprietário já cadastrado: **{prop_existente.get('nome')}**")

        col_sb, col_vr = st.columns(2)
        with col_sb:
            if st.button("💾 Salvar no banco", use_container_width=True, type="primary"):
                prop_id = db.salvar_proprietario({
                    "nome": c.get("proprietario",""),
                    "cpf":  c.get("cpf",""),
                    "cnpj": c.get("cnpj",""),
                })
                db.salvar_imovel({
                    "proprietario_id": prop_id,
                    "nome_imovel":     c.get("imovel",""),
                    "car_estadual":    c.get("car_estadual",""),
                    "car_federal":     c.get("car_federal",""),
                    "municipio":       c.get("municipio",""),
                    "area_total_ha":   c.get("area_total_ha"),
                    "modulos_fiscais": c.get("modulos_fiscais",1),
                })
                st.success("Salvo com sucesso!")
        with col_vr:
            if st.button("📋 Ver banco de imóveis", use_container_width=True):
                imoveis = db.listar_imoveis()
                if imoveis:
                    import pandas as pd
                    st.dataframe(
                        pd.DataFrame(imoveis)[["nome_imovel","proprietario_nome","municipio","area_total_ha","car_estadual"]],
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.caption("Nenhum imóvel salvo ainda.")

    # Aviso se poucos campos foram extraídos
    campos = S.pdf_dados.get("campos_extraidos", {})
    n_extraidos = sum(1 for v in campos.values() if v)
    if S.pdf_dados and n_extraidos < 3:
        with st.expander("⚠️ Poucos campos extraídos do PDF — clique para ver detalhes"):
            st.caption(
                f"{n_extraidos} campo(s) identificado(s). "
                "Verifique se o PDF é um Demonstrativo SIMCAR válido e preencha os campos manualmente acima."
            )
            st.caption("Texto bruto extraído:")
            st.code(S.pdf_dados.get("texto_bruto_truncado", "")[:2000], language=None)

    st.divider()

    col_v, col_p = st.columns(2)
    with col_v:
        if st.button("◀  Voltar", use_container_width=True):
            S.etapa = 0; st.rerun()
    with col_p:
        if st.button("▶  Confirmar e consultar APIs", type="primary",
                      use_container_width=True):
            S.etapa = 2; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 2 — Consulta APIs
# ══════════════════════════════════════════════════════════════════════════════

elif S.etapa == 2:
    st.markdown('<p class="step-title">🌍 Etapa 3 — Consultas às APIs</p>',
                unsafe_allow_html=True)

    car = S.cadastro.get("car_estadual") or S.cadastro.get("car_federal","")
    lat = S.cadastro.get("centroide_lat")
    lon = S.cadastro.get("centroide_lon")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**MapBiomas Alerta**")
        st.caption(f"CAR: `{car or 'não informado'}`")
        cache_mb = db.get_mapbiomas_cache(car) if car else None
        if cache_mb:
            st.success(f"Cache disponível — Marco temporal: **{cache_mb['marco_temporal']}**")
        else:
            st.info("Sem cache. Será consultado ao clicar em Executar.")
    with col2:
        st.markdown("**GBIF + Flora do Brasil**")
        st.caption(f"Centroide: lat {lat:.4f}, lon {lon:.4f}" if lat and lon else "Centroide não disponível")
        cache_gbif = db.get_gbif_cache(lat, lon) if lat and lon else None
        if cache_gbif:
            st.success(f"Cache disponível — {len(cache_gbif)} espécies")
        else:
            st.info("Sem cache. Será consultado ao clicar em Executar.")

    log_area = st.empty()

    def mostrar_log():
        msgs = S.progress_log[-12:]
        log_area.code("\n".join(
            f"{'✅' if s=='success' else '⚠️' if s=='warning' else '⏳'} {m}"
            for m, s in msgs
        ), language=None)

    st.divider()
    col_v, col_r, col_p = st.columns([1, 2, 1])
    with col_v:
        if st.button("◀  Voltar", use_container_width=True):
            S.etapa = 1; st.rerun()
    with col_r:
        executar = st.button("🔄 Executar consultas",
                              type="primary", use_container_width=True,
                              disabled=S.rodando)
    with col_p:
        pular = st.button("▶  Pular (usar cache)", use_container_width=True)

    if pular:
        if cache_mb:
            S.mapbiomas = cache_mb
        if cache_gbif:
            S.especies = cache_gbif
        S.etapa = 3; st.rerun()

    if executar and not S.rodando:
        S.progress_log = []
        S.rodando = True

        def _progress(msg, status="info"):
            S.progress_log.append((msg, status))

        with st.spinner("Consultando APIs..."):
            # MapBiomas
            if car:
                S.mapbiomas = pipeline.consultar_mapbiomas(car, S.diretorio, _progress)
            # GBIF
            if lat and lon:
                S.especies = pipeline.consultar_gbif(lat, lon, S.diretorio,
                                                      progress=_progress)
                if S.especies:
                    _progress("Enriquecendo com Flora do Brasil (top 40)...", "info")
                    S.especies = pipeline.enriquecer_especies(
                        S.especies[:40], S.diretorio, _progress)

        S.rodando = False
        mostrar_log()
        S.etapa = 3
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 3 — Florística (editável)
# ══════════════════════════════════════════════════════════════════════════════

elif S.etapa == 3:
    st.markdown('<p class="step-title">🌿 Etapa 4 — Lista florística</p>',
                unsafe_allow_html=True)
    st.caption("Edite a lista: ajuste grupo sucessional, dispersão e inclua/exclua espécies.")

    if not S.especies:
        st.warning("Nenhuma espécie carregada. Volte à etapa anterior ou adicione manualmente.")

    import pandas as pd

    # Garante colunas mínimas
    cols = ["nome_cientifico", "nome_popular", "familia",
            "grupo_sucessional", "dispersao", "incluir"]
    df_base = []
    for sp in S.especies:
        df_base.append({
            "nome_cientifico":  sp.get("nome_cientifico", ""),
            "nome_popular":     sp.get("nome_popular", ""),
            "familia":          sp.get("familia", ""),
            "grupo_sucessional": sp.get("grupo_sucessional", "indefinida"),
            "dispersao":        sp.get("dispersao", "indefinida"),
            "incluir":          True,
        })

    df = pd.DataFrame(df_base, columns=cols) if df_base else pd.DataFrame(columns=cols)

    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "grupo_sucessional": st.column_config.SelectboxColumn(
                "Grupo Suc.",
                options=["pioneira", "não-pioneira", "indefinida"],
                required=True,
            ),
            "dispersao": st.column_config.SelectboxColumn(
                "Dispersão",
                options=["zoocórica", "anemocórica", "autocórica", "indefinida"],
                required=True,
            ),
            "incluir": st.column_config.CheckboxColumn("Incluir", default=True),
        },
        hide_index=True,
        key="tabela_especies",
    )

    # Métricas do consórcio em tempo real
    df_incl = edited[edited["incluir"] == True]
    consorcio = rules.validar_consorcio(df_incl.to_dict("records"))
    tem_especies = consorcio["total_especies"] > 0
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Espécies selecionadas", consorcio["total_especies"])
    m2.metric("Pioneiras", f"{consorcio['percentual_pioneiras']}%" if tem_especies else "—",
              delta="≥50% exigido" if tem_especies and consorcio['percentual_pioneiras'] < 50 else None,
              delta_color="inverse")
    m3.metric("Zoocóricas", f"{consorcio['percentual_zoocoricas']}%" if tem_especies else "—",
              delta="≥30% exigido" if tem_especies and consorcio['percentual_zoocoricas'] < 30 else None,
              delta_color="inverse")
    m4.metric("Conforme SEMA-MT",
              "✅ Sim" if tem_especies and consorcio["conforme"] else
              ("⚠️ Não" if tem_especies else "— sem dados"))

    if tem_especies and consorcio["alertas"]:
        for alerta in consorcio["alertas"]:
            st.warning(alerta)

    st.divider()
    col_v, col_p = st.columns(2)
    with col_v:
        if st.button("◀  Voltar", use_container_width=True):
            S.etapa = 2; st.rerun()
    with col_p:
        if st.button("▶  Confirmar lista", type="primary", use_container_width=True):
            S.especies = df_incl.drop(columns=["incluir"]).to_dict("records")
            S.etapa = 4; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 4 — Metodologia SIMCAR (editável)
# ══════════════════════════════════════════════════════════════════════════════

elif S.etapa == 4:
    st.markdown('<p class="step-title">⚙️  Etapa 5 — Metodologia SIMCAR</p>',
                unsafe_allow_html=True)

    c     = S.cadastro
    mf    = c.get("modulos_fiscais", 1)
    marco = S.mapbiomas.get("marco_temporal", "indefinido")
    faixa_auto = rules.faixa_recuperacao_appd(mf)

    appd_ha = float(c.get("appd_ha") or 0)
    aurd_ha = float(c.get("aurd_ha") or 0)
    arld_ha = float(c.get("arld_ha") or 0)

    # ── Listas SIMCAR ─────────────────────────────────────────────────────────
    FITOECOLOGIA = ["Cerrado", "Amazônia", "Ecótono Cerrado/Amazônia"]
    FITOFISIONOMIA = {
        "Cerrado": [
            "Savana Arborizada",
            "Savana Parque",
            "Savana Gramíneo-Lenhosa",
            "Savana Estépica Parque",
            "Savana Estépica Gramíneo-Lenhosa",
            "Vegetação com influência fluvial e/ou lacustre",
            "Contato Savana/Savana Estépica",
        ],
        "Amazônia": [
            "Floresta Ombrófila Aberta",
            "Floresta Ombrófila Densa",
            "Floresta Estacional Semidecidual",
            "Floresta Estacional Decidual",
            "Contato Savana/Floresta Ombrófila",
        ],
        "Ecótono Cerrado/Amazônia": [
            "Contato Savana/Floresta Ombrófila",
            "Floresta Estacional Semidecidual",
            "Savana Arborizada",
        ],
    }
    CARACT_AREA = [
        "Existe aceiro na propriedade",
        "Não existe aceiro na propriedade",
        "A condição atual da área degrada é capoeira ou capoeirão",
        "A condição atual da área degrada é pasto sujo ou arborizado",
        "A condição atual da área degrada é pasto",
        "A condição atual da área degrada é silvipastoril",
        "A condição atual da área degrada é silvicultura",
        "A condição atual da área degrada é agricultura",
        "O relevo da área recuperada possui Declive Suave",
        "O relevo da área recuperada possui Declive Íngrime",
        "Não existem processos erosivos instalados na área",
        "Existem sulcos na área",
        "Existem ravinas na área",
        "Existem voçorocas na área",
        "A distância do fragmento de vegetação nativa mais próximo é de até 50 m",
        "A distância do fragmento de vegetação nativa mais próximo é acima de 50 m",
        "O solo da área a ser recuperada esta em condições Compacta",
        "O solo da área a ser recuperada não esta em condições Compacta",
    ]
    TECNICAS_APPD = [
        "Isolamento da área (retirada do agente degradador)",
        "Cercamento da área",
        "Condução de regeneração natural assistida",
        "Plantio de espécies nativas",
        "Nucleação",
        "Semeadura direta",
        "Transplantio de plântulas",
        "Enriquecimento de capoeira",
        "Plantio intercalado com exóticas de ciclo curto (Art. 61-A §13)",
        "Controle de espécies invasoras",
        "Subsolagem / preparo de solo",
        "Adubação orgânica",
    ]
    TECNICAS_ARLD = [
        "Isolamento da área (retirada do agente degradador)",
        "Cercamento da área",
        "Condução de regeneração natural assistida",
        "Plantio de espécies nativas",
        "Nucleação",
        "Semeadura direta",
        "Transplantio de plântulas",
        "Enriquecimento de capoeira",
        "Controle de espécies invasoras",
        "Subsolagem / preparo de solo",
        "Adubação orgânica",
    ]
    TECNICAS_AURD = [
        "Isolamento da área (retirada do agente degradador)",
        "Manejo sustentável da vegetação nativa",
        "Condução de regeneração natural assistida",
        "Cercamento da área",
        "Controle de espécies invasoras",
        "Recuperação de processos erosivos",
        "Adubação orgânica",
    ]

    def _bloco_veg(sufixo: str, fito_default: str = "Cerrado") -> tuple:
        """Renderiza seleção de Fitoecologia + Fitofisionomia. Retorna (fito, fitofisio)."""
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fito = st.selectbox("Fitoecologia *", FITOECOLOGIA,
                                index=FITOECOLOGIA.index(fito_default)
                                if fito_default in FITOECOLOGIA else 0,
                                key=f"fito_{sufixo}")
        with col_f2:
            opts_fisio = FITOFISIONOMIA.get(fito, FITOFISIONOMIA["Cerrado"])
            fitofisio = st.selectbox("Fitofisionomia *", opts_fisio,
                                     key=f"fitofisio_{sufixo}")
        return fito, fitofisio

    # ═══════════════════════════════════════════════════
    # ABA 3 — APPD
    # ═══════════════════════════════════════════════════
    st.subheader(f"Aba 3 — APPD  ({appd_ha} ha)")
    if appd_ha == 0:
        st.caption("Nenhum passivo APPD identificado. Preencha manualmente se necessário.")

    fito_appd, fitofisio_appd = _bloco_veg("appd")

    col1, col2 = st.columns(2)
    with col1:
        met_appd = st.selectbox("Método de recuperação",
            ["Condução de Regeneração Natural Assistida",
             "Plantio de Espécies Nativas",
             "Plantio Intercalado (nativas + exóticas)"],
            index=1 if "pós" in marco.lower() else 0,
            key="met_appd")
    with col2:
        faixa = st.number_input("Faixa de recuperação (m)",
                                 value=faixa_auto, min_value=5, step=1,
                                 key="faixa_appd",
                                 help=f"Calculado automaticamente: {faixa_auto}m para {mf} MF")

    caract_appd = st.multiselect("Características da Área *", CARACT_AREA,
                                  key="caract_appd")
    tecnicas_appd = st.multiselect("Técnicas a serem utilizadas *", TECNICAS_APPD,
                                    key="tec_appd")
    just_appd = st.text_input("Justificativa APPD",
                               value=f"Imóvel com {mf} MF — Art. 61-A da Lei 12.651/2012",
                               key="just_appd")

    # ═══════════════════════════════════════════════════
    # ABA 4 — AURD
    # ═══════════════════════════════════════════════════
    st.divider()
    st.subheader(f"Aba 4 — AURD  ({aurd_ha} ha)")
    if aurd_ha == 0:
        st.caption("Nenhum passivo AURD identificado. Preencha manualmente se necessário.")

    fito_aurd, fitofisio_aurd = _bloco_veg("aurd")

    tipo_aurd = st.selectbox("Tipo de restrição",
        ["nenhuma", "Pantanal", "Vale do Guaporé", "Declividade >25°", "outro"],
        key="tipo_aurd")
    caract_aurd = st.multiselect("Características da Área *", CARACT_AREA,
                                  key="caract_aurd")
    tecnicas_aurd = st.multiselect("Técnicas a serem utilizadas *", TECNICAS_AURD,
                                    key="tec_aurd")
    met_aurd = "Manejo sustentável / Regeneração natural (vedado corte raso)"

    # ═══════════════════════════════════════════════════
    # ABA 5 — ARLD
    # ═══════════════════════════════════════════════════
    st.divider()
    st.subheader(f"Aba 5 — ARLD  ({arld_ha} ha)")
    if arld_ha == 0:
        st.caption("Nenhum passivo ARLD identificado. Preencha manualmente se necessário.")

    fito_arld, fitofisio_arld = _bloco_veg("arld")

    alt_arld = st.selectbox("Alternativa legal (Art. 66, Lei 12.651/2012)",
        rules.ALTERNATIVAS_ARLD, key="alt_arld")
    prazo_arld = st.number_input("Prazo de execução (anos)", value=20,
                                  min_value=1, max_value=20, key="prazo_arld")
    caract_arld = st.multiselect("Características da Área *", CARACT_AREA,
                                  key="caract_arld")
    tecnicas_arld = st.multiselect("Técnicas a serem utilizadas *", TECNICAS_ARLD,
                                    key="tec_arld")
    just_arld = st.text_area("Justificativa ARLD",
                              value="Área com condições físicas para plantio de espécies nativas.",
                              height=80, key="just_arld")

    # ═══════════════════════════════════════════════════
    # ABA 6 — Compensação
    # ═══════════════════════════════════════════════════
    st.divider()
    st.subheader("Aba 6 — Compensação")
    tem_comp = st.checkbox("Possui compensação via CRA ou equivalente")
    comp_dados = None
    if tem_comp:
        col1, col2 = st.columns(2)
        with col1:
            tipo_comp = st.selectbox("Tipo", ["CRA", "Doação à União", "Imóvel equivalente"])
            area_comp = st.number_input("Área compensada (ha)", min_value=0.0, step=0.01)
        with col2:
            local_comp  = st.text_input("Localização da área compensatória")
            status_comp = st.selectbox("Status", ["pendente", "aprovado SEMA-MT"])
        comp_dados = {"tipo": tipo_comp, "area_ha": area_comp,
                      "localizacao": local_comp, "status_aprovacao": status_comp}

    st.divider()
    col_v, col_p = st.columns(2)
    with col_v:
        if st.button("◀  Voltar", use_container_width=True):
            S.etapa = 3; st.rerun()
    with col_p:
        if st.button("▶  Confirmar metodologia", type="primary", use_container_width=True):
            S.metodologia = {
                "aba3_appd": {
                    "metodo": met_appd,
                    "faixa_m": faixa,
                    "justificativa": just_appd,
                    "fitoecologia": fito_appd,
                    "fitofisionomia": fitofisio_appd,
                    "caracteristicas_area": caract_appd,
                    "tecnicas": tecnicas_appd,
                },
                "aba4_aurd": {
                    "metodo": met_aurd,
                    "tipo_restricao": tipo_aurd,
                    "fitoecologia": fito_aurd,
                    "fitofisionomia": fitofisio_aurd,
                    "caracteristicas_area": caract_aurd,
                    "tecnicas": tecnicas_aurd,
                },
                "aba5_arld": {
                    "alternativa_legal": alt_arld,
                    "justificativa": just_arld,
                    "prazo_anos": prazo_arld,
                    "fitoecologia": fito_arld,
                    "fitofisionomia": fitofisio_arld,
                    "caracteristicas_area": caract_arld,
                    "tecnicas": tecnicas_arld,
                },
                "aba6_compensacao": comp_dados,
            }
            S.etapa = 5; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 5 — Orçamento e cronograma (editável)
# ══════════════════════════════════════════════════════════════════════════════

elif S.etapa == 5:
    st.markdown('<p class="step-title">💰 Etapa 6 — Orçamento & Cronograma</p>',
                unsafe_allow_html=True)

    import pandas as pd

    c = S.cadastro
    appd = c.get("appd_ha", 0)
    arld = c.get("arld_ha", 0)
    aurd = c.get("aurd_ha", 0)
    orc  = rules.calcular_orcamento(appd, arld, aurd)

    st.subheader("Estimativa de custos")
    st.caption("Referência: IMEA-MT / SEAF-MT. Edite os valores se necessário.")

    col1, col2 = st.columns(2)
    with col1:
        custo_mudas    = st.number_input("Mudas (R$)",        value=float(orc["custo_mudas_R$"]),    step=100.0)
        custo_insumos  = st.number_input("Insumos solo (R$)", value=float(orc["custo_insumos_solo_R$"]), step=50.0)
        custo_cerca    = st.number_input("Cercamento (R$)",   value=float(orc["custo_cercamento_R$"]),  step=50.0)
    with col2:
        custo_maquina  = st.number_input("Horas-máquina (R$)", value=float(orc["custo_horas_maquina_R$"]), step=50.0)
        custo_monitor  = st.number_input("Monitoramento (R$)", value=float(orc["custo_monitoramento_R$"]),  step=100.0)
        total_calc = custo_mudas + custo_insumos + custo_cerca + custo_maquina + custo_monitor
        st.metric("Total estimado", f"R$ {total_calc:,.2f}")

    st.divider()
    st.subheader("Cronograma físico-financeiro")
    st.caption("Todas as operações de plantio: outubro a março (período chuvoso MT).")

    prazo = getattr(S, "metodologia", {}).get("aba5_arld", {}).get("prazo_anos", 20) if hasattr(S, "metodologia") else 20
    crono = rules.gerar_cronograma(appd, arld, prazo)

    df_crono = pd.DataFrame(crono)
    edited_crono = st.data_editor(df_crono, use_container_width=True,
                                   num_rows="fixed", hide_index=True,
                                   key="tabela_cronograma")

    st.divider()
    col_v, col_p = st.columns(2)
    with col_v:
        if st.button("◀  Voltar", use_container_width=True):
            S.etapa = 4; st.rerun()
    with col_p:
        if st.button("▶  Confirmar orçamento", type="primary", use_container_width=True):
            S.orcamento_editado = {
                "area_plantio_ha":       appd + arld + aurd,
                "mudas_total":           orc["mudas_total"],
                "custo_mudas_R$":        custo_mudas,
                "custo_insumos_solo_R$": custo_insumos,
                "custo_cercamento_R$":   custo_cerca,
                "custo_horas_maquina_R$": custo_maquina,
                "custo_monitoramento_R$": custo_monitor,
                "total_estimado_R$":     round(total_calc, 2),
                "referencia_precos":     "IMEA-MT / SEAF-MT",
            }
            S.cronograma_editado = edited_crono.to_dict("records")
            S.etapa = 6; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ETAPA 6 — Gerar PRADA
# ══════════════════════════════════════════════════════════════════════════════

elif S.etapa == 6:
    st.markdown('<p class="step-title">📄 Etapa 7 — Gerar PRADA oficial</p>',
                unsafe_allow_html=True)

    c = S.cadastro
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Proprietário", c.get("proprietario","—")[:20])
    m2.metric("Imóvel", c.get("imovel","—")[:20])
    m3.metric("APPD", f"{c.get('appd_ha',0)} ha")
    m4.metric("ARLD", f"{c.get('arld_ha',0)} ha")
    m5.metric("Espécies", len(S.especies))

    nome_saida = st.text_input(
        "Nome do arquivo de saída (sem extensão)",
        value=f"PRADA_{c.get('imovel','Projeto').replace(' ','_')}"
    )

    st.divider()

    col_v, col_g = st.columns(2)
    with col_v:
        if st.button("◀  Voltar", use_container_width=True):
            S.etapa = 5; st.rerun()
    with col_g:
        gerar = st.button("📄 Gerar PRADA (.md + .docx)",
                           type="primary", use_container_width=True)

    if gerar:
        met = getattr(S, "metodologia", None)
        draft = pipeline.montar_draft(S.cadastro, S.mapbiomas, S.especies, met)

        # Substitui orçamento e cronograma editados
        if hasattr(S, "orcamento_editado"):
            draft["orcamento_preliminar"] = S.orcamento_editado
        if hasattr(S, "cronograma_editado"):
            draft["abas_simcar"]["aba7_prazos"]["cronograma"] = S.cronograma_editado

        # Salva draft no arquivo e no banco
        diretorio = S.diretorio
        draft_path = Path(diretorio) / "prada_draft.json"
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)

        if S.projeto_id:
            db.salvar_draft(S.projeto_id, draft)

        # Gera .md e .docx
        with st.spinner("Gerando documento..."):
            r = execute_tool("gerar_documento_final",
                              {"nome_arquivo_saida": nome_saida}, diretorio)

        if "resultado" in r:
            res = r["resultado"]
            st.success(res.get("mensagem","Gerado com sucesso."))

            # Download .docx
            docx_path = Path(res.get("arquivo_docx", ""))
            if docx_path.exists():
                with open(docx_path, "rb") as f:
                    st.download_button(
                        "⬇️  Baixar PRADA.docx",
                        data=f,
                        file_name=docx_path.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                        type="primary",
                    )

            # Preview markdown
            md_path = Path(res.get("arquivo_md", ""))
            if md_path.exists():
                with st.expander("📝 Prévia do documento"):
                    st.markdown(md_path.read_text(encoding="utf-8"))
        else:
            st.error(f"Erro ao gerar: {r.get('erro','desconhecido')}")
