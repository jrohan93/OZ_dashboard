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
.venv/bin/python scripts/build_pages.py             # dashboard/index.html -> docs/index.html (GitHub Pages)

# Supabase CLI (Docker 필요)
supabase start                                      # 로컬 스택
supabase db reset                                   # 로컬 DB를 migrations 로 다시 만든다 (데이터는 지워짐 -> load --local 다시)
supabase migration new <name>                       # 스키마 변경은 항상 새 마이그레이션 파일로
supabase link --project-ref <ref> && supabase db push   # 원격 반영
```

테스트·린트 설정은 없다. 변경 검증은 앱을 띄워 보거나, `dm.load_csv()`와 `dm.load_db()` 결과의 합계를 비교한다.

## 구조

- **시장 정의가 두 곳에 있다.** `dm_market.py`의 `load_csv()`(판다스)와 `supabase/migrations/*_dm_market_views.sql`의 `claim_dims` → `dm_rx`·`dm_dx` 뷰(SQL)가 같은 규칙(약효분류 396 = 당뇨병용제, 주상병 E11, 거주 시도 기준 권역, `institution.cl_cd` 종별, 연령 = 진료연도 − 출생연도)을 구현한다. 하나를 바꾸면 다른 쪽도 바꾸고 합계를 대조한다.
- `dm.load()`는 `.env`에 `SUPABASE_DB_URL`이 있으면 뷰를 읽고(`load_db`), 없으면 CSV로 계산한다(`load_csv`). `.env`는 import 시점에 한 번만 읽으므로, 바꾸면 Streamlit 서버를 다시 시작해야 한다(사이드바 새로고침 버튼으로는 안 바뀐다). 반환 모양(행 단위 rx/dx 데이터프레임 + `ym`, `year`, `cl_nm`, `region_nm`, `sido_nm`, `sex`, `age_grp` 차원)은 같아야 한다. `app.py`가 모든 집계·필터를 이 행 단위 데이터 위에서 판다스로 한다(환자수 = `jid` nunique라 사전 합산 테이블로는 대체 불가).
- 성분 표시명·계열 매핑은 파이썬 `INGREDIENTS`와 DB 테이블 `dm_ingredient` 두 곳에 있다. 표시 순서 상수(`INGREDIENT_ORDER`, `CL_ORDER`, `AGE_ORDER`, `REGION_ORDER`)는 파이썬에만 있다.
- 전국 추정 = 샘플 값 × (전국 인구 ÷ 3,000). 단순 인구 비례이며 연령·지역 가중치 없음.
- 권한: 원본 테이블은 RLS 켜짐·정책 없음, 내부 뷰(`claim_dims`, `dm_rx`, `dm_dx`)는 anon/authenticated 권한 회수. Streamlit은 DB 연결 문자열(postgres 역할)로 읽는다. publishable(anon) 키로 읽히는 건 공개 뷰 `dm_rx_public`·`dm_dx_public`뿐이다. 이 뷰는 ID·진료일을 빼고 수진자·명세서를 md5 해시(`pid`, `cid`)로 가명처리한다. 공개 뷰는 소유자 권한으로 내부 뷰를 읽기 때문에 내부 뷰는 `security_invoker = false`다. 내부 뷰에 anon grant를 주면 그대로 노출되니 주의한다.
- GitHub Pages 공개판(https://jrohan93.github.io/OZ_dashboard/)은 `docs/index.html`이다. 직접 고치지 말고 `dashboard/index.html`을 고친 뒤 `scripts/build_pages.py`로 다시 만든다. 이 스크립트가 claude.ai 런타임(`dash.*`)과 디자인 토큰을 대체 코드로 채우고, 공개 뷰를 REST로 읽어 `pid`→`jid`, `cid`→`mid`로 넘긴다. 로컬 확인은 `.claude/launch.json`의 `pages`(포트 8600)로 한다.
- 공유판(https://claude.ai/artifact/FAe1GcavAmRRMVRSCQJwWS)은 Dashboard 타입 아티팩트다. 페이지는 네트워크에 접속할 수 없어서 Supabase를 직접 읽지 못한다. 데이터셋 `dm_rx`·`dm_dx`는 `scripts/export_artifact_data.py`가 Supabase 뷰에서 뽑은 CSV를 업로드한 파일이다. 갱신 절차는 `/refresh-dashboard` 스킬(`.claude/skills/refresh-dashboard/SKILL.md`)에 있다. `dashboard/index.html`은 그 페이지의 로컬 사본이다.
- `data/`(원본·내보낸 CSV)는 git에 올리지 않는다(공개 저장소). `fetch_data.py`·`export_artifact_data.py`로 다시 만든다.
- 코드 컬럼(`sido_cd`, `cl_cd`, `fom_tp_cd`, `dgsbjt_cd` 등)은 앞자리 0이 있으므로 DB에서는 `text`, 판다스에서는 `dtype=str`로 읽는다.
- 데이터 한계: 당뇨병용제 성분은 시타글립틴·글리메피리드·메트포르민 세 가지뿐이다.
