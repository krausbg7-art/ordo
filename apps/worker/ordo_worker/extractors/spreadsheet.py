from io import BytesIO

import openpyxl
import pandas as pd


def extract_xlsx_text(content: bytes) -> str:
    workbook = openpyxl.load_workbook(BytesIO(content), data_only=True)
    lines: list[str] = []
    for sheet in workbook.worksheets:
        lines.append(f"# {sheet.title}")
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                lines.append(" | ".join("" if cell is None else str(cell) for cell in row))
    return "\n".join(lines)


def extract_csv_text(content: bytes) -> str:
    df = pd.read_csv(BytesIO(content))
    lines = [" | ".join(str(c) for c in df.columns)]
    for _, row in df.iterrows():
        lines.append(" | ".join("" if pd.isna(v) else str(v) for v in row.values))
    return "\n".join(lines)
