#!/usr/bin/env python3
"""
腾讯控股 (00700.HK) 财务数据分析工具
年度数据来自官方季报/年报（已核实），季度数据从PDF自动提取
输出: 财务分析报告.html, 财务分析报告.md, 财务数据.xlsx, charts/
"""

import os, re, json, sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 配置
# ============================================================
def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    else:
        cfg = {}
    cfg.setdefault('company_name', '腾讯控股有限公司')
    cfg.setdefault('company_short', '腾讯')
    return cfg

CONFIG = load_config()
COMPANY = CONFIG['company_name']

# ============================================================
# 已核实的年度财务数据（人民币百万元）
# 来源：各年度 Q4 全年业绩公告 + 年报，经交叉验证
# ============================================================
KNOWN_ANNUAL = {
    2018: {'revenue': 312694, 'gross': 142120, 'op_profit':  97648,
           'net_profit':  79984, 'attr_profit':  78719, 'basic_eps':  8.336},
    2019: {'revenue': 377289, 'gross': 167533, 'op_profit': 118694,
           'net_profit':  95888, 'attr_profit':  93310, 'basic_eps':  9.856},
    2020: {'revenue': 482064, 'gross': 221532, 'op_profit': 184237,
           'net_profit': 160125, 'attr_profit': 159847, 'basic_eps': 16.844},
    2021: {'revenue': 560118, 'gross': 245944, 'op_profit': 271620,
           'net_profit': 227810, 'attr_profit': 224822, 'basic_eps': 23.597},
    2022: {'revenue': 554552, 'gross': 238746, 'op_profit': 235706,
           'net_profit': 188709, 'attr_profit': 188243, 'basic_eps': 19.757},
    2023: {'revenue': 609015, 'gross': 293109, 'op_profit': 160074,
           'net_profit': 118048, 'attr_profit': 115216, 'basic_eps': 12.186},
    2024: {'revenue': 660257, 'gross': 349246, 'op_profit': 208099,
           'net_profit': 196467, 'attr_profit': 194073, 'basic_eps': 20.938},
    2025: {'revenue': 751766, 'gross': 422593, 'op_profit': 241562,
           'net_profit': 229801, 'attr_profit': 224842, 'basic_eps': 24.749},
}

# ============================================================
# 中文字体
# ============================================================
def _detect_chinese_font():
    candidates = [
        'Heiti TC', 'STHeiti', 'PingFang HK', 'Hiragino Sans GB',
        'SimHei', 'Microsoft YaHei',
        'Noto Sans CJK SC', 'Noto Sans SC', 'WenQuanYi Micro Hei',
        'Lantinghei SC', 'Songti SC',
    ]
    available = set(f.name for f in fm.fontManager.ttflist)
    detected = [f for f in candidates if f in available]
    return detected if detected else ['sans-serif']

_chinese_fonts = _detect_chinese_font()
plt.rcParams['font.sans-serif'] = _chinese_fonts
plt.rcParams['axes.unicode_minus'] = False

COLORS = {
    'revenue':  '#1f6aa5',
    'gross':    '#2ca02c',
    'op':       '#ff7f0e',
    'net':      '#d62728',
    'eps':      '#9467bd',
    'pos':      '#2ca02c',
    'neg':      '#d62728',
}

# ============================================================
# PDF 季度数据提取
# ============================================================
def _nums(text):
    return [float(x.replace(',', '')) for x in re.findall(r'\d[\d,]*(?:\.\d+)?', text)]

def _classify_pdf(filepath):
    fn = os.path.basename(filepath)
    # 年份
    m = re.search(r'(20\d{2})', fn)
    year = int(m.group(1)) if m else None
    if year is None:
        zh = re.search(r'二零([一二三四五六七八九零]{2})年', fn)
        if zh:
            s = zh.group(1)
            mp = {'零':'0','一':'1','二':'2','三':'3','四':'4',
                  '五':'5','六':'6','七':'7','八':'8','九':'9'}
            try:
                year = 2000 + int(''.join(mp.get(c,'?') for c in s))
            except:
                pass
    if year is None:
        return None, None, 'unknown'

    fn_l = fn.lower()
    if any(k in fn for k in ['演示', '展示', 'presentation']):
        return year, None, 'skip'
    if any(k in fn for k in ['年报', '年度报告', 'annual report']) or \
       re.search(r'20\d{2}\s*financial\s*report', fn_l):
        return year, None, 'annual_report'
    if '中期' in fn or '半年' in fn:
        return year, 2, 'interim'

    q_map = {'第一季':1,'q1':1,'第二季':2,'q2':2,'第三季':3,'q3':3,'第四季':4,'q4':4}
    q = None
    for k, v in q_map.items():
        if k in fn or k in fn_l:
            q = v; break
    if q is None:
        m2 = re.search(r'Q(\d)', fn, re.I)
        if m2:
            q = int(m2.group(1))
    if q == 4:
        return year, 4, 'q4_annual'
    if q in (1,2,3):
        return year, q, 'quarterly'
    return year, None, 'unknown'

def _extract_quarterly_from_pdf(filepath, year, quarter):
    """从季报PDF提取单季度财务数据，返回 dict 或 {}"""
    try:
        from pdfplumber import open as opdf
        with opdf(filepath) as pdf:
            for pg_idx in range(min(8, len(pdf.pages))):
                text = pdf.pages[pg_idx].extract_text() or ''
                result = {}

                # 英文格式：Three months ended
                if 'Three months ended' in text or 'three months ended' in text:
                    for line in text.replace('\n','|').split('|'):
                        ns = _nums(line)
                        if not ns: continue
                        if re.search(r'^Revenues\s', line) and 'revenue' not in result:
                            result['revenue'] = ns[0]
                        elif re.search(r'^Gross profit\s', line) and 'gross' not in result:
                            result['gross'] = ns[0]
                        elif re.search(r'^Operating profit\s', line) and 'op_profit' not in result:
                            result['op_profit'] = ns[0]
                        elif re.search(r'^Profit for the period|^Profit for the year', line) and 'net_profit' not in result:
                            result['net_profit'] = ns[0]
                        elif re.search(r'^Profit attributable to equity holders', line) and 'attr_profit' not in result:
                            result['attr_profit'] = ns[0]
                        elif re.search(r'–\s*basic|– basic', line) and 'basic_eps' not in result:
                            if ns[0] < 100: result['basic_eps'] = ns[0]

                # 中文格式：三个月/三個月
                elif re.search(r'三个月|三個月|截至.*止三', text):
                    in_q = False
                    for line in text.replace('\n','|').split('|'):
                        if re.search(r'止三个月|止三個月|截至.*止三', line):
                            in_q = True
                        ns = _nums(line)
                        if not ns or not in_q: continue
                        if re.search(r'^收入\s', line) and 'revenue' not in result:
                            result['revenue'] = ns[0]
                        elif re.search(r'^毛利\s', line) and '率' not in line and 'gross' not in result:
                            result['gross'] = ns[0]
                        elif re.search(r'^[经經]营[盈盈]利\s', line) and '率' not in line and 'op_profit' not in result:
                            result['op_profit'] = ns[0]
                        elif re.search(r'^期[内內]盈利\s', line) and 'net_profit' not in result:
                            result['net_profit'] = ns[0]
                        elif re.search(r'本公司[权權]益持有人', line) and '非' not in line and 'attr_profit' not in result:
                            result['attr_profit'] = ns[0]
                        elif re.search(r'[－-]基本', line) and 'basic_eps' not in result:
                            if ns[0] < 100: result['basic_eps'] = ns[0]

                if len(result) >= 2:
                    result.update({'year': year, 'quarter': quarter,
                                   'period': f'{year}Q{quarter}'})
                    return result
    except Exception as e:
        pass
    return {}

def _extract_q4_standalone_from_pdf(filepath, year):
    """从 Q4 全年公告中提取 Q4 单季度数据（用于季度图表）"""
    try:
        from pdfplumber import opdf
    except ImportError:
        from pdfplumber import open as opdf
    try:
        with opdf(filepath) as pdf:
            for pg_idx in range(min(6, len(pdf.pages))):
                text = pdf.pages[pg_idx].extract_text() or ''
                result = {}

                # 中文综合收益表格式 4QYYYY 4QPREV YYYY PREV
                if '综合收益表' in text or '綜合收益表' in text:
                    hm = re.search(r'4Q(\d{4})\s+4Q(\d{4})', text)
                    if not hm:
                        continue
                    for line in text.replace('\n','|').split('|'):
                        ns = _nums(line)
                        if len(ns) < 2: continue
                        if re.search(r'^收入\s', line) and 'revenue' not in result:
                            result['revenue'] = ns[0]
                        elif re.search(r'^毛利\s', line) and '率' not in line and 'gross' not in result:
                            result['gross'] = ns[0]
                        elif re.search(r'^经营盈利|^經營盈利', line) and '率' not in line and 'op_profit' not in result:
                            result['op_profit'] = ns[0]
                        elif re.search(r'^期内盈利|^期內盈利', line) and 'net_profit' not in result:
                            result['net_profit'] = ns[0]
                        elif re.search(r'本公司[权权]益持有人\s', line) and '非' not in line and 'attr_profit' not in result:
                            result['attr_profit'] = ns[0]
                    if len(result) >= 2:
                        result.update({'year': year, 'quarter': 4, 'period': f'{year}Q4'})
                        return result

                # 繁体/英文：页面摘要表格
                elif any(k in text for k in ['Three months ended', 'three months ended',
                                              '截至下列日期止三個月', '截至下列日期止三个月']):
                    for line in text.replace('\n','|').split('|'):
                        ns = _nums(line)
                        if not ns: continue
                        if re.search(r'^Revenues\s|^收入\s', line) and 'revenue' not in result:
                            result['revenue'] = ns[0]
                        elif re.search(r'^Gross profit\s|^毛利\s', line) and '率' not in line and 'gross' not in result:
                            result['gross'] = ns[0]
                        elif re.search(r'^Operating profit\s|^[经經]营[盈盈]利\s', line) and '率' not in line and 'op_profit' not in result:
                            result['op_profit'] = ns[0]
                        elif re.search(r'^Profit for the (year|period)|^期[内內]盈利\s', line) and 'net_profit' not in result:
                            result['net_profit'] = ns[0]
                        elif re.search(r'^Profit attributable|本公司[权權]益持有人', line) and '非' not in line and 'attr_profit' not in result:
                            result['attr_profit'] = ns[0]
                        elif re.search(r'–\s*basic|[－-]基本', line) and 'basic_eps' not in result:
                            if ns[0] < 100: result['basic_eps'] = ns[0]
                    if len(result) >= 2:
                        result.update({'year': year, 'quarter': 4, 'period': f'{year}Q4'})
                        return result
    except Exception:
        pass
    return {}


def extract_quarterly_data():
    """扫描所有子目录，提取季度数据"""
    quarterly = {}  # (year, q) -> dict

    year_dirs = sorted([d for d in os.listdir('.')
                        if os.path.isdir(d) and re.match(r'20\d{2}', d)])
    for yd in year_dirs:
        for fn in sorted(os.listdir(yd)):
            if not fn.endswith('.pdf'):
                continue
            fp = os.path.join(yd, fn)
            year, quarter, rtype = _classify_pdf(fp)
            if rtype == 'skip' or year is None:
                continue

            if rtype == 'quarterly' and quarter in (1, 2, 3):
                d = _extract_quarterly_from_pdf(fp, year, quarter)
                if len(d) >= 3:
                    key = (year, quarter)
                    if key not in quarterly or len(d) > len(quarterly[key]):
                        quarterly[key] = d
                        print(f'  [Q{quarter}] {fn}: 收入={d.get("revenue","?")}M')

            elif rtype == 'q4_annual':
                # Q4 单季度
                d = _extract_q4_standalone_from_pdf(fp, year)
                if len(d) >= 3:
                    key = (year, 4)
                    if key not in quarterly or len(d) > len(quarterly[key]):
                        quarterly[key] = d
                        print(f'  [Q4] {fn}: Q4收入={d.get("revenue","?")}M')

    return sorted(quarterly.values(), key=lambda x: (x['year'], x['quarter']))


# ============================================================
# 主分析器
# ============================================================
class TencentAnalyzer:

    def build_annual_df(self):
        rows = []
        for yr in sorted(KNOWN_ANNUAL.keys()):
            row = {'年份': yr}
            row.update(KNOWN_ANNUAL[yr])
            rows.append(row)
        df = pd.DataFrame(rows)
        for c in ['revenue','gross','op_profit','net_profit','attr_profit','basic_eps']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        self.annual_df = df
        return df

    def build_quarterly_df(self, quarterly_rows):
        if not quarterly_rows:
            self.quarterly_df = pd.DataFrame()
            return self.quarterly_df
        df = pd.DataFrame(quarterly_rows)
        for c in ['revenue','gross','op_profit','net_profit','attr_profit','basic_eps']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.sort_values(['year','quarter']).reset_index(drop=True)
        self.quarterly_df = df
        return df

    def calc_growth(self):
        df = self.annual_df.copy()
        for c in ['revenue','gross','op_profit','net_profit','attr_profit','basic_eps']:
            if c in df.columns:
                df[f'{c}_yoy'] = df[c].pct_change() * 100
        self.growth_df = df
        return df

    # ------------------------------------------------------------------
    # 图表
    # ------------------------------------------------------------------
    def generate_charts(self):
        os.makedirs('charts', exist_ok=True)
        ann = self.annual_df
        qtr = self.quarterly_df if hasattr(self, 'quarterly_df') else pd.DataFrame()
        gdf = self.growth_df if hasattr(self, 'growth_df') else ann

        self._plot_annual_trend(ann)
        self._plot_scale_compare(ann)
        self._plot_growth_rates(gdf)
        self._plot_margins_eps(ann)
        if len(qtr) >= 4:
            self._plot_quarterly(qtr)
        print('  图表已保存到 charts/')

    def _plot_annual_trend(self, df):
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{COMPANY} 年度核心财务指标', fontsize=16, fontweight='bold')
        pairs = [
            ('revenue',    '营业收入',   COLORS['revenue']),
            ('gross',      '毛利润',     COLORS['gross']),
            ('op_profit',  '经营利润',   COLORS['op']),
            ('attr_profit','归母净利润', COLORS['net']),
        ]
        for ax, (col, label, color) in zip(axes.flatten(), pairs):
            valid = df.dropna(subset=[col])
            ax.plot(valid['年份'], valid[col]/1e4, marker='o', color=color,
                    linewidth=3, markersize=9)
            for _, r in valid.iterrows():
                ax.annotate(f'{r[col]/1e4:.0f}',
                            (r['年份'], r[col]/1e4),
                            textcoords='offset points', xytext=(0, 11),
                            ha='center', fontsize=9)
            ax.fill_between(valid['年份'], valid[col]/1e4, alpha=0.08, color=color)
            ax.set_title(f'{label}（百亿元）', fontsize=13, fontweight='bold')
            ax.set_xlabel('年份')
            ax.grid(True, alpha=0.3)
            ax.set_xticks(valid['年份'])
            ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        plt.savefig('charts/年度财务指标趋势图.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_scale_compare(self, df):
        valid = df.dropna(subset=['revenue']).copy()
        fig, ax = plt.subplots(figsize=(14, 7))
        n = len(valid)
        x = list(range(n))
        w = 0.25
        cols = [('revenue','营业收入',COLORS['revenue']),
                ('gross','毛利润',COLORS['gross']),
                ('attr_profit','归母净利润',COLORS['net'])]
        for i, (col, label, color) in enumerate(cols):
            if col not in valid.columns: continue
            vals = valid[col].fillna(0) / 1e4
            offset = (i - 1) * w
            bars = ax.bar([xi + offset for xi in x], vals,
                          width=w, label=label, color=color, alpha=0.85)
            for bar_idx, (bar, val) in enumerate(zip(bars, vals)):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width()/2,
                            bar.get_height() + 0.3,
                            f'{val:.0f}', ha='center', va='bottom', fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels([str(int(y)) for y in valid['年份']], fontsize=11)
        ax.set_ylabel('百亿元（RMB）')
        ax.set_title(f'{COMPANY} 收入与利润规模对比（百亿元）', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig('charts/收入与利润规模对比.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_growth_rates(self, df):
        fig, axes = plt.subplots(2, 2, figsize=(16, 11))
        fig.suptitle(f'{COMPANY} 年度同比增长率 (%)', fontsize=15, fontweight='bold')
        pairs = [
            ('revenue_yoy',    '营业收入增长率'),
            ('attr_profit_yoy','归母净利润增长率'),
            ('gross_yoy',      '毛利增长率'),
            ('op_profit_yoy',  '经营利润增长率'),
        ]
        for ax, (col, label) in zip(axes.flatten(), pairs):
            if col not in df.columns:
                ax.set_visible(False)
                continue
            v = df.dropna(subset=[col])
            clrs = [COLORS['pos'] if x >= 0 else COLORS['neg'] for x in v[col]]
            ax.bar(v['年份'], v[col], color=clrs, alpha=0.85, width=0.6)
            ax.axhline(0, color='black', linewidth=0.8)
            for _, r in v.iterrows():
                off = 0.8 if r[col] >= 0 else -2.5
                ax.text(r['年份'], r[col]+off, f'{r[col]:.0f}%',
                        ha='center', fontsize=9, fontweight='bold')
            ax.set_title(label)
            ax.set_ylabel('%')
            ax.grid(True, alpha=0.3, axis='y')
            ax.set_xticks(v['年份'])
            ax.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        plt.savefig('charts/财务指标增长率.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_margins_eps(self, df):
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle(f'{COMPANY} 盈利能力指标', fontsize=15, fontweight='bold')

        ax = axes[0]
        valid = df.dropna(subset=['revenue']).copy()
        if 'gross' in df.columns:
            gm = valid['gross'] / valid['revenue'] * 100
            ax.plot(valid['年份'], gm, marker='o', color=COLORS['gross'],
                    label='毛利率', linewidth=2.5, markersize=8)
            for x, y in zip(valid['年份'], gm):
                ax.annotate(f'{y:.0f}%', (x,y),
                            textcoords='offset points', xytext=(0,8),
                            ha='center', fontsize=9)
        if 'attr_profit' in df.columns:
            nm = valid['attr_profit'] / valid['revenue'] * 100
            ax.plot(valid['年份'], nm, marker='s', color=COLORS['net'],
                    label='归母净利率', linewidth=2.5, markersize=8, linestyle='--')
            for x, y in zip(valid['年份'], nm):
                ax.annotate(f'{y:.0f}%', (x,y),
                            textcoords='offset points', xytext=(0,-14),
                            ha='center', fontsize=9)
        ax.set_title('毛利率与归母净利率 (%)')
        ax.set_ylabel('%')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(valid['年份'])
        ax.tick_params(axis='x', rotation=45)

        ax2 = axes[1]
        if 'basic_eps' in df.columns:
            v = df.dropna(subset=['basic_eps'])
            ax2.bar(v['年份'], v['basic_eps'], color=COLORS['eps'], alpha=0.85, width=0.6)
            for _, r in v.iterrows():
                ax2.text(r['年份'], r['basic_eps']+0.25,
                         f'{r["basic_eps"]:.2f}', ha='center', fontsize=10, fontweight='bold')
            ax2.set_title('基本每股盈利 EPS（人民币元/股）')
            ax2.set_ylabel('人民币元')
            ax2.grid(True, alpha=0.3, axis='y')
            ax2.set_xticks(v['年份'])
            ax2.tick_params(axis='x', rotation=45)
        plt.tight_layout()
        plt.savefig('charts/利润率与EPS.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_quarterly(self, qtr):
        valid = qtr.dropna(subset=['revenue']).copy()
        if len(valid) < 4:
            return
        fig, axes = plt.subplots(2, 1, figsize=(20, 13))
        fig.suptitle(f'{COMPANY} 季度财务趋势', fontsize=15, fontweight='bold')

        x = list(range(len(valid)))
        periods = list(valid['period'])

        # 收入柱图 + 同比增长折线
        ax = axes[0]
        rev_vals = valid['revenue'] / 1e4
        ax.bar(x, rev_vals, color=COLORS['revenue'], alpha=0.75, width=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(periods, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('百亿元')
        ax.set_title('季度营业收入（百亿元）+ 同比增长率')
        ax.grid(True, alpha=0.3, axis='y')

        # 同比增长率
        valid_sorted = valid.copy().reset_index(drop=True)
        valid_sorted['rev_yoy'] = None
        for i, row in valid_sorted.iterrows():
            prev_q = valid_sorted[(valid_sorted['year'] == row['year'] - 1) &
                                   (valid_sorted['quarter'] == row['quarter'])]
            if len(prev_q) > 0 and not pd.isna(prev_q.iloc[0]['revenue']) and prev_q.iloc[0]['revenue'] > 0:
                valid_sorted.at[i, 'rev_yoy'] = (row['revenue'] - prev_q.iloc[0]['revenue']) / prev_q.iloc[0]['revenue'] * 100

        ax2 = ax.twinx()
        yoy_x = [xi for xi, v in zip(x, valid_sorted['rev_yoy']) if pd.notna(v)]
        yoy_y = [v for v in valid_sorted['rev_yoy'] if pd.notna(v)]
        if yoy_x:
            ax2.plot(yoy_x, yoy_y, color='red', marker='o', linewidth=2, markersize=5, label='同比增长率')
            ax2.axhline(0, color='red', linewidth=0.5, linestyle='--')
            ax2.set_ylabel('同比增长率 (%)', color='red')
            ax2.legend(loc='upper left')

        # 归母净利润
        ax3 = axes[1]
        if 'attr_profit' in valid.columns and valid['attr_profit'].notna().any():
            v2 = valid.dropna(subset=['attr_profit'])
            x2 = [periods.index(p) for p in v2['period'] if p in periods]
            clrs = [COLORS['pos'] if n >= 0 else COLORS['neg']
                    for n in v2['attr_profit']]
            ax3.bar(x2, v2['attr_profit']/1e4, color=clrs, alpha=0.8, width=0.7)
            ax3.set_xticks(x)
            ax3.set_xticklabels(periods, rotation=45, ha='right', fontsize=8)
            ax3.set_ylabel('百亿元')
            ax3.set_title('季度归母净利润（百亿元）')
            ax3.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig('charts/季度收入与利润趋势.png', dpi=300, bbox_inches='tight')
        plt.close()

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------
    def generate_markdown(self):
        from datetime import datetime
        ann = self.annual_df
        gdf = self.growth_df if hasattr(self, 'growth_df') else ann
        lines = [f'# {COMPANY}财务数据分析报告',
                 f'生成日期: {datetime.now().strftime("%Y年%m月%d日")}', '']

        latest = ann.iloc[-1]
        yr = int(latest['年份'])
        prev  = ann.iloc[-2] if len(ann) >= 2 else latest
        prev_yr = int(prev['年份'])

        lines += ['## 一、最新年度财务摘要（RMB）', '', '| 指标 | 数值 |', '|------|------|']
        for col, label, unit, scale in [
            ('revenue',    f'{yr}年营业收入', '亿元', 1e8),
            ('gross',      f'{yr}年毛利润',   '亿元', 1e8),
            ('op_profit',  f'{yr}年经营利润', '亿元', 1e8),
            ('attr_profit',f'{yr}年归母净利润','亿元',1e8),
            ('basic_eps',  f'{yr}年基本EPS',  '元/股',1),
        ]:
            v = latest.get(col)
            if v is not None and not pd.isna(v):
                disp = v/scale if scale != 1 else v
                lines.append(f'| {label} | {disp:,.2f} {unit} |')
        lines.append('')

        rev  = latest.get('revenue'); grss = latest.get('gross')
        nett = latest.get('attr_profit')
        if rev and grss and nett:
            lines.append(f'> 毛利率: **{grss/rev*100:.1f}%** ｜ 归母净利率: **{nett/rev*100:.1f}%**')
            lines.append('')

        lines += ['## 二、同比增长率', '', '| 指标 | 增速 |', '|------|------|']
        lg = gdf.iloc[-1]
        for col, label in [('revenue_yoy','营业收入'),('attr_profit_yoy','归母净利润'),
                            ('gross_yoy','毛利'),('op_profit_yoy','经营利润'),
                            ('basic_eps_yoy','基本EPS')]:
            v = lg.get(col)
            if v is not None and not pd.isna(v):
                arrow = '↑' if v >= 0 else '↓'
                lines.append(f'| {label} | {arrow} {v:.1f}% |')
        lines.append('')

        lines += ['## 三、历年核心数据一览（亿元/元）', '',
                  '| 年份 | 营收 | 毛利 | 经营利润 | 归母净利 | 毛利率 | EPS |',
                  '|------|------|------|--------|--------|------|-----|']
        for _, row in ann.iterrows():
            yr2 = int(row['年份'])
            def _f(c, sc=1e8): v=row.get(c); return f'{v/sc:,.0f}' if v and not pd.isna(v) else '-'
            def _p(a,b): return f'{row[a]/row[b]*100:.0f}%' if row.get(a) and row.get(b) and not pd.isna(row[a]) and not pd.isna(row[b]) else '-'
            lines.append(f'| {yr2} | {_f("revenue")} | {_f("gross")} | {_f("op_profit")} | '
                         f'{_f("attr_profit")} | {_p("gross","revenue")} | '
                         f'{row["basic_eps"]:.2f} |' if row.get("basic_eps") and not pd.isna(row.get("basic_eps","")) else
                         f'| {yr2} | {_f("revenue")} | {_f("gross")} | {_f("op_profit")} | {_f("attr_profit")} | {_p("gross","revenue")} | - |')
        lines.append('')

        lines += ['## 四、风险提示',
                  '- 监管政策（游戏、平台经济、数据安全）的不确定性',
                  '- 宏观经济疲软对广告/VAS消费的负面影响',
                  '- AI大模型投入导致资本开支大幅增加',
                  '- 港币/人民币汇率波动影响HKD投资者回报']

        text = '\n'.join(lines)
        with open('财务分析报告.md', 'w', encoding='utf-8') as f:
            f.write(text)
        return text

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------
    def save_excel(self):
        with pd.ExcelWriter('财务数据.xlsx', engine='xlsxwriter') as wr:
            self.annual_df.to_excel(wr, sheet_name='年度数据', index=False)
            if hasattr(self,'quarterly_df') and len(self.quarterly_df):
                self.quarterly_df.to_excel(wr, sheet_name='季度数据', index=False)
            if hasattr(self,'growth_df'):
                self.growth_df.to_excel(wr, sheet_name='增长率', index=False)
        print('  数据已保存: 财务数据.xlsx')


# ============================================================
# 主入口
# ============================================================
def main():
    from datetime import datetime
    print('='*60)
    print(f'  {COMPANY} 财务数据分析工具')
    print(f'  字体: {_chinese_fonts[0]}')
    print('='*60)

    a = TencentAnalyzer()

    print('\n1️⃣  加载年度数据（已核实，2018-2025）...')
    ann = a.build_annual_df()
    print(f'  年度数据: {len(ann)} 年 ({int(ann.iloc[0]["年份"])}-{int(ann.iloc[-1]["年份"])})')

    print('\n2️⃣  从PDF提取季度数据...')
    qtr_rows = extract_quarterly_data()
    a.build_quarterly_df(qtr_rows)
    print(f'  季度数据: {len(a.quarterly_df)} 个季度')

    print('\n3️⃣  计算增长率...')
    a.calc_growth()

    print('\n4️⃣  生成图表...')
    a.generate_charts()

    print('\n5️⃣  生成Markdown报告...')
    a.generate_markdown()
    print('  报告已生成: 财务分析报告.md')

    print('\n6️⃣  保存Excel数据...')
    a.save_excel()

    print('\n7️⃣  生成HTML报告...')
    from generate_html_report import generate_tencent_html
    generate_tencent_html(a.annual_df, a.quarterly_df,
                          a.growth_df, COMPANY)

    print('\n' + '='*60)
    print(f'  ✅ {COMPANY}分析完成!')
    print('  输出: 财务分析报告.html | 财务分析报告.md | 财务数据.xlsx | charts/')
    print('='*60)


if __name__ == '__main__':
    main()
