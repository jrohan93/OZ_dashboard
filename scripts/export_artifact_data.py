"""공유용 대시보드(Artifact)에 올릴 팩트 테이블 CSV를 만든다.

.env 에 SUPABASE_DB_URL 이 있으면 Supabase 뷰(dm_rx, dm_dx)에서, 없으면 data/raw CSV에서 만든다.
공유판에 올리는 절차는 /refresh-dashboard (.claude/skills/refresh-dashboard) 참고.

    .venv/bin/python scripts/export_artifact_data.py
    -> data/export/dm_rx.csv, data/export/dm_dx.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import dm_market as dm  # noqa: E402

OUT = ROOT / "data" / "export"
DIMS = ["ym", "cl_nm", "region_nm", "sido_nm", "sex", "age_grp"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rx, dx = dm.load()
    rx = rx[["mid", "jid", *DIMS, "ingredient", "drug_class", "amt"]].sort_values(["ym", "mid"])
    dx = dx[["mid", "jid", *DIMS, "total", "insurer", "self"]].sort_values(["ym", "mid"])
    for df in (rx, dx):
        for col in ("amt", "total", "insurer", "self"):
            if col in df:
                df[col] = df[col].astype(int)
    rx.to_csv(OUT / "dm_rx.csv", index=False)
    dx.to_csv(OUT / "dm_dx.csv", index=False)
    print(f"source={dm.source()} dm_rx.csv {len(rx)} rows (amt {rx.amt.sum():,}), "
          f"dm_dx.csv {len(dx)} rows (total {dx.total.sum():,})")


if __name__ == "__main__":
    main()
