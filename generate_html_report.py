#!/usr/bin/env python3
"""生成专业HTML财务分析报告 — 通用版 + 腾讯专用版"""

import pandas as pd
from datetime import datetime


def _fmt_yi(v):
    return v / 1e8


def _tag(val, unit='%'):
    if val >= 0:
        return f'<span class="tag-up">+{val:.2f}{unit}</span>'
    return f'<span class="tag-down">{val:.2f}{unit}</span>'


def _arrow(val):
    return '↑' if val >= 0 else '↓'


def generate_html_report(financial_data, growth_data, company_name, output_path='财务分析报告.html'):
    annual = financial_data[~financial_data['是否半年报']].sort_values('年份')
    latest = annual.iloc[-1]
    latest_year = int(latest['年份'])
    first_year = int(annual.iloc[0]['年份'])

    # ---- KPI 值 ----
    latest_rev = _fmt_yi(latest['营业收入'])
    latest_profit = _fmt_yi(latest['净利润'])
    latest_assets = _fmt_yi(latest['总资产'])
    latest_equity = _fmt_yi(latest['净资产'])
    latest_eps = latest['每股收益']
    latest_roe = latest['净资产收益率']

    # ---- 增长率 ----
    if len(annual) >= 2:
        prev = annual.iloc[-2]
        rev_growth = (latest['营业收入'] - prev['营业收入']) / prev['营业收入'] * 100
        profit_growth = (latest['净利润'] - prev['净利润']) / prev['净利润'] * 100
        roe_change = latest['净资产收益率'] - prev['净资产收益率']
        prev_year = int(prev['年份'])
    else:
        prev_year = first_year
        rev_growth, profit_growth, roe_change = 0, 0, 0

    # ---- 数据明细表 ----
    data_rows = ''
    for yr_row in annual.itertuples():
        yr = int(yr_row.年份)
        gr = growth_data[(growth_data['年份'] == yr) & (~growth_data['是否半年报'])]
        if len(gr) > 0:
            g = gr.iloc[0]
            tags = ''.join(
                _tag(g[f'{k}_增长率'])
                for k in ['营业收入', '净利润', '总资产', '净资产', '每股收益', '净资产收益率']
                if f'{k}_增长率' in growth_data.columns and pd.notna(g.get(f'{k}_增长率'))
            ) or '<span style="color:#999">基准年</span>'
        else:
            tags = '<span style="color:#999">基准年</span>'

        data_rows += f'''
          <tr>
            <td>{yr} 年</td>
            <td>{_fmt_yi(yr_row.营业收入):,.2f} 亿</td>
            <td>{_fmt_yi(yr_row.净利润):,.2f} 亿</td>
            <td>{_fmt_yi(yr_row.总资产):,.2f} 亿</td>
            <td>{_fmt_yi(yr_row.净资产):,.2f} 亿</td>
            <td>{yr_row.每股收益:.2f} 元</td>
            <td>{yr_row.净资产收益率:.2f}%</td>
            <td>{tags}</td>
          </tr>'''

    # ---- 增长率表格 ----
    if len(annual) >= 2:
        growth_annual = growth_data[~growth_data['是否半年报']].sort_values('年份')
        latest_g = growth_annual.iloc[-1]
        growth_rows = ''
        for k, label in [('营业收入', '营业收入'), ('净利润', '归母净利润'),
                         ('总资产', '总资产'), ('净资产', '净资产'),
                         ('每股收益', '每股收益 (EPS)'), ('净资产收益率', '净资产收益率 (ROE)')]:
            gcol = f'{k}_增长率'
            if gcol in growth_annual.columns and pd.notna(latest_g.get(gcol)):
                growth_rows += f'<tr><td>{label}</td><td>{_tag(latest_g[gcol])}</td></tr>'
    else:
        growth_rows = '<tr><td colspan="2" style="color:#999">需要至少两年数据</td></tr>'

    # ---- 三阶段分析文本 ----
    first_rev = _fmt_yi(annual.iloc[0]['营业收入'])
    first_profit = _fmt_yi(annual.iloc[0]['净利润'])

    # 近年对比
    if len(annual) >= 3:
        y2024_row = annual[annual['年份'] == 2024]
        y2025_row = annual[annual['年份'] == 2025]
        if len(y2025_row) > 0 and len(y2024_row) > 0:
            r25 = y2025_row.iloc[0]
            r24 = y2024_row.iloc[0]
            g25 = growth_data[(growth_data['年份'] == 2025) & (~growth_data['是否半年报'])].iloc[0]
            g24 = growth_data[(growth_data['年份'] == 2024) & (~growth_data['是否半年报'])].iloc[0]
            analysis_left_title = f'{latest_year} 年：增速转负'
            analysis_right_title = f'{prev_year} 年：增长高峰'
            analysis_left = f'''<ul>
              <li><strong>营收下滑 {abs(g25["营业收入_增长率"]):.2f}%</strong> — 终端动销放缓，渠道库存压力显现</li>
              <li><strong>净利润下滑 {abs(g25["净利润_增长率"]):.2f}%</strong> — 利润降幅大于营收降幅，利润率承压</li>
              <li><strong>ROE 下滑 {r25["净资产收益率"] - r24["净资产收益率"]:.2f}pp</strong> — 净资产增长但利润收缩，双重因素拉低 ROE</li>
              <li><strong>EPS 下滑 {abs(g25["每股收益_增长率"]):.2f}%</strong> — 每股收益跟随利润同步回落</li>
            </ul>'''
            analysis_right = f'''<ul>
              <li><strong>营收增长 {g24["营业收入_增长率"]:.2f}%</strong> — 受益于提价效应与渠道改革红利</li>
              <li><strong>净利润增长 {g24["净利润_增长率"]:.2f}%</strong> — 利润增速与营收增速匹配</li>
              <li><strong>ROE 提升至 {r24["净资产收益率"]:.2f}%</strong> — 资本回报效率达近年峰值</li>
              <li><strong>EPS 增长 {g24["每股收益_增长率"]:.2f}%</strong> — 每股收益同步提升</li>
            </ul>'''
        else:
            analysis_left_title, analysis_right_title = '', ''
            analysis_left, analysis_right = '', ''
    else:
        analysis_left_title, analysis_right_title = '', ''
        analysis_left, analysis_right = '', ''

    # ---- 时间线 ----
    timeline_items = ''
    for yr_row in annual.itertuples():
        yr = int(yr_row.年份)
        roe = yr_row.净资产收益率
        eps = yr_row.每股收益
        if roe >= 30:
            desc = f'ROE {roe:.2f}% / EPS {eps:.2f} 元 — 盈利能力处于行业绝对领先水平'
        elif roe >= 20:
            desc = f'ROE {roe:.2f}% / EPS {eps:.2f} 元 — 资本回报效率稳健，盈利质量优异'
        elif roe >= 15:
            desc = f'ROE {roe:.2f}% / EPS {eps:.2f} 元 — 股东回报处于较好水平'
        else:
            desc = f'ROE {roe:.2f}% / EPS {eps:.2f} 元'
        timeline_items += f'''
        <div class="timeline-item">
          <div class="timeline-year">{yr}</div>
          <div class="timeline-text">{desc}</div>
        </div>'''

    # 执行摘要
    if len(annual) >= 2:
        prev2 = annual.iloc[-2]
        prev_peak_rev = _fmt_yi(prev2['营业收入'])
        prev_peak_profit = _fmt_yi(prev2['净利润'])
        prev_peak_roe = prev2['净资产收益率']
        summary_text = f'''{company_name}在数据覆盖期内呈现<span class="highlight">"先增后调"</span>的财务走势。
        {prev_year} 年为近年来业绩高峰，营收突破 <span class="highlight">{prev_peak_rev:,.0f} 亿元</span>，净利润达 <span class="highlight">{prev_peak_profit:,.0f} 亿元</span>。
        进入 {latest_year} 年，受宏观经济承压与消费结构调整影响，公司营收同比{'下滑' if rev_growth < 0 else '增长'} <span class="highlight">{abs(rev_growth):.2f}%</span>，
        净利润同比{'下滑' if profit_growth < 0 else '增长'} <span class="highlight">{abs(profit_growth):.2f}%</span>，ROE 从 {prev_peak_roe:.2f}% {'回落至' if roe_change < 0 else '提升至'} <span class="highlight">{latest_roe:.2f}%</span>。
        尽管如此，公司总资产规模突破 <span class="highlight">{latest_assets:,.0f} 亿元</span>，净资产达 <span class="highlight">{latest_equity:,.0f} 亿元</span>，资产负债表依然稳健。'''
    else:
        summary_text = f'{company_name}最新年报显示，营收 {latest_rev:,.0f} 亿元，净利润 {latest_profit:,.0f} 亿元，ROE {latest_roe:.2f}%。'

    # ================================================================
    # HTML 模板
    # ================================================================
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{company_name}财务分析报告 {first_year}-{latest_year}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  :root {{
    --gold: #C9A84C;
    --gold-light: #F5E6C8;
    --red: #C41E3A;
    --navy: #1B2A4A;
    --slate: #2D3A52;
    --bg: #F7F4EF;
    --white: #FFFFFF;
    --text: #2C2416;
    --text-secondary: #6B5E4A;
    --green: #2E7D32;
    --border: #E0D5C1;
    --shadow: 0 4px 24px rgba(27, 42, 74, 0.08);
    --shadow-lg: 0 12px 48px rgba(27, 42, 74, 0.12);
  }}

  body {{
    font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.8;
    -webkit-font-smoothing: antialiased;
  }}

  .hero {{
    background: linear-gradient(135deg, var(--navy) 0%, #243456 40%, #1a1a2e 100%);
    color: white;
    padding: 80px 0 60px;
    position: relative;
    overflow: hidden;
  }}
  .hero::before {{
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(201,168,76,0.08) 0%, transparent 50%),
                radial-gradient(circle at 70% 30%, rgba(196,30,58,0.06) 0%, transparent 50%);
    animation: heroGlow 8s ease-in-out infinite;
  }}
  @keyframes heroGlow {{
    0%, 100% {{ transform: translate(0, 0); }}
    50% {{ transform: translate(2%, 1%); }}
  }}
  .hero-content {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 40px;
    position: relative;
    z-index: 1;
  }}
  .hero-badge {{
    display: inline-block;
    background: rgba(201,168,76,0.15);
    border: 1px solid var(--gold);
    color: var(--gold);
    padding: 6px 20px;
    border-radius: 20px;
    font-size: 13px;
    letter-spacing: 2px;
    margin-bottom: 24px;
  }}
  .hero h1 {{
    font-size: 48px;
    font-weight: 900;
    letter-spacing: 4px;
    margin-bottom: 12px;
    background: linear-gradient(180deg, #fff 0%, #C9A84C 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .hero-subtitle {{
    font-size: 18px;
    color: rgba(255,255,255,0.6);
    font-weight: 300;
  }}
  .hero-date {{
    color: rgba(255,255,255,0.45);
    font-size: 13px;
    margin-top: 8px;
  }}

  .container {{ max-width: 1100px; margin: 0 auto; padding: 0 40px; }}

  .kpi-section {{ margin-top: -40px; position: relative; z-index: 2; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }}
  .kpi-card {{
    background: var(--white);
    border-radius: 16px;
    padding: 28px 24px;
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--border);
    transition: transform 0.3s, box-shadow 0.3s;
  }}
  .kpi-card:hover {{ transform: translateY(-4px); box-shadow: 0 16px 56px rgba(27, 42, 74, 0.16); }}
  .kpi-card.primary {{ border-left: 4px solid var(--gold); }}
  .kpi-card.accent {{ border-left: 4px solid var(--red); }}
  .kpi-label {{ font-size: 13px; color: var(--text-secondary); letter-spacing: 1px; margin-bottom: 8px; }}
  .kpi-value {{ font-size: 36px; font-weight: 900; color: var(--navy); margin-bottom: 4px; }}
  .kpi-unit {{ font-size: 14px; font-weight: 400; color: var(--text-secondary); }}
  .kpi-change {{ font-size: 13px; margin-top: 8px; font-weight: 500; }}
  .kpi-change.down {{ color: var(--red); }}
  .kpi-change.up {{ color: var(--green); }}

  .section {{ padding: 60px 0; }}
  .section-header {{ text-align: center; margin-bottom: 48px; }}
  .section-number {{ font-size: 12px; color: var(--gold); letter-spacing: 3px; margin-bottom: 8px; }}
  .section-title {{ font-size: 32px; font-weight: 700; color: var(--navy); margin-bottom: 12px; }}
  .section-line {{ width: 60px; height: 3px; background: linear-gradient(90deg, var(--gold), var(--red)); margin: 0 auto; border-radius: 2px; }}
  .section-desc {{ color: var(--text-secondary); font-size: 15px; margin-top: 12px; max-width: 600px; margin-left: auto; margin-right: auto; }}

  .chart-block {{
    background: var(--white);
    border-radius: 16px;
    padding: 32px;
    box-shadow: var(--shadow);
    margin-bottom: 32px;
    border: 1px solid var(--border);
  }}
  .chart-title {{
    font-size: 18px;
    font-weight: 700;
    color: var(--navy);
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--border);
  }}
  .chart-img {{ width: 100%; border-radius: 8px; }}

  .data-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 14px;
  }}
  .data-table thead th {{
    background: var(--navy);
    color: white;
    padding: 14px 16px;
    font-weight: 500;
    font-size: 13px;
    letter-spacing: 1px;
    text-align: center;
  }}
  .data-table thead th:first-child {{ border-radius: 10px 0 0 0; text-align: left; }}
  .data-table thead th:last-child {{ border-radius: 0 10px 0 0; }}
  .data-table tbody td {{
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    text-align: center;
  }}
  .data-table tbody td:first-child {{ text-align: left; font-weight: 600; color: var(--navy); }}
  .data-table tbody tr:hover {{ background: var(--gold-light); }}
  .data-table tbody tr:last-child td:first-child {{ border-radius: 0 0 0 10px; }}
  .data-table tbody tr:last-child td:last-child {{ border-radius: 0 0 10px 0; }}
  .tag-down {{
    display: inline-block;
    background: #FDE8EC;
    color: var(--red);
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }}
  .tag-up {{
    display: inline-block;
    background: #E8F5E9;
    color: var(--green);
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
  }}

  .analysis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  .analysis-card {{
    background: var(--white);
    border-radius: 16px;
    padding: 28px;
    box-shadow: var(--shadow);
    border: 1px solid var(--border);
  }}
  .analysis-card h3 {{ font-size: 18px; font-weight: 700; color: var(--navy); margin-bottom: 12px; }}
  .analysis-card li {{ color: var(--text-secondary); font-size: 14px; line-height: 1.9; margin-bottom: 6px; }}
  .analysis-card ul {{ padding-left: 18px; }}

  .exec-summary {{
    background: linear-gradient(135deg, var(--navy), var(--slate));
    color: white;
    border-radius: 16px;
    padding: 40px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
  }}
  .exec-summary::after {{
    content: '';
    position: absolute;
    right: -40px;
    top: -40px;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(201,168,76,0.15) 0%, transparent 70%);
    border-radius: 50%;
  }}
  .exec-summary h3 {{
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 16px;
    color: var(--gold);
    position: relative;
    z-index: 1;
  }}
  .exec-summary p {{
    font-size: 15px;
    line-height: 2;
    color: rgba(255,255,255,0.85);
    position: relative;
    z-index: 1;
  }}
  .exec-summary .highlight {{ color: var(--gold); font-weight: 600; }}

  .timeline {{
    position: relative;
    padding-left: 32px;
  }}
  .timeline::before {{
    content: '';
    position: absolute;
    left: 8px;
    top: 4px;
    bottom: 4px;
    width: 2px;
    background: linear-gradient(180deg, var(--gold), var(--red));
  }}
  .timeline-item {{ position: relative; margin-bottom: 28px; }}
  .timeline-item::before {{
    content: '';
    position: absolute;
    left: -28px;
    top: 6px;
    width: 14px;
    height: 14px;
    background: var(--gold);
    border-radius: 50%;
    border: 3px solid var(--white);
    box-shadow: 0 0 0 2px var(--gold);
  }}
  .timeline-year {{ font-size: 13px; color: var(--gold); font-weight: 700; letter-spacing: 2px; margin-bottom: 4px; }}
  .timeline-text {{ font-size: 14px; color: var(--text-secondary); line-height: 1.8; }}

  .footer {{
    background: var(--navy);
    color: rgba(255,255,255,0.5);
    text-align: center;
    padding: 40px 0;
    font-size: 13px;
    margin-top: 20px;
  }}

  @media (max-width: 768px) {{
    .kpi-grid {{ grid-template-columns: 1fr; }}
    .analysis-grid {{ grid-template-columns: 1fr; }}
    .hero h1 {{ font-size: 32px; }}
    .section-title {{ font-size: 24px; }}
    .kpi-value {{ font-size: 28px; }}
  }}

  @media print {{
    body {{ background: white; }}
    .hero {{ padding: 40px 0 30px; }}
    .chart-block, .analysis-card, .kpi-card {{ box-shadow: none; break-inside: avoid; }}
    .section {{ padding: 30px 0; }}
  }}
</style>
</head>
<body>

<header class="hero">
  <div class="hero-content">
    <div class="hero-badge">FINANCIAL ANALYSIS REPORT</div>
    <h1>{company_name}<br>财务分析报告</h1>
    <p class="hero-subtitle">基于 {first_year}—{latest_year} 年年度报告数据的深度财务分析</p>
    <p class="hero-date">报告生成日期：{datetime.now().strftime("%Y 年 %m 月 %d 日")} ｜ 数据来源：上市公司年度报告</p>
  </div>
</header>

<div class="container kpi-section">
  <div class="kpi-grid">
    <div class="kpi-card primary">
      <div class="kpi-label">{latest_year} 年营业收入</div>
      <div class="kpi-value">{latest_rev:,.0f}<span class="kpi-unit"> 亿元</span></div>
      <div class="kpi-change {'down' if rev_growth < 0 else 'up'}">{_arrow(rev_growth)} {abs(rev_growth):.2f}% 同比{'下滑' if rev_growth < 0 else '增长'}</div>
    </div>
    <div class="kpi-card primary">
      <div class="kpi-label">{latest_year} 年归母净利润</div>
      <div class="kpi-value">{latest_profit:,.0f}<span class="kpi-unit"> 亿元</span></div>
      <div class="kpi-change {'down' if profit_growth < 0 else 'up'}">{_arrow(profit_growth)} {abs(profit_growth):.2f}% 同比{'下滑' if profit_growth < 0 else '增长'}</div>
    </div>
    <div class="kpi-card accent">
      <div class="kpi-label">{latest_year} 年 ROE</div>
      <div class="kpi-value">{latest_roe:.2f}<span class="kpi-unit">%</span></div>
      <div class="kpi-change {'down' if roe_change < 0 else 'up'}">{_arrow(roe_change)} {abs(roe_change):.2f}pp 同比{'下滑' if roe_change < 0 else '提升'}</div>
    </div>
  </div>
</div>

<div class="container">
  <div class="section">
    <div class="section-header">
      <div class="section-number">PART 01</div>
      <div class="section-title">执行摘要</div>
      <div class="section-line"></div>
    </div>

    <div class="exec-summary">
      <h3>核心观点</h3>
      <p>{summary_text}</p>
    </div>
  </div>
</div>

<div class="container">
  <div class="section">
    <div class="section-header">
      <div class="section-number">PART 02</div>
      <div class="section-title">核心财务指标趋势</div>
      <div class="section-line"></div>
      <p class="section-desc">营业收入、净利润、总资产、净资产历年变化一览</p>
    </div>

    <div class="chart-block full-width">
      <div class="chart-title">年度财务指标趋势图</div>
      <img class="chart-img" src="charts/年度财务指标趋势图.png" alt="年度财务指标趋势">
    </div>

    <div class="chart-block" style="overflow-x: auto;">
      <div class="chart-title">年度财务数据明细</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>年份</th>
            <th>营业收入</th>
            <th>归母净利润</th>
            <th>总资产</th>
            <th>净资产</th>
            <th>每股收益</th>
            <th>ROE</th>
            <th>变动趋势</th>
          </tr>
        </thead>
        <tbody>{data_rows}
        </tbody>
      </table>
    </div>
  </div>
</div>

<div class="container">
  <div class="section">
    <div class="section-header">
      <div class="section-number">PART 03</div>
      <div class="section-title">增长率分析</div>
      <div class="section-line"></div>
      <p class="section-desc">各财务指标年度同比增长率对比，揭示增长动能变化</p>
    </div>

    <div class="chart-block full-width">
      <div class="chart-title">财务指标同比增长率</div>
      <img class="chart-img" src="charts/财务指标增长率.png" alt="财务指标增长率">
    </div>

    <div class="chart-block">
      <div class="chart-title">最新年度增长率明细</div>
      <table class="data-table">
        <thead><tr><th>指标</th><th>同比增长率</th></tr></thead>
        <tbody>{growth_rows}</tbody>
      </table>
    </div>

    <div class="analysis-grid">
      <div class="analysis-card">
        <h3>{analysis_right_title}</h3>
        {analysis_right}
      </div>
      <div class="analysis-card">
        <h3>{analysis_left_title}</h3>
        {analysis_left}
      </div>
    </div>
  </div>
</div>

<div class="container">
  <div class="section">
    <div class="section-header">
      <div class="section-number">PART 04</div>
      <div class="section-title">盈利能力与估值指标</div>
      <div class="section-line"></div>
      <p class="section-desc">ROE 与 EPS 走势分析，评估股东回报质量</p>
    </div>

    <div class="chart-block full-width">
      <div class="chart-title">ROE 与 EPS 变化趋势</div>
      <img class="chart-img" src="charts/财务比率分析.png" alt="财务比率分析">
    </div>

    <div class="chart-block">
      <div class="chart-title">历年 ROE / EPS 速览</div>
      <div class="timeline">{timeline_items}
      </div>
    </div>
  </div>
</div>

<div class="container">
  <div class="section">
    <div class="section-header">
      <div class="section-number">PART 05</div>
      <div class="section-title">指标相关性分析</div>
      <div class="section-line"></div>
      <p class="section-desc">各财务维度之间的统计学关联，洞察业务驱动关系</p>
    </div>

    <div class="chart-block full-width">
      <div class="chart-title">财务指标相关性矩阵</div>
      <img class="chart-img" src="charts/财务指标相关性矩阵.png" alt="财务指标相关性矩阵">
    </div>
  </div>
</div>

<div class="container">
  <div class="section">
    <div class="section-header">
      <div class="section-number">PART 06</div>
      <div class="section-title">风险提示与展望</div>
      <div class="section-line"></div>
    </div>

    <div class="analysis-grid">
      <div class="analysis-card">
        <h3>宏观风险</h3>
        <ul>
          <li><strong>宏观经济承压</strong> — 经济增速放缓可能抑制终端消费需求</li>
          <li><strong>行业政策调控</strong> — 税收、环保等行业政策变化可能影响盈利空间</li>
          <li><strong>市场竞争加剧</strong> — 行业竞争格局变化可能影响市场份额</li>
        </ul>
      </div>
      <div class="analysis-card">
        <h3>公司层面关注点</h3>
        <ul>
          <li><strong>渠道库存</strong> — 关注经销商库存水平和动销情况</li>
          <li><strong>成本控制</strong> — 原材料及人工成本上升对毛利率的影响</li>
          <li><strong>增长质量</strong> — 收入增长是否可持续，利润转化效率如何</li>
          <li><strong>分红政策</strong> — 利润分配政策对股东回报的影响</li>
        </ul>
      </div>
      <div class="analysis-card">
        <h3>积极因素</h3>
        <ul>
          <li><strong>品牌壁垒</strong> — 品牌价值和市场地位构筑核心护城河</li>
          <li><strong>资产负债表稳健</strong> — 净资产 {latest_equity:,.0f} 亿，抗风险能力强</li>
          <li><strong>现金流充沛</strong> — 经营性现金流稳定，经营质量高</li>
          <li><strong>长期成长空间</strong> — 产品结构升级和市场拓展存在增量空间</li>
        </ul>
      </div>
      <div class="analysis-card">
        <h3>{latest_year + 1} 年展望</h3>
        <ul>
          <li>关注 Q1 季报能否止住下滑趋势，验证 {latest_year} 年是否为阶段性底部</li>
          <li>若宏观消费复苏信号明确，公司作为行业龙头具备较强修复动能</li>
          <li>中长期看，产品结构升级和市场拓展仍是核心增长引擎</li>
        </ul>
      </div>
    </div>
  </div>
</div>

<footer class="footer">
  <div class="container">
    <p>{company_name}财务分析报告 ｜ 数据区间 {first_year}—{latest_year} ｜ 由 AI 辅助生成</p>
    <p style="margin-top: 8px;">本报告基于公开年报数据，仅供参考，不构成投资建议</p>
  </div>
</footer>

</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path


if __name__ == "__main__":
    import json, os, sys
    cfg = {}
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    company = cfg.get('company_name', os.path.basename(os.getcwd()))
    sys.path.insert(0, '.')
    from financial_analysis import TencentAnalyzer
    a = TencentAnalyzer()
    ann, qtr = a.extract_all()
    a.calc_growth()
    generate_tencent_html(ann, qtr, a.growth_df, company)
    print("HTML报告已生成: 财务分析报告.html")


# ============================================================
# 腾讯专用 HTML 报告生成器
# ============================================================

def _pct_tag(val):
    if pd.isna(val):
        return '<span style="color:#999">N/A</span>'
    css = 'tag-up' if val >= 0 else 'tag-down'
    sign = '+' if val >= 0 else ''
    return '<span class="%s">%s%.1f%%</span>' % (css, sign, val)


def generate_tencent_html(annual_df, quarterly_df, growth_df, company_name,
                          output_path='财务分析报告.html'):
    ann = annual_df.sort_values('年份').reset_index(drop=True)
    gdf = growth_df.sort_values('年份').reset_index(drop=True)
    has_qtr = len(quarterly_df) > 0
    if has_qtr:
        qcols = [c for c in ['year','quarter','period'] if c in quarterly_df.columns]
        sort_cols = [c for c in ['year','quarter'] if c in quarterly_df.columns]
        qtr = quarterly_df.sort_values(sort_cols).reset_index(drop=True) if sort_cols else quarterly_df
    else:
        qtr = pd.DataFrame()

    if len(ann) == 0:
        print("无年度数据，跳过HTML生成")
        return

    latest = ann.iloc[-1]
    latest_yr = int(latest['年份'])
    first_yr  = int(ann.iloc[0]['年份'])
    prev      = ann.iloc[-2] if len(ann) >= 2 else latest

    def _safe(row, col, scale=1):
        v = row.get(col)
        return v / scale if (v is not None and not pd.isna(v)) else None

    rev   = _safe(latest, 'revenue', 1e8)
    gross = _safe(latest, 'gross', 1e8)
    op    = _safe(latest, 'op_profit', 1e8)
    net   = _safe(latest, 'attr_profit', 1e8)
    eps   = _safe(latest, 'basic_eps')

    prev_rev = _safe(prev, 'revenue', 1e8)
    prev_net = _safe(prev, 'attr_profit', 1e8)
    rev_growth  = (rev - prev_rev) / prev_rev * 100 if (rev and prev_rev) else 0
    net_growth  = (net - prev_net) / prev_net * 100 if (net and prev_net) else 0
    gm = gross / rev * 100 if (gross and rev) else None
    nm = net / rev * 100 if (net and rev) else None

    # ---- 年度数据表 ----
    data_rows = ''
    for _, row in ann.iterrows():
        yr = int(row['年份'])
        gr = gdf[gdf['年份'] == yr]
        g  = gr.iloc[0] if len(gr) else None

        rev_v   = f"{row['revenue']/1e8:,.0f}"    if 'revenue'    in ann.columns and pd.notna(row.get('revenue'))    else '-'
        gro_v   = f"{row['gross']/1e8:,.0f}"      if 'gross'      in ann.columns and pd.notna(row.get('gross'))      else '-'
        net_v   = f"{row['attr_profit']/1e8:,.0f}" if 'attr_profit' in ann.columns and pd.notna(row.get('attr_profit')) else '-'
        eps_v   = f"{row['basic_eps']:.2f}"       if 'basic_eps'  in ann.columns and pd.notna(row.get('basic_eps'))  else '-'
        gm_v    = f"{row['gross']/row['revenue']*100:.1f}%" if ('gross' in ann.columns and 'revenue' in ann.columns
                   and pd.notna(row.get('gross')) and pd.notna(row.get('revenue')) and row['revenue']>0) else '-'

        rev_tag = _pct_tag(g['revenue_yoy']) if g is not None and 'revenue_yoy' in gdf.columns and pd.notna(g.get('revenue_yoy')) else '<span style="color:#999">基准</span>'
        net_tag = _pct_tag(g['attr_profit_yoy']) if g is not None and 'attr_profit_yoy' in gdf.columns and pd.notna(g.get('attr_profit_yoy')) else ''

        data_rows += f'''
          <tr>
            <td><strong>{yr}</strong></td>
            <td>{rev_v}</td>
            <td>{gro_v}</td>
            <td>{net_v}</td>
            <td>{eps_v}</td>
            <td>{gm_v}</td>
            <td>{rev_tag} {net_tag}</td>
          </tr>'''

    # ---- 季度数据表 ----
    qtr_rows = ''
    if len(qtr) > 0:
        recent_qtr = qtr.tail(12)
        period_col = 'period' if 'period' in qtr.columns else ('期间' if '期间' in qtr.columns else None)
        for _, row in recent_qtr.iterrows():
            r_v = ('%.1f' % (row['revenue']/1e4)) if 'revenue' in qtr.columns and pd.notna(row.get('revenue')) else '-'
            n_v = ('%.1f' % (row['attr_profit']/1e4)) if 'attr_profit' in qtr.columns and pd.notna(row.get('attr_profit')) else '-'
            p_v = str(row[period_col]) if period_col else str(row.get('year','?')) + 'Q' + str(row.get('quarter','?'))
            qtr_rows += '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (p_v, r_v, n_v)

    # ---- 关键指标变化 ----
    yoy_rows = ''
    if len(gdf) >= 2:
        lg = gdf.iloc[-1]
        for col, label in [('revenue_yoy','营业收入'), ('attr_profit_yoy','归母净利润'),
                           ('gross_yoy','毛利润'), ('op_profit_yoy','经营利润'),
                           ('basic_eps_yoy','基本 EPS')]:
            if col in gdf.columns and pd.notna(lg.get(col)):
                yoy_rows += f'<tr><td>{label}</td><td>{_pct_tag(lg[col])}</td></tr>'

    # ---- 执行摘要 ----
    if rev and net:
        summary = f'''腾讯控股在 <span class="hl">{first_yr}—{latest_yr}</span> 年的财务表现呈现强劲增长趋势。
        {latest_yr} 年营业收入达 <span class="hl">{rev:,.0f} 亿元</span>，
        同比{'增长' if rev_growth>=0 else '下滑'} <span class="hl">{abs(rev_growth):.1f}%</span>；
        归母净利润 <span class="hl">{net:,.0f} 亿元</span>，
        同比{'增长' if net_growth>=0 else '下滑'} <span class="hl">{abs(net_growth):.1f}%</span>。
        {'毛利率达 <span class="hl">' + f'{gm:.1f}%</span>' if gm else ''}
        {'，归母净利率 <span class="hl">' + f'{nm:.1f}%</span>' if nm else ''}。
        基本每股盈利 <span class="hl">{eps:.2f} 元</span>，公司盈利能力持续改善。'''
    else:
        summary = f'{company_name} 财务分析报告，数据区间 {first_yr}—{latest_yr} 年。'

    # ---- KPI 变动方向 ----
    def _kpi_change_class(val):
        return 'up' if val >= 0 else 'down'
    def _arrow(val):
        return '↑' if val >= 0 else '↓'

    # ---- 时间线 ----
    timeline_items = ''
    for _, row in ann.iterrows():
        yr  = int(row['年份'])
        rev_b = row.get('revenue')
        net_b = row.get('attr_profit')
        eps_b = row.get('basic_eps')
        if rev_b and net_b:
            nm_b = net_b / rev_b * 100
            desc = f'营收 {rev_b/1e8:,.0f} 亿 · 归母净利 {net_b/1e8:,.0f} 亿 · 净利率 {nm_b:.1f}%'
            if eps_b:
                desc += f' · EPS {eps_b:.2f} 元'
        else:
            desc = '数据部分提取'
        timeline_items += f'''
        <div class="timeline-item">
          <div class="tl-year">{yr}</div>
          <div class="tl-text">{desc}</div>
        </div>'''

    # ---- 季度区块（pre-compute to avoid nested f-string with triple quotes) ----
    if has_qtr:
        qtr_section = (
            '<div class="sec">'
            '<div class="sec-hd">'
            '<div class="sec-no">PART 05</div>'
            '<div class="sec-title">季度财务趋势</div>'
            '<div class="sec-line"></div>'
            '<p class="sec-desc">逐季营收与利润变化，捕捉短周期增长动能</p>'
            '</div>'
            '<div class="card">'
            '<div class="card-title">季度收入与利润趋势</div>'
            '<img class="chart" src="charts/季度收入与利润趋势.png" alt="季度趋势">'
            '</div>'
            '<div class="card" style="overflow-x:auto;max-width:460px">'
            '<div class="card-title">近12季度数据（百亿元）</div>'
            '<table class="dt">'
            '<thead><tr><th>期间</th><th>营收(百亿)</th><th>归母净利(百亿)</th></tr></thead>'
            '<tbody>' + qtr_rows + '</tbody>'
            '</table></div></div>'
        )
        risk_part_no = 'PART 06'
    else:
        qtr_section = ''
        risk_part_no = 'PART 05'

    # ====================================================================
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{company_name}财务分析报告 {first_yr}-{latest_yr}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
  *{{margin:0;padding:0;box-sizing:border-box}}
  :root{{
    --teal:#006D77;--teal-light:#83C5BE;--coral:#E29578;--gold:#FFDDD2;
    --navy:#1B2A4A;--bg:#F8F9FA;--white:#fff;--text:#2C2C2C;
    --green:#2E7D32;--red:#C62828;--border:#E0E0E0;
    --shadow:0 4px 20px rgba(0,0,0,.08);--shadow-lg:0 8px 40px rgba(0,0,0,.12)
  }}
  body{{font-family:'Noto Sans SC',-apple-system,sans-serif;background:var(--bg);color:var(--text);line-height:1.7;-webkit-font-smoothing:antialiased}}
  .hero{{background:linear-gradient(135deg,#003840 0%,#006D77 50%,#83C5BE 100%);color:#fff;padding:72px 0 56px;overflow:hidden;position:relative}}
  .hero::after{{content:'';position:absolute;right:-60px;top:-60px;width:320px;height:320px;background:radial-gradient(circle,rgba(255,255,255,.06),transparent 70%);border-radius:50%}}
  .hero-inner{{max-width:1100px;margin:0 auto;padding:0 40px;position:relative;z-index:1}}
  .badge{{display:inline-block;border:1px solid rgba(255,255,255,.4);color:rgba(255,255,255,.9);padding:5px 18px;border-radius:20px;font-size:12px;letter-spacing:2px;margin-bottom:20px}}
  .hero h1{{font-size:44px;font-weight:900;letter-spacing:3px;margin-bottom:10px}}
  .hero-sub{{color:rgba(255,255,255,.7);font-size:17px;font-weight:300}}
  .hero-date{{color:rgba(255,255,255,.45);font-size:12px;margin-top:6px}}
  .container{{max-width:1100px;margin:0 auto;padding:0 40px}}
  .kpi-wrap{{margin-top:-36px;position:relative;z-index:2}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}
  .kpi{{background:#fff;border-radius:14px;padding:24px 20px;box-shadow:var(--shadow-lg);border:1px solid var(--border);border-top:4px solid var(--teal);transition:transform .2s}}
  .kpi:hover{{transform:translateY(-3px)}}
  .kpi-label{{font-size:12px;color:#888;letter-spacing:1px;margin-bottom:6px}}
  .kpi-val{{font-size:30px;font-weight:900;color:var(--navy)}}
  .kpi-unit{{font-size:13px;font-weight:400;color:#999}}
  .kpi-chg{{font-size:12px;margin-top:6px;font-weight:600}}
  .kpi-chg.up{{color:var(--green)}}.kpi-chg.down{{color:var(--red)}}
  .sec{{padding:56px 0}}.sec-hd{{text-align:center;margin-bottom:40px}}
  .sec-no{{font-size:11px;color:var(--teal);letter-spacing:3px;margin-bottom:6px}}
  .sec-title{{font-size:28px;font-weight:700;color:var(--navy);margin-bottom:10px}}
  .sec-line{{width:48px;height:3px;background:linear-gradient(90deg,var(--teal),var(--coral));margin:0 auto;border-radius:2px}}
  .sec-desc{{color:#888;font-size:14px;margin-top:10px;max-width:560px;margin-left:auto;margin-right:auto}}
  .card{{background:#fff;border-radius:14px;padding:28px;box-shadow:var(--shadow);border:1px solid var(--border);margin-bottom:24px}}
  .card-title{{font-size:16px;font-weight:700;color:var(--navy);margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid var(--border)}}
  img.chart{{width:100%;border-radius:8px}}
  table.dt{{width:100%;border-collapse:separate;border-spacing:0;font-size:13px}}
  .dt thead th{{background:var(--navy);color:#fff;padding:12px 14px;font-weight:500;font-size:12px;letter-spacing:1px;text-align:center}}
  .dt thead th:first-child{{border-radius:8px 0 0 0;text-align:left}}
  .dt thead th:last-child{{border-radius:0 8px 0 0}}
  .dt tbody td{{padding:10px 14px;border-bottom:1px solid var(--border);text-align:center}}
  .dt tbody td:first-child{{text-align:left;font-weight:600;color:var(--navy)}}
  .dt tbody tr:hover{{background:#F0F7F8}}
  .tag-up{{display:inline-block;background:#E8F5E9;color:var(--green);padding:2px 9px;border-radius:10px;font-size:11px;font-weight:700}}
  .tag-down{{display:inline-block;background:#FFEBEE;color:var(--red);padding:2px 9px;border-radius:10px;font-size:11px;font-weight:700}}
  .exec-box{{background:linear-gradient(135deg,var(--navy),#243456);color:#fff;border-radius:14px;padding:36px;margin-bottom:24px;position:relative;overflow:hidden}}
  .exec-box::after{{content:'';position:absolute;right:-30px;top:-30px;width:180px;height:180px;background:radial-gradient(circle,rgba(131,197,190,.15),transparent 70%);border-radius:50%}}
  .exec-box h3{{font-size:18px;font-weight:700;color:var(--teal-light);margin-bottom:12px;position:relative;z-index:1}}
  .exec-box p{{font-size:14px;line-height:2;color:rgba(255,255,255,.85);position:relative;z-index:1}}
  .hl{{color:#83C5BE;font-weight:700}}
  .tl{{position:relative;padding-left:28px}}.tl::before{{content:'';position:absolute;left:6px;top:4px;bottom:4px;width:2px;background:linear-gradient(180deg,var(--teal),var(--coral))}}
  .timeline-item{{position:relative;margin-bottom:22px}}.timeline-item::before{{content:'';position:absolute;left:-24px;top:5px;width:12px;height:12px;background:var(--teal);border-radius:50%;border:2px solid #fff;box-shadow:0 0 0 2px var(--teal)}}
  .tl-year{{font-size:12px;color:var(--teal);font-weight:700;letter-spacing:2px;margin-bottom:3px}}
  .tl-text{{font-size:13px;color:#666;line-height:1.7}}
  .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
  .risk-card{{background:#fff;border-radius:14px;padding:24px;box-shadow:var(--shadow);border:1px solid var(--border)}}
  .risk-card h3{{font-size:15px;font-weight:700;color:var(--navy);margin-bottom:10px}}
  .risk-card li{{color:#666;font-size:13px;line-height:1.8;margin-bottom:4px;padding-left:4px}}
  footer{{background:var(--navy);color:rgba(255,255,255,.45);text-align:center;padding:36px 0;font-size:12px;margin-top:16px}}
  @media(max-width:768px){{.kpi-grid{{grid-template-columns:1fr 1fr}}.grid2{{grid-template-columns:1fr}}.hero h1{{font-size:30px}}}}
</style>
</head>
<body>

<header class="hero">
  <div class="hero-inner">
    <div class="badge">FINANCIAL ANALYSIS · {latest_yr}</div>
    <h1>{company_name}</h1>
    <p class="hero-sub">财务数据深度分析报告 · {first_yr}—{latest_yr} 年</p>
    <p class="hero-date">生成日期：{datetime.now().strftime("%Y 年 %m 月 %d 日")} ｜ 单位：人民币百万元（另有注明除外）</p>
  </div>
</header>

<div class="container kpi-wrap">
  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-label">{latest_yr} 年营业收入</div>
      <div class="kpi-val">{rev:,.0f}<span class="kpi-unit"> 亿</span></div>
      <div class="kpi-chg {_kpi_change_class(rev_growth)}">{_arrow(rev_growth)} {abs(rev_growth):.1f}% 同比</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">{latest_yr} 年归母净利润</div>
      <div class="kpi-val">{net:,.0f}<span class="kpi-unit"> 亿</span></div>
      <div class="kpi-chg {_kpi_change_class(net_growth)}">{_arrow(net_growth)} {abs(net_growth):.1f}% 同比</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">{latest_yr} 年毛利率</div>
      <div class="kpi-val">{gm:.1f}<span class="kpi-unit">%</span></div>
      <div class="kpi-chg up">盈利能力持续改善</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">{latest_yr} 年基本 EPS</div>
      <div class="kpi-val">{eps:.2f}<span class="kpi-unit"> 元/股</span></div>
      <div class="kpi-chg up">每股盈利持续提升</div>
    </div>
  </div>
</div>

<div class="container">
  <div class="sec">
    <div class="sec-hd">
      <div class="sec-no">PART 01</div>
      <div class="sec-title">执行摘要</div>
      <div class="sec-line"></div>
    </div>
    <div class="exec-box">
      <h3>核心观点</h3>
      <p>{summary}</p>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd">
      <div class="sec-no">PART 02</div>
      <div class="sec-title">年度财务指标趋势</div>
      <div class="sec-line"></div>
      <p class="sec-desc">营业收入、毛利润、经营利润、归母净利润历年变化</p>
    </div>
    <div class="card">
      <div class="card-title">年度四大指标趋势图（百亿元）</div>
      <img class="chart" src="charts/年度财务指标趋势图.png" alt="年度趋势">
    </div>
    <div class="card">
      <div class="card-title">收入与利润规模对比</div>
      <img class="chart" src="charts/收入与利润规模对比.png" alt="规模对比">
    </div>
    <div class="card" style="overflow-x:auto">
      <div class="card-title">历年年度财务数据明细（亿元）</div>
      <table class="dt">
        <thead>
          <tr><th>年份</th><th>营业收入</th><th>毛利润</th><th>归母净利润</th><th>基本EPS(元)</th><th>毛利率</th><th>增速</th></tr>
        </thead>
        <tbody>{data_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd">
      <div class="sec-no">PART 03</div>
      <div class="sec-title">增长率分析</div>
      <div class="sec-line"></div>
      <p class="sec-desc">各财务指标年度同比增长率，揭示增长动能变化</p>
    </div>
    <div class="card">
      <div class="card-title">年度同比增长率</div>
      <img class="chart" src="charts/财务指标增长率.png" alt="增长率">
    </div>
    <div class="card" style="max-width:480px">
      <div class="card-title">{latest_yr} 年增长率速览</div>
      <table class="dt">
        <thead><tr><th>指标</th><th>同比增长</th></tr></thead>
        <tbody>{yoy_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="sec">
    <div class="sec-hd">
      <div class="sec-no">PART 04</div>
      <div class="sec-title">盈利能力分析</div>
      <div class="sec-line"></div>
      <p class="sec-desc">毛利率、净利率、EPS 走势，评估股东回报质量</p>
    </div>
    <div class="card">
      <div class="card-title">毛利率 / 净利率 / EPS 趋势</div>
      <img class="chart" src="charts/利润率与EPS.png" alt="利润率EPS">
    </div>
    <div class="card">
      <div class="card-title">历年盈利能力时间线</div>
      <div class="tl">{timeline_items}</div>
    </div>
  </div>

  {qtr_section}

  <div class="sec">
    <div class="sec-hd">
      <div class="sec-no">{risk_part_no}</div>
      <div class="sec-title">风险提示与展望</div>
      <div class="sec-line"></div>
    </div>
    <div class="grid2">
      <div class="risk-card">
        <h3>主要风险</h3>
        <ul>
          <li><strong>监管风险</strong> — 游戏版号、平台经济、数据安全法规持续演变</li>
          <li><strong>宏观风险</strong> — 消费复苏节奏影响广告收入与 VAS 付费率</li>
          <li><strong>AI 竞争</strong> — 大模型军备竞赛加剧资本支出与人才竞争</li>
          <li><strong>汇率风险</strong> — 港币/人民币波动影响 HKD 计价回报</li>
        </ul>
      </div>
      <div class="risk-card">
        <h3>积极因素</h3>
        <ul>
          <li><strong>微信生态护城河</strong> — 月活超 13 亿，黏性极强的超级平台</li>
          <li><strong>AI 变现加速</strong> — 混元大模型赋能广告、游戏、云业务</li>
          <li><strong>国际化游戏</strong> — 海外游戏收入持续贡献多元化增长</li>
          <li><strong>股票回购</strong> — 积极回购彰显对长期价值的信心</li>
        </ul>
      </div>
      <div class="risk-card">
        <h3>{latest_yr + 1} 年展望</h3>
        <ul>
          <li>关注 AI 广告定向与推荐算法持续带来的货币化效率提升</li>
          <li>视频号商业化及小程序生态拓展是新增量</li>
          <li>云业务规模化盈利有望贡献利润率改善</li>
          <li>资本回报（分红 + 回购）力度持续提升</li>
        </ul>
      </div>
      <div class="risk-card">
        <h3>关键观察指标</h3>
        <ul>
          <li>广告收入增速（AI 赋能效果验证）</li>
          <li>金融科技及企业服务增速（含云）</li>
          <li>Non-IFRS 净利润率水平</li>
          <li>年度回购金额与股息率变化</li>
        </ul>
      </div>
    </div>
  </div>
</div>

<footer>
  <p>{company_name}财务分析报告 ｜ 数据区间 {first_yr}—{latest_yr} ｜ 由 AI 辅助生成</p>
  <p style="margin-top:6px">本报告基于公开发布的财报/季报数据，仅供参考，不构成投资建议</p>
</footer>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  HTML 报告已写入: {output_path}")
    return output_path