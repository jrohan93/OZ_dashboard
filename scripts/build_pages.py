"""공유판 페이지(dashboard/index.html)를 GitHub Pages용 단독 페이지(docs/index.html)로 만든다.

    .venv/bin/python scripts/build_pages.py

공유판은 claude.ai 대시보드 런타임(dash.*)과 디자인 토큰(--cds-*, --color-*) 위에서 돈다.
여기서는 그 둘을 작은 대체 코드로 채우고, 데이터는 Supabase 공개 뷰(dm_rx_public,
dm_dx_public)를 publishable 키로 REST에서 직접 읽는다. 페이지 본문·차트 코드는 그대로 쓴다.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dashboard" / "index.html"
OUT = ROOT / "docs" / "index.html"

SUPABASE_URL = "https://nsapqdsikjgpkdsftxkz.supabase.co"
# publishable 키는 브라우저 공개용이다. 이 키로는 공개 뷰 두 개만 읽힌다(나머지는 RLS·권한으로 차단).
SUPABASE_KEY = "sb_publishable_LVvurfGf0QFwJdprFYuaaA_JxaMmcBH"

HEAD = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>당뇨병 시장 규모</title>
<meta name="description" content="청구 데이터 실습 샘플로 본 국내 당뇨병 약물·질환 시장 규모 (Supabase 실시간 연결)">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<script src="https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js"></script>
<style>
  :root {
    --font-anthropic-sans: "Pretendard", system-ui, -apple-system, sans-serif;
    --font-anthropic-serif: "Pretendard", system-ui, -apple-system, sans-serif;
    --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 12px; --cds-gap-lg: 20px;
    --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 12px; --cds-pad-lg: 16px;
    --cds-radius: 10px; --cds-font-weight-medium: 600;
    --cds-font-size-caption: 12.5px; --cds-font-size-body: 15px; --cds-font-size-heading: 16px; --cds-font-size-title: 28px;
    --cds-dur-slow: .3s;
    --color-bg: #fafaf7; --color-panel: #ffffff; --color-fg: #0b0b0b; --color-fg-muted: #6b6a65;
    --color-border-line: #e1e0d9; --color-ok: #1a8a5e; --color-bad: #c8412b; --color-warn: #b7791f;
    --cds-chart-grid: #ecebe5; --cds-chart-axis: #c3c2b7; --cds-chart-reference: #898781;
    --cds-surface-popover: #ffffff; --cds-border: #e1e0d9; --cds-text-secondary: #6b6a65;
    --cds-shadow-popover: 0 4px 16px rgba(0,0,0,.08);
    --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a;
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --color-bg: #151514; --color-panel: #1e1e1c; --color-fg: #f2f1ec; --color-fg-muted: #a3a29b;
      --color-border-line: #33322f; --color-ok: #4cc391; --color-bad: #f07a63; --color-warn: #e0b04a;
      --cds-chart-grid: #2c2b28; --cds-chart-axis: #4a4945; --cds-chart-reference: #8a8983;
      --cds-surface-popover: #262624; --cds-border: #3a3936; --cds-text-secondary: #a3a29b;
      --cds-shadow-popover: 0 4px 16px rgba(0,0,0,.4);
      --s1: #5a9cf0; --s2: #f28a5c; --s3: #3fc995;
      color-scheme: dark;
    }
  }
  body { margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); }
  .page { max-width: 1200px; margin: 0 auto; padding: 28px 16px 48px; }
  .dash-skeleton { color: transparent !important; background: var(--color-border-line); border-radius: 6px; animation: pulse 1.2s ease-in-out infinite; }
  .dm-chart.dash-skeleton, .dm-chart-sm.dash-skeleton { color: inherit !important; }
  @keyframes pulse { 50% { opacity: .5; } }
  .site-foot { margin-top: 28px; font-size: 12.5px; color: var(--color-fg-muted); line-height: 1.6; }
  .site-foot a { color: inherit; }
</style>
</head>
<body>
<main class="page">
"""

SHIM = """<script>
// claude.ai 대시보드 런타임(dash.*) 대체: Supabase 공개 뷰를 읽어 같은 모양으로 넘긴다.
(() => {
  const URL_ = %(url)r, KEY = %(key)r;
  const VIEWS = { dm_rx: 'dm_rx_public', dm_dx: 'dm_dx_public' };
  const PAGE = 1000;  // PostgREST 기본 최대 행 수
  const state = {}, subs = [];
  let params = {};

  async function fetchAll(view) {
    const rows = [];
    for (let from = 0; ; from += PAGE) {
      const res = await fetch(`${URL_}/rest/v1/${view}?select=*&order=cid`, {
        headers: { apikey: KEY, Authorization: `Bearer ${KEY}`, Range: `${from}-${from + PAGE - 1}` },
      });
      if (!res.ok) throw new Error(`${view}: HTTP ${res.status}`);
      const part = await res.json();
      rows.push(...part);
      if (part.length < PAGE) return rows;
    }
  }
  const notify = () => subs.forEach((fn) => fn());
  function load(id) {
    state[id] = { status: 'loading', data: [] };
    fetchAll(VIEWS[id])
      // 페이지 코드는 jid(수진자)·mid(명세서)로 고유 수를 센다. 공개 뷰의 가명 ID를 그 이름으로 넘긴다.
      .then((rows) => {
        state[id] = { status: 'ok', data: rows.map(({ pid, cid, ...r }) => ({ ...r, jid: pid, mid: cid })) };
        window.dispatchEvent(new CustomEvent('dm-loaded'));
      })
      .catch((e) => { console.error(e); state[id] = { status: 'error', data: [], message: String(e) }; })
      .finally(notify);
  }
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  window.dash = {
    get colors() { return [css('--s1'), css('--s2'), css('--s3')]; },
    data(id) { if (!state[id]) load(id); return state[id]; },
    onData(fn) { subs.push(fn); fn(); },
    params: () => params,
    setParams(p) { params = { ...params, ...p }; notify(); },
    resetParams() { params = {}; notify(); },
    setLink(id) { history.replaceState(null, '', '#' + id); },
  };
  let w = window.innerWidth;
  window.addEventListener('resize', () => { if (window.innerWidth !== w) { w = window.innerWidth; notify(); } });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', notify);
})();
</script>
"""

FOOT = """<footer class="site-foot">
  데이터: Supabase(Postgres) 공개 뷰 <code>dm_rx_public</code>·<code>dm_dx_public</code>를 페이지를 열 때마다 실시간으로 읽습니다.
  수진자·명세서 ID는 해시로 가명처리했고, 원본 청구 테이블은 공개되지 않습니다. <span id="loaded-at"></span><br>
  소스: <a href="https://github.com/jrohan93/OZ_dashboard">github.com/jrohan93/OZ_dashboard</a>
</footer>
</main>
<script>
window.addEventListener('dm-loaded', () => {
  document.getElementById('loaded-at').textContent = '불러온 시각: ' + new Date().toLocaleString('ko-KR');
});
</script>
</body>
</html>
"""


def main():
    page = SRC.read_text()
    style_end = page.index("</style>") + len("</style>")
    body = page[style_end:]
    page_css = page[:style_end]
    script_at = body.index("<script>")
    html = (HEAD + page_css + body[:script_at] + SHIM % {"url": SUPABASE_URL, "key": SUPABASE_KEY}
            + body[script_at:] + FOOT)
    html = html.replace(
        "<p>오즈코딩 헬스케어 SQL 3기 실습 데이터 백업(Google Sheets, 2026-10-06 배포판). 2024-01 ~ 2025-12 명세서 38,375건 중 당뇨병 관련 행만 추렸습니다.</p>",
        "<p>오즈코딩 헬스케어 SQL 3기 실습 데이터 백업(Google Sheets, 2026-10-06 배포판). 2024-01 ~ 2025-12 명세서 38,375건을 "
        "Supabase에 적재하고, 시장 정의는 SQL 뷰(dm_rx, dm_dx)로 구현했습니다. 이 페이지는 그 뷰를 가명처리한 공개 뷰를 읽습니다.</p>")
    html = html.replace("emptyMsg(bx, 'Failed to load', true)", "emptyMsg(bx, '데이터를 불러오지 못했습니다', true)")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html)
    (OUT.parent / ".nojekyll").write_text("")
    print(f"{OUT.relative_to(ROOT)} {len(html):,} bytes")


if __name__ == "__main__":
    main()
