"""당뇨병 시장 집계용 데이터 준비.

두 가지 시장을 정의한다.
- 약물 시장: 당뇨병용제(약효분류 396) 원외처방 금액(claim_rx.amt)
- 질환 시장: 주상병이 2형 당뇨병(E11)인 명세서의 총진료비(rvd_rpe_tamt_amt)

지역은 수진자 거주 시도(patient.sido_cd), 요양기관 종별은 institution.cl_cd 기준.
연령은 진료 연도 - 출생 연도.

같은 규칙이 supabase/migrations/*_dm_market_views.sql 의 dm_rx·dm_dx 뷰에도 있다. 한쪽을 바꾸면 둘 다 바꾼다.
SUPABASE_DB_URL(.env)이 있으면 load()는 그 뷰를 읽고, 없으면 data/raw CSV로 직접 계산한다.
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
load_dotenv(ROOT / ".env")

SAMPLE_PATIENTS = 3000           # patient 테이블 행 수
DEFAULT_POPULATION = 51_200_000  # 전국 주민등록인구 (약 5,120만, 조정 가능)

DM_CLASS = "396"                 # 당뇨병용제
DM_DX = "E11"                    # 2형 당뇨병

INGREDIENTS = {                  # 성분명(영문 원본) -> (표시명, 계열)
    "sitagliptin phosphate hydrate (as sitagliptin)": ("시타글립틴", "DPP-4 억제제"),
    "glimepiride": ("글리메피리드", "설포닐우레아"),
    "metformin hydrochloride": ("메트포르민", "비구아나이드"),
}
INGREDIENT_ORDER = ["시타글립틴", "글리메피리드", "메트포르민"]

CL_NAMES = {"01": "상급종합병원", "11": "종합병원", "21": "병원", "31": "의원"}
CL_ORDER = ["상급종합병원", "종합병원", "병원", "의원"]
SEX_NAMES = {"1": "남", "2": "여"}
AGE_ORDER = ["40세 미만", "40대", "50대", "60대", "70대", "80세 이상"]
REGION_ORDER = ["수도권", "강원충청권", "호남제주권", "영남권"]


def _read(name):
    return pd.read_csv(RAW / f"{name}.csv", dtype=str)


def _age_group(age):
    if age < 40:
        return "40세 미만"
    if age >= 80:
        return "80세 이상"
    return f"{age // 10 * 10}대"


def _with_dims(df, patient, inst, sido):
    """명세서 단위 데이터에 시간·지역·종별·성별·연령 차원을 붙인다."""
    df = (df.merge(patient, on="jid", how="left")
            .merge(inst[["yid", "cl_cd"]], on="yid", how="left")
            .merge(sido[["sido_cd", "sido_nm", "region_nm"]], on="sido_cd", how="left"))
    df["ym"] = df["recu_fr_dd"].str[:7]
    df["year"] = df["recu_fr_dd"].str[:4].astype(int)
    df["cl_nm"] = df["cl_cd"].map(CL_NAMES).fillna("기타")
    df["sex"] = df["sex_tp_cd"].map(SEX_NAMES).fillna("미상")
    age = df["year"] - df["birth_yr"].astype(int)
    df["age_grp"] = age.map(_age_group)
    return df


def source():
    return "supabase" if os.environ.get("SUPABASE_DB_URL") else "csv"


def load():
    """(rx, dx) 두 개의 팩트 테이블을 돌려준다.

    rx: 당뇨병용제 원외처방 한 줄 = 한 행 (amt, ingredient, mid, jid + 차원)
    dx: E11 주상병 명세서 한 건 = 한 행 (total/insurer/self 금액 + 차원)
    """
    return load_db() if source() == "supabase" else load_csv()


def load_db():
    import psycopg

    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn, conn.cursor() as cur:
        out = []
        for view in ("dm_rx", "dm_dx"):
            cur.execute(f"select * from {view}")
            df = pd.DataFrame(cur.fetchall(), columns=[c.name for c in cur.description])
            for col in ("amt", "total", "insurer", "self"):
                if col in df:
                    df[col] = df[col].astype(float)
            out.append(df)
    return tuple(out)


def load_csv():
    """load()와 같은 결과를 data/raw CSV에서 판다스로 계산한다."""
    claim = _read("claim")
    patient = _read("patient")[["jid", "sex_tp_cd", "birth_yr", "sido_cd"]]
    inst = _read("institution")
    sido = _read("sido_code")
    drug = _read("drug_ingredient")[["gnl_cd", "gnl_nm", "class_no"]]
    claim_rx = _read("claim_rx")[["mid", "gnl_cd", "amt"]]

    head = claim[["mid", "jid", "yid", "recu_fr_dd", "main_sick"]]

    rx = (claim_rx.merge(drug, on="gnl_cd", how="left")
                  .query("class_no == @DM_CLASS")
                  .merge(head, on="mid", how="inner"))
    rx["amt"] = rx["amt"].astype(float)
    rx["ingredient"] = rx["gnl_nm"].map(lambda n: INGREDIENTS.get(n, (n, ""))[0])
    rx["drug_class"] = rx["gnl_nm"].map(lambda n: INGREDIENTS.get(n, ("", "기타"))[1])
    rx = _with_dims(rx, patient, inst, sido)

    dx = claim[claim["main_sick"].str[:3] == DM_DX].copy()
    dx = dx.rename(columns={"rvd_rpe_tamt_amt": "total",
                            "rvd_insup_brdn_amt": "insurer",
                            "rvd_slf_brdn_amt": "self"})
    for col in ("total", "insurer", "self"):
        dx[col] = dx[col].astype(float)
    dx = dx[["mid", "jid", "yid", "recu_fr_dd", "total", "insurer", "self"]]
    dx = _with_dims(dx, patient, inst, sido)

    return rx, dx


def scale_factor(population=DEFAULT_POPULATION):
    """샘플 -> 전국 추정 배율 (단순 인구 비례)."""
    return population / SAMPLE_PATIENTS
