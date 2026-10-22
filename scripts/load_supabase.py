"""data/raw/*.csv 를 Supabase(Postgres) 원본 테이블로 적재한다. 테이블을 비우고 다시 넣는다.

    .venv/bin/python scripts/load_supabase.py            # .env 의 SUPABASE_DB_URL
    .venv/bin/python scripts/load_supabase.py --local    # supabase start 로 띄운 로컬 DB

스키마는 supabase/migrations/ 에 있고 `supabase db push`(원격) / `supabase db reset`(로컬)로 만든다.
"""
import io
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
LOCAL_DB_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
TABLES = [
    "sido_code", "code_table", "patient", "institution", "hospital_open",
    "sick_master", "drug_ingredient", "claim", "claim_rx", "claim_sick",
]


def db_url():
    if "--local" in sys.argv:
        return LOCAL_DB_URL
    load_dotenv(ROOT / ".env")
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        sys.exit("SUPABASE_DB_URL 이 없습니다. .env.example 을 참고해 .env 를 만드세요.")
    return url


def main():
    with psycopg.connect(db_url()) as conn, conn.cursor() as cur:
        cur.execute(f"truncate {', '.join(TABLES)}")
        for table in TABLES:
            # 빈 칸은 NaN -> 따옴표 없는 빈 값으로 써서 COPY 가 NULL 로 받게 한다.
            df = pd.read_csv(RAW / f"{table}.csv", dtype=str)
            buf = io.StringIO()
            df.to_csv(buf, index=False, header=False)
            cols = ", ".join(df.columns)
            with cur.copy(f"copy {table} ({cols}) from stdin with (format csv)") as copy:
                copy.write(buf.getvalue())
            print(f"{table}: {len(df)} rows")
    print("done")


if __name__ == "__main__":
    main()
