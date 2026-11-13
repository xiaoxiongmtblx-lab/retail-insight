# 零售经营洞察台 Retail Insight

基于 **Streamlit** 的零售经营分析应用，完整演示数据分析 → 可视化 → 指标异动归因 → 情景模拟的分析链路。

## 数据来源（公开，可自由迁移）

| 项 | 说明 |
|---|---|
| 数据集 | Tableau 公开示例数据集 **Sample - Superstore**（2019-2020 变体） |
| 内容 | 5,901 行美国零售订单明细：地区 / 品类 / 子品类 / 客户类型 / 配送方式 / 支付方式 / 销售额 / 利润 / 退货标记 |
| 托管仓库 | github.com/abrarghoury/Superstore-Sale-Dashboard-Power-BI（MIT License） |
| 位置 | `data/superstore.csv`（随项目打包，**离线可运行**，无需联网） |

## 运行

```bash
# 1. 安装依赖（建议 Python 3.9+）
pip install -r requirements.txt

# 2. 启动
streamlit run app.py
```

浏览器自动打开 `http://localhost:8501`。

## 五大功能模块

| 模块 | 内容 | 方法要点 |
|---|---|---|
| 📌 经营总览 | KPI 指标卡、月度趋势、品类×年度、地区利润 + 自动洞察 | 帕累托思维、亏损结构定位 |
| 🔍 交互探索 | 六维度下钻、Top N 排名、月度趋势、散点关系 | 维度切片、相关性观察 |
| 📊 深度可视化 | 热力图、帕累托图（80/20）、箱线图、堆叠图、退货率 | 结构分析四件套 |
| 🧭 指标异动归因 | 2019→2020 任意维度贡献度分解 + 瀑布图 + 自动结论文案 | **加法贡献度分解**（见下） |
| 🎬 情景模拟 | 拖累项恢复到基期水平的 What-if 估计 | 归因→干预→预估闭环 |

## 归因方法论（本项目核心）

采用**维度贡献度分解**（加法分解 / Contribution Analysis）：

```
delta_i = 指标_i(对比期) - 指标_i(基期)     # 各组变动量
Delta   = Σ delta_i = 指标(对比期) - 指标(基期)   # 严格可加，无残差
贡献度_i = delta_i / Delta                    # 同向为正、反向为负
```

- 适用于销售额、利润、订单量等**可加指标**的涨跌归因
- 结论由规则模板基于计算数字生成（`src/attribution.py` 的 `generate_insight`），**无人工修饰、无编造**
- 情景模拟为基于历史区间的静态估计（保守下界），**不是对未来预测**

## 目录结构

```
retail-insight/
├── app.py               # Streamlit 主应用（五模块导航）
├── requirements.txt
├── data/superstore.csv  # 公开数据集（离线打包）
└── src/
    ├── loader.py        # 数据加载与清洗（列名规范化、中文映射、派生字段）
    └── attribution.py   # 归因引擎（贡献度分解 + 自动结论 + 情景模拟）
```

## 推上 GitHub

```bash
git init
git add .
git commit -m "feat: 零售经营洞察台 v1.0"
git branch -M main
git remote add origin https://github.com/<你的用户名>/retail-insight.git
git push -u origin main
```

> 部署在线版（可选）：Streamlit Cloud 免费托管 Public 仓库，或用 Docker 自部署。

## License

MIT（数据集遵循其托管仓库许可）
