"""Descriptive analysis and outlier check for fastfashion.xlsx.

The script avoids external dependencies by parsing the XLSX file with the
standard library. It produces a Markdown report summarizing trends and
potential outliers for each brand.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean, median, quantiles
from typing import Dict, Iterable, List, Tuple
from xml.etree import ElementTree
from zipfile import ZipFile

DATA_FILE = Path("fastfashion.xlsx")
REPORT_FILE = Path("analysis_report.md")


@dataclass
class SeriesStats:
    brand: str
    start: Tuple[datetime, float]
    end: Tuple[datetime, float]
    minimum: Tuple[datetime, float]
    maximum: Tuple[datetime, float]
    avg: float
    med: float
    iqr_bounds: Tuple[float, float]
    outliers: List[Tuple[datetime, float]]



def _load_shared_strings(zf: ZipFile) -> List[str]:
    with zf.open("xl/sharedStrings.xml") as f:
        tree = ElementTree.parse(f)
    root = tree.getroot()
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    shared: List[str] = []
    for si in root.findall("s:si", ns):
        text_element = si.find(".//s:t", ns)
        shared.append(text_element.text if text_element is not None else "")
    return shared


def _load_sheet_rows(zf: ZipFile, shared: List[str]) -> List[List[str]]:
    with zf.open("xl/worksheets/sheet1.xml") as f:
        tree = ElementTree.parse(f)
    root = tree.getroot()
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

    rows: List[List[str]] = []
    for row in root.findall("s:sheetData/s:row", ns):
        values: List[str] = []
        for cell in row.findall("s:c", ns):
            cell_type = cell.attrib.get("t")
            value_element = cell.find("s:v", ns)
            value = value_element.text if value_element is not None else ""
            if cell_type == "s":
                value = shared[int(value)]
            values.append(value)
        rows.append(values)
    return rows


def load_data() -> Tuple[List[Dict[str, float]], List[str]]:
    with ZipFile(DATA_FILE) as zf:
        shared_strings = _load_shared_strings(zf)
        rows = _load_sheet_rows(zf, shared_strings)

    if not rows:
        raise ValueError("No data found in worksheet")

    headers = rows[0]
    data_rows = rows[1:]
    data: List[Dict[str, float]] = []
    def parse_value(raw: str) -> float:
        if not raw:
            return 0.0
        if raw.startswith("<"):
            # Valores reportados como "<1" se aproximan a 0.5 para mantener
            # la continuidad de la serie.
            try:
                upper_bound = float(raw[1:])
                return upper_bound / 2
            except ValueError:
                return 0.0
        return float(raw)

    for row in data_rows:
        # Pad rows that might have trailing empty cells.
        if len(row) < len(headers):
            row += [""] * (len(headers) - len(row))
        entry: Dict[str, float] = {"Mes": datetime.strptime(row[0], "%Y-%m")}
        for key, value in zip(headers[1:], row[1:]):
            entry[key] = parse_value(value)
        data.append(entry)
    return data, headers


def compute_stats(data: List[Dict[str, float]], brand: str) -> SeriesStats:
    values = [(entry["Mes"], entry[brand]) for entry in data]
    values.sort(key=lambda t: t[0])
    numbers = [v for _, v in values]
    q1, q3 = quantiles(numbers, n=4, method="inclusive")[0], quantiles(
        numbers, n=4, method="inclusive"
    )[2]
    iqr = q3 - q1
    if iqr == 0:
        lower, upper = min(numbers), max(numbers)
    else:
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = [(d, v) for d, v in values if v < lower or v > upper]

    minimum = min(values, key=lambda t: t[1])
    maximum = max(values, key=lambda t: t[1])
    start = values[0]
    end = values[-1]

    return SeriesStats(
        brand=brand,
        start=start,
        end=end,
        minimum=minimum,
        maximum=maximum,
        avg=mean(numbers),
        med=median(numbers),
        iqr_bounds=(lower, upper),
        outliers=outliers,
    )


def describe_trend(stat: SeriesStats) -> str:
    start_date, start_value = stat.start
    end_date, end_value = stat.end
    change = end_value - start_value
    pct_change = (change / start_value * 100) if start_value != 0 else float("inf")
    return (
        f"Inicio {start_date:%Y-%m}: {start_value:.0f}; "
        f"Fin {end_date:%Y-%m}: {end_value:.0f}; "
        f"Cambio: {change:+.0f} ({pct_change:+.1f}%)"
    )


def format_outliers(outliers: Iterable[Tuple[datetime, float]]) -> str:
    formatted = [f"{d:%Y-%m} → {v:.0f}" for d, v in outliers]
    return ", ".join(formatted) if formatted else "Ninguno"


def build_report(stats: List[SeriesStats]) -> str:
    lines = ["# Análisis descriptivo de series mensuales", ""]
    lines.append(
        "Los valores corresponden al interés mensual (Google Trends) de cada marca. "
        "Se revisan tendencias y valores atípicos con el criterio de rango "
        "intercuartílico (IQR)."
    )
    lines.append("")

    for stat in stats:
        lines.append(f"## {stat.brand.capitalize()}")
        lines.append("- " + describe_trend(stat))
        lines.append(
            f"- Promedio: {stat.avg:.1f}; Mediana: {stat.med:.1f}; "
            f"Mínimo: {stat.minimum[0]:%Y-%m} ({stat.minimum[1]:.0f}); "
            f"Máximo: {stat.maximum[0]:%Y-%m} ({stat.maximum[1]:.0f})"
        )
        lines.append(
            f"- Límites IQR: {stat.iqr_bounds[0]:.1f} a {stat.iqr_bounds[1]:.1f}; "
            f"Atípicos: {format_outliers(stat.outliers)}"
        )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    data, headers = load_data()
    brands = headers[1:]
    stats = [compute_stats(data, brand) for brand in brands]
    report = build_report(stats)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"Reporte generado en {REPORT_FILE}")


if __name__ == "__main__":
    main()
