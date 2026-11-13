# -*- coding: utf-8 -*-
"""零售经营洞察台（Retail Insight）

基于 Tableau 公开示例数据集 Sample - Superstore（2019-2020）的 Streamlit 应用，
演示数据分析 → 可视化 → 指标异动归因 → 情景模拟 的完整分析链路。

运行：streamlit run app.py
"""

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from src.loader import load_data, apply_filters, fmt_money  # noqa: E402
from src.attribution import compute_attribution, generate_insight, recovery_scenario  # noqa: E402

# ---------------- 页面配置 ----------------
st.set_page_config(
    page_title="零售经营洞察台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 品牌色（与分析卡片一致的暖纸风）
INK = "#1c1917"
PINK = "#FF2E7E"
ORANGE = "#FF6A00"
TEAL = "#0d9488"
INDIGO = "#4f46e5"
AMBER = "#d97706"
PALETTE = [INDIGO, PINK, ORANGE, TEAL, AMBER, "#7c3aed", "#0369a1", "#78716c"]

st.markdown(
    """
    <style>
    .block-container{padding-top:2rem;max-width:1280px}
    div[data-testid="stMetric"]{background:#fffef9;border:1.5px solid #1c1917;border-radius:10px;
      box-shadow:3px 3px 0 rgba(28,25,23,.85);padding:14px 18px}
    div[data-testid="stMetric"] label{font-size:14px}
    .insight-box{border:1.5px solid #1c1917;border-radius:10px;background:#fffef9;
      box-shadow:3px 3px 0 rgba(28,25,23,.85);padding:8px 4px}
    main table{border-collapse:collapse;font-size:13px;width:100%;margin:8px 0}
    main table th,main table td{border:1px solid #e5decf;padding:6px 10px;text-align:left}
    main table th{background:#f0ebdd;font-family:Georgia,'Songti SC',serif}
    main table tr:nth-child(even) td{background:#faf7ee}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- 版本兼容工具 ----------------
def show_chart(fig):
    """兼容不同 Streamlit 版本的图表渲染（新版本将 use_container_width 更名为 width）。"""
    try:
        st.plotly_chart(fig, use_container_width=True)
    except TypeError:
        st.plotly_chart(fig)


def show_table(df):
    """渲染明细表：优先原生组件，异常时回退 HTML 表格（兼容老系统环境）。"""
    try:
        st.table(df)
    except Exception:
        st.markdown(df.to_html(index=False, border=0), unsafe_allow_html=True)


# ---------------- 数据加载 ----------------
df = load_data()
YEARS = sorted(df["Year"].unique().tolist())

# ---------------- 侧边栏：全局筛选 ----------------
st.sidebar.title("🛒 零售经营洞察台")
st.sidebar.caption("数据：Tableau Sample - Superstore（公开数据集）")

page = st.sidebar.radio(
    "导航",
    ["📌 经营总览", "🔍 交互探索", "📊 深度可视化", "🧭 指标异动归因", "🎬 情景模拟 What-if"],
    label_visibility="collapsed",
)

with st.sidebar.expander("数据筛选（总览/探索页生效）", expanded=False):
    d_min, d_max = df["Order Date"].min().date(), df["Order Date"].max().date()
    date_range = st.date_input("订单日期区间", (d_min, d_max), min_value=d_min, max_value=d_max)
    regions = st.multiselect("地区", options=sorted(df["Region CN"].unique()))
    categories = st.multiselect("品类", options=sorted(df["Category CN"].unique()))

fdf = apply_filters(df, date_range, regions, categories)


def money_metric(label, value, delta=None, help_text=None):
    """带样式的指标卡。"""
    st.metric(label, fmt_money(value), delta=None if delta is None else fmt_money(delta), help=help_text)


# ================= 页面：经营总览 =================
if page == "📌 经营总览":
    st.title("📌 经营总览")
    st.caption("全量订单的核心经营指标 · 支持侧边栏筛选")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        money_metric("总销售额", fdf["Sales"].sum(), help_text="筛选范围内的订单金额合计")
    with c2:
        money_metric("总利润", fdf["Profit"].sum(), help_text="销售额 - 成本")
    with c3:
        margin = fdf["Profit"].sum() / fdf["Sales"].sum() if fdf["Sales"].sum() else 0
        st.metric("整体利润率", f"{margin*100:.1f}%", help="总利润 / 总销售额")
    with c4:
        st.metric("订单数", f"{fdf['Order ID'].nunique():,}")
    with c5:
        st.metric("退货订单行", f"{int(fdf['Returned'].sum()):,}", help="Returns=1 的订单行数")

    st.subheader("月度销售额与利润趋势")
    trend = fdf.groupby("YearMonth").agg(Sales=("Sales", "sum"), Profit=("Profit", "sum")).reset_index()
    fig = go.Figure()
    fig.add_bar(x=trend["YearMonth"], y=trend["Sales"], name="销售额", marker_color=ORANGE, opacity=0.85)
    fig.add_scatter(x=trend["YearMonth"], y=trend["Profit"], name="利润", mode="lines+markers", line=dict(color=INK, width=2.5))
    fig.update_layout(barmode="overlay", height=360, margin=dict(t=10, l=10, r=10, b=10),
                      legend=dict(orientation="h", y=1.12), yaxis_title="金额 ($)")
    show_chart(fig)

    left, right = st.columns(2)
    with left:
        st.subheader("品类 × 年度销售额")
        cat = fdf.groupby(["Year", "Category CN"])["Sales"].sum().reset_index()
        fig = px.bar(cat, x="Category CN", y="Sales", color="Category CN", facet_col="Year",
                     color_discrete_sequence=[INDIGO, PINK, ORANGE], height=320)
        fig.update_layout(margin=dict(t=30, l=10, r=10, b=10), showlegend=False)
        show_chart(fig)
    with right:
        st.subheader("地区利润贡献")
        reg = fdf.groupby("Region CN")["Profit"].sum().sort_values()
        fig = px.bar(reg, orientation="h", color=reg.values >= 0,
                     color_discrete_map={True: TEAL, False: PINK}, height=320)
        fig.update_layout(margin=dict(t=30, l=10, r=10, b=10), showlegend=False, yaxis_title=None)
        show_chart(fig)

    # 自动结论（规则模板，只引用计算数字）
    st.subheader("自动洞察")
    loss_rows = fdf[fdf["Is Loss"]]
    insights = []
    if len(fdf):
        worst_sub = fdf.groupby("Sub-Category")["Profit"].sum().sort_values()
        insights.append(f"利润最差的子品类是「{worst_sub.index[0]}」（{fmt_money(worst_sub.iloc[0])}），最优是「{worst_sub.index[-1]}」（{fmt_money(worst_sub.iloc[-1])}）。")
        y_sales = fdf.groupby("Year")["Sales"].sum()
        if len(y_sales) >= 2:
            yoy = (y_sales.iloc[-1] - y_sales.iloc[0]) / y_sales.iloc[0]
            insights.append(f"最新年度销售额较上一年度 {'增长' if yoy>=0 else '下降'} {abs(yoy)*100:.1f}%，详情请移步「指标异动归因」页。")
        if len(loss_rows):
            insights.append(f"亏损订单行占比 {len(loss_rows)/len(fdf)*100:.1f}%，合计侵蚀利润 {fmt_money(-loss_rows['Profit'].sum())}——集中在折扣高、低毛利的品类。")
        pay = fdf.groupby("Payment CN")["Sales"].sum()
        insights.append(f"支付结构中「{pay.idxmax()}」占比最高（{pay.max()/pay.sum()*100:.0f}%），「{pay.idxmin()}」最低（{pay.min()/pay.sum()*100:.0f}%）。")
    with st.container(border=True):
        for s in insights:
            st.markdown(f"- {s}")


# ================= 页面：交互探索 =================
elif page == "🔍 交互探索":
    st.title("🔍 交互探索")
    st.caption("按维度下钻看结构 · 左侧筛选器同步生效")

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        dim = st.selectbox("分析维度", ["Region CN", "Category CN", "Sub-Category", "Segment CN", "Ship Mode CN", "Payment CN"],
                           format_func=lambda x: {"Region CN": "地区", "Category CN": "品类", "Sub-Category": "子品类",
                                                  "Segment CN": "客户类型", "Ship Mode CN": "配送方式", "Payment CN": "支付方式"}[x])
    with c2:
        metric = st.selectbox("分析指标", ["Sales", "Profit", "Quantity"],
                              format_func=lambda x: {"Sales": "销售额", "Profit": "利润", "Quantity": "销量"}[x])
    with c3:
        topn = st.slider("只看 Top N", 5, 20, 10)

    g = fdf.groupby(dim)[metric].sum().sort_values(ascending=False)
    g_cn = {"Region CN": "地区", "Category CN": "品类", "Sub-Category": "子品类",
            "Segment CN": "客户类型", "Ship Mode CN": "配送方式", "Payment CN": "支付方式"}[dim]

    st.subheader(f"各{g_cn}的{ {True:'销售额', False:'利润', }[metric=='Sales'] if metric in ('Sales','Profit') else '销量' } 排名")
    fig = px.bar(g.head(topn).iloc[::-1], orientation="h",
                 color=g.head(topn).iloc[::-1].index, color_discrete_sequence=PALETTE,
                 labels={"value": "金额 ($)", "index": g_cn})
    fig.update_layout(height=380, margin=dict(t=10, l=10, r=10, b=10), showlegend=False)
    show_chart(fig)

    tab1, tab2, tab3 = st.tabs(["明细表", "月度趋势", "散点关系"])
    with tab1:
        show_table(
            g.reset_index().rename(columns={dim: g_cn, metric: {"Sales": "销售额", "Profit": "利润", "Quantity": "销量"}[metric]})
        )
    with tab2:
        monthly = fdf.groupby(["YearMonth", dim])[metric].sum().reset_index()
        top_names = g.head(topn).index.tolist()
        monthly = monthly[monthly[dim].isin(top_names)]
        fig = px.line(monthly, x="YearMonth", y=metric, color=dim, color_discrete_sequence=PALETTE)
        fig.update_layout(height=360, margin=dict(t=10, l=10, r=10, b=10), yaxis_title="金额 ($)")
        show_chart(fig)
    with tab3:
        fig = px.scatter(fdf.sample(min(len(fdf), 1500), random_state=42), x="Sales", y="Profit",
                         color="Category CN", size="Quantity", opacity=0.6,
                         color_discrete_sequence=[INDIGO, PINK, ORANGE],
                         labels={"Sales": "单行销售额 ($)", "Profit": "单行利润 ($)"})
        fig.update_layout(height=360, margin=dict(t=10, l=10, r=10, b=10))
        show_chart(fig)
        st.caption("每点=一行订单明细。注意大量点落在利润<0区域——高销售额≠高利润。")


# ================= 页面：深度可视化 =================
elif page == "📊 深度可视化":
    st.title("📊 深度可视化")
    st.caption("结构分析四件套：热力图 · 帕累托 · 箱线 · 堆叠")

    l, r = st.columns(2)
    with l:
        st.subheader("客户类型 × 品类 销售热力图")
        pivot = df.pivot_table(index="Segment CN", columns="Category CN", values="Sales", aggfunc="sum")
        fig = px.imshow(pivot, text_auto=True, color_continuous_scale=["#fff4e0", ORANGE, PINK], aspect="auto")
        fig.update_layout(height=330, margin=dict(t=10, l=10, r=10, b=10))
        show_chart(fig)
    with r:
        st.subheader("子品类利润帕累托（80/20）")
        sub = df.groupby("Sub-Category")["Sales"].sum().sort_values(ascending=False)
        cum = sub.cumsum() / sub.sum() * 100
        fig = go.Figure()
        fig.add_bar(x=sub.index, y=sub.values, marker_color=INDIGO, name="销售额")
        fig.add_scatter(x=sub.index, y=cum.values, name="累计占比%", yaxis="y2",
                        line=dict(color=PINK, width=3, shape="spline"))
        fig.add_hline(y=80, line=dict(color=INK, dash="dot", width=1.5), yref="y2",
                      annotation_text="80%", annotation_position="top left")
        fig.update_layout(height=330, margin=dict(t=10, l=10, r=10, b=30),
                          yaxis=dict(title="销售额 ($)"),
                          yaxis2=dict(title="累计占比%", overlaying="y", side="right", range=[0, 105]),
                          legend=dict(orientation="h", y=1.18), xaxis_tickangle=-40)
        show_chart(fig)

    l, r = st.columns(2)
    with l:
        st.subheader("各品类单行利润分布（箱线）")
        fig = px.box(df, x="Category CN", y="Profit", color="Category CN",
                     color_discrete_sequence=[INDIGO, PINK, ORANGE], points="outliers")
        fig.update_layout(height=330, margin=dict(t=10, l=10, r=10, b=10), showlegend=False,
                          yaxis_title="单行利润 ($)")
        show_chart(fig)
    with r:
        st.subheader("月度销售 × 支付方式（堆叠）")
        pay = df.groupby(["YearMonth", "Payment CN"])["Sales"].sum().reset_index()
        fig = px.bar(pay, x="YearMonth", y="Sales", color="Payment CN", color_discrete_sequence=[TEAL, INDIGO, PINK])
        fig.update_layout(height=330, barmode="stack", margin=dict(t=10, l=10, r=10, b=10),
                          legend=dict(orientation="h", y=1.15), yaxis_title="销售额 ($)")
        show_chart(fig)

    st.subheader("退货视角：各品类退货率")
    ret = df.groupby("Category CN").agg(returned=("Returned", "sum"), rows=("Returned", "count")).reset_index()
    ret["rate"] = ret["returned"] / ret["rows"] * 100
    fig = px.bar(ret, x="Category CN", y="rate", color="Category CN", color_discrete_sequence=[INDIGO, PINK, ORANGE],
                 text_auto=".1f", labels={"rate": "退货行占比 (%)"})
    fig.update_layout(height=300, margin=dict(t=10, l=10, r=10, b=10), showlegend=False)
    show_chart(fig)


# ================= 页面：指标异动归因 =================
elif page == "🧭 指标异动归因":
    st.title("🧭 指标异动归因")
    st.caption("维度贡献度分解：指标为什么变了，主要是谁干的（加法分解，各组贡献严格可加）")

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        metric = st.selectbox("归因指标", ["Sales", "Profit"],
                              format_func=lambda x: {"Sales": "销售额", "Profit": "利润"}[x])
    with c2:
        dim = st.selectbox("归因维度", ["Sub-Category", "Region CN", "Category CN", "Segment CN", "Payment CN", "Ship Mode CN"],
                           format_func=lambda x: {"Sub-Category": "子品类", "Region CN": "地区", "Category CN": "品类",
                                                  "Segment CN": "客户类型", "Payment CN": "支付方式", "Ship Mode CN": "配送方式"}[x])
    with c3:
        if len(YEARS) >= 2:
            base_year, cmp_year = st.select_slider("基期 → 对比期", options=YEARS, value=(YEARS[0], YEARS[-1]))
        else:
            base_year = cmp_year = YEARS[0]

    base_mask = df["Year"] == base_year
    cmp_mask = df["Year"] == cmp_year

    res = compute_attribution(
        df, dimension=dim, dimension_cn={"Sub-Category": "子品类", "Region CN": "地区", "Category CN": "品类",
                                         "Segment CN": "客户类型", "Payment CN": "支付方式", "Ship Mode CN": "配送方式"}[dim],
        metric=metric, metric_cn={"Sales": "销售额", "Profit": "利润"}[metric],
        base_mask=base_mask, cmp_mask=cmp_mask,
        base_label=f"{base_year}年", cmp_label=f"{cmp_year}年",
    )

    st.subheader(f"{res.metric_cn}变动瀑布图（{res.base_label} → {res.cmp_label}，按{res.dimension_cn}）")
    t = res.table.copy()
    t["贡献符号"] = ["+" if v >= 0 else "-" for v in t["变动量"]]
    fig = go.Figure(
        go.Waterfall(
            x=t["dim"].tolist(),
            measure=["absolute"] * len(t),
            y=t["变动量"].tolist(),
            text=[f"{v:+,.0f}" for v in t["变动量"]],
            textposition="outside",
            connector={"line": {"color": "#a8a29e", "width": 1}},
            increasing={"marker": {"color": TEAL}},
            decreasing={"marker": {"color": PINK}},
        )
    )
    fig.update_layout(height=420, margin=dict(t=10, l=10, r=10, b=30), yaxis_title="对总变动的贡献 ($)")
    show_chart(fig)

    st.subheader("归因明细表")
    show = t[["dim", "基期", "对比期", "变动量", "贡献度", "累计贡献"]].copy()
    show["贡献度"] = (show["贡献度"] * 100).round(1).astype(str) + "%"
    show["累计贡献"] = (show["累计贡献"] * 100).round(1).astype(str) + "%"
    for c in ["基期", "对比期", "变动量"]:
        show[c] = show[c].map(lambda v: f"${v:,.0f}")
    show.columns = [res.dimension_cn] + list(show.columns[1:])
    show_table(show)
    st.caption(f"贡献度 = 该组变动量 ÷ 总变动量（总变动 {fmt_money(res.delta_total)}）。同向为正、反向为负，合计恒等于 100%。")

    st.subheader("自动结论文案")
    with st.container(border=True):
        for s in generate_insight(res, fmt_money):
            st.markdown(f"- {s}")
    st.caption("结论由规则模板基于上表数字生成，无人工修饰——可直接复制进汇报材料。")


# ================= 页面：情景模拟 =================
elif page == "🎬 情景模拟 What-if":
    st.title("🎬 情景模拟 What-if")
    st.caption("基于归因结果的干预模拟：假设拖累项恢复到基期水平，指标能回到哪里")

    if len(YEARS) < 2:
        st.warning("需要至少两个年度的数据才能做对比模拟。")
        st.stop()

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        metric = st.selectbox("模拟指标", ["Sales", "Profit"],
                              format_func=lambda x: {"Sales": "销售额", "Profit": "利润"}[x], key="wf_metric")
    with c2:
        base_year, cmp_year = st.select_slider("基期 → 对比期", options=YEARS, value=(YEARS[0], YEARS[-1]), key="wf_years")
    with c3:
        k = st.slider("恢复前 N 个拖累项", 1, 5, 1, help="假设贡献度最差的前 N 个子品类回到基期水平")

    res = compute_attribution(
        df, dimension="Sub-Category", dimension_cn="子品类",
        metric=metric, metric_cn={"Sales": "销售额", "Profit": "利润"}[metric],
        base_mask=df["Year"] == base_year, cmp_mask=df["Year"] == cmp_year,
        base_label=f"{base_year}年", cmp_label=f"{cmp_year}年",
    )
    sc = recovery_scenario(res, fmt_money, k=k)

    st.subheader("情景对比")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("当前总变动", fmt_money(sc["old_delta"]))
    with c2:
        st.metric("恢复的拖累量", fmt_money(-sc["recovered"]),
                  help=f"假设 {sc['names']} 恢复到 {res.base_label} 水平")
    with c3:
        st.metric("情景后的总变动", fmt_money(sc["new_delta"]))

    fig = go.Figure()
    fig.add_bar(x=["基期总量", "对比期（实际）", "对比期（情景）"],
                y=[res.base_total, sc["old_total"], sc["new_total"]],
                marker_color=[AMBER, PINK, TEAL], width=0.5,
                text=[fmt_money(res.base_total), fmt_money(sc["old_total"]), fmt_money(sc["new_total"])],
                textposition="outside")
    fig.update_layout(height=380, margin=dict(t=30, l=10, r=10, b=10), yaxis_title="金额 ($)")
    show_chart(fig)

    with st.container(border=True):
        st.markdown(
            f"- **情景定义**：{res.base_label}→{res.cmp_label} 的{res.metric_cn}变动中，"
            f"子品类「{sc['names']}」为拖累项（合计 {fmt_money(sc['recovered'])}）。"
        )
        st.markdown(f"- **模拟规则**：假设这 {k} 个子品类恢复到基期水平，其余组保持不变——不引入任何外部参数。")
        st.markdown(
            f"- **结果解读**：{res.metric_cn}将从 {fmt_money(sc['old_total'])} 修正到 "
            f"{fmt_money(sc['new_total'])}，即挽回 {abs(sc['recovered']/sc['old_delta'])*100 if sc['old_delta'] else 0:.0f}% 的变动缺口（保守估计，实际取决于治理动作）。"
        )
        st.caption("方法论提示：这是基于历史区间加法分解的静态情景，属于『归因→干预→预估』闭环的下界估计，不是对未来的预测。")


# ---------------- 页脚 ----------------
st.divider()
st.caption(
    "零售经营洞察台 · 数据：Tableau Sample - Superstore（公开示例数据，MIT 仓库托管）· "
    "方法：加法贡献度分解（各组贡献严格可加，结论由数据生成）"
)
