"""Minimal visualization for fast fashion brand time series.

This script avoids external dependencies by parsing the XLSX file
with the standard library and emitting a standalone SVG chart.
"""
from __future__ import annotations

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


def generate_visualization():
    months, series = load_fastfashion_data(XLSX_PATH)
    palette = ["#3b82f6", "#10b981", "#f97316"]
    series_data = [SeriesData(label, series[label], color) for label, color in zip(series.keys(), palette)]
    svg_content = build_svg(months, series_data)
    OUTPUT_SVG.write_text(svg_content, encoding="utf-8")
    return OUTPUT_SVG


if __name__ == "__main__":
    path = generate_visualization()
    print(f"SVG guardado en {path}")
