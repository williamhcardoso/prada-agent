import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import shapefile
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import math

SHP_DIR = r"C:\Users\WILLIAM\Downloads\shp_culueno"

def ler_shp(nome):
    try:
        sf = shapefile.Reader(f"{SHP_DIR}\\{nome}.shp")
        feats = []
        for sr in sf.shapeRecords():
            geom = shape(sr.shape.__geo_interface__)
            rec  = dict(zip([f[0] for f in sf.fields[1:]], sr.record))
            feats.append((geom, rec))
        return feats
    except Exception as e:
        return []

def area_ha(geom_list):
    if not geom_list:
        return 0.0
    union = unary_union([g for g,_ in geom_list])
    # Coordenadas em graus decimais -> converter para metros (lat media ~-13.58)
    # 1 grau lat ≈ 111320 m; 1 grau lon ≈ 111320 * cos(-13.58°) ≈ 108245 m
    # Área em graus^2 * fator de conversão
    lat_ref = -13.58
    fator = 111320 * 111320 * math.cos(math.radians(lat_ref))
    return union.area * fator / 10000

def geom_union(geom_list):
    if not geom_list:
        return None
    return unary_union([g for g,_ in geom_list])

print("=" * 65)
print("ANÁLISE ESPACIAL — FAZENDA CULUENO")
print("=" * 65)

# === CAMADAS PRINCIPAIS ===
atp   = ler_shp("ATP")
app   = ler_shp("APP")
appd  = ler_shp("APPD")
avn   = ler_shp("AVN")
arl   = ler_shp("ARL")
arl_fl_pres = ler_shp("ARL_FLORESTA_PRESERVADA")
arl_ce_pres = ler_shp("ARL_CERRADO_PRESERVADA")
arl_fl_rec  = ler_shp("ARL_FLORESTA_RECOMPOR")
arl_ce_rec  = ler_shp("ARL_CERRADO_RECOMPOR")
area_cons   = ler_shp("AREA_CONSOLIDADA")
tipologia   = ler_shp("TIPOLOGIA_VEGETAL")
apprl       = ler_shp("APPRL")
air         = ler_shp("AIR")
auas        = ler_shp("AUAS")
aurd        = ler_shp("AURD")
nascente    = ler_shp("NASCENTE")
lag_nat     = ler_shp("LAGOA_NATURAL")
reserv      = ler_shp("RESERVATORIO_ARTIFICIAL")
vereda      = ler_shp("VEREDA")

# Cursos d'água
rio_ate10   = ler_shp("RIO_ATE_10")
rio_10_50   = ler_shp("RIO_10_A_50")
rio_50_200  = ler_shp("RIO_50_A_200")
rio_200_600 = ler_shp("RIO_200_A_600")
rio_ac600   = ler_shp("ACIMA_600")

print("\n--- ÁREAS PRINCIPAIS ---")
print(f"ATP  (Área Total Propriedade):    {area_ha(atp):.2f} ha")
print(f"APP  (APP Total):                 {area_ha(app):.2f} ha")
print(f"APPD (APP com Passivo):           {area_ha(appd):.2f} ha")
print(f"APPRL (APP preservada em RL):     {area_ha(apprl):.2f} ha")
print(f"AVN  (Vegetação Nativa):          {area_ha(avn):.2f} ha")
print(f"ARL  (RL Total declarada):        {area_ha(arl):.2f} ha")
print(f"  ARL Floresta preservada:        {area_ha(arl_fl_pres):.2f} ha")
print(f"  ARL Cerrado preservada:         {area_ha(arl_ce_pres):.2f} ha")
print(f"  ARL Floresta recompor:          {area_ha(arl_fl_rec):.2f} ha")
print(f"  ARL Cerrado recompor:           {area_ha(arl_ce_rec):.2f} ha")
print(f"AREA_CONSOLIDADA:                 {area_ha(area_cons):.2f} ha")
print(f"AUAS (Área Uso Alternativo Solo): {area_ha(auas):.2f} ha")
print(f"AURD (Uso Restrito degradada):    {area_ha(aurd):.2f} ha")
print(f"AIR  (Área Imóvel Rural):         {area_ha(air):.2f} ha")
print(f"LAGOA_NATURAL:                    {area_ha(lag_nat):.2f} ha")
print(f"RESERVATORIO_ARTIFICIAL:          {area_ha(reserv):.2f} ha")

print("\n--- CURSOS D'ÁGUA ---")
print(f"RIO_ATE_10   (≤10m, APP 30m):    {len(rio_ate10)} feição(ões)")
print(f"RIO_10_A_50  (10-50m, APP 50m):  {len(rio_10_50)} feição(ões)")
print(f"RIO_50_A_200 (50-200m, APP 100m):{len(rio_50_200)} feição(ões)")
print(f"RIO_200_A_600:                   {len(rio_200_600)} feição(ões)")

print("\n--- TIPOLOGIA VEGETAL ---")
for g, rec in tipologia:
    print(f"  {rec}")

# === CÁLCULO DA FAIXA DE 20m ===
print("\n--- ANÁLISE BRECHA: FAIXA DE 20m vs APPD TOTAL ---")

# Converter buffer: 20m em graus (lat -13.58)
# 1 grau ≈ 111320m; 20m ≈ 0.0001797 graus
METROS_20 = 20
graus_20m = METROS_20 / 111320.0

appd_union = geom_union(appd)
area_appd_total = area_ha(appd)

if appd_union is None:
    print("APPD: sem geometria")
else:
    resultados_buffer = {}

    # Buffer nos rios <= 10m (faixa normal 30m, mas obrigação 20m)
    if rio_ate10:
        rios_u = geom_union(rio_ate10)
        buf20 = rios_u.buffer(graus_20m)
        intersec = appd_union.intersection(buf20)
        lat_ref = -13.58
        fator = 111320 * 111320 * math.cos(math.radians(lat_ref))
        area_20m = intersec.area * fator / 10000
        resultados_buffer['RIO_ATE_10 (20m)'] = area_20m

    # Buffer nos rios 10-50m (faixa normal 50m, mas obrigação 20m)
    if rio_10_50:
        rios_u = geom_union(rio_10_50)
        buf20 = rios_u.buffer(graus_20m)
        intersec = appd_union.intersection(buf20)
        lat_ref = -13.58
        fator = 111320 * 111320 * math.cos(math.radians(lat_ref))
        area_20m = intersec.area * fator / 10000
        resultados_buffer['RIO_10_A_50 (20m)'] = area_20m

    # Buffer combinado todos os rios
    todos_rios = rio_ate10 + rio_10_50 + rio_50_200
    if todos_rios:
        rios_u = geom_union(todos_rios)
        buf20 = rios_u.buffer(graus_20m)
        intersec_total = appd_union.intersection(buf20)
        lat_ref = -13.58
        fator = 111320 * 111320 * math.cos(math.radians(lat_ref))
        area_obrigacao = intersec_total.area * fator / 10000
        area_dispensada = area_appd_total - area_obrigacao

        print(f"\nAPPD total declarada:          {area_appd_total:.4f} ha")
        print(f"Área dentro faixa 20m:         {area_obrigacao:.4f} ha  ← OBRIGAÇÃO REAL")
        print(f"Área dispensada (além 20m):     {area_dispensada:.4f} ha  ← DISPENSADO Art.61-A §2")
        print(f"Redução de recomposição:        {(area_dispensada/area_appd_total*100):.1f}%")

        for k, v in resultados_buffer.items():
            print(f"  {k}: {v:.4f} ha")
    else:
        print("Nenhum curso d'água com geometria encontrado.")
        print(f"APPD total: {area_appd_total:.4f} ha (verificar geometria dos rios)")

# === ATRIBUTOS APPD ===
print("\n--- ATRIBUTOS APPD (por polígono) ---")
for i, (g, rec) in enumerate(appd):
    lat_ref = -13.58
    fator = 111320 * 111320 * math.cos(math.radians(lat_ref))
    a = g.area * fator / 10000
    print(f"  Polígono {i+1}: {a:.4f} ha | atributos: {rec}")

# === ATRIBUTOS RIO_10_A_50 ===
print("\n--- ATRIBUTOS RIO_10_A_50 ---")
for i, (g, rec) in enumerate(rio_10_50):
    print(f"  Trecho {i+1}: {rec} | tipo_geom: {g.geom_type}")

print("\n--- ATRIBUTOS RIO_ATE_10 (primeiros 5) ---")
for i, (g, rec) in enumerate(rio_ate10[:5]):
    print(f"  Trecho {i+1}: {rec} | tipo_geom: {g.geom_type}")

# === CENTROIDE DO IMÓVEL ===
if atp:
    c = geom_union(atp).centroid
    print(f"\n--- CENTROIDE DO IMÓVEL ---")
    print(f"  Lat: {c.y:.6f} | Lon: {c.x:.6f}")
