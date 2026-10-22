# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트

국내 당뇨병 시장 규모 대시보드(제약회사 마케터용). 심평원 청구 형식 실습 샘플(수진자 3,000명, 2024-01 ~ 2025-12)을 Supabase(Postgres)에 올리고, Streamlit 대시보드가 그 DB를 읽어 그린다. 사용자 문서·UI·주석은 한국어로 쓴다.

## 명령

```bash
uv venv && uv pip install -r requirements.txt
.venv/bin/streamlit run app.py                      # 대시보드 (.claude/launch.json 의 "dashboard", 포트 8501)

# 데이터 파이프라인: 구글 시트 -> CSV -> Supabase
.venv/bin/python scripts/fetch_data.py              # 시트 탭 -> data/raw/*.csv
.venv/bin/python scripts/load_supabase.py           # data/raw -> .env 의 SUPABASE_DB_URL (truncate 후 재적재)
.venv/bin/python scripts/load_supabase.py --local   # 로컬 Supabase(127.0.0.1:54322)로 적재

# Supabase CLI (Docker 필요)
supabase start                                      # 로컬 스택
supabase db reset                                   # 로컬 DB를 migrations 로 다시 만든다 (데이터는 지워짐 -> load --local 다시)
supabase migration new <name>                       # 스키마 변경은 항상 새 마이그레이션 파일로
supabase link --project-ref <ref> && supabase db push   # 원격 반영
```

테스트·린트 설정은 없다. 변경 검증은 앱을 띄워 보거나, `dm.load_csv()`와 `dm.load_db()` 결과의 합계를 비교한다.

## 구조

- **시장 정의가 두 곳에 있다.** `dm_market.py`의 `load_csv()`(판다스)와 `supabase/migrations/*_dm_market_views.sql`의 `claim_dims` → `dm_rx`·`dm_dx` 뷰(SQL)가 같은 규칙(약효분류 396 = 당뇨병용제, 주상병 E11, 거주 시도 기준 권역, `institution.cl_cd` 종별, 연령 = 진료연도 − 출생연도)을 구현한다. 하나를 바꾸면 다른 쪽도 바꾸고 합계를 대조한다.
- `dm.load()`는 `.env`에 `SUPABASE_DB_URL`이 있으면 뷰를 읽고(`load_db`), 없으면 CSV로 계산한다(`load_csv`). 반환 모양(행 단위 rx/dx 데이터프레임 + `ym`, `year`, `cl_nm`, `region_nm`, `sido_nm`, `sex`, `age_grp` 차원)은 같아야 한다. `app.py`가 모든 집계·필터를 이 행 단위 데이터 위에서 판다스로 한다(환자수 = `jid` nunique라 사전 합산 테이블로는 대체 불가).
- 성분 표시명·계열 매핑은 파이썬 `INGREDIENTS`와 DB 테이블 `dm_ingredient` 두 곳에 있다. 표시 순서 상수(`INGREDIENT_ORDER`, `CL_ORDER`, `AGE_ORDER`, `REGION_ORDER`)는 파이썬에만 있다.
- 전국 추정 = 샘플 값 × (전국 인구 ÷ 3,000). 단순 인구 비례이며 연령·지역 가중치 없음.
- 원본 테이블은 모두 RLS 켜짐·정책 없음, 뷰는 `security_invoker` + anon/authenticated 권한 회수. 즉 Supabase API(anon key)로는 아무것도 안 보이고, 대시보드는 DB 연결 문자열(postgres 역할)로 직접 읽는다. 행 단위 뷰에는 수진자 ID(`jid`)가 있으니 공개 화면에 열 때는 집계 뷰를 따로 만들어 그것만 grant 한다.
- `dashboard/index.html`은 claude.ai Artifact(공유판) 원본이다. 데이터는 `scripts/export_artifact_data.py`가 만든 `data/export/dm_rx.csv`·`dm_dx.csv`를 쓰며 아직 Supabase에 연결되지 않았다. 공유판 주소: https://claude.ai/artifact/FAe1GcavAmRRMVRSCQJwWS
- 코드 컬럼(`sido_cd`, `cl_cd`, `fom_tp_cd`, `dgsbjt_cd` 등)은 앞자리 0이 있으므로 DB에서는 `text`, 판다스에서는 `dtype=str`로 읽는다.
- 데이터 한계: 당뇨병용제 성분은 시타글립틴·글리메피리드·메트포르민 세 가지뿐이다.
