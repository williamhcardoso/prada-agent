# ANÁLISE ESTRATÉGICA — FAZENDA CULUENO
**CAR:** MT-5103858-D30C43BA77D949E09F7F431DFED8AF01 | **Município:** Gaúcha do Norte – MT  
**Área:** 738,29 ha (SHP) / 734,40 ha (CAR) | **8,16 MF** (MF = 90 ha) | **Bioma:** Amazônia  
**Data da análise:** 25/05/2026 | **Análise SHP:** 26/05/2026

---

## SITUAÇÃO ATUAL DO IMÓVEL

| Item | Dado |
|---|---|
| CAR Estadual | MT105306/2022 |
| Bioma | Amazônia (Floresta 649 ha + Cerrado/Ecótono 78 ha) |
| RL exigida (Floresta 80%) | 519,47 ha |
| RL exigida (Cerrado 35%) | 27,32 ha |
| RL declarada (Floresta) | 409,87 ha |
| RL declarada (Cerrado) | 36,22 ha |
| Superávit Cerrado | +8,90 ha |
| Déficit Floresta | -109,60 ha |
| **Déficit Líquido RL** | **-100,70 ha** |
| APPD declarada | 16,307 ha |
| **APPD obrigação real (20m)** | **2,30 ha** ← calculado por SHP |
| **APPD dispensada (Art. 61-A §2)** | **14,09 ha (86%)** |
| ARLD | 0 ha (sem passivo de RL no imóvel) |
| AURD | 0 ha |
| Marco temporal APPD | **CONSOLIDADA antes de 22/07/2008** ✅ |

---

## PASSIVO 1 — APPD (16,307 ha)

### O que é
Área de Preservação Permanente com Passivo: porção de APP que foi suprimida antes de 22/07/2008 e que precisa de recomposição parcial conforme Art. 61-A do Código Florestal.

### Marco temporal confirmado
- Desmatamento ocorreu entre **1997–2000** (MapBiomas LULC série histórica)
- Zero alertas de desmatamento 2019–2026 (MapBiomas Alerta)
- Área de Agropecuária em 2008: **281 ha** — idêntica a 2024: **277 ha**
- **Conclusão:** área consolidada antes de 22/07/2008, Art. 61-A §2 plenamente aplicável

### Enquadramento legal
**Art. 61-A §2 — imóveis > 4 MF (8,16 MF):**
> *"é obrigatória a recomposição das respectivas faixas marginais em **20 metros**, contados da borda da calha do leito regular, independentemente da largura do curso d'água"*

**Impacto prático:** o proprietário recompõe APENAS os primeiros 20m a partir da margem do curso d'água, independentemente de o rio ter 10m, 30m ou 50m de largura.

### BRECHA 1 — Faixa efetiva vs. APPD declarada ✅ CALCULADA

**Resultado da análise espacial (26/05/2026) — dados definitivos:**

| Métrica | Valor |
|---|---|
| APPD total declarada no CAR | 16,40 ha |
| Área dentro da faixa de 20m | **2,30 ha** ← OBRIGAÇÃO REAL |
| Área dispensada (além dos 20m) | **14,09 ha** |
| **Redução da obrigação** | **86,0%** |

**Cursos d'água identificados no SHP:**
- 14 feições de RIO_ATE_10 (rios ≤10m, faixa APP 30m) → geram 2,30 ha de APPD nos 20m
- 1 feição de RIO_10_A_50 (rio 10–50m, polígono 32,56 ha) → APPD adjacente dispensada pela faixa de 20m
- Nenhum rio ≥50m na propriedade

**Estrutura dos 9 polígonos APPD:**
- 5 polígonos sobrepostos à AUAS (menores, totalizando ~6,96 ha)
- 4 polígonos sobrepostos à AREA_CONSOLIDADA (maiores: 6,22 + 3,05 + 0,18 ha)
- Maior polígono individual: 6,89 ha (AUAS)

**Conclusão definitiva:** de 16,40 ha declarados como APPD, **apenas 2,30 ha precisam ser recompostos**. Os outros 14,09 ha podem permanecer como pastagem consolidada legalmente, sem necessidade de intervenção.

### BRECHA 2 — Condução de Regeneração Natural
Art. 61-A §13 e Resolução CONAMA 429/2011:

> Se houver **regeneração natural espontânea** na APPD, a técnica preferencial é a condução dessa regeneração (cercamento + exclusão de gado + manejo de invasoras), que:
> - É aceita pela SEMA-MT como método de recomposição
> - Tem custo 60–70% menor que plantio de mudas
> - Conta como cumprimento do prazo do PRA

**Ação recomendada:** durante o diagnóstico de campo, **documentar e fotografar qualquer regeneração natural** na APPD (arbustos, embaúbas, capoeira). Se presente, justifica condução de regeneração como técnica principal no PRADA.

### BRECHA 3 — Prazo de 10 anos (Decreto MT 1.253/2017)
O prazo máximo para recomposição de APPD em imóveis > 4 MF com área > 5 ha é de **até 10 anos**, parcelado em cronograma físico-financeiro.

**Oportunidade:** o cronograma pode ser calibrado para minimizar desembolso anual do cliente. A SEMA-MT aceita metas físicas graduais (ex.: 10% ao ano por 10 anos). O custo total de recomposição pode ser diluído.

### Opções técnicas de recomposição

| Técnica | Custo estimado/ha | Adequação | Observação |
|---|---|---|---|
| Plantio em consórcio (padrão SEMA-MT) | R$ 8.000–14.000 | Alta | Exige ≥30 spp, ≥50% P, ≥30% Z |
| Condução de regeneração natural | R$ 2.500–5.000 | Alta se há regeneração | Precisa laudo de campo |
| Nucleação + enriquecimento | R$ 5.000–9.000 | Média-Alta | Boa para áreas com regeneração parcial |
| Sistemas agroflorestais (SAFs) | R$ 6.000–12.000 | Média | Aceito em casos específicos (Art. 61-A §11) |

### Custo estimado da APPD
Considerando faixa efetiva de 20m (área real a calcular após shapefile):
- Cenário conservador (plantio consórcio): **R$ 8.000–14.000 × área efetiva**
- Cenário otimista (regeneração natural): **R$ 2.500–5.000 × área efetiva**

---

## PASSIVO 2 — DÉFICIT DE RESERVA LEGAL (100,70 ha)

### O que é
A propriedade não possui Reserva Legal suficiente no bioma Floresta (déficit de 109,60 ha) que, compensado pelo superávit de Cerrado (8,90 ha), resulta em déficit líquido de **100,70 ha** a compensar fora do imóvel.

**Importante:** ARLD = 0 → o proprietário **NÃO é obrigado a reflorestar dentro do imóvel**. Pode compensar 100% via mecanismos externos (Art. 66 Código Florestal).

### Opções legais disponíveis (Art. 66)

#### OPÇÃO A — CRA (Cota de Reserva Ambiental)
**Art. 44 Lei 12.651/2012**
- Título representando 1 ha de vegetação nativa excedente ao mínimo de RL de outro imóvel
- Deve ser do **mesmo bioma** (Amazônia)
- Pode ser de qualquer estado da Amazônia Legal

**BRECHA 4 — Buscar CRA fora de MT**
CRAs em Pará, Amazonas, Rondônia têm preço significativamente menor que MT:

| Estado | Faixa de preço CRA (2024-25) | Custo para 100,70 ha |
|---|---|---|
| Mato Grosso | R$ 1.000–1.800/ha | R$ 100.700 – 181.260 |
| Pará | R$ 600–1.000/ha | R$ 60.420 – 100.700 |
| Amazonas | R$ 400–700/ha | R$ 40.280 – 70.490 |
| Rondônia | R$ 500–900/ha | R$ 50.350 – 90.630 |

> A lei exige **mesmo bioma**, não mesmo estado, não mesma bacia. Comprar CRA no Amazonas é tão legal quanto comprar em MT — e 60% mais barato.

**Referências de mercado:** Biofílica, BVRio, Bolsa de Valores Ambientais, corretoras especializadas (Sinop/Cuiabá).

#### OPÇÃO B — Compensação direta no SIMCAR (Aba 6) sem CRA formal
Mais rápida e sem custo de emissão de CRA:
- Encontrar imóvel com superávit de RL no bioma Amazônia
- Registrar a compensação na Aba 6 do SIMCAR-MT
- Contrato particular entre os proprietários
- SEMA-MT valida e o déficit é zerado

**BRECHA 5 — Uso de imóvel de familiar/parceiro**
Se o cliente ou parceiro comercial tiver outra propriedade em bioma Amazônia com superávit de RL, a compensação pode ser feita gratuitamente (ou a custo mínimo) por contrato de cessão de direitos de compensação, sem transação financeira de CRA no mercado.

**Ação:** perguntar ao cliente se tem outras propriedades no bioma Amazônia ou conhece proprietários com superávit de RL.

#### OPÇÃO C — Aquisição de área para RL
- Comprar terra no bioma Amazônia para constituir a RL faltante
- Mais caro e burocrático
- Só faz sentido se o cliente quiser expandir patrimônio fundiário
- **Não recomendado** como primeira opção

#### OPÇÃO D — Doação ao poder público
- Doação de área equivalente em UC de proteção integral
- Praticamente inviável na prática (UCs raramente aceitam)
- **Descartar**

### BRECHA 6 — Prazo de regularização do CAR como proteção
Enquanto o imóvel estiver com PRA ativo e dentro do cronograma de regularização:
- **Multas ambientais por déficit de RL ficam suspensas** (Art. 59 §2 Lei 12.651/2012)
- Embargos não se aplicam à área de RL faltante
- O proprietário fica protegido juridicamente durante todo o prazo do PRADA

**Ação:** protocolar o PRADA o quanto antes para ativar essa proteção.

---

## OPORTUNIDADES ESTRATÉGICAS ADICIONAIS

### BRECHA 7 — Superávit de Cerrado como CRA vendável
A propriedade tem **8,90 ha de superávit de Cerrado** (36,22 ha declarados vs. 27,32 ha exigidos).

Esse superávit, depois que o déficit líquido for quitado, pode ser:
- Registrado como CRA de bioma Cerrado
- **Vendido no mercado** para outros proprietários com déficit de Cerrado

Preço médio CRA Cerrado MT: R$ 800–1.500/ha → potencial de **R$ 7.120–13.350** de receita.

> Isso não anula o déficit de Floresta — são fitofisionomias diferentes — mas gera receita que pode amortizar parte do custo da regularização.

### BRECHA 8 — Crédito de carbono pela área de RL mantida
A RL existente de 409,87 ha (Floresta) é uma floresta nativa conservada que potencialmente pode gerar créditos de carbono REDD+ ou IFM (Improved Forest Management).

No contexto atual de mercado voluntário de carbono:
- Propriedades em Gaúcha do Norte/MT com floresta nativa conservada são elegíveis
- Projetos REDD+ em MT: padrão VCS + CCB
- Potencial: 5–15 tCO2e/ha/ano × R$ 30–80/tCO2e

**Ação futura:** após regularização do CAR, avaliar agregação a projeto REDD+ regional ou iniciativa individual.

---

## RISCOS E PONTOS DE ATENÇÃO

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Suspensão do CAR novamente (pendências) | Baixa (cliente afirmou resolver) | Alto | Confirmar situação no SICAR federal antes de protocolar PRADA |
| APPD real maior que 20m de faixa (precisão do shapefile) | Média | Médio | Obter shapefile com delimitação precisa do curso d'água |
| CRA de outro estado não aceito pela SEMA-MT | Baixa (lei federal permite) | Alto | Verificar norma SEMA-MT específica para compensação interestadual |
| Inventário florístico não atingir critérios SEMA-MT | Média | Alto | Suplementar lista GBIF com levantamento de campo, incluir pioneiras obrigatórias |
| Prazo do cronograma não cumprido | Baixa (10 anos) | Médio | Calibrar cronograma conservador com metas anuais mínimas |
| RT sem ART registrada na SEMA | Alta se não providenciado | Alto | Providenciar ART antes de protocolo |

---

## SEQUÊNCIA DE AÇÕES RECOMENDADA

### Fase 1 — Viabilização (0–30 dias)
1. Confirmar situação do CAR no SICAR federal (sem novas pendências)
2. Obter shapefile do imóvel + polígonos APP e RL do cliente
3. Calcular faixa efetiva de 20m da APPD (reduzir área a recompor)
4. Perguntar se cliente tem propriedade/parceiro com superávit RL em Amazônia
5. Coletar dados do RT (nome, CREA/CFBio, ART)
6. Certidão de matrícula atualizada

### Fase 2 — Campo (30–60 dias)
7. Vistoria da APPD: diagnóstico de cobertura atual, fotodocumentação
8. Avaliar presença de regeneração natural (define técnica de recomposição)
9. Inventário florístico na região de influência da APPD

### Fase 3 — PRADA (60–90 dias)
10. Preenchimento das Abas 3, 4, 5 do SIMCAR (APPD + consórcio)
11. Preenchimento da Aba 6 (Compensação RL) com CRA ou compensação direta
12. Geração do documento PRADA (.docx)
13. Protocolo junto à SEMA-MT

---

*Análise elaborada com base em Lei 12.651/2012, LC-MT 592/2017, Decreto MT 1.031/2017, Decreto MT 1.253/2017, CONAMA 429/2011, dados MapBiomas Coleção 10.1 e MapBiomas Alerta (consulta 25/05/2026).*
