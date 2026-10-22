"""국내 당뇨병 시장 규모 대시보드 (Streamlit)

    .venv/bin/streamlit run app.py
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dm_market as dm

st.set_page_config(page_title="당뇨병 시장 규모", page_icon="📈", layout="wide")

# 검증된 기본 팔레트 (dataviz 기준 슬롯 1~3)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
ING_COLOR = dict(zip(dm.INGREDIENT_ORDER, SERIES))
SEX_COLOR = {"남": SERIES[0], "여": SERIES[1]}
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


@st.cache_data(ttl=600)  # Supabase 데이터가 바뀌면 최대 10분 뒤 반영
def load():
    return dm.load()


def won(v):
    """원 단위 금액을 읽기 쉬운 한글 단위로."""
    a = abs(v)
    if a >= 1e12:
        return f"{v / 1e12:,.2f}조원"
    if a >= 1e8:
        return f"{v / 1e8:,.1f}억원"
    if a >= 1e4:
        return f"{v / 1e4:,.0f}만원"
    return f"{v:,.0f}원"


def count(v):
    if v >= 1e4:
        return f"{v / 1e4:,.1f}만"
    return f"{v:,.0f}"


def growth(cur, prev):
    return None if not prev else f"{(cur / prev - 1) * 100:+.1f}% YoY"


def style(fig, height=320, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, -apple-system, sans-serif", color=INK2, size=12),
        showlegend=legend, bargap=0.35, bargroupgap=0.08,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        hoverlabel=dict(bgcolor="white", font_color=INK),
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, tickcolor=AXIS, tickfont_color=MUTED)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS, tickfont_color=MUTED)
    return fig


def money_unit(vmax):
    """금액 축 단위: (나눌 값, 접미사)."""
    if vmax >= 1e8:
        return 1e8, "억"
    return 1e4, "만"


def bar_h(df, label, value, fmt, color=SERIES[0], order=None):
    """한 시리즈 가로 막대 (값 직접 표기)."""
    if order:
        df = df.set_index(label).reindex([o for o in order if o in set(df[label])]).reset_index()
    df = df.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=df[value], y=df[label], orientation="h", marker_color=color,
        marker_cornerradius=4, text=[fmt(v) for v in df[value]], textposition="outside",
        textfont_color=INK2, cliponaxis=False,
        hovertemplate="%{y}: %{text}<extra></extra>"))
    fig.update_xaxes(visible=False, range=[0, df[value].max() * 1.6 if len(df) else 1])
    return style(fig, height=max(180, 44 * len(df) + 30), legend=False)


# ---------------------------------------------------------------- data
rx_all, dx_all = load()

with st.sidebar:
    st.header("추정 설정")
    pop = st.number_input("전국 인구 (명)", value=dm.DEFAULT_POPULATION, step=100_000,
                          help="샘플 수진자 3,000명을 전국 인구로 단순 확대합니다.")
    factor = dm.scale_factor(pop)
    view = st.radio("차트 기준", ["전국 추정", "샘플 실측"], horizontal=True)
    st.caption(f"확대 배율 ×{factor:,.0f}  (전국 인구 ÷ 샘플 {dm.SAMPLE_PATIENTS:,}명)")
    st.caption("추정치는 샘플이 전국 인구 구성을 대표한다는 가정의 단순 비례 추정입니다. "
               "연령·지역 가중치를 적용하지 않았습니다.")
    st.divider()
    st.caption(f"데이터 원본: {'Supabase' if dm.source() == 'supabase' else '로컬 CSV'}")
    if st.button("데이터 새로고침"):
        load.clear()
        st.rerun()

k = factor if view == "전국 추정" else 1.0

st.title("국내 당뇨병 시장 규모")
st.caption("심평원 청구 형식 실습 샘플(수진자 3,000명, 2024-01 ~ 2025-12) 기준.  "
           "약물 시장 = 당뇨병용제(약효분류 396) 원외처방액 · "
           "질환 시장 = 2형 당뇨병(E11) 주상병 명세서 총진료비")

# 필터 (모든 차트에 공통 적용)
def pick(col, label, options, **kw):
    return col.pills(label, options, selection_mode="multi", default=options, **kw) or []


with st.container(border=True):
    f1, f2, f3 = st.columns([1, 2, 1])
    all_years = sorted(set(rx_all.year) | set(dx_all.year))
    years = [int(y) for y in pick(f1, "연도", [str(y) for y in all_years])]
    ings = pick(f2, "성분", dm.INGREDIENT_ORDER, help="약물 시장에만 적용")
    sexes = pick(f3, "성별", ["남", "여"])
    f4, f5, f6 = st.columns([2, 2, 3])
    cls = pick(f4, "요양기관 종별", dm.CL_ORDER)
    regions = pick(f5, "권역 (거주지)", dm.REGION_ORDER)
    ages = pick(f6, "연령대", dm.AGE_ORDER)


def apply(df):
    return df[df.cl_nm.isin(cls) & df.region_nm.isin(regions)
              & df.sex.isin(sexes) & df.age_grp.isin(ages)]


rx_dim = apply(rx_all[rx_all.ingredient.isin(ings)])  # 연도 필터 전 (YoY 계산용)
dx_dim = apply(dx_all)
rx = rx_dim[rx_dim.year.isin(years)]
dx = dx_dim[dx_dim.year.isin(years)]

if rx.empty and dx.empty:
    st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
    st.stop()

# ---------------------------------------------------------------- KPI
def yoy(df, col=None, nunique=None):
    v = {}
    for y in (2024, 2025):
        d = df[df.year == y]
        v[y] = d[nunique].nunique() if nunique else d[col].sum()
    return growth(v[2025], v[2024])


st.subheader("한눈에 보기")
st.caption("큰 숫자 = 전국 추정, 작은 글씨 = 샘플 실측.  YoY는 2025 vs 2024 (연도 필터와 무관)")
kpis = [
    ("당뇨병용제 처방액", rx.amt.sum(), won, yoy(rx_dim, "amt")),
    ("처방 환자수", rx.jid.nunique(), count, yoy(rx_dim, nunique="jid")),
    ("처방 건수", rx.mid.nunique(), count, yoy(rx_dim, nunique="mid")),
    ("E11 총진료비", dx.total.sum(), won, yoy(dx_dim, "total")),
    ("E11 진료 환자수", dx.jid.nunique(), count, yoy(dx_dim, nunique="jid")),
    ("E11 명세서", len(dx), count, yoy(dx_dim, nunique="mid")),
]
for title, row in (("💊 약물 시장 · 당뇨병용제 원외처방", kpis[:3]),
                   ("🏥 질환 시장 · 2형 당뇨병(E11) 진료", kpis[3:])):
    st.markdown(f"**{title}**")
    for col, (label, v, fmt, d) in zip(st.columns(3), row):
        with col.container(border=True):
            st.metric(label, fmt(v * factor), d)
            st.caption(f"샘플 실측 {fmt(v)}")

unit = "전국 추정" if k != 1 else "샘플 실측"
tab_rx, tab_dx, tab_tbl = st.tabs(["💊 약물 시장 (당뇨병용제)", "🏥 질환 시장 (E11 진료)", "📋 표 보기"])

# ---------------------------------------------------------------- 약물 시장
with tab_rx:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"**월별 처방액 추이 — 성분별** · {unit}")
        m = rx.groupby(["ym", "ingredient"]).amt.sum().unstack(fill_value=0) * k
        div, suf = money_unit(m.values.max() if m.size else 0)
        fig = go.Figure()
        for ing in [i for i in dm.INGREDIENT_ORDER if i in m.columns]:
            fig.add_scatter(x=m.index, y=m[ing] / div, name=ing, mode="lines",
                            line=dict(color=ING_COLOR[ing], width=2),
                            customdata=[won(v) for v in m[ing]],
                            hovertemplate=f"{ing}: %{{customdata}}<extra></extra>")
        fig.update_layout(hovermode="x unified")
        fig.update_yaxes(tickformat=",.0f", ticksuffix=suf, rangemode="tozero")
        st.plotly_chart(style(fig, 340), width="stretch")
    with right:
        st.markdown("**성분별 점유율** (선택 기간 처방액 기준)")
        s = rx.groupby("ingredient").agg(amt=("amt", "sum"), n=("mid", "nunique"),
                                         pts=("jid", "nunique")).reindex(
            [i for i in dm.INGREDIENT_ORDER if i in set(rx.ingredient)])
        s["share"] = s.amt / s.amt.sum()
        s["n_share"] = s.n / s.n.sum()
        fig = go.Figure(go.Bar(
            x=s.share, y=s.index, orientation="h",
            marker_color=[ING_COLOR[i] for i in s.index], marker_cornerradius=4,
            text=[f"{v:.1%}" for v in s.share], textposition="outside", cliponaxis=False,
            textfont_color=INK2,
            customdata=[[won(a * k), f"{ns:.1%}"] for a, ns in zip(s.amt, s.n_share)],
            hovertemplate="%{y}<br>금액 점유율 %{text} (%{customdata[0]})"
                          "<br>건수 점유율 %{customdata[1]}<extra></extra>"))
        fig.update_xaxes(visible=False, range=[0, 1])
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(style(fig, 200, legend=False), width="stretch")
        tbl = pd.DataFrame({
            "계열": [dm.INGREDIENTS[[g for g, v in dm.INGREDIENTS.items() if v[0] == i][0]][1]
                   for i in s.index],
            "처방액": [won(a * k) for a in s.amt],
            "금액 점유율": [f"{v:.1%}" for v in s.share],
            "건수 점유율": [f"{v:.1%}" for v in s.n_share],
            "건당 금액": [won(a / n) for a, n in zip(s.amt, s.n)],
        }, index=s.index)
        st.dataframe(tbl, width="stretch")

    st.markdown("**분기별 점유율 변화** (처방액 기준)")
    q = rx.assign(q=rx.year.astype(str) + "-Q" + ((rx.ym.str[5:].astype(int) - 1) // 3 + 1).astype(str))
    qs = q.groupby(["q", "ingredient"]).amt.sum().unstack(fill_value=0)
    qs = qs.div(qs.sum(axis=1), axis=0)
    fig = go.Figure()
    for ing in [i for i in dm.INGREDIENT_ORDER if i in qs.columns]:
        fig.add_scatter(x=qs.index, y=qs[ing], name=ing, mode="lines+markers",
                        line=dict(color=ING_COLOR[ing], width=2), marker=dict(size=8),
                        hovertemplate=f"{ing}: %{{y:.1%}}<extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    st.plotly_chart(style(fig, 280), width="stretch")

    a, b = st.columns(2)
    with a:
        st.markdown(f"**요양기관 종별 처방액** · {unit}")
        d = rx.groupby("cl_nm").amt.sum().mul(k).reset_index()
        st.plotly_chart(bar_h(d, "cl_nm", "amt", won, order=dm.CL_ORDER), width="stretch")
    with b:
        st.markdown(f"**권역별 처방액** (환자 거주지) · {unit}")
        d = rx.groupby("region_nm").amt.sum().mul(k).reset_index()
        st.plotly_chart(bar_h(d, "region_nm", "amt", won, order=dm.REGION_ORDER), width="stretch")
    with st.container():
        st.markdown(f"**성별·연령대 처방액** · {unit}")
        d = rx.groupby(["age_grp", "sex"]).amt.sum().mul(k).unstack(fill_value=0).reindex(dm.AGE_ORDER).fillna(0)
        div, suf = money_unit(d.values.max() if d.size else 0)
        fig = go.Figure()
        for sx in [s_ for s_ in ["남", "여"] if s_ in d.columns]:
            fig.add_bar(x=d.index, y=d[sx] / div, name=sx, marker_color=SEX_COLOR[sx], marker_cornerradius=4,
                        customdata=[won(v) for v in d[sx]],
                        hovertemplate=f"%{{x}} {sx}: %{{customdata}}<extra></extra>")
        fig.update_yaxes(tickformat=",.0f", ticksuffix=suf)
        st.plotly_chart(style(fig, 280), width="stretch")

    with st.expander("시도별 처방액"):
        d = rx.groupby("sido_nm").agg(처방액=("amt", "sum"), 환자수=("jid", "nunique"))
        d = d.sort_values("처방액", ascending=False)
        d["처방액"] = [won(v * k) for v in d["처방액"]]
        d["환자수"] = [count(v * k) for v in d["환자수"]]
        st.dataframe(d, width="stretch")

# ---------------------------------------------------------------- 질환 시장
with tab_dx:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"**월별 E11 총진료비** · {unit}")
        m = dx.groupby("ym").agg(total=("total", "sum"), pts=("jid", "nunique"))
        div, suf = money_unit((m.total * k).max() if len(m) else 0)
        fig = go.Figure(go.Scatter(
            x=m.index, y=m.total * k / div, mode="lines", line=dict(color=SERIES[0], width=2),
            customdata=[[won(t * k), count(p * k)] for t, p in zip(m.total, m.pts)],
            hovertemplate="%{x}<br>총진료비 %{customdata[0]}<br>환자수 %{customdata[1]}<extra></extra>"))
        fig.update_yaxes(tickformat=",.0f", ticksuffix=suf, rangemode="tozero")
        st.plotly_chart(style(fig, 300, legend=False), width="stretch")
    with right:
        st.markdown("**연도별 비교**")
        y = dx_dim.groupby("year").agg(총진료비=("total", "sum"), 보험자부담=("insurer", "sum"),
                                       본인부담=("self", "sum"), 환자수=("jid", "nunique"),
                                       명세서=("mid", "nunique"))
        y["환자당 진료비"] = y["총진료비"] / y["환자수"]
        y["명세서당 진료비"] = y["총진료비"] / y["명세서"]
        out = pd.DataFrame(index=y.index)
        for col in ["총진료비", "보험자부담", "본인부담"]:
            out[col] = [won(v * k) for v in y[col]]
        for col in ["환자수", "명세서"]:
            out[col] = [count(v * k) for v in y[col]]
        for col in ["환자당 진료비", "명세서당 진료비"]:
            out[col] = [won(v) for v in y[col]]
        st.dataframe(out.T, width="stretch")
        st.caption("환자당·명세서당 진료비는 배율과 무관 (샘플 실측). 연도 필터와 무관하게 두 해를 모두 표시.")

    a, b = st.columns(2)
    with a:
        st.markdown(f"**요양기관 종별 진료 환자수** · {unit}")
        d = dx.groupby("cl_nm").jid.nunique().mul(k).reset_index()
        st.plotly_chart(bar_h(d, "cl_nm", "jid", count, order=dm.CL_ORDER), width="stretch")
    with b:
        st.markdown(f"**권역별 진료 환자수** (거주지) · {unit}")
        d = dx.groupby("region_nm").jid.nunique().mul(k).reset_index()
        st.plotly_chart(bar_h(d, "region_nm", "jid", count, order=dm.REGION_ORDER), width="stretch")
    with st.container():
        st.markdown(f"**성별·연령대 진료 환자수** · {unit}")
        d = dx.groupby(["age_grp", "sex"]).jid.nunique().mul(k).unstack(fill_value=0).reindex(dm.AGE_ORDER).fillna(0)
        fig = go.Figure()
        for sx in [s_ for s_ in ["남", "여"] if s_ in d.columns]:
            fig.add_bar(x=d.index, y=d[sx], name=sx, marker_color=SEX_COLOR[sx], marker_cornerradius=4,
                        customdata=[count(v) for v in d[sx]],
                        hovertemplate=f"%{{x}} {sx}: %{{customdata}}명<extra></extra>")
        st.plotly_chart(style(fig, 280), width="stretch")

# ---------------------------------------------------------------- 표
with tab_tbl:
    st.markdown(f"**월별 시장 규모** · {unit}")
    mr = rx.groupby(["ym", "ingredient"]).amt.sum().unstack(fill_value=0)
    md = dx.groupby("ym").agg(E11_총진료비=("total", "sum"), E11_환자수=("jid", "nunique"))
    t = mr.join(md, how="outer").fillna(0) * k
    t.insert(len(mr.columns), "당뇨병용제_합계", t[mr.columns].sum(axis=1))
    st.dataframe(t.round(0), width="stretch")
    st.download_button("CSV 내려받기", t.round(0).to_csv().encode("utf-8-sig"),
                       "dm_market_monthly.csv", "text/csv")
