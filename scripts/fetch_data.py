"""구글 시트의 각 탭(테이블)을 data/raw/<탭>.csv 로 내려받는다.

    python scripts/fetch_data.py
"""
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

SHEET_ID = "1nPuY8AKFAs2r9da4xUBV3WMKdLEBZJGpmd3kP7xKNvU"
TABS = [
    "claim", "patient", "institution", "sick_master", "code_table",
    "sido_code", "hospital_open", "claim_sick", "claim_rx", "drug_ingredient",
]
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for tab in TABS:
        url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
               f"/gviz/tq?tqx=out:csv&sheet={quote(tab)}")
        with urlopen(url) as r:
            body = r.read()
        (OUT / f"{tab}.csv").write_bytes(body)
        print(f"{tab}: {body.count(b'\n')} lines")


if __name__ == "__main__":
    main()
