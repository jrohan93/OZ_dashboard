---
name: refresh-dashboard
description: 공유판(claude.ai 대시보드 아티팩트)의 데이터를 Supabase 최신 값으로 갱신한다. 사용자가 "공유판 갱신", "대시보드 데이터 업데이트", "/refresh-dashboard"라고 할 때 쓴다. 시트에서 새로 받아 Supabase에 다시 적재하는 것까지 원하면 1단계부터, Supabase는 이미 최신이면 2단계부터 한다.
---

# 공유판 데이터 갱신 (Supabase → 공유판)

공유판: https://claude.ai/artifact/FAe1GcavAmRRMVRSCQJwWS
데이터셋 두 개(`datasets/dm_rx`, `datasets/dm_dx`)가 각각 업로드된 CSV 파일을 가리킨다. 공유판 페이지는 인터넷에 직접 접속할 수 없어서 Supabase를 실시간으로 읽지 못한다. 그래서 이 절차로 파일을 바꿔 끼운다.

DB에 접속하는 명령은 네트워크가 필요하다(샌드박스 밖에서 실행). 출력에 연결 문자열이 섞일 수 있으니 `sed -E 's#://[^@]*@#://***@#g'`로 가린다.

1. (선택: 원본까지 새로 받을 때)
   ```bash
   .venv/bin/python scripts/fetch_data.py && .venv/bin/python scripts/load_supabase.py
   ```
2. Supabase 뷰에서 CSV 만들기:
   ```bash
   .venv/bin/python scripts/export_artifact_data.py
   ```
   출력 첫머리가 `source=supabase`인지 확인한다. `csv`이면 `.env`의 `SUPABASE_DB_URL`이 비어 있는 것이니 멈추고 사용자에게 알린다.
3. Artifact 도구로 두 파일을 따로따로 올린다. CSV는 한 번에 하나씩만 올릴 수 있다. `action: "publish"`, `url`: 위 공유판, `asset: true`, `file_path`: `data/export/dm_rx.csv`(그다음 `dm_dx.csv`). 결과로 나온 `/_blob/<id>`를 적어 둔다.
4. ArtifactData로 `datasets` 컬렉션을 먼저 `list`해서 각 문서의 `version`을 확인한다. 그다음 `batch`로 두 문서를 `update`한다(`if_version` 지정). 바꿀 필드:
   - `source`: `{kind: "file", name: "dm_rx.csv", url: "/_blob/<id>"}`
   - `updated`: `{at: <지금 ISO 시각>, by: "Claude (/refresh-dashboard)"}`
5. 이전 파일(바꾸기 전 `source.url`의 id)은 더 이상 쓰이지 않는다. Artifact `action: "delete"`에 `path: <id>`를 주어 지운다.
6. 사용자에게 보고한다. 갱신한 행 수와 합계(2단계 출력), 공유판 링크를 알려 준다. 보고는 한국어로 한다.

페이지(`files/index.html`)는 바꾸지 않는다. 열 이름이나 의미가 바뀌었으면 데이터만 갱신하지 말고, 사용자와 먼저 상의한다.
