#!/usr/bin/env python3
"""生成腾讯控股 2004-2025 交互式财务分析报告（仿贵州茅台报告风格）。"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ROOT, '腾讯控股_annual_master.json'), encoding='utf-8') as f:
    ANNUAL = json.load(f)
with open(os.path.join(ROOT, 'mgmt_data.json'), encoding='utf-8') as f:
    MGMT = json.load(f)
with open(os.path.join(ROOT, '腾讯控股_raw_extract.json'), encoding='utf-8') as f:
    RAW = json.load(f)
with open(os.path.join(ROOT, '腾讯控股_supplement.json'), encoding='utf-8') as f:
    SUPP = json.load(f)
with open(os.path.join(ROOT, '腾讯控股_现金流质量.json'), encoding='utf-8') as f:
    CFQ = {r['年份']: r for r in json.load(f)}

YI = 100.0  # RMB Million -> 亿元

def yi(v):
    return round(v / YI, 2) if v is not None else None

ANNUAL_SORTED = sorted(ANNUAL, key=lambda r: r['year'])
YEARS = [r['year'] for r in ANNUAL_SORTED]

def col(name, scale=YI):
    out = []
    for r in ANNUAL_SORTED:
        v = r.get(name)
        out.append(round(v/scale, 2) if v is not None else None)
    return out

REV   = col('revenue')
GROSS = col('gross')
OP    = col('op_profit')
ATTR  = col('attr_profit')
NIFRS = col('nifrs_net')
TA    = col('total_assets')
NA    = col('net_assets')
EPS   = [r.get('eps_basic') for r in ANNUAL_SORTED]

def yoy(series):
    out = [None]
    for i in range(1, len(series)):
        a, b = series[i-1], series[i]
        if a and b is not None and a != 0:
            out.append(round((b-a)/a*100, 1))
        else:
            out.append(None)
    return out

REV_G  = yoy(REV)
ATTR_G = yoy(ATTR)

GROSS_MARGIN = [round(g/r*100,1) if (g is not None and r) else None for g,r in zip(GROSS, REV)]
NET_MARGIN   = [round(a/r*100,1) if (a is not None and r) else None for a,r in zip(ATTR, REV)]
DEBT_RATIO   = [round((t-n)/t*100,1) if (t is not None and n is not None and t) else None for t,n in zip(TA, NA)]

# ROE（估算）= 归母净利润 / 期初期末归母净资产均值 * 100；无法取得期初值（首年）时用期末值近似
ROE = []
for i, (a, n) in enumerate(zip(ATTR, NA)):
    if a is None or n is None:
        ROE.append(None)
        continue
    prev_n = NA[i-1] if i > 0 and NA[i-1] is not None else n
    avg_n = (n + prev_n) / 2
    ROE.append(round(a/avg_n*100, 1) if avg_n else None)

# ROA（估算）= 归母净利润 / 期初期末总资产均值 * 100
ROA = []
for i, (a, t) in enumerate(zip(ATTR, TA)):
    if a is None or t is None:
        ROA.append(None)
        continue
    prev_t = TA[i-1] if i > 0 and TA[i-1] is not None else t
    avg_t = (t + prev_t) / 2
    ROA.append(round(a/avg_t*100, 1) if avg_t else None)

# ---------------- 补充指标（分部收入 / FCF / Capex / 股息 / Non-GAAP经营利润） ----------------
# 分部收入：2004-2012 的 IVAS+MVAS 合并为"增值服务"，与 2013 年起的 VAS 口径可比
SEG_VAS, SEG_ADS, SEG_FINTECH, SEG_ECOM, SEG_OTHERS = [], [], [], [], []
for y in YEARS:
    s = SUPP['segments'].get(str(y), {})
    vas = s.get('vas')
    if vas is None and ('ivas' in s or 'mvas' in s):
        vas = (s.get('ivas') or 0) + (s.get('mvas') or 0)
    SEG_VAS.append(round(vas/YI, 1) if vas is not None else None)
    SEG_ADS.append(round(s['ads']/YI, 1) if s.get('ads') is not None else None)
    SEG_FINTECH.append(round(s['fintech']/YI, 1) if s.get('fintech') is not None else None)
    SEG_ECOM.append(round(s['ecommerce']/YI, 1) if s.get('ecommerce') is not None else None)
    SEG_OTHERS.append(round(s['others']/YI, 1) if s.get('others') is not None else None)

# 收入占比（%）
def _share(seg):
    out = []
    for v, r in zip(seg, REV):
        out.append(round(v/r*100, 1) if (v is not None and r) else None)
    return out
SEG_VAS_PCT, SEG_ADS_PCT = _share(SEG_VAS), _share(SEG_ADS)
SEG_FINTECH_PCT, SEG_ECOM_PCT, SEG_OTHERS_PCT = _share(SEG_FINTECH), _share(SEG_ECOM), _share(SEG_OTHERS)

# FCF / Capex 季度序列（2019Q1-2026Q1）与年度加总
FC_LABELS, FC_FCF, FC_CAPEX = [], [], []
for y in range(2019, 2027):
    for q in (1, 2, 3, 4):
        key = f'{y}Q{q}'
        rec = SUPP['fcf_capex_quarterly'].get(key)
        if rec is None:
            continue
        FC_LABELS.append(key)
        FC_FCF.append(round(rec['fcf']/YI, 1) if rec.get('fcf') is not None else None)
        FC_CAPEX.append(round(rec['capex']/YI, 1) if rec.get('capex') is not None else None)

FCF_FY, CAPEX_FY = [], []   # 与 YEARS 对齐（2004-2018 为 None）
for y in YEARS:
    qs = [SUPP['fcf_capex_quarterly'].get(f'{y}Q{q}') for q in (1, 2, 3, 4)]
    fvals = [r.get('fcf') for r in qs if r]
    if len(fvals) == 4 and all(v is not None for v in fvals):
        FCF_FY.append(round(sum(fvals)/YI, 1))
    else:
        FCF_FY.append(None)
    q4 = SUPP['fcf_capex_quarterly'].get(f'{y}Q4') or {}
    CAPEX_FY.append(round(q4['capex_fy']/YI, 1) if q4.get('capex_fy') is not None else None)

DPS = [SUPP['dps'].get(str(y)) for y in YEARS]                     # 港元/股，拆股调整后
NIFRS_OP = [round(SUPP['nifrs_op'][str(y)]/YI, 1) if str(y) in SUPP['nifrs_op'] else None for y in YEARS]

# ---------------- 现金流质量（2004-2025，来自年报现金流量表与资产负债表） ----------------
def _cfq(key):
    out = []
    for y in YEARS:
        v = CFQ.get(y, {}).get(key)
        out.append(round(v/YI, 1) if v is not None else None)
    return out

OCF        = _cfq('经营现金流')
CAPEX_CF   = _cfq('资本开支')       # 购建固定资产+无形资产（现金流量表口径）
FCF_CF     = _cfq('自由现金流')     # OCF − 上述资本开支
DIVIDEND   = _cfq('分红')
BUYBACK    = _cfq('回购')
CASH_BAL   = _cfq('现金余额')       # 期末现金及现金等价物（不含定期存款）
DEBT       = _cfq('有息负债')       # 借款+应付票据（流动+非流动）

SHAREHOLDER_RET = [
    None if (d is None and b is None) else round((d or 0) + (b or 0), 1)
    for d, b in zip(DIVIDEND, BUYBACK)
]
# 净现比双口径：IFRS 净利润受非现金投资损益扰动，Non-GAAP 口径更能反映主业含金量
NCR_IFRS = [round(o/a*100, 1) if (o is not None and a) else None for o, a in zip(OCF, ATTR)]
NCR_NG   = [round(o/n*100, 1) if (o is not None and n) else None for o, n in zip(OCF, NIFRS)]

# ---------------- 季度追踪（2019-2026） ----------------
# PDF 摘要表在个别年份（如 2022/2023）把"三个月"表误判为"H1"、把"全年"表误判为"Q4"，
# 因此这里用已核实的年度口径（ANNUAL master）做锚点重新校正：Q1/Q3 直接取值（经交叉验证
# 在所有年份均可靠），H1 若小于 Q1 说明其实是 Q2 单季度值，Q4 一律用 FY - Q1 - Q2 - Q3 反推，
# 不采信摘要表里可能连年份/期间都取错的 Q4 原始抓取值。
annual_by_year = {r['year']: r for r in ANNUAL_SORTED}
periods_by_key = {}
for rec in RAW['periods_2019_2026']:
    periods_by_key[(rec['year'], rec['period_type'])] = rec

def _reconcile_year(y):
    q1 = periods_by_key.get((y,'Q1'))
    h1 = periods_by_key.get((y,'H1'))
    q3 = periods_by_key.get((y,'Q3'))
    fy = annual_by_year.get(y)

    out = {'Q1': None, 'Q2': None, 'Q3': None, 'Q4': None}
    q1_rev = q1.get('revenue') if q1 else None
    q1_attr = q1.get('attr_profit') if q1 else None
    if q1_rev is not None:
        out['Q1'] = dict(revenue=q1_rev, attr_profit=q1_attr)

    q2_rev = q2_attr = None
    if h1 and h1.get('revenue') is not None:
        if q1_rev is not None and h1['revenue'] >= q1_rev:
            q2_rev = h1['revenue'] - q1_rev
            if q1_attr is not None and h1.get('attr_profit') is not None:
                q2_attr = h1['attr_profit'] - q1_attr
        else:
            # H1 摘要表实际抓到的是单季（三个月）数据，而非累计六个月
            q2_rev = h1['revenue']
            q2_attr = h1.get('attr_profit')
    if q2_rev is not None:
        out['Q2'] = dict(revenue=q2_rev, attr_profit=q2_attr)

    q3_rev = q3.get('revenue') if q3 else None
    q3_attr = q3.get('attr_profit') if q3 else None
    if q3_rev is not None:
        out['Q3'] = dict(revenue=q3_rev, attr_profit=q3_attr)

    if fy is not None:
        known = [v for v in (q1_rev, q2_rev, q3_rev) if v is not None]
        if len(known) == 3:
            q4_rev = fy['revenue'] - q1_rev - q2_rev - q3_rev
            q4_attr = None
            attrs = [q1_attr, q2_attr, q3_attr]
            if all(a is not None for a in attrs):
                q4_attr = fy['attr_profit'] - sum(attrs)
            out['Q4'] = dict(revenue=q4_rev, attr_profit=q4_attr)
    return out

quarter_labels, quarter_rev, quarter_attr = [], [], []
interim_from_periods = []
for y in range(2019, 2027):
    rec = _reconcile_year(y)
    for label in ('Q1','Q2','Q3','Q4'):
        d = rec[label]
        if d is None or d.get('revenue') is None:
            continue
        quarter_labels.append(f'{y}{label}')
        quarter_rev.append(round(d['revenue']/YI,1))
        quarter_attr.append(round(d['attr_profit']/YI,1) if d.get('attr_profit') is not None else None)
    if rec['Q1'] and rec['Q2']:
        h1_rev = rec['Q1']['revenue'] + rec['Q2']['revenue']
        h1_attr = None
        if rec['Q1'].get('attr_profit') is not None and rec['Q2'].get('attr_profit') is not None:
            h1_attr = rec['Q1']['attr_profit'] + rec['Q2']['attr_profit']
        interim_from_periods.append(dict(year=y, revenue=round(h1_rev/YI,2),
                                          gross=None, op=None,
                                          attr=round(h1_attr/YI,2) if h1_attr is not None else None,
                                          eps=None))

# ---------------- 半年报数据（2004-2025） ----------------
interim_rows = []
for r in RAW['interim_2004_2018']:
    interim_rows.append(dict(
        year=r['year'],
        revenue=round(r['revenue']/YI,2) if r.get('revenue') is not None else None,
        gross=round(r['gross']/YI,2) if r.get('gross') is not None else None,
        op=round(r['op_profit']/YI,2) if r.get('op_profit') is not None else None,
        attr=round(r['attr_profit']/YI,2) if r.get('attr_profit') is not None else None,
        eps=r.get('eps_basic'),
    ))
interim_rows.extend(interim_from_periods)
interim_rows.sort(key=lambda r: r['year'])

# ---------------- HTML ----------------
def js(v):
    return json.dumps(v, ensure_ascii=False)

latest = ANNUAL_SORTED[-1]
prev = ANNUAL_SORTED[-2]
first_year = YEARS[0]
latest_year = YEARS[-1]
rev_growth_latest = REV_G[-1]
attr_growth_latest = ATTR_G[-1]

kpi_rev = REV[-1]
kpi_attr = ATTR[-1]
kpi_nifrs = NIFRS[-1]
kpi_ta = TA[-1]
kpi_na = NA[-1]
kpi_roe = ROE[-1]
kpi_roe_prev = ROE[-2]
roe_chg = round(kpi_roe - kpi_roe_prev, 1) if (kpi_roe is not None and kpi_roe_prev is not None) else None

rev_multiple = round(REV[-1]/REV[0], 1)

detail_rows_html = ''
for i, y in enumerate(YEARS):
    def fmt(v, nd=0):
        return f'{v:,.{nd}f}' if v is not None else '—'
    gm = GROSS_MARGIN[i]
    nm = NET_MARGIN[i]
    tags = ''
    if REV_G[i] is not None:
        cls = 'tag-up' if REV_G[i] >= 0 else 'tag-down'
        arrow = '+' if REV_G[i] >= 0 else ''
        tags += f'<span class="{cls}">营收{arrow}{REV_G[i]:.1f}%</span> '
    if ATTR_G[i] is not None:
        cls = 'tag-up' if ATTR_G[i] >= 0 else 'tag-down'
        arrow = '+' if ATTR_G[i] >= 0 else ''
        tags += f'<span class="{cls}">净利{arrow}{ATTR_G[i]:.1f}%</span>'
    if not tags:
        tags = '<span style="color:#999">基准年</span>'
    detail_rows_html += f'''
      <tr>
        <td>{y}</td>
        <td>{fmt(REV[i])}</td>
        <td>{fmt(GROSS[i])}</td>
        <td>{fmt(OP[i])}</td>
        <td>{fmt(ATTR[i])}</td>
        <td>{fmt(NIFRS[i]) if NIFRS[i] is not None else '—'}</td>
        <td>{EPS[i]:.3f}</td>
        <td>{fmt(TA[i])}</td>
        <td>{fmt(NA[i])}</td>
        <td>{f'{ROE[i]:.1f}%' if ROE[i] is not None else '—'}</td>
        <td>{tags}</td>
      </tr>'''

cfq_rows_html = ''
for i, y in enumerate(YEARS):
    def cf(v, nd=0):
        return f'{v:,.{nd}f}' if v is not None else '—'
    def ratio(v):
        if v is None:
            return '—'
        cls = 'tag-up' if v >= 100 else 'tag-down'
        return f'<span class="{cls}">{v:.0f}%</span>'
    cfq_rows_html += f'''
      <tr>
        <td>{y}</td>
        <td>{cf(OCF[i])}</td>
        <td>{cf(ATTR[i])}</td>
        <td>{ratio(NCR_IFRS[i])}</td>
        <td>{ratio(NCR_NG[i])}</td>
        <td>{cf(CAPEX_CF[i])}</td>
        <td>{cf(FCF_CF[i])}</td>
        <td>{cf(DIVIDEND[i])}</td>
        <td>{cf(BUYBACK[i])}</td>
        <td>{cf(CASH_BAL[i])}</td>
        <td>{cf(DEBT[i])}</td>
      </tr>'''

supp_rows_html = ''
for i, y in enumerate(YEARS):
    def sf(v, nd=1):
        return f'{v:,.{nd}f}' if v is not None else '—'
    dps_v = f'{DPS[i]:.3f}' if DPS[i] is not None else '—'
    supp_rows_html += f'''
      <tr>
        <td>{y}</td>
        <td>{sf(SEG_VAS[i])}</td>
        <td>{sf(SEG_ADS[i])}</td>
        <td>{sf(SEG_FINTECH[i])}</td>
        <td>{sf(SEG_ECOM[i])}</td>
        <td>{sf(SEG_OTHERS[i])}</td>
        <td>{sf(FCF_FY[i])}</td>
        <td>{sf(CAPEX_FY[i])}</td>
        <td>{dps_v}</td>
        <td>{sf(NIFRS_OP[i])}</td>
      </tr>'''

interim_rows_html = ''
for r in interim_rows:
    def f2(v, nd=1):
        return f'{v:,.{nd}f}' if v is not None else '—'
    eps_v = f"{r['eps']:.3f}" if r.get('eps') is not None else '—'
    interim_rows_html += f'''
      <tr>
        <td>{r['year']} 中期</td>
        <td>{f2(r['revenue'])}</td>
        <td>{f2(r['gross'])}</td>
        <td>{f2(r['op'])}</td>
        <td>{f2(r['attr'])}</td>
        <td>{eps_v}</td>
      </tr>'''

quarter_rows_html = ''
for lbl, rv, ap in zip(quarter_labels, quarter_rev, quarter_attr):
    ap_s = f'{ap:,.1f}' if ap is not None else '—'
    quarter_rows_html += f'<tr><td>{lbl}</td><td>{rv:,.1f}</td><td>{ap_s}</td></tr>'

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>腾讯控股 财务分析报告 2004-2025</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  :root {{ --teal:#006D77; --teal-light:#83C5BE; --coral:#E29578; --gold:#FFDDD2; --navy:#1B2A4A; --slate:#243456; --bg:#F5F8F8; --white:#FFF; --text:#1F2937; --text-secondary:#5B6B76; --green:#2E7D32; --red:#C62828; --border:#DCE6E6; }}
  body {{ font-family:'Noto Sans SC',-apple-system,sans-serif; background:var(--bg); color:var(--text); line-height:1.8; }}
  .hero {{ background:linear-gradient(135deg,#003840,#006D77 55%,#0B4F58); color:#fff; padding:60px 0 40px; text-align:center; position:relative; overflow:hidden; }}
  .hero::before {{ content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%; background:radial-gradient(circle at 30% 50%,rgba(131,197,190,.10) 0%,transparent 50%),radial-gradient(circle at 70% 30%,rgba(226,149,120,.08) 0%,transparent 50%); }}
  .hero h1 {{ font-size:40px; font-weight:900; letter-spacing:3px; position:relative; z-index:1; background:linear-gradient(180deg,#fff,#83C5BE); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }}
  .hero .sub {{ color:rgba(255,255,255,.55); font-size:14px; position:relative; z-index:1; margin-top:8px; }}
  .kpi-row {{ max-width:1100px; margin:-30px auto 0; padding:0 20px; position:relative; z-index:2; display:grid; grid-template-columns:repeat(5,1fr); gap:14px; }}
  .kpi-card {{ background:var(--white); border-radius:14px; padding:22px 18px; box-shadow:0 8px 32px rgba(0,60,64,.12); border:1px solid var(--border); text-align:center; transition:transform .2s; border-top:4px solid var(--teal); }}
  .kpi-card:hover {{ transform:translateY(-3px); }}
  .kpi-card .label {{ font-size:12px; color:var(--text-secondary); letter-spacing:1px; }}
  .kpi-card .value {{ font-size:27px; font-weight:900; color:var(--navy); margin:4px 0; }}
  .kpi-card .unit {{ font-size:13px; color:var(--text-secondary); font-weight:400; }}
  .kpi-card .change {{ font-size:12px; margin-top:4px; font-weight:600; }}
  .down {{ color:var(--red); }} .up {{ color:var(--green); }}
  .nav-bar {{ max-width:1100px; margin:30px auto 0; padding:0 20px; display:flex; gap:4px; flex-wrap:wrap; justify-content:center; }}
  .nav-bar button {{ background:var(--white); border:1px solid var(--border); padding:10px 18px; border-radius:10px; cursor:pointer; font-size:13px; font-family:inherit; color:var(--text-secondary); transition:all .2s; }}
  .nav-bar button:hover {{ border-color:var(--teal); color:var(--navy); }}
  .nav-bar button.active {{ background:var(--navy); color:#fff; border-color:var(--navy); }}
  .section {{ display:none; max-width:1100px; margin:0 auto; padding:30px 20px; }}
  .section.active {{ display:block; }}
  .chart-block {{ background:var(--white); border-radius:14px; padding:24px; box-shadow:0 4px 20px rgba(0,60,64,.06); border:1px solid var(--border); margin-bottom:20px; }}
  .chart-block h3 {{ font-size:16px; color:var(--navy); margin-bottom:16px; }}
  .chart-row {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px; }}
  .chart-row.single {{ grid-template-columns:1fr; }}
  .chart-row canvas {{ width:100% !important; max-height:380px; }}
  .chart-row.full canvas {{ max-height:400px; }}
  .data-table {{ width:100%; border-collapse:separate; border-spacing:0; font-size:12px; }}
  .data-table thead th {{ background:var(--navy); color:#fff; padding:10px 10px; font-weight:500; font-size:11px; letter-spacing:.5px; text-align:center; position:sticky; top:0; z-index:1; }}
  .data-table thead th:first-child {{ border-radius:10px 0 0 0; }}
  .data-table thead th:last-child {{ border-radius:0 10px 0 0; }}
  .data-table tbody td {{ padding:8px 10px; border-bottom:1px solid var(--border); text-align:center; }}
  .data-table tbody td:first-child {{ text-align:left; font-weight:600; color:var(--navy); }}
  .data-table tbody tr:hover {{ background:#EAF4F3; }}
  .table-scroll {{ max-height:600px; overflow-y:auto; border-radius:10px; }}
  .tag-down {{ background:#FDE8EC; color:var(--red); padding:2px 6px; border-radius:8px; font-size:10px; font-weight:600; }}
  .tag-up {{ background:#E8F5E9; color:var(--green); padding:2px 6px; border-radius:8px; font-size:10px; font-weight:600; }}
  .tag-src {{ background:#E3F2FD; color:#1565C0; padding:2px 6px; border-radius:8px; font-size:10px; }}
  .summary-box {{ background:linear-gradient(135deg,var(--navy),var(--slate)); color:#fff; border-radius:14px; padding:30px; margin-bottom:20px; }}
  .summary-box h3 {{ color:var(--teal-light); margin-bottom:12px; font-size:18px; }}
  .summary-box p {{ color:rgba(255,255,255,.85); font-size:14px; line-height:2; }}
  .summary-box .hl {{ color:var(--teal-light); font-weight:600; }}
  .stats-grid {{ max-width:1100px; margin:20px auto 0; padding:0 20px; display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
  .stat-card {{ background:var(--white); border-radius:10px; padding:16px; text-align:center; border:1px solid var(--border); }}
  .stat-card .n {{ font-size:24px; font-weight:900; color:var(--navy); }}
  .stat-card .l {{ font-size:11px; color:var(--text-secondary); }}
  .footer {{ text-align:center; padding:30px; color:var(--text-secondary); font-size:12px; }}
  @media(max-width:768px){{ .kpi-row{{grid-template-columns:1fr 1fr;}} .chart-row{{grid-template-columns:1fr;}} .hero h1{{font-size:26px;}} .stats-grid{{grid-template-columns:1fr 1fr;}} }}
  @media(max-width:1024px) and (min-width:769px){{ .kpi-row{{grid-template-columns:repeat(3,1fr);}} }}

  .mgmt-filters {{ max-width:1100px; margin:0 auto 20px; padding:0 20px; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }}
  .mgmt-filter {{ background:var(--white); border:1px solid var(--border); padding:6px 14px; border-radius:8px; cursor:pointer; font-size:12px; font-family:inherit; color:var(--text-secondary); transition:all .2s; }}
  .mgmt-filter:hover {{ border-color:var(--teal); }}
  .mgmt-filter.active {{ background:var(--navy); color:#fff; border-color:var(--navy); }}
  #mgmt-search {{ padding:6px 14px; border:1px solid var(--border); border-radius:8px; font-size:12px; font-family:inherit; width:200px; margin-left:auto; }}
  .mgmt-timeline {{ max-width:1100px; margin:0 auto; padding:0 20px; }}
  .mgmt-year-block {{ margin-bottom:24px; }}
  .mgmt-year-header {{ background:linear-gradient(135deg,var(--navy),var(--slate)); color:#fff; padding:14px 20px; border-radius:12px 12px 0 0; cursor:pointer; display:flex; justify-content:space-between; align-items:center; }}
  .mgmt-year-header .year {{ font-size:20px; font-weight:700; color:var(--teal-light); }}
  .mgmt-year-header .title {{ font-size:13px; color:rgba(255,255,255,.7); }}
  .mgmt-year-header .toggle {{ font-size:18px; transition:transform .2s; }}
  .mgmt-year-body {{ background:var(--white); border:1px solid var(--border); border-top:none; border-radius:0 0 12px 12px; padding:20px; display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .mgmt-year-body.collapsed {{ display:none; }}
  .mgmt-dim {{ padding:12px; border-radius:8px; }}
  .mgmt-dim.highlights {{ background:#E6F5F3; border-left:3px solid var(--teal); }}
  .mgmt-dim.market {{ background:#E3F2FD; border-left:3px solid #1565C0; }}
  .mgmt-dim.outlook {{ background:#E8F5E9; border-left:3px solid var(--green); }}
  .mgmt-dim.risks {{ background:#FDE8EC; border-left:3px solid var(--red); }}
  .mgmt-dim h4 {{ font-size:13px; margin-bottom:8px; color:var(--navy); }}
  .mgmt-dim li {{ font-size:13px; line-height:1.8; color:var(--text); margin-bottom:4px; padding-left:4px; }}
  .mgmt-dim li.hidden {{ display:none; }}
  .mgmt-dim li.match {{ background:#FFEB3B40; border-radius:4px; padding:2px 6px; }}
  @media(max-width:768px){{ .mgmt-year-body {{ grid-template-columns:1fr; }} .mgmt-filters {{ flex-direction:column; }} #mgmt-search {{ width:100%; margin-left:0; }} }}
</style>
</head>
<body>
<header class="hero">
  <h1>腾讯控股 财务分析报告</h1>
  <div class="sub">2004—2025 跨越 22 年上市历程 ｜ 官方年报 / 中期 / 季度业绩公告 ｜ 生成日期：2026-07-10</div>
</header>

<div class="kpi-row">
  <div class="kpi-card"><div class="label">{latest_year}年 营业收入</div><div class="value">{kpi_rev:,.0f}<span class="unit"> 亿</span></div><div class="change {'up' if rev_growth_latest and rev_growth_latest>=0 else 'down'}">{'↑' if rev_growth_latest and rev_growth_latest>=0 else '↓'} {abs(rev_growth_latest):.1f}%</div></div>
  <div class="kpi-card"><div class="label">{latest_year}年 归母净利润</div><div class="value">{kpi_attr:,.0f}<span class="unit"> 亿</span></div><div class="change {'up' if attr_growth_latest and attr_growth_latest>=0 else 'down'}">{'↑' if attr_growth_latest and attr_growth_latest>=0 else '↓'} {abs(attr_growth_latest):.1f}%</div></div>
  <div class="kpi-card"><div class="label">{latest_year}年 Non-GAAP归母净利润</div><div class="value">{kpi_nifrs:,.0f}<span class="unit"> 亿</span></div><div class="change" style="color:var(--text-secondary)">剔除股份酬金/减值等口径</div></div>
  <div class="kpi-card"><div class="label">{latest_year}年 总资产</div><div class="value">{kpi_ta:,.0f}<span class="unit"> 亿</span></div><div class="change" style="color:var(--text-secondary)">净资产 {kpi_na:,.0f} 亿</div></div>
  <div class="kpi-card"><div class="label">{latest_year}年 ROE（估算）</div><div class="value">{kpi_roe:.1f}<span class="unit">%</span></div><div class="change {'up' if roe_chg and roe_chg>=0 else 'down'}">{('↑' if roe_chg>=0 else '↓') + f' {abs(roe_chg):.1f}pp' if roe_chg is not None else '归母净利/期初期末净资产均值'}</div></div>
</div>

<div class="stats-grid">
  <div class="stat-card"><div class="n">22年</div><div class="l">数据跨度（2004上市至今）</div></div>
  <div class="stat-card"><div class="n">22年</div><div class="l">完整年报数据</div></div>
  <div class="stat-card"><div class="n">70+份</div><div class="l">PDF 财报</div></div>
  <div class="stat-card"><div class="n">{rev_multiple}倍</div><div class="l">营收增长（2004→2025）</div></div>
</div>

<div class="nav-bar">
  <button class="active" id="btn-overview">📈 22年全景</button>
  <button id="btn-core">📊 核心指标</button>
  <button id="btn-revenue">💼 收入结构</button>
  <button id="btn-returns">💎 股东回报</button>
  <button id="btn-growth">🚀 增长分析</button>
  <button id="btn-quality">💰 利润质量</button>
  <button id="btn-cashflow">🌊 现金流</button>
  <button id="btn-cfquality">💧 现金流质量</button>
  <button id="btn-quarterly">📅 季度追踪</button>
  <button id="btn-detail">📋 数据明细</button>
  <button id="btn-mgmt">💬 管理层观点</button>
</div>

<div class="section active" id="sec-overview">
  <div class="summary-box"><h3>📌 22年增长传奇</h3><p>腾讯控股自 2004 年在香港联交所主板上市以来，营业收入从 <span class="hl">11.4 亿元</span> 增长至 2025 年的 <span class="hl">7,518 亿元</span>，增长约 <span class="hl">{rev_multiple} 倍</span>；归母净利润从 <span class="hl">4.4 亿元</span> 增长至 <span class="hl">2,248 亿元</span>。期间经历了2004-2010门户与增值服务黄金期、2011微信诞生开启移动互联网时代、2014京东换股完成电商转型、2018组织架构"930变革"、2021-2022反垄断监管与降本增效、2023-2025视频号与AI驱动的新一轮增长周期。</p></div>
  <div class="chart-row single full"><div class="chart-block"><h3>营业收入：22年增长曲线（2004—2025，亿元）</h3><canvas id="chart_rev22"></canvas></div></div>
  <div class="chart-row">
    <div class="chart-block"><h3>营收同比增速（%）</h3><canvas id="chart_revg"></canvas></div>
    <div class="chart-block"><h3>归母净利润趋势（2004—2025，亿元）</h3><canvas id="chart_profit"></canvas></div>
  </div>
</div>

<div class="section" id="sec-core">
  <div class="chart-row"><div class="chart-block"><h3>营业收入（亿元）</h3><canvas id="chart_rev_core"></canvas></div><div class="chart-block"><h3>归母净利润（亿元）</h3><canvas id="chart_profit_core"></canvas></div></div>
  <div class="chart-row"><div class="chart-block"><h3>总资产 vs 归母净资产（亿元）</h3><canvas id="chart_ae"></canvas></div><div class="chart-block"><h3>资产负债率 & ROA（%，估算）</h3><canvas id="chart_dar"></canvas></div></div>
</div>

<div class="section" id="sec-revenue">
  <div class="summary-box"><h3>📌 收入结构 22 年变迁</h3><p>腾讯的收入引擎经历了三次切换：上市初期靠<span class="hl">移动增值服务（SP业务）</span>；2006 年起 <span class="hl">互联网增值服务（游戏+社交）</span>接棒成为绝对主力，占比一度超过 80%；2019 年单独披露的 <span class="hl">金融科技及企业服务</span> 已成长为第二大分部（2025 年占比约 31%），叠加广告（营销服务）复苏，收入结构显著多元化。注：2004—2012 年"增值服务"为 IVAS+MVAS 合并口径，与 2013 年后可比；2013—2014 年含电商分部（后并入京东）。</p></div>
  <div class="chart-row single full"><div class="chart-block"><h3>分部收入堆叠（2004—2025，亿元）</h3><canvas id="chart_seg_abs"></canvas></div></div>
  <div class="chart-row single full"><div class="chart-block"><h3>分部收入占比（2004—2025，%）</h3><canvas id="chart_seg_pct"></canvas></div></div>
</div>

<div class="section" id="sec-returns">
  <div class="chart-row"><div class="chart-block"><h3>每股收益 EPS（元，已按2014年5股拆1股调整）</h3><canvas id="chart_eps"></canvas></div><div class="chart-block"><h3>净资产收益率 ROE（%，估算＝归母净利润/期初期末净资产均值）</h3><canvas id="chart_roe"></canvas></div></div>
  <div class="chart-row"><div class="chart-block"><h3>末期股息 DPS（港元/股，2013年前已按拆股调整；2008/2013含特别股息）</h3><canvas id="chart_dps"></canvas></div><div class="chart-block"><h3>ROE vs 归母净利率 双轴对比（%）</h3><canvas id="chart_roe_npm"></canvas></div></div>
</div>

<div class="section" id="sec-growth">
  <div class="chart-row"><div class="chart-block"><h3>营收 & 归母净利润 同比增速（%）</h3><canvas id="chart_rpg"></canvas></div><div class="chart-block"><h3>毛利率 & 归母净利率走势（%）</h3><canvas id="chart_margin"></canvas></div></div>
</div>

<div class="section" id="sec-quality">
  <div class="chart-row single full"><div class="chart-block"><h3>IFRS 归母净利润 vs Non-GAAP 归母净利润（亿元，2011年起披露）</h3><canvas id="chart_ifrs_nifrs"></canvas></div></div>
  <div class="chart-row single full"><div class="chart-block"><h3>IFRS 经营利润 vs Non-GAAP 经营利润（亿元；2019-2022 为重列口径，剔除投资相关损益）</h3><canvas id="chart_op_cmp"></canvas></div></div>
  <div class="chart-row"><div class="chart-block"><h3>经营利润（IFRS，亿元）</h3><canvas id="chart_op"></canvas></div><div class="chart-block"><h3>毛利润（亿元）</h3><canvas id="chart_gross"></canvas></div></div>
</div>

<div class="section" id="sec-cashflow">
  <div class="summary-box"><h3>📌 现金流与资本开支</h3><p>自由现金流（FCF）为公司自行披露口径：经营活动现金流减去资本开支、媒体内容开支及租赁负债付款。年度 FCF 为四个季度加总（估算）。<span class="hl">2024 年起资本开支跳升至 768 亿元、2025 年达 792 亿元</span>，主要投向 AI 算力与数据中心基础设施——这是当前腾讯财务叙事的核心变量：Capex 高企但核心业务现金创造能力仍在增强。</p></div>
  <div class="chart-row single full"><div class="chart-block"><h3>季度自由现金流 & 资本开支（2019Q1—2026Q1，亿元）</h3><canvas id="chart_fc_q"></canvas></div></div>
  <div class="chart-row"><div class="chart-block"><h3>年度自由现金流 vs 归母净利润（亿元，FCF为四季加总估算）</h3><canvas id="chart_fcf_np"></canvas></div><div class="chart-block"><h3>年度资本开支（亿元，官方全年披露值）</h3><canvas id="chart_capex_fy"></canvas></div></div>
</div>

<div class="section" id="sec-cfquality">
  <div class="summary-box"><h3>📌 利润含金量：赚的是不是真钱</h3><p>利润表可以修饰，现金流量表很难。核心结论：<span class="hl">腾讯自 2005 年起，经营活动现金流连续 21 年为正且几乎每年都高于净利润</span>——2004 年（上市当年）是唯一的负值。<br><br><b>⚠️ 一个重要的口径说明：收现比无法计算。</b>A 股中国会计准则要求用<b>直接法</b>披露「销售商品、提供劳务收到的现金」，可直接算收现比；腾讯按 IFRS 用<b>间接法</b>编制现金流量表，从税前利润倒推，报表中<b>根本不存在该科目</b>。因此这里改用<b>净现比（经营现金流÷净利润）</b>作为主要含金量指标，并同时给出 IFRS 与 Non-GAAP 两个口径。</p></div>
  <div class="chart-row single full"><div class="chart-block"><h3>经营活动现金流 vs 净利润（亿元）——两线贴合说明利润有现金支撑</h3><canvas id="chart_cfq_ocf"></canvas></div></div>
  <div class="chart-row single full"><div class="chart-block"><h3>净现比双口径对比（%，100% 为界）——IFRS 的剧烈波动是分母失真，非现金流恶化</h3><canvas id="chart_cfq_ncr"></canvas></div></div>
  <div class="chart-row"><div class="chart-block"><h3>现金去向：自由现金流 / 资本开支 / 股东回报（亿元）</h3><canvas id="chart_cfq_use"></canvas></div><div class="chart-block"><h3>现金余额 vs 有息负债（亿元）</h3><canvas id="chart_cfq_debt"></canvas></div></div>
  <div class="chart-block"><h3>📋 现金流质量明细（2004—2025，亿元）</h3><div class="table-scroll"><table class="data-table"><thead><tr><th>年份</th><th>经营现金流</th><th>归母净利润</th><th>净现比(IFRS)</th><th>净现比(Non-GAAP)</th><th>资本开支</th><th>自由现金流</th><th>分红</th><th>回购</th><th>现金余额</th><th>有息负债</th></tr></thead><tbody>{cfq_rows_html}</tbody></table></div>
    <div style="font-size:12px;color:var(--text-secondary);line-height:1.9;margin-top:12px">
      <b>口径说明（务必阅读）：</b><br>
      · <b>收现比不可计算</b>：IFRS 间接法不披露「销售商品、提供劳务收到的现金」，与 A 股直接法报表无法对齐。<br>
      · <b>资本开支</b>＝现金流量表「购建物业设备及器材/在建工程/投资物业」＋「购买无形资产」，与公司在业绩公告中自行定义的 capital expenditures（含数据中心、土地使用权等）口径不同，故本表 2025 年为 1,129 亿，公司口径为 792 亿。<br>
      · <b>自由现金流</b>＝经营现金流 − 上述资本开支，未扣除媒体内容开支与租赁负债本金，故高于公司披露的 FCF（2025 年公司口径 1,826 亿）。<br>
      · <b>现金余额</b>仅为「现金及现金等价物」，不含定期存款。2025 年另有定期存款 3,071 亿，故账面虽有 3,877 亿有息负债，加回定期存款后仍为<b>净现金约 604 亿</b>。<br>
      · <b>单位换算</b>：2004—2012 年报以人民币千元列示，已统一折算为百万元再转亿元。<br>
      · <b>两处公司重新列报</b>：2007 年 OCF 原报 15.4 亿、2008 年报重列为 18.4 亿；2018 年原报 1,064 亿、2019 年报重新列报为 1,109 亿。本表采用各年年报<b>当年原始披露值</b>。<br>
      · 数据来源：2004—2025 各年度年报现金流量表与综合财务状况表原文提取，逐年勾稽校验（21 组对照中 19 组完全一致，2 组差异即上述公司重列）。
    </div>
  </div>
</div>

<div class="section" id="sec-quarterly">
  <div class="chart-row single full"><div class="chart-block"><h3>季度营收追踪（2019—2026，亿元）</h3><canvas id="chart_q_rev"></canvas></div></div>
  <div class="chart-row single full"><div class="chart-block"><h3>季度归母净利润追踪（IFRS，亿元；Q2 由中期报减一季报推算）</h3><canvas id="chart_q_attr"></canvas></div></div>
</div>

<div class="section" id="sec-detail">
  <div class="chart-block"><h3>📋 全部年报数据（2004—2025，亿元/元）</h3><div class="table-scroll"><table class="data-table"><thead><tr><th>年份</th><th>营业收入</th><th>毛利润</th><th>经营利润</th><th>归母净利润</th><th>Non-GAAP归母净利</th><th>基本EPS(元)</th><th>总资产</th><th>归母净资产</th><th>ROE(估算)</th><th>同比</th></tr></thead><tbody>{detail_rows_html}</tbody></table></div></div>
  <div class="chart-block"><h3>📋 半年报数据（2004—2025，亿元/元）</h3><div class="table-scroll"><table class="data-table"><thead><tr><th>报告期</th><th>营业收入</th><th>毛利润</th><th>经营利润</th><th>归母净利润</th><th>基本EPS(元)</th></tr></thead><tbody>{interim_rows_html}</tbody></table></div></div>
  <div class="chart-block"><h3>📋 季度数据（2019—2026，亿元）</h3><div class="table-scroll"><table class="data-table"><thead><tr><th>期间</th><th>营收</th><th>归母净利润</th></tr></thead><tbody>{quarter_rows_html}</tbody></table></div></div>
  <div class="chart-block"><h3>📋 补充指标（2004—2025，亿元/港元）</h3><div class="table-scroll"><table class="data-table"><thead><tr><th>年份</th><th>增值服务</th><th>广告/营销服务</th><th>金融科技及企服</th><th>电商</th><th>其他</th><th>FCF(估算)</th><th>Capex</th><th>DPS(港元)</th><th>Non-GAAP经营利润</th></tr></thead><tbody>{supp_rows_html}</tbody></table></div></div>
</div>

<div class="section" id="sec-mgmt">
  <div class="summary-box">
    <h3>📌 管理层观点时间轴</h3>
    <p>基于历年年度报告<span class="hl">"主席报告 / Chairman's Statement / 业务回顾与展望"</span>原文，从业务亮点、市场环境、展望目标和风险挑战四个维度提炼管理层核心判断。覆盖 <span class="hl">2004—2025</span> 共 {len(MGMT)} 个关键转折年份。</p>
  </div>

  <div class="mgmt-filters">
    <button class="mgmt-filter active" data-dim="all">全部</button>
    <button class="mgmt-filter" data-dim="highlights">🔆 业务亮点</button>
    <button class="mgmt-filter" data-dim="market">📊 市场环境</button>
    <button class="mgmt-filter" data-dim="outlook">🎯 展望目标</button>
    <button class="mgmt-filter" data-dim="risks">⚠️ 风险挑战</button>
    <input type="text" id="mgmt-search" placeholder="🔍 搜索关键词..." />
  </div>

  <div class="mgmt-timeline" id="mgmt-timeline"></div>
</div>

<footer class="footer"><p>腾讯控股财务分析报告 ｜ 2004—2025 ｜ AI 辅助生成 ｜ 数据来源：香港联交所披露易 / 腾讯投资者关系官网公开年报、中期报告及季度业绩公告 PDF ｜ 仅供参考，不构成投资建议</p></footer>

<script>
const REV_Y = {js([str(y) for y in YEARS])};
const REV_V = {js(REV)};
const GROSS_V = {js(GROSS)};
const OP_V = {js(OP)};
const ATTR_V = {js(ATTR)};
const NIFRS_V = {js(NIFRS)};
const TA_V = {js(TA)};
const NA_V = {js(NA)};
const EPS_V = {js(EPS)};
const ROE_V = {js(ROE)};
const ROA_V = {js(ROA)};
const DPS_V = {js(DPS)};
const NIFRS_OP_V = {js(NIFRS_OP)};
const SEG_VAS = {js(SEG_VAS)};
const SEG_ADS = {js(SEG_ADS)};
const SEG_FINTECH = {js(SEG_FINTECH)};
const SEG_ECOM = {js(SEG_ECOM)};
const SEG_OTHERS = {js(SEG_OTHERS)};
const SEG_VAS_PCT = {js(SEG_VAS_PCT)};
const SEG_ADS_PCT = {js(SEG_ADS_PCT)};
const SEG_FINTECH_PCT = {js(SEG_FINTECH_PCT)};
const SEG_ECOM_PCT = {js(SEG_ECOM_PCT)};
const SEG_OTHERS_PCT = {js(SEG_OTHERS_PCT)};
const FC_LABELS = {js(FC_LABELS)};
const FC_FCF = {js(FC_FCF)};
const FC_CAPEX = {js(FC_CAPEX)};
const FCF_FY = {js(FCF_FY)};
const CAPEX_FY = {js(CAPEX_FY)};
const OCF_V = {js(OCF)};
const CAPEX_CF_V = {js(CAPEX_CF)};
const FCF_CF_V = {js(FCF_CF)};
const DIVIDEND_V = {js(DIVIDEND)};
const BUYBACK_V = {js(BUYBACK)};
const SHRET_V = {js(SHAREHOLDER_RET)};
const CASH_BAL_V = {js(CASH_BAL)};
const DEBT_V = {js(DEBT)};
const NCR_IFRS_V = {js(NCR_IFRS)};
const NCR_NG_V = {js(NCR_NG)};
const REV_G = {js(REV_G)};
const ATTR_G = {js(ATTR_G)};
const GROSS_MARGIN = {js(GROSS_MARGIN)};
const NET_MARGIN = {js(NET_MARGIN)};
const DEBT_RATIO = {js(DEBT_RATIO)};

const Q_LABELS = {js(quarter_labels)};
const Q_REV = {js(quarter_rev)};
const Q_ATTR = {js(quarter_attr)};

var C = ['#006D77','#E29578','#1B2A4A','#83C5BE','#9467bd','#00b894','#e17055','#fd79a8'];
var cr = {{}};

function showTab(id) {{
  document.querySelectorAll('.section').forEach(function(s) {{ s.classList.remove('active'); }});
  document.querySelectorAll('.nav-bar button').forEach(function(b) {{ b.classList.remove('active'); }});
  document.getElementById('sec-' + id).classList.add('active');
  document.getElementById('btn-' + id).classList.add('active');
  if (!cr[id]) {{ cr[id] = true;
    var f = {{ overview: initOverview, core: initCore, revenue: initRevenue, returns: initReturns, growth: initGrowth, quality: initQuality, cashflow: initCashflow, cfquality: initCfQuality, quarterly: initQuarterly, mgmt: initMgmtTimeline }};
    if (f[id]) f[id]();
  }}
}}

['overview','core','revenue','returns','growth','quality','cashflow','cfquality','quarterly','detail','mgmt'].forEach(function(id) {{
  document.getElementById('btn-' + id).addEventListener('click', function() {{ showTab(id); }});
}});

function initOverview() {{
  new Chart(document.getElementById('chart_rev22'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [{{ label: '营业收入(亿)', data: REV_V, borderColor: C[0], backgroundColor: C[0] + '15', fill: true, tension: 0.2, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2 }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ title: {{ display: true, text: '亿元' }} }} }} }}
  }});
  new Chart(document.getElementById('chart_revg'), {{ type: 'bar',
    data: {{ labels: REV_Y.slice(1), datasets: [{{ label: '营收增速%', data: REV_G.slice(1), backgroundColor: REV_G.slice(1).map(function(v) {{ return v >= 0 ? C[0] + '99' : C[1] + '99'; }}) }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ title: {{ display: true, text: '增长率%' }} }} }} }}
  }});
  new Chart(document.getElementById('chart_profit'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [{{ label: '归母净利润(亿)', data: ATTR_V, borderColor: C[1], backgroundColor: C[1] + '15', fill: true, tension: 0.3, pointRadius: 3, borderWidth: 2 }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ title: {{ display: true, text: '亿元' }} }} }} }}
  }});
}}

function initCore() {{
  new Chart(document.getElementById('chart_rev_core'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [{{ label: '营业收入(亿)', data: REV_V, borderColor: C[0], backgroundColor: C[0] + '15', fill: true, tension: 0.3, pointRadius: 3, borderWidth: 2 }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
  new Chart(document.getElementById('chart_profit_core'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [{{ label: '归母净利润(亿)', data: ATTR_V, borderColor: C[1], backgroundColor: C[1] + '15', fill: true, tension: 0.3, pointRadius: 3, borderWidth: 2 }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
  new Chart(document.getElementById('chart_ae'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [{{ label: '总资产', data: TA_V, backgroundColor: C[2] + '99' }},{{ label: '归母净资产', data: NA_V, backgroundColor: C[3] + '99' }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }} }}
  }});
  new Chart(document.getElementById('chart_dar'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [
      {{ label: '资产负债率%', data: DEBT_RATIO, borderColor: C[1], tension: 0.3, pointRadius: 3, fill: false, borderWidth: 2 }},
      {{ label: 'ROA%（归母净利/总资产均值）', data: ROA_V, borderColor: C[0], tension: 0.3, pointRadius: 3, fill: false, borderWidth: 2, borderDash: [5,5] }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }} }}
  }});
}}

function initRevenue() {{
  var segDs = [
    {{ label: '增值服务', data: SEG_VAS, backgroundColor: C[0] + 'CC' }},
    {{ label: '广告/营销服务', data: SEG_ADS, backgroundColor: C[1] + 'CC' }},
    {{ label: '金融科技及企业服务', data: SEG_FINTECH, backgroundColor: C[3] + 'CC' }},
    {{ label: '电子商务', data: SEG_ECOM, backgroundColor: C[4] + 'CC' }},
    {{ label: '其他', data: SEG_OTHERS, backgroundColor: '#B0BEC5CC' }}
  ];
  new Chart(document.getElementById('chart_seg_abs'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: segDs }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, title: {{ display: true, text: '亿元' }} }} }} }}
  }});
  var segPctDs = [
    {{ label: '增值服务', data: SEG_VAS_PCT, backgroundColor: C[0] + 'CC' }},
    {{ label: '广告/营销服务', data: SEG_ADS_PCT, backgroundColor: C[1] + 'CC' }},
    {{ label: '金融科技及企业服务', data: SEG_FINTECH_PCT, backgroundColor: C[3] + 'CC' }},
    {{ label: '电子商务', data: SEG_ECOM_PCT, backgroundColor: C[4] + 'CC' }},
    {{ label: '其他', data: SEG_OTHERS_PCT, backgroundColor: '#B0BEC5CC' }}
  ];
  new Chart(document.getElementById('chart_seg_pct'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: segPctDs }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, max: 100, title: {{ display: true, text: '%' }} }} }} }}
  }});
}}

function initCashflow() {{
  new Chart(document.getElementById('chart_fc_q'), {{ type: 'bar',
    data: {{ labels: FC_LABELS, datasets: [
      {{ label: '自由现金流(亿)', data: FC_FCF, backgroundColor: C[0] + '99' }},
      {{ label: '资本开支(亿)', data: FC_CAPEX, backgroundColor: C[1] + '99' }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ x: {{ ticks: {{ maxRotation: 90, minRotation: 60, font: {{ size: 9 }} }} }} }} }}
  }});
  new Chart(document.getElementById('chart_fcf_np'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [
      {{ label: '年度FCF(亿,估算)', data: FCF_FY, backgroundColor: C[0] + '99' }},
      {{ label: '归母净利润(亿)', data: ATTR_V, type: 'line', borderColor: C[1], tension: 0.3, pointRadius: 3, borderWidth: 2 }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }} }}
  }});
  new Chart(document.getElementById('chart_capex_fy'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [{{ label: '资本开支(亿)', data: CAPEX_FY, backgroundColor: C[1] + '99' }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
}}

function initGrowth() {{
  new Chart(document.getElementById('chart_rpg'), {{ type: 'bar',
    data: {{ labels: REV_Y.slice(1), datasets: [{{ label: '营收增速%', data: REV_G.slice(1), backgroundColor: C[0] + '99' }},{{ label: '归母净利润增速%', data: ATTR_G.slice(1), backgroundColor: C[1] + '99' }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }} }}
  }});
  new Chart(document.getElementById('chart_margin'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [
      {{ label: '毛利率%', data: GROSS_MARGIN, borderColor: C[3], tension: 0.3, pointRadius: 3, borderWidth: 2 }},
      {{ label: '归母净利率%', data: NET_MARGIN, borderColor: C[1], tension: 0.3, pointRadius: 3, borderWidth: 2, borderDash: [5,5] }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }} }}
  }});
}}

function initReturns() {{
  new Chart(document.getElementById('chart_eps'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [{{ label: 'EPS(元)', data: EPS_V, backgroundColor: C[4] + '99' }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
  new Chart(document.getElementById('chart_roe'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [{{ label: 'ROE%', data: ROE_V, borderColor: C[1], backgroundColor: C[1] + '15', fill: true, tension: 0.3, pointRadius: 3, borderWidth: 3 }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
  new Chart(document.getElementById('chart_dps'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [{{ label: 'DPS(港元)', data: DPS_V, backgroundColor: C[3] + 'CC' }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
  new Chart(document.getElementById('chart_roe_npm'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [
      {{ label: 'ROE%', data: ROE_V, borderColor: C[1], tension: 0.3, pointRadius: 4, borderWidth: 3, yAxisID: 'y' }},
      {{ label: '归母净利率%', data: NET_MARGIN, borderColor: C[0], tension: 0.3, pointRadius: 4, borderWidth: 2, yAxisID: 'y1', borderDash: [5,5] }}
    ] }},
    options: {{ responsive: true, scales: {{ y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'ROE%' }} }}, y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: '归母净利率%' }}, grid: {{ drawOnChartArea: false }} }} }}, plugins: {{ legend: {{ position: 'top' }} }} }}
  }});
}}

function initQuality() {{
  new Chart(document.getElementById('chart_ifrs_nifrs'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [
      {{ label: 'IFRS归母净利润(亿)', data: ATTR_V, borderColor: C[1], tension: 0.3, pointRadius: 3, borderWidth: 3 }},
      {{ label: 'Non-GAAP归母净利润(亿)', data: NIFRS_V, borderColor: C[0], tension: 0.3, pointRadius: 3, borderWidth: 2, borderDash: [5,5], spanGaps: true }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ y: {{ title: {{ display: true, text: '亿元' }} }} }} }}
  }});
  new Chart(document.getElementById('chart_op_cmp'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [
      {{ label: 'IFRS经营利润(亿)', data: OP_V, borderColor: C[2], tension: 0.3, pointRadius: 3, borderWidth: 3 }},
      {{ label: 'Non-GAAP经营利润(亿)', data: NIFRS_OP_V, borderColor: C[0], tension: 0.3, pointRadius: 3, borderWidth: 2, borderDash: [5,5], spanGaps: true }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ y: {{ title: {{ display: true, text: '亿元' }} }} }} }}
  }});
  new Chart(document.getElementById('chart_op'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [{{ label: '经营利润(亿)', data: OP_V, backgroundColor: C[2] + '99' }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
  new Chart(document.getElementById('chart_gross'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [{{ label: '毛利润(亿)', data: GROSS_V, backgroundColor: C[3] + '99' }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
  }});
}}

function initCfQuality() {{
  new Chart(document.getElementById('chart_cfq_ocf'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [
      {{ label: '经营活动现金流净额(亿)', data: OCF_V, borderColor: C[0], tension: 0.2, pointRadius: 3, borderWidth: 3, spanGaps: true }},
      {{ label: 'IFRS归母净利润(亿)', data: ATTR_V, borderColor: C[1], borderDash: [6,4], tension: 0.2, pointRadius: 3, borderWidth: 2 }},
      {{ label: 'Non-GAAP归母净利润(亿)', data: NIFRS_V, borderColor: C[3], borderDash: [2,3], tension: 0.2, pointRadius: 3, borderWidth: 2, spanGaps: true }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ y: {{ title: {{ display: true, text: '亿元' }} }} }} }}
  }});
  new Chart(document.getElementById('chart_cfq_ncr'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [
      {{ label: '净现比 IFRS口径%', data: NCR_IFRS_V, backgroundColor: NCR_IFRS_V.map(function(v) {{ return (v!==null&&v>=100) ? C[2]+'99' : '#C6282899'; }}) }},
      {{ label: '净现比 Non-GAAP口径%', data: NCR_NG_V, backgroundColor: C[0]+'CC' }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }},
      scales: {{ y: {{ title: {{ display: true, text: '净现比 %' }}, suggestedMin: 0 }} }} }}
  }});
  new Chart(document.getElementById('chart_cfq_use'), {{ type: 'bar',
    data: {{ labels: REV_Y, datasets: [
      {{ label: '自由现金流(亿)', data: FCF_CF_V, backgroundColor: C[0]+'99' }},
      {{ label: '资本开支(亿)', data: CAPEX_CF_V, backgroundColor: C[1]+'99' }},
      {{ label: '股东回报 分红+回购(亿)', data: SHRET_V, backgroundColor: C[3]+'99' }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ y: {{ title: {{ display: true, text: '亿元' }} }} }} }}
  }});
  new Chart(document.getElementById('chart_cfq_debt'), {{ type: 'line',
    data: {{ labels: REV_Y, datasets: [
      {{ label: '现金及等价物(亿)', data: CASH_BAL_V, borderColor: C[0], tension: 0.2, pointRadius: 3, borderWidth: 3, spanGaps: true }},
      {{ label: '有息负债(亿)', data: DEBT_V, borderColor: C[1], tension: 0.2, pointRadius: 3, borderWidth: 2, spanGaps: true }}
    ] }},
    options: {{ responsive: true, plugins: {{ legend: {{ position: 'top' }} }}, scales: {{ y: {{ title: {{ display: true, text: '亿元' }} }} }} }}
  }});
}}

function initQuarterly() {{
  new Chart(document.getElementById('chart_q_rev'), {{ type: 'bar',
    data: {{ labels: Q_LABELS, datasets: [{{ label: '季度营收(亿)', data: Q_REV, backgroundColor: C[0] + '99' }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ ticks: {{ maxRotation: 90, minRotation: 60, font: {{ size: 9 }} }} }} }} }}
  }});
  new Chart(document.getElementById('chart_q_attr'), {{ type: 'bar',
    data: {{ labels: Q_LABELS, datasets: [{{ label: '季度归母净利润(亿)', data: Q_ATTR, backgroundColor: Q_ATTR.map(function(v) {{ return (v===null||v>=0) ? C[1]+'99' : '#C6282899'; }}) }}] }},
    options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ ticks: {{ maxRotation: 90, minRotation: 60, font: {{ size: 9 }} }} }} }} }}
  }});
}}

var MGMT = {json.dumps(MGMT, ensure_ascii=False)};
var mgmtFilter = 'all';

function initMgmtTimeline() {{ renderMgmt(); }}

function renderMgmt() {{
  var html = '';
  var years = Object.keys(MGMT).sort().reverse();
  var searchTerm = (document.getElementById('mgmt-search') || {{}}).value || '';

  years.forEach(function(year) {{
    var d = MGMT[year];
    var summary = '';
    if (d.highlights && d.highlights.length) summary += d.highlights[0].substring(0, 30) + '... ';

    html += '<div class="mgmt-year-block">';
    html += '<div class="mgmt-year-header" onclick="toggleYear(this)">';
    html += '<div><span class="year">' + year + '</span><span class="title">  ' + summary + '</span></div>';
    html += '<span class="toggle">▼</span></div>';
    html += '<div class="mgmt-year-body">';

    var dims = [
      {{ key: 'highlights', label: '🔆 业务亮点与战略方向', cls: 'highlights' }},
      {{ key: 'market', label: '📊 市场环境与竞争判断', cls: 'market' }},
      {{ key: 'outlook', label: '🎯 展望与目标', cls: 'outlook' }},
      {{ key: 'risks', label: '⚠️ 风险与挑战', cls: 'risks' }}
    ];

    dims.forEach(function(dim) {{
      if (mgmtFilter !== 'all' && mgmtFilter !== dim.key) return;
      var items = d[dim.key] || [];
      html += '<div class="mgmt-dim ' + dim.cls + '"><h4>' + dim.label + '</h4><ul>';
      items.forEach(function(item) {{
        var cls = '';
        if (searchTerm && item.indexOf(searchTerm) >= 0) cls = ' match';
        else if (searchTerm) cls = ' hidden';
        html += '<li class="' + cls + '">' + item + '</li>';
      }});
      html += '</ul></div>';
    }});

    html += '</div></div>';
  }});

  document.getElementById('mgmt-timeline').innerHTML = html;
}}

function toggleYear(header) {{
  var body = header.nextElementSibling;
  var toggle = header.querySelector('.toggle');
  body.classList.toggle('collapsed');
  toggle.textContent = body.classList.contains('collapsed') ? '▶' : '▼';
}}

document.addEventListener('click', function(e) {{
  if (e.target.classList.contains('mgmt-filter')) {{
    document.querySelectorAll('.mgmt-filter').forEach(function(b) {{ b.classList.remove('active'); }});
    e.target.classList.add('active');
    mgmtFilter = e.target.dataset.dim;
    renderMgmt();
  }}
}});

document.addEventListener('input', function(e) {{
  if (e.target.id === 'mgmt-search') {{
    renderMgmt();
    if (e.target.value) {{
      document.querySelectorAll('.mgmt-year-body').forEach(function(b) {{
        if (b.querySelector('.match')) b.classList.remove('collapsed');
      }});
    }}
  }}
}});

window.addEventListener('load', function() {{ cr['overview'] = true; initOverview(); }});
</script>
</body>
</html>
'''

out_path = os.path.join(ROOT, '腾讯控股_财务分析报告.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('written', out_path, len(html), 'bytes')
