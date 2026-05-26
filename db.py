"""
Camada de persistência SQLite para o Agente PRADA.
Cache de APIs + histórico de projetos e drafts.
"""

import json
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "prada.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS projetos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            car_estadual    TEXT,
            car_federal     TEXT,
            proprietario    TEXT,
            imovel          TEXT,
            municipio       TEXT,
            area_total_ha   REAL,
            modulos_fiscais INTEGER DEFAULT 1,
            appd_ha         REAL DEFAULT 0,
            aurd_ha         REAL DEFAULT 0,
            arld_ha         REAL DEFAULT 0,
            centroide_lat   REAL,
            centroide_lon   REAL,
            shp_path        TEXT,
            pdf_path        TEXT,
            criado_em       TEXT
        );

        CREATE TABLE IF NOT EXISTS mapbiomas_cache (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            car_codigo      TEXT UNIQUE,
            marco_temporal  TEXT,
            tipologia       TEXT,
            alertas_json    TEXT,
            status          TEXT,
            criado_em       TEXT
        );

        CREATE TABLE IF NOT EXISTS especies_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bbox_hash   TEXT UNIQUE,
            dados_json  TEXT,
            criado_em   TEXT
        );

        CREATE TABLE IF NOT EXISTS flora_cache (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_cientifico     TEXT UNIQUE,
            habito              TEXT,
            grupo_sucessional   TEXT,
            dispersao           TEXT,
            dados_json          TEXT,
            criado_em           TEXT
        );

        CREATE TABLE IF NOT EXISTS prada_drafts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id  INTEGER,
            draft_json  TEXT,
            versao      INTEGER DEFAULT 1,
            criado_em   TEXT,
            FOREIGN KEY (projeto_id) REFERENCES projetos(id)
        );

        CREATE TABLE IF NOT EXISTS proprietarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT NOT NULL,
            cpf         TEXT,
            cnpj        TEXT,
            tipo_pessoa TEXT,
            criado_em   TEXT
        );

        CREATE TABLE IF NOT EXISTS imoveis (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            proprietario_id INTEGER,
            nome_imovel     TEXT,
            car_estadual    TEXT UNIQUE,
            car_federal     TEXT,
            municipio       TEXT,
            area_total_ha   REAL,
            modulos_fiscais INTEGER DEFAULT 1,
            criado_em       TEXT,
            FOREIGN KEY (proprietario_id) REFERENCES proprietarios(id)
        );
        """)


# ── Projetos ──────────────────────────────────────────────────────────────────

def salvar_projeto(dados: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO projetos
              (car_estadual, car_federal, proprietario, imovel, municipio,
               area_total_ha, modulos_fiscais, appd_ha, aurd_ha, arld_ha,
               centroide_lat, centroide_lon, shp_path, pdf_path, criado_em)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            dados.get("car_estadual"), dados.get("car_federal"),
            dados.get("proprietario"), dados.get("imovel"),
            dados.get("municipio"), dados.get("area_total_ha"),
            dados.get("modulos_fiscais", 1),
            dados.get("appd_ha", 0), dados.get("aurd_ha", 0),
            dados.get("arld_ha", 0), dados.get("centroide_lat"),
            dados.get("centroide_lon"), dados.get("shp_path"),
            dados.get("pdf_path"), datetime.now().isoformat(),
        ))
        return cur.lastrowid


def atualizar_projeto(projeto_id: int, dados: dict) -> None:
    campos = {k: v for k, v in dados.items() if k not in ("id", "criado_em")}
    sets = ", ".join(f"{k}=?" for k in campos)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE projetos SET {sets} WHERE id=?",
            list(campos.values()) + [projeto_id]
        )


def listar_projetos() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM projetos ORDER BY criado_em DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def buscar_projeto(projeto_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM projetos WHERE id=?", (projeto_id,)
        ).fetchone()
    return dict(row) if row else None


# ── Cache MapBiomas ───────────────────────────────────────────────────────────

def get_mapbiomas_cache(car: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM mapbiomas_cache WHERE car_codigo=?", (car,)
        ).fetchone()
    if not row:
        return None
    r = dict(row)
    r["alertas"] = json.loads(r.pop("alertas_json") or "[]")
    return r


def set_mapbiomas_cache(car: str, dados: dict) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO mapbiomas_cache
              (car_codigo, marco_temporal, tipologia, alertas_json, status, criado_em)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(car_codigo) DO UPDATE SET
              marco_temporal=excluded.marco_temporal,
              tipologia=excluded.tipologia,
              alertas_json=excluded.alertas_json,
              status=excluded.status,
              criado_em=excluded.criado_em
        """, (
            car,
            dados.get("marco_temporal", "indefinido"),
            dados.get("tipologia", ""),
            json.dumps(dados.get("alertas", []), ensure_ascii=False),
            dados.get("status", "ok"),
            datetime.now().isoformat(),
        ))


# ── Cache GBIF ────────────────────────────────────────────────────────────────

def _bbox_hash(lat: float, lon: float, raio: float = 0.45) -> str:
    key = f"{round(lat,2)},{round(lon,2)},{raio}"
    return hashlib.md5(key.encode()).hexdigest()


def get_gbif_cache(lat: float, lon: float, raio: float = 0.45) -> list | None:
    h = _bbox_hash(lat, lon, raio)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT dados_json FROM especies_cache WHERE bbox_hash=?", (h,)
        ).fetchone()
    return json.loads(row["dados_json"]) if row else None


def set_gbif_cache(lat: float, lon: float, especies: list, raio: float = 0.45) -> None:
    h = _bbox_hash(lat, lon, raio)
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO especies_cache (bbox_hash, dados_json, criado_em)
            VALUES (?,?,?)
            ON CONFLICT(bbox_hash) DO UPDATE SET
              dados_json=excluded.dados_json,
              criado_em=excluded.criado_em
        """, (h, json.dumps(especies, ensure_ascii=False), datetime.now().isoformat()))


# ── Cache Flora do Brasil ─────────────────────────────────────────────────────

def get_flora_cache(nome: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM flora_cache WHERE nome_cientifico=?", (nome,)
        ).fetchone()
    return dict(row) if row else None


def set_flora_cache(nome: str, dados: dict) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO flora_cache
              (nome_cientifico, habito, grupo_sucessional, dispersao, dados_json, criado_em)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(nome_cientifico) DO UPDATE SET
              habito=excluded.habito,
              grupo_sucessional=excluded.grupo_sucessional,
              dispersao=excluded.dispersao,
              dados_json=excluded.dados_json,
              criado_em=excluded.criado_em
        """, (
            nome,
            dados.get("habito", ""),
            dados.get("grupo_sucessional", "indefinida"),
            dados.get("dispersao", "indefinida"),
            json.dumps(dados, ensure_ascii=False),
            datetime.now().isoformat(),
        ))


# ── Proprietários ────────────────────────────────────────────────────────────

def salvar_proprietario(dados: dict) -> int:
    """Insere ou atualiza proprietário pelo CPF ou CNPJ."""
    cpf  = dados.get("cpf", "")
    cnpj = dados.get("cnpj", "")
    tipo = "juridica" if cnpj else "fisica"
    with get_conn() as conn:
        # Verifica se já existe
        row = None
        if cpf:
            row = conn.execute("SELECT id FROM proprietarios WHERE cpf=?", (cpf,)).fetchone()
        if not row and cnpj:
            row = conn.execute("SELECT id FROM proprietarios WHERE cnpj=?", (cnpj,)).fetchone()
        if row:
            conn.execute(
                "UPDATE proprietarios SET nome=?, cpf=?, cnpj=?, tipo_pessoa=? WHERE id=?",
                (dados.get("nome",""), cpf, cnpj, tipo, row["id"])
            )
            return row["id"]
        cur = conn.execute(
            "INSERT INTO proprietarios (nome, cpf, cnpj, tipo_pessoa, criado_em) VALUES (?,?,?,?,?)",
            (dados.get("nome",""), cpf, cnpj, tipo, datetime.now().isoformat())
        )
        return cur.lastrowid


def buscar_proprietario(cpf: str = "", cnpj: str = "") -> dict | None:
    with get_conn() as conn:
        row = None
        if cpf:
            row = conn.execute("SELECT * FROM proprietarios WHERE cpf=?", (cpf,)).fetchone()
        if not row and cnpj:
            row = conn.execute("SELECT * FROM proprietarios WHERE cnpj=?", (cnpj,)).fetchone()
    return dict(row) if row else None


def listar_proprietarios() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM proprietarios ORDER BY nome").fetchall()
    return [dict(r) for r in rows]


# ── Imóveis ───────────────────────────────────────────────────────────────────

def salvar_imovel(dados: dict) -> int:
    """Insere ou atualiza imóvel pelo CAR estadual."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM imoveis WHERE car_estadual=?", (dados.get("car_estadual",""),)
        ).fetchone()
        if row:
            conn.execute("""
                UPDATE imoveis SET proprietario_id=?, nome_imovel=?, car_federal=?,
                  municipio=?, area_total_ha=?, modulos_fiscais=? WHERE id=?
            """, (
                dados.get("proprietario_id"), dados.get("nome_imovel",""),
                dados.get("car_federal",""), dados.get("municipio",""),
                dados.get("area_total_ha"), dados.get("modulos_fiscais",1),
                row["id"]
            ))
            return row["id"]
        cur = conn.execute("""
            INSERT INTO imoveis
              (proprietario_id, nome_imovel, car_estadual, car_federal,
               municipio, area_total_ha, modulos_fiscais, criado_em)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            dados.get("proprietario_id"), dados.get("nome_imovel",""),
            dados.get("car_estadual",""), dados.get("car_federal",""),
            dados.get("municipio",""), dados.get("area_total_ha"),
            dados.get("modulos_fiscais",1), datetime.now().isoformat()
        ))
        return cur.lastrowid


def buscar_imovel_por_car(car_estadual: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT i.*, p.nome as proprietario_nome, p.cpf, p.cnpj "
            "FROM imoveis i LEFT JOIN proprietarios p ON i.proprietario_id=p.id "
            "WHERE i.car_estadual=?", (car_estadual,)
        ).fetchone()
    return dict(row) if row else None


def listar_imoveis() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT i.*, p.nome as proprietario_nome
            FROM imoveis i LEFT JOIN proprietarios p ON i.proprietario_id=p.id
            ORDER BY i.nome_imovel
        """).fetchall()
    return [dict(r) for r in rows]


# ── Drafts ────────────────────────────────────────────────────────────────────

def salvar_draft(projeto_id: int, draft: dict) -> int:
    with get_conn() as conn:
        versao = (conn.execute(
            "SELECT COALESCE(MAX(versao),0)+1 FROM prada_drafts WHERE projeto_id=?",
            (projeto_id,)
        ).fetchone()[0])
        cur = conn.execute("""
            INSERT INTO prada_drafts (projeto_id, draft_json, versao, criado_em)
            VALUES (?,?,?,?)
        """, (projeto_id, json.dumps(draft, ensure_ascii=False),
              versao, datetime.now().isoformat()))
        return cur.lastrowid


def get_ultimo_draft(projeto_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT draft_json FROM prada_drafts
            WHERE projeto_id=? ORDER BY versao DESC LIMIT 1
        """, (projeto_id,)).fetchone()
    return json.loads(row["draft_json"]) if row else None


# Inicializa o banco ao importar
init_db()
