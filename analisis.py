"""
Análisis de Tendencias en Google Trends: Zara · Shein · Temu (España)
Módulo: Análisis Avanzado de Datos y Visualización

Pipeline completo:
  A. Análisis descriptivo
  B. Correlaciones (periodo completo vs. ventana de coexistencia)
  C. Descomposición temporal (tendencia / estacionalidad / residual)
  D. Forecast a 6 meses (Holt-Winters)
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.holtwinters import ExponentialSmoothing

plt.rcParams.update({
    "figure.dpi": 110,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
})

MARCAS = ["zara", "shein", "temu"]
COLORS = {"zara": "#1f77b4", "shein": "#d62728", "temu": "#2ca02c"}

# ---------------------------------------------------------------------------
# 0. Carga de datos
# ---------------------------------------------------------------------------
df = pd.read_csv("data/google_trends_zara_shein_temu_ES.csv", parse_dates=["Time"])
df = df.rename(columns={"Time": "fecha"}).set_index("fecha").sort_index()
df.index.freq = "MS"  # inicio de mes
print("Datos:", df.shape, "| rango:", df.index.min().date(), "->", df.index.max().date())

# ---------------------------------------------------------------------------
# A. ANÁLISIS DESCRIPTIVO
# ---------------------------------------------------------------------------
print("\n=== A. DESCRIPTIVO ===")
print(df.describe().round(2).to_string())

# Aparición de cada marca
aparicion = {c: df.loc[df[c] > 0].index.min() for c in MARCAS}
print("\nPrimer mes con interés > 0:")
for c, f in aparicion.items():
    print(f"  {c:6s}: {f.date()}")

# Interés medio y crecimiento acumulado (primeros vs. últimos 12 meses activos)
resumen = []
for c in MARCAS:
    serie = df[c]
    activo = serie[serie > 0]
    ini = activo.head(12).mean()
    fin = activo.tail(12).mean()
    crec = (fin - ini) / ini * 100 if ini > 0 else np.nan
    resumen.append({
        "marca": c,
        "media_global": round(serie.mean(), 1),
        "media_ult_12m": round(serie.tail(12).mean(), 1),
        "pico_max": int(serie.max()),
        "mes_pico": serie.idxmax().strftime("%Y-%m"),
        "crecimiento_%": round(crec, 1),
    })
resumen = pd.DataFrame(resumen)
print("\nResumen comparativo:")
print(resumen.to_string(index=False))

# --- Figura 1: evolución completa
fig, ax = plt.subplots(figsize=(13, 5.5))
for c in MARCAS:
    ax.plot(df.index, df[c], label=c.capitalize(), color=COLORS[c], lw=1.6)
ax.set_title("Interés de búsqueda en Google Trends (España, 2004–2026)\nZara · Shein · Temu", fontweight="bold")
ax.set_ylabel("Interés relativo (0–100)")
ax.set_xlabel("Año")
ax.legend()
ax.xaxis.set_major_locator(mdates.YearLocator(2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout()
fig.savefig("figuras/01_evolucion.png", bbox_inches="tight")
plt.close(fig)

# --- Figura 2: estacionalidad mensual (patrón medio por mes, Zara)
df_m = df.copy()
df_m["mes"] = df_m.index.month
estacional_zara = df_m.groupby("mes")["zara"].mean()
fig, ax = plt.subplots(figsize=(10, 4.5))
meses_lbl = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
bars = ax.bar(meses_lbl, estacional_zara.values, color=COLORS["zara"], alpha=0.85)
ax.set_title("Patrón estacional medio de Zara por mes (2004–2026)", fontweight="bold")
ax.set_ylabel("Interés medio")
# resaltar picos
for i, b in enumerate(bars):
    if estacional_zara.values[i] >= estacional_zara.max() * 0.97:
        b.set_color("#d62728")
fig.tight_layout()
fig.savefig("figuras/02_estacionalidad_zara.png", bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# B. CORRELACIONES
# ---------------------------------------------------------------------------
print("\n=== B. CORRELACIONES ===")
corr_full = df[MARCAS].corr()
print("\nPeriodo completo 2004–2026 (SESGADO por los ceros):")
print(corr_full.round(3).to_string())

# Ventana de coexistencia: desde que Temu aparece (may-2023)
inicio_coex = aparicion["temu"]
df_coex = df.loc[inicio_coex:]
corr_coex = df_coex[MARCAS].corr()
print(f"\nVentana de coexistencia (desde {inicio_coex.date()}):")
print(corr_coex.round(3).to_string())

# Ventana Zara-Shein (desde 2022, cuando Shein ya es relevante)
df_zs = df.loc["2022-01-01":]
print("\nCorrelación Zara–Shein desde 2022:",
      round(df_zs["zara"].corr(df_zs["shein"]), 3))

# --- Figura 3: heatmaps de correlación
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
for ax, (titulo, cm) in zip(
    axes,
    [("Periodo completo (2004–2026)", corr_full),
     (f"Coexistencia (desde {inicio_coex.strftime('%Y-%m')})", corr_coex)],
):
    im = ax.imshow(cm, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(3)); ax.set_xticklabels([m.capitalize() for m in MARCAS])
    ax.set_yticks(range(3)); ax.set_yticklabels([m.capitalize() for m in MARCAS])
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{cm.iloc[i, j]:.2f}", ha="center", va="center",
                    color="white" if abs(cm.iloc[i, j]) > 0.5 else "black", fontweight="bold")
    ax.set_title(titulo, fontsize=11, fontweight="bold")
fig.colorbar(im, ax=axes, shrink=0.8, label="Correlación de Pearson")
fig.savefig("figuras/03_correlaciones.png", bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------------
# C. DESCOMPOSICIÓN TEMPORAL
# ---------------------------------------------------------------------------
print("\n=== C. DESCOMPOSICIÓN TEMPORAL ===")
var_explicada = {}
for c in MARCAS:
    # usamos solo el tramo activo de cada serie
    serie = df.loc[aparicion[c]:, c].astype(float)
    if len(serie) < 24:
        continue
    result = seasonal_decompose(serie, model="additive", period=12)

    fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(serie.index, serie, color=COLORS[c]); axes[0].set_ylabel("Observada")
    axes[1].plot(result.trend.index, result.trend, color="#333"); axes[1].set_ylabel("Tendencia")
    axes[2].plot(result.seasonal.index, result.seasonal, color="#ff7f0e"); axes[2].set_ylabel("Estacional")
    axes[3].plot(result.resid.index, result.resid, color="#999"); axes[3].set_ylabel("Residual")
    axes[0].set_title(f"Descomposición temporal — {c.capitalize()} (aditiva, periodo=12)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"figuras/04_descomposicion_{c}.png", bbox_inches="tight")
    plt.close(fig)

    # varianza explicada por cada componente
    total_var = serie.var()
    var_explicada[c] = {
        "tendencia_%": round(result.trend.dropna().var() / total_var * 100, 1),
        "estacional_%": round(result.seasonal.var() / total_var * 100, 1),
        "residual_%": round(result.resid.dropna().var() / total_var * 100, 1),
    }
print("\nPeso relativo de cada componente (varianza):")
print(pd.DataFrame(var_explicada).T.to_string())

# ---------------------------------------------------------------------------
# D. FORECAST A 6 MESES (Holt-Winters)
# ---------------------------------------------------------------------------
print("\n=== D. FORECAST 6 MESES ===")
H = 6
forecasts = {}
fig, ax = plt.subplots(figsize=(13, 5.5))
for c in MARCAS:
    serie = df.loc[aparicion[c]:, c].astype(float)
    modelo = ExponentialSmoothing(serie, trend="add", seasonal="add", seasonal_periods=12)
    ajuste = modelo.fit()
    pred = ajuste.forecast(H).clip(lower=0).round(1)
    forecasts[c] = pred
    # dibujar últimos 3 años + forecast
    hist = serie.loc[serie.index.max() - pd.DateOffset(years=3):]
    ax.plot(hist.index, hist, color=COLORS[c], lw=1.6, label=f"{c.capitalize()} (histórico)")
    ax.plot(pred.index, pred, color=COLORS[c], lw=2.2, ls="--", marker="o", ms=4,
            label=f"{c.capitalize()} (forecast)")
ax.axvline(df.index.max(), color="gray", ls=":", alpha=0.7)
ax.set_title("Forecast a 6 meses (Holt-Winters aditivo) — Zara · Shein · Temu", fontweight="bold")
ax.set_ylabel("Interés relativo (0–100)")
ax.legend(ncol=3, fontsize=9)
fig.tight_layout()
fig.savefig("figuras/05_forecast.png", bbox_inches="tight")
plt.close(fig)

tabla_forecast = pd.DataFrame(forecasts)
tabla_forecast.index.name = "fecha"
print("\nPredicción próximos 6 meses:")
print(tabla_forecast.to_string())
tabla_forecast.to_csv("resultados/forecast_6meses.csv")
resumen.to_csv("resultados/resumen_descriptivo.csv", index=False)
corr_coex.to_csv("resultados/correlaciones_coexistencia.csv")

print("\n✅ Análisis completado. Figuras en 'figuras/', tablas en 'resultados/'.")
