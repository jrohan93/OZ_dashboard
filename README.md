# 국내 당뇨병 시장 규모 대시보드

제약회사 마케터용. 실습 청구 데이터(수진자 3,000명, 2024-01 ~ 2025-12)로 당뇨병 시장 크기를 봅니다.

- **약물 시장**: 당뇨병용제(약효분류 396) 원외처방액 · 성분별 점유율
- **질환 시장**: 2형 당뇨병(E11) 주상병 명세서의 총진료비 · 환자수
- 세분화: 월·연도(YoY), 성분, 요양기관 종별, 권역·시도(거주지), 성별·연령대
- 샘플 실측값과 전국 추정값(전국 인구 ÷ 3,000 배율, 조정 가능)을 함께 표시

## 실행

```bash
uv venv && uv pip install -r requirements.txt
cp .env.example .env                                  # SUPABASE_DB_URL 채우기 (없으면 data/raw CSV로 동작)
.venv/bin/python scripts/fetch_data.py                # 구글 시트 -> data/raw/*.csv
.venv/bin/python scripts/load_supabase.py             # data/raw -> Supabase
.venv/bin/streamlit run app.py
```

Supabase 스키마는 `supabase/migrations/`에 있고 CLI로 반영합니다.

```bash
supabase login
supabase link --project-ref <ref>
supabase db push
```

## 파일

| 파일 | 역할 |
|---|---|
| `dm_market.py` | 시장 정의·차원 조인, Supabase/CSV 로드 (Streamlit과 공유판이 같이 씀) |
| `supabase/migrations/` | 원본 테이블·RLS, 시장 뷰(`dm_rx`, `dm_dx`) |
| `scripts/load_supabase.py` | CSV를 Supabase 원본 테이블로 적재 |
| `app.py` | Streamlit 대시보드 |
| `scripts/fetch_data.py` | 시트의 각 탭을 CSV로 내려받기 |
| `scripts/export_artifact_data.py` | 공유판용 팩트 CSV(`data/export/`) 생성 |
| `dashboard/index.html` | 공유판(claude.ai Artifact) 페이지 원본 |

공유판: https://claude.ai/artifact/FAe1GcavAmRRMVRSCQJwWS

공유판은 페이지가 직접 인터넷에 접속할 수 없어서 Supabase를 실시간으로 읽지 못합니다. Claude Code에서 `/refresh-dashboard`를 실행하면 Supabase 뷰에서 CSV를 뽑아 공유판 데이터를 바꿔 줍니다.

## 한계

전국 추정은 단순 인구 비례입니다. 연령·지역 가중치가 없으므로 공식 통계와 대조해 보정하세요.
데이터에 당뇨병용제는 시타글립틴·글리메피리드·메트포르민 세 성분뿐입니다.
