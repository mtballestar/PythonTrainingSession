"""Minimal visualization for fast fashion brand time series.

This script avoids external dependencies by parsing the XLSX file
with the standard library and emitting standalone SVG charts.
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from zipfile import ZipFile

XLSX_PATH = Path("fastfashion.xlsx")
OUTPUT_SVG = Path("brand_timeseries.svg")
NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@dataclass
class SeriesData:
    label: str
    values: List[float]
    color: str


@dataclass
class Decomposition:
    observed: List[float]
    trend: List[float]
    seasonal: List[float]
    remainder: List[float]


def _col_to_idx(col: str) -> int:
    idx = 0
    for ch in col:
        idx = idx * 26 + (ord(ch) - 64)
    return idx - 1


def _read_shared_strings(zf: ZipFile) -> List[str]:
    data = zf.read("xl/sharedStrings.xml")
    root = ET.fromstring(data)
    return [node.find(".//a:t", NS).text for node in root.findall("a:si", NS)]


def load_fastfashion_data(xlsx_path: Path = XLSX_PATH) -> Tuple[List[str], Dict[str, List[float]]]:
    """Load month labels and brand columns from the XLSX file.

    Returns
    -------
    months: list of month labels as strings (e.g., "2004-01")
    series: mapping of brand name to numeric values
    """

    with ZipFile(xlsx_path) as zf:
        shared_strings = _read_shared_strings(zf)
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))

    rows: List[List[object]] = []
    for row in sheet.findall(".//a:sheetData/a:row", NS):
        row_data: Dict[int, object] = {}
        for cell in row.findall("a:c", NS):
            ref = cell.get("r") or ""
            col = re.match(r"[A-Z]+", ref).group(0)
            idx = _col_to_idx(col)
            cell_type = cell.get("t")
            v_el = cell.find("a:v", NS)
            val = v_el.text if v_el is not None else ""
            if cell_type == "s":
                val = shared_strings[int(val)]
            elif val != "":
                val = float(val)
            row_data[idx] = val
        max_idx = max(row_data.keys()) if row_data else -1
        rows.append([row_data.get(i, "") for i in range(max_idx + 1)])

    def to_float(value: object) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.lstrip("<")
            return float(cleaned)
        raise TypeError(f"Unsupported value: {value!r}")

    header, *body = rows
    months = [str(r[0]) for r in body]
    series = {header[i]: [to_float(r[i]) for r in body] for i in range(1, len(header))}
    return months, series


def _scale(value: float, *, min_v: float, max_v: float, height: float, padding: float) -> float:
    span = max_v - min_v or 1.0
    return padding + (max_v - value) / span * (height - 2 * padding)


def _x_position(index: int, total: int, *, width: float, padding: float) -> float:
    if total <= 1:
        return padding
    return padding + index * (width - 2 * padding) / (total - 1)


def _moving_average(values: Sequence[float], window: int) -> List[float]:
    if window <= 0:
        raise ValueError("window must be positive")

    result: List[float] = []
    half = window // 2
    n = len(values)
    for i in range(n):
        start = max(0, i - half)
        end = min(n, start + window)
        start = max(0, end - window)
        segment = values[start:end]
        result.append(sum(segment) / len(segment))
    return result


def decompose_series(values: Sequence[float], *, period: int = 12) -> Decomposition:
    """Produce a simple additive decomposition using moving averages."""

    trend = _moving_average(values, window=period)

    seasonal_totals: Dict[int, List[float]] = {i: [] for i in range(period)}
    for idx, (value, trend_value) in enumerate(zip(values, trend)):
        seasonal_totals[idx % period].append(value - trend_value)

    seasonal_lookup = {k: sum(v) / len(v) if v else 0.0 for k, v in seasonal_totals.items()}
    seasonal = [seasonal_lookup[i % period] for i in range(len(values))]

    remainder = [v - t - s for v, t, s in zip(values, trend, seasonal)]
    return Decomposition(list(values), trend, seasonal, remainder)


def build_svg(months: Sequence[str], series_data: Sequence[SeriesData], *, width: int = 1100, height: int = 650, padding: int = 70) -> str:
    all_values = [v for s in series_data for v in s.values]
    min_v, max_v = min(all_values), max(all_values)

    def y(val: float) -> float:
        return _scale(val, min_v=min_v, max_v=max_v, height=height, padding=padding)

    def x(idx: int) -> float:
        return _x_position(idx, len(months), width=width, padding=padding)

    # Axes and ticks
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>.axis { stroke: #333; stroke-width: 1.5; } .tick { stroke: #888; stroke-width: 1; } .label { font-family: sans-serif; font-size: 12px; fill: #111; }</style>',
        f'<rect width="100%" height="100%" fill="#fafafa" />',
        f'<line class="axis" x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" />',
        f'<line class="axis" x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" />',
    ]

    # y ticks: 6 steps
    for i in range(6):
        val = min_v + i * (max_v - min_v) / 5
        y_pos = y(val)
        svg_parts.append(f'<line class="tick" x1="{padding - 5}" y1="{y_pos:.2f}" x2="{width - padding}" y2="{y_pos:.2f}" stroke-dasharray="2,2" />')
        svg_parts.append(f'<text class="label" x="{padding - 10}" y="{y_pos + 4:.2f}" text-anchor="end">{val:.0f}</text>')

    # x ticks roughly every 24 months
    step = max(1, len(months) // 10)
    for i in range(0, len(months), step):
        x_pos = x(i)
        svg_parts.append(f'<line class="tick" x1="{x_pos:.2f}" y1="{height - padding}" x2="{x_pos:.2f}" y2="{height - padding + 6}" />')
        label = months[i]
        svg_parts.append(f'<text class="label" x="{x_pos:.2f}" y="{height - padding + 18}" text-anchor="middle" transform="rotate(45 {x_pos:.2f},{height - padding + 18})">{label}</text>')

    # Series polylines
    for s in series_data:
        points = " ".join(f"{x(i):.2f},{y(val):.2f}" for i, val in enumerate(s.values))
        svg_parts.append(f'<polyline fill="none" stroke="{s.color}" stroke-width="2.5" points="{points}" />')

    # Legend
    legend_x, legend_y = width - padding - 120, padding
    for idx, s in enumerate(series_data):
        y_pos = legend_y + idx * 22
        svg_parts.append(f'<rect x="{legend_x}" y="{y_pos}" width="14" height="14" fill="{s.color}" />')
        svg_parts.append(f'<text class="label" x="{legend_x + 20}" y="{y_pos + 12}" text-anchor="start">{s.label}</text>')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def build_decomposition_svg(
    months: Sequence[str],
    brand: str,
    values: Sequence[float],
    *,
    width: int = 1100,
    height: int = 1000,
    padding: int = 70,
    period: int = 12,
) -> str:
    decomposition = decompose_series(values, period=period)

    panels = [
        ("Serie original", decomposition.observed, "#1d4ed8"),
        ("Tendencia", decomposition.trend, "#a855f7"),
        ("Estacionalidad", decomposition.seasonal, "#22c55e"),
        ("Residuo", decomposition.remainder, "#ef4444"),
    ]

    panel_gap = 30
    panel_height = (height - 2 * padding - panel_gap * (len(panels) - 1)) / len(panels)

    def x(idx: int) -> float:
        return _x_position(idx, len(months), width=width, padding=padding)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>.axis { stroke: #333; stroke-width: 1.5; } .tick { stroke: #888; stroke-width: 1; } .label { font-family: sans-serif; font-size: 12px; fill: #111; }</style>',
        f'<rect width="100%" height="100%" fill="#fafafa" />',
        f'<text class="label" x="{padding}" y="{padding - 25}" font-size="18" font-weight="bold">Descomposición: {brand}</text>',
    ]

    for idx, (title, data, color) in enumerate(panels):
        top = padding + idx * (panel_height + panel_gap)
        bottom = top + panel_height
        min_v, max_v = min(data), max(data)
        span = max_v - min_v or 1.0

        def y(val: float) -> float:
            return bottom - (val - min_v) / span * panel_height

        svg_parts.append(f'<text class="label" x="{padding}" y="{top - 8}" font-weight="bold">{title}</text>')
        svg_parts.append(f'<line class="axis" x1="{padding}" y1="{bottom}" x2="{width - padding}" y2="{bottom}" />')
        svg_parts.append(f'<line class="axis" x1="{padding}" y1="{top}" x2="{padding}" y2="{bottom}" />')

        if min_v < 0 < max_v:
            zero_y = y(0)
            svg_parts.append(f'<line class="tick" x1="{padding}" y1="{zero_y:.2f}" x2="{width - padding}" y2="{zero_y:.2f}" stroke-dasharray="3,3" />')

        for i in range(5):
            val = min_v + i * (span) / 4
            y_pos = y(val)
            svg_parts.append(f'<line class="tick" x1="{padding - 5}" y1="{y_pos:.2f}" x2="{width - padding}" y2="{y_pos:.2f}" stroke-dasharray="2,2" />')
            svg_parts.append(f'<text class="label" x="{padding - 10}" y="{y_pos + 4:.2f}" text-anchor="end">{val:.1f}</text>')

        points = " ".join(f"{x(i):.2f},{y(val):.2f}" for i, val in enumerate(data))
        svg_parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{points}" />')

        if idx == len(panels) - 1:
            step = max(1, len(months) // 10)
            for j in range(0, len(months), step):
                x_pos = x(j)
                svg_parts.append(f'<line class="tick" x1="{x_pos:.2f}" y1="{bottom}" x2="{x_pos:.2f}" y2="{bottom + 6}" />')
                label = months[j]
                svg_parts.append(
                    f'<text class="label" x="{x_pos:.2f}" y="{bottom + 18}" text-anchor="middle" transform="rotate(45 {x_pos:.2f},{bottom + 18})">{label}</text>'
                )

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def generate_visualization():
    months, series = load_fastfashion_data(XLSX_PATH)
    palette = ["#3b82f6", "#10b981", "#f97316"]
    series_data = [SeriesData(label, series[label], color) for label, color in zip(series.keys(), palette)]
    svg_content = build_svg(months, series_data)
    OUTPUT_SVG.write_text(svg_content, encoding="utf-8")
    return OUTPUT_SVG


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera visualizaciones de las series temporales de fast fashion.")
    parser.add_argument(
        "--decompose",
        dest="decompose_brand",
        help="Nombre de la marca que se desea descomponer (zara, temu, shein)",
    )
    parser.add_argument(
        "--output",
        dest="output",
        help="Ruta del archivo SVG de salida. Si se omite, se usa un nombre por defecto.",
    )
    args = parser.parse_args()

    months, series = load_fastfashion_data(XLSX_PATH)

    if args.decompose_brand:
        brand_key = args.decompose_brand.lower()
        if brand_key not in series:
            available = ", ".join(series.keys())
            raise SystemExit(f"Marca desconocida: {brand_key}. Disponibles: {available}")

        output_path = Path(args.output) if args.output else Path(f"{brand_key}_decomposition.svg")
        svg_content = build_decomposition_svg(months, brand_key, series[brand_key])
        output_path.write_text(svg_content, encoding="utf-8")
        print(f"SVG de descomposición guardado en {output_path}")
    else:
        palette = ["#3b82f6", "#10b981", "#f97316"]
        series_data = [SeriesData(label, series[label], color) for label, color in zip(series.keys(), palette)]
        svg_content = build_svg(months, series_data)
        output_path = Path(args.output) if args.output else OUTPUT_SVG
        output_path.write_text(svg_content, encoding="utf-8")
        print(f"SVG guardado en {output_path}")
