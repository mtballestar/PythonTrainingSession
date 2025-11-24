# PythonTrainingSession

Este repositorio contiene un pequeño ejemplo para visualizar series temporales de marcas de *fast fashion* a partir del archivo `fastfashion.xlsx`.

## Uso

Generar el gráfico combinado de las tres marcas:

```bash
python visualize_brands.py
```

Crear un gráfico de descomposición (observado, tendencia, estacionalidad y residuo) para una marca específica, por ejemplo Zara:

```bash
python visualize_brands.py --decompose zara --output zara_decomposition.svg
```

También puedes generar la descomposición para otras marcas, por ejemplo Temu:

```bash
python visualize_brands.py --decompose temu --output temu_decomposition.svg
```

El parámetro `--output` es opcional y permite elegir el nombre del archivo SVG de salida.
