# -*- coding: utf-8 -*-
"""数据加载与清洗模块。

数据源：Tableau 公开示例数据集 Sample - Superstore 变体（2019-2020 美国零售订单明细，
5901 行，含地区/品类/客户类型/配送方式/支付方式/退货标记等维度）。
来源仓库：github.com/abrarghoury/Superstore-Sale-Dashboard-Power-BI（MIT License）。
列名做了规范化处理，兼容不同版本的数据文件。
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "superstore.csv"

SEGMENT_CN = {"Consumer": "个人消费者", "Corporate": "企业客户", "Home Office": "居家办公"}
CATEGORY_CN = {"Furniture": "家具", "Office Supplies": "办公用品", "Technology": "科技产品"}
REGION_CN = {"West": "西部", "East": "东部", "Central": "中部", "South": "南部"}
SHIP_CN = {
    "Standard Class": "标准配送",
    "Second Class": "二级配送",
    "First Class": "一级配送",
    "Same Day": "当日达",
}
PAY_CN = {"COD": "货到付款", "Online": "在线支付", "Cards": "刷卡支付"}


@st.cache_data(ttl=600, show_spinner="正在加载数据…")
def load_data() -> pd.DataFrame:
    """读取并清洗 Superstore 数据集。"""
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", engine="python", on_bad_lines="skip")

    # ---- 列名规范化（兼容多种列名写法）----
    rename = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl.startswith("row id"):
            rename[c] = "Row ID"
        elif cl == "order id":
            rename[c] = "Order ID"
        elif cl == "order date":
            rename[c] = "Order Date"
        elif cl == "ship date":
            rename[c] = "Ship Date"
        elif cl == "ship mode":
            rename[c] = "Ship Mode"
        elif cl == "customer id":
            rename[c] = "Customer ID"
        elif cl == "customer name":
            rename[c] = "Customer Name"
        elif cl == "product id":
            rename[c] = "Product ID"
        elif cl == "product name":
            rename[c] = "Product Name"
        elif cl == "sub-category":
            rename[c] = "Sub-Category"
        elif cl == "payment mode":
            rename[c] = "Payment Mode"
    df = df.rename(columns=rename)

    # ---- 日期解析（该数据为 dd-mm-yyyy 格式）----
    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True, errors="coerce")
    if "Ship Date" in df.columns:
        df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True, errors="coerce")

    # ---- 关键字段清洗 ----
    for col in ["Sales", "Profit", "Quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Order Date", "Sales", "Profit", "Order ID"])

    # ---- 派生字段 ----
    df["Year"] = df["Order Date"].dt.year
    df["Month"] = df["Order Date"].dt.month
    df["YearMonth"] = df["Order Date"].dt.to_period("M").astype(str)
    df["Month CN"] = df["Month"].map(lambda m: f"{m}月")
    df["Unit Price"] = df["Sales"] / df["Quantity"].replace(0, pd.NA)
    df["Is Loss"] = df["Profit"] < 0
    df["Profit Margin"] = df["Profit"] / df["Sales"]

    # ---- 中文维度列（保留原英文值，新增中文列）----
    df["Segment CN"] = df["Segment"].map(SEGMENT_CN).fillna(df["Segment"])
    df["Category CN"] = df["Category"].map(CATEGORY_CN).fillna(df["Category"])
    df["Region CN"] = df["Region"].map(REGION_CN).fillna(df["Region"])
    df["Ship Mode CN"] = df["Ship Mode"].map(SHIP_CN).fillna(df["Ship Mode"])
    if "Payment Mode" in df.columns:
        df["Payment CN"] = df["Payment Mode"].map(PAY_CN).fillna(df["Payment Mode"])
    else:
        df["Payment CN"] = "未知"

    # ---- 退货标记（Returns=1 表示退货）----
    if "Returns" in df.columns:
        df["Returned"] = pd.to_numeric(df["Returns"], errors="coerce").fillna(0).astype(int).astype(bool)
    else:
        df["Returned"] = False

    return df


def apply_filters(df: pd.DataFrame, date_range, regions, categories) -> pd.DataFrame:
    """应用侧边栏筛选条件。"""
    out = df
    if date_range is not None and len(date_range) == 2:
        out = out[(out["Order Date"] >= pd.Timestamp(date_range[0])) & (out["Order Date"] <= pd.Timestamp(date_range[1]))]
    if regions:
        out = out[out["Region CN"].isin(regions)]
    if categories:
        out = out[out["Category CN"].isin(categories)]
    return out


def fmt_money(v: float) -> str:
    """金额格式化。"""
    if abs(v) >= 1_000_000:
        return f"${v/1_000_000:,.2f}M"
    if abs(v) >= 1_000:
        return f"${v/1_000:,.1f}K"
    return f"${v:,.0f}"
