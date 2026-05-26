# 🌿 Agente PRADA — SIMCAR MT

Ferramenta desktop para elaboração de **Projetos de Regularização Ambiental (PRADA)** no fluxo SIMCAR-MT, sem dependência de IA generativa no fluxo principal.

Processa Shapefile + PDF SIMCAR + Demonstrativo do CAR → consulta APIs públicas → gera PRADA completo em `.docx`.

---

## Funcionalidades

| Etapa | O que faz |
|---|---|
| **Arquivos** | Importa Shapefile, PDF SIMCAR e Demonstrativo de Informações do CAR |
| **Cadastro** | Extrai automaticamente proprietário, CPF/CNPJ, CAR estadual/federal, área total, passivos |
| **Passivos** | Identifica APPD, ARLD e AURD automaticamente a partir do Demonstrativo CAR |
| **APIs** | Consulta MapBiomas Alerta (marco temporal), GBIF (flora nativa) e Flora do Brasil (grupo sucessional) |
| **Florística** | Lista editável de espécies com validação SEMA-MT (≥20 spp, ≥50% pioneiras, ≥30% zoocóricas) |
| **Metodologia** | Preenche Abas 3-6 do SIMCAR: Fitoecologia, Fitofisionomia, Características da Área, Técnicas por passivo |
| **Orçamento** | Estimativa de custos (IMEA-MT) + cronograma físico-financeiro editável |
| **Documento** | Gera PRADA `.md` + `.docx` (via pandoc) com todos os 11 tópicos do TR SEMA-MT |

### Cache SQLite local
Todas as consultas a APIs são armazenadas em `prada.db` — rodar offline em consultas repetidas ao mesmo imóvel.

---

## Pré-requisitos

- Python 3.11+
- [pandoc](https://pandoc.org/installing.html) (opcional, para gerar `.docx`)

```bash
pip install -r requirements.txt
```

**Dependências:**

```
streamlit
requests
pdfplumber
pyshp
shapely
pyproj
python-dotenv
pandas
```

---

## Instalação

```bash
git clone https://github.com/williamhcardoso/prada-agent.git
cd prada-agent
pip install -r requirements.txt
```

Crie o arquivo `.env` na raiz (somente se usar o `agent.py` com IA):

```env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Uso

### Interface gráfica (recomendado)

**Windows** — duplo clique em `iniciar_prada.vbs`  
Abre o Streamlit em segundo plano e lança o browser automaticamente.

**Terminal:**

```bash
python -m streamlit run app.py
```

Acesse: [http://localhost:8501](http://localhost:8501)

### Fluxo de trabalho

1. **Arquivos** — selecione o `.shp`, o PDF SIMCAR e (opcional) o Demonstrativo do CAR
2. **Cadastro** — revise os dados extraídos automaticamente; os passivos são preenchidos pelo Demonstrativo
3. **APIs** — consulte MapBiomas + GBIF ou use o cache local
4. **Florística** — ajuste grupo sucessional e dispersão na tabela editável
5. **Metodologia** — preencha Fitoecologia, Fitofisionomia, Características da Área e Técnicas para cada passivo (Abas 3, 4, 5 SIMCAR)
6. **Orçamento** — edite custos e cronograma
7. **Gerar PRADA** — baixe o `.docx` pronto para assinar

---

## Estrutura do projeto

```
prada-agent/
├── app.py            # Interface Streamlit (7 etapas)
├── pipeline.py       # Orquestração do fluxo principal
├── tools.py          # Ferramentas: leitura de SHP/PDF, APIs, geração de documento
├── db.py             # Camada SQLite (cache + histórico de projetos)
├── rules.py          # Regras do Código Florestal (faixas, prazos, consórcio)
├── agent.py          # Modo agente com IA (Anthropic SDK) — opcional
├── main.py           # Entrada CLI
├── iniciar_prada.vbs # Launcher silencioso Windows
└── requirements.txt
```

---

## APIs utilizadas

| API | Uso | Autenticação |
|---|---|---|
| [MapBiomas Alerta](https://plataforma.alerta.mapbiomas.org) | Marco temporal de desmatamento | Pública (GraphQL) |
| [GBIF](https://www.gbif.org/developer/occurrence) | Ocorrências de flora nativa por coordenada | Pública (REST) |
| [Flora do Brasil 2020 (JBRJ)](https://floradobrasil.jbrj.gov.br) | Hábito e grupo sucessional de espécies | Pública (REST) |

---

## Legislação de referência

- Lei Federal nº 12.651/2012 — Código Florestal (Arts. 61-A, 66, 78-A)
- Resolução CONAMA nº 429/2011 — Metodologias de restauração
- Lei Complementar MT nº 592/2017 e Decreto MT nº 1.031/2017
- Termos de Referência SEMA-MT para PRADA (versão vigente)

---

## Licença

MIT
