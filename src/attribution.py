# -*- coding: utf-8 -*-
"""指标异动归因引擎。

方法：维度贡献度分解（加法分解，业内称「贡献度拆解 / Contribution Analysis」）。

    设指标 M 在基期(base)与对比期(cmp)的总量分别为 M_base、M_cmp，
    按维度 D 分组后，各组贡献量 delta_i = M_cmp,i - M_base,i，
    则总变动 Delta = Σ delta_i = M_cmp - M_base（严格可加，无残差项），
    组 i 的贡献度 = delta_i / Delta。

适用于销售额、利润、订单量等可加指标的涨跌归因：
回答「指标为什么变了，主要是谁干的、往哪个方向干的」。
这是业务异动排查（指标涨跌归因）的标准方法之一，
与乘法分解（量价拆解）、对数加权分解（LMDI）同属常用工具箱。
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class AttributionResult:
    dimension: str          # 归因维度列名
    dimension_cn: str       # 归因维度中文名
    metric: str             # 指标列名
    metric_cn: str          # 指标中文名
    base_label: str         # 基期标签
    cmp_label: str          # 对比期标签
    base_total: float       # 基期总量
    cmp_total: float        # 对比期总量
    delta_total: float      # 总变动
    table: pd.DataFrame     # 各组归因明细表


def compute_attribution(
    df: pd.DataFrame,
    dimension: str,
    dimension_cn: str,
    metric: str,
    metric_cn: str,
    base_mask: pd.Series,
    cmp_mask: pd.Series,
    base_label: str,
    cmp_label: str,
    min_share: float = 0.001,
) -> AttributionResult:
    """计算按 dimension 分组的指标变动贡献度。

    base_mask / cmp_mask: 布尔掩码，分别选中基期与对比期数据。
    min_share: 基期+对比期总量占比过低的小组合并进「其他」。
    """
    base = df.loc[base_mask].groupby(dimension)[metric].sum()
    cmp_ = df.loc[cmp_mask].groupby(dimension)[metric].sum()

    table = pd.DataFrame({"base": base, "cmp": cmp_}).fillna(0.0)

    # 微小组合归并
    scale = table["base"].abs() + table["cmp"].abs()
    if scale.sum() > 0 and len(table) > 6:
        keep = scale / scale.sum() > min_share
        if (~keep).any() and keep.sum() >= 3:
            other = table.loc[~keep].sum()
            table = table.loc[keep].copy()
            table.loc["其他(合并)"] = other

    table["delta"] = table["cmp"] - table["base"]
    delta_total = table["delta"].sum()

    if abs(delta_total) > 1e-9:
        table["contribution"] = table["delta"] / delta_total  # 有符号贡献度
    else:
        table["contribution"] = 0.0
    table["abs_contribution"] = table["contribution"].abs()
    table = table.sort_values("abs_contribution", ascending=False)
    table["cumulative"] = table["abs_contribution"].cumsum()

    out = table.reset_index().rename(
        columns={
            "index": "dim",
            table.index.name or "index": "dim",
            "base": "基期",
            "cmp": "对比期",
            "delta": "变动量",
            "contribution": "贡献度",
            "cumulative": "累计贡献",
        }
    )
    if "dim" not in out.columns:  # groupby 的索引列名即维度名
        out = table.reset_index().rename(columns={dimension: "dim", "base": "基期", "cmp": "对比期", "delta": "变动量", "contribution": "贡献度", "cumulative": "累计贡献"})

    return AttributionResult(
        dimension=dimension,
        dimension_cn=dimension_cn,
        metric=metric,
        metric_cn=metric_cn,
        base_label=base_label,
        cmp_label=cmp_label,
        base_total=float(table["base"].sum()),
        cmp_total=float(table["cmp"].sum()),
        delta_total=float(delta_total),
        table=out,
    )


def generate_insight(res: AttributionResult, fmt) -> list[str]:
    """根据归因结果自动生成结论文案（规则模板法，结论只引用计算数字）。"""
    t = res.table
    total_pct = (res.delta_total / res.base_total) if res.base_total else 0
    direction = "增长" if res.delta_total > 0 else ("下滑" if res.delta_total < 0 else "持平")
    insights = []

    insights.append(
        f"**总体结论**：{res.metric_cn}从 {res.base_label} 的 {fmt(res.base_total)} 变为 {res.cmp_label} 的 {fmt(res.cmp_total)}，"
        f"变动 {fmt(res.delta_total)}（{direction} {abs(total_pct)*100:.1f}%）。"
    )

    if res.delta_total == 0:
        return insights

    # 与总变动同向的贡献者 / 反向的拖累者
    same_dir = t[t["变动量"] * res.delta_total > 0]
    oppo_dir = t[t["变动量"] * res.delta_total < 0]

    if len(same_dir):
        top = same_dir.iloc[0]
        insights.append(
            f"**最大正向驱动**：{res.dimension_cn}「{top['dim']}」变动 {fmt(top['变动量'])}，"
            f"占总变动的 {top['贡献度']*100:.1f}%——是本次{direction}的头号推手。"
        )
    if len(oppo_dir):
        worst = oppo_dir.sort_values("变动量").iloc[0]
        insights.append(
            f"**主要拖累项**：「{worst['dim']}」逆势变动 {fmt(worst['变动量'])}，"
            f"抵消了部分{direction}；若剔除它，总变动将达 {fmt(res.delta_total - worst['变动量'])}。"
        )
    if len(same_dir):
        k = min(3, len(same_dir))
        cum = same_dir.head(k)["贡献度"].abs().sum()
        insights.append(
            f"**集中度**：前 {k} 个正向{res.dimension_cn}合计贡献了相当于总变动 {cum*100:.0f}% 的增量"
            f"（超过 100% 的部分被拖累项抵消），归因高度集中——治理资源应优先投向「{same_dir.iloc[0]['dim']}」等头部。"
        )
    # 结构提示：增长还是衰退性变动
    if len(oppo_dir):
        oppo_sum = oppo_dir["变动量"].sum()
        insights.append(
            f"**结构提示**：有 {len(oppo_dir)} 个{res.dimension_cn}与大盘反向变动，合计 {fmt(oppo_sum)}，"
            f"提示这不是全面{direction}，而是结构分化——排查时别只看大盘。"
        )
    return insights


def recovery_scenario(res: AttributionResult, fmt, k: int = 1) -> dict:
    """情景模拟：假设前 k 个拖累组恢复到基期水平，指标会变成多少。

    这是「归因 -> 干预 -> 预估」的完整闭环演示：
    情景严格基于历史数据区间，不含任何外部假设，属于保守下界估计。
    """
    t = res.table
    oppo = t[t["变动量"] * res.delta_total < 0] if res.delta_total != 0 else t.iloc[0:0]
    oppo = oppo.sort_values("变动量").head(k)
    recovered = float(oppo["变动量"].sum()) if len(oppo) else 0.0
    new_delta = res.delta_total - recovered
    new_total = res.cmp_total - recovered
    names = "、".join(oppo["dim"].tolist()) if len(oppo) else "无"
    return {
        "names": names,
        "recovered": recovered,
        "new_delta": new_delta,
        "new_total": new_total,
        "old_total": res.cmp_total,
        "old_delta": res.delta_total,
    }
