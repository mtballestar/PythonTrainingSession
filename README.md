# 📊 Análisis de Tendencias en Google Trends: Zara · Shein · Temu

**Módulo:** Análisis Avanzado de Datos y Visualización — *Práctica Aplicada*
**País:** España · **Periodo:** 2004–2026 · **Frecuencia:** mensual · **Fuente:** Google Trends (Web Search)

Análisis descriptivo y comparativo del interés de búsqueda online de tres marcas de moda que
representan estrategias y geografías distintas: **Zara** (fast fashion europeo), **Shein** y **Temu**
(plataformas digitales asiáticas). Combina el enfoque **programático** (Python) con la interpretación
cualitativa del enfoque conversacional.

---

## 📁 Estructura del repositorio

```
├── data/
│   └── google_trends_zara_shein_temu_ES.csv   # Datos de Google Trends (España, mensual)
├── notebook/
│   ├── analisis_zara_shein_temu.ipynb          # Notebook COMPLETO y EJECUTADO (para Colab)
│   └── analisis_zara_shein_temu.html           # Versión HTML (ver sin ejecutar nada)
├── figuras/                                     # Gráficos generados (PNG)
├── resultados/                                  # Tablas exportadas (CSV)
├── analisis.py                                  # Script del pipeline completo
└── build_notebook.py                            # Generador del notebook
```

## 🔬 Contenido del análisis

| Sección | Qué incluye |
|---|---|
| **A. Descriptivo** | Evolución 2004–2026, aparición de cada marca, media/pico/crecimiento, estacionalidad mensual |
| **B. Correlaciones** | Periodo completo vs. ventana de coexistencia (desde may-2023) + heatmaps |
| **C. Descomposición** | Tendencia + estacionalidad + residual (aditiva, periodo 12) por marca |
| **D. Forecast** | Predicción a 6 meses con Holt-Winters (tabla + CSV + gráfico) |

## 📈 Principales conclusiones

- **Zara domina** el interés en toda la serie (media ≈ **42** vs. **7.7** Shein y **1.6** Temu). Marca **madura**, con pico histórico en **noviembre 2017**.
- **Shein** despega con la pandemia (2020) y alcanza su máximo en **2022**.
- **Temu** entra muy tarde (**may-2023**) pero crece de forma sostenida, acercándose a Shein hacia 2025–2026.
- **Correlación más fuerte:** **Temu ↔ Shein = negativa** en la ventana de coexistencia → **sustitución competitiva directa** (mismo perfil de consumidor de bajo coste).
- **Estacionalidad** común y clara: picos en **noviembre (Black Friday)** y **enero (rebajas)**, valles en **febrero/agosto**.
- En las tres series, la **tendencia** es el componente que más variabilidad explica; el residual es pequeño → series bien estructuradas.

### Forecast a 6 meses (interés relativo 0–100)

| Fecha | Zara | Shein | Temu |
|---|---|---|---|
| 2026-07 | 43.3 | 18.1 | 13.2 |
| 2026-08 | 38.8 | 15.4 | 15.5 |
| 2026-09 | 41.9 | 15.3 | 15.5 |
| 2026-10 | 44.2 | 16.2 | 15.9 |
| 2026-11 | 57.9 | 18.7 | 16.9 |
| 2026-12 | 56.2 | 15.4 | 14.9 |

## ▶️ Cómo ejecutarlo

**En Google Colab:** abre `notebook/analisis_zara_shein_temu.ipynb`, sube el CSV de `data/`
(o usa `pytrends`) y ejecuta *Entorno de ejecución → Ejecutar todo*.

**En local:**
```bash
pip install pandas numpy matplotlib statsmodels
python analisis.py
```

> **Nota sobre los datos:** Google Trends devuelve un índice **relativo 0–100** (100 = máximo interés del
> periodo). Shein y Temu valen 0 en los primeros años porque aún no existían/no tenían búsquedas — es
> correcto, no es un error. Por eso las correlaciones con sentido se calculan en la ventana de coexistencia.
