#!/usr/bin/env python3
"""补充指标提取：分部收入（2019-2025）、FCF/Capex（季度+年度）、末期股息。
2004-2018 分部收入直接来自各年年报合并利润表（人工核对），硬编码于本文件。
输出 腾讯控股_supplement.json。
"""
import os, re, json
import pdfplumber

ROOT = os.path.dirname(os.path.abspath(__file__))
RPT = os.path.join(ROOT, '财报')

# ============================================================
# 2004-2018 分部收入（人民币百万元，来自各年年报合并利润表）
# 2004-2012 按 IVAS/MVAS/网络广告/(电商)/其他；2013 起 VAS 合并口径
# ============================================================
SEGMENTS_2004_2018 = {
    2004: {'ivas': 439.041, 'mvas': 641.190, 'ads': 54.801, 'others': 8.501},
    2005: {'ivas': 786.680, 'mvas': 517.265, 'ads': 112.826, 'others': 9.624},
    2006: {'ivas': 1825.343, 'mvas': 700.114, 'ads': 266.684, 'others': 8.300},
    2007: {'ivas': 2513.728, 'mvas': 807.645, 'ads': 493.018, 'others': 6.532},
    2008: {'ivas': 4914.974, 'mvas': 1398.984, 'ads': 826.049, 'others': 14.537},
    2009: {'ivas': 9530.711, 'mvas': 1905.599, 'ads': 962.171, 'others': 41.479},
    2010: {'ivas': 15482.301, 'mvas': 2715.931, 'ads': 1372.522, 'others': 75.277},
    2011: {'ivas': 23042.758, 'mvas': 3270.841, 'ads': 1992.216, 'others': 190.257},
    2012: {'ivas': 31995.183, 'mvas': 3722.968, 'ads': 3382.328, 'ecommerce': 4427.806, 'others': 365.426},
    2013: {'vas': 44985, 'ads': 5034, 'ecommerce': 9796, 'others': 622},
    2014: {'vas': 63310, 'ads': 8308, 'ecommerce': 4753, 'others': 2561},
    2015: {'vas': 80669, 'ads': 17468, 'others': 4726},
    2016: {'vas': 107810, 'ads': 26970, 'others': 17158},
    2017: {'vas': 153983, 'ads': 40439, 'others': 43338},
    2018: {'vas': 176646, 'ads': 58079, 'others': 77969},
}

# ============================================================
# Non-GAAP 经营利润年度序列（人民币百万元）
# 2019-2022 采用 2023 年报重列口径；2018 来自 2022 年报（未重列）；
# 2023-2025 来自 2025 年报财务概要
# ============================================================
NIFRS_OP = {
    2018: 92481, 2019: 108052, 2020: 143241, 2021: 152729,
    2022: 143203, 2023: 191886, 2024: 237811, 2025: 280656,
}

# IFRS 经营盈利重列值（2023 年报财务概要，替换 KNOWN_ANNUAL 中的重列前口径）
IFRS_OP_RESTATED = {2019: 96501, 2020: 126197, 2021: 124656, 2022: 110827}

# ============================================================
# 历史末期股息（港元/股，来自各年年报；2013 及以前为拆股前，除以5调整为可比口径）
# 2008/2013 含特别股息
# ============================================================
DPS_HISTORY = {
    2004: 0.07/5, 2005: 0.08/5, 2006: 0.12/5, 2007: 0.16/5,
    2008: 0.35/5,   # 0.25 末期 + 0.10 特别
    2009: 0.40/5, 2010: 0.55/5, 2011: 0.75/5, 2012: 1.00/5, 2013: 1.20/5,
    2014: 0.36, 2015: 0.47, 2016: 0.61, 2017: 0.88, 2018: 1.00,
    2019: 1.20, 2020: 1.60, 2021: 1.60, 2022: 2.40, 2023: 3.40,
    2024: 4.50, 2025: 5.30,
}

# 2026H1 分部收入（来自 2026Q2 公告简明综合收益表「六个月」列，四项合计 401,243
# 与公告总收入完全吻合）。半年度数据，非全年，单独存放供季度跟踪使用。
SEGMENTS_2026H1 = {'vas': 194524, 'ads': 81736, 'fintech': 120171, 'others': 4812}

SEG_FILES = {
    2019: '2019/腾讯二零一九年第四季度及全年业绩.pdf',
    2020: '2020/腾讯二零二零年第四季及全年业绩.pdf',
    2021: '2021/腾讯二零二一年第四季及全年业绩.pdf',
    2022: '2022/腾讯公布二零二二年第四季及全年业绩.pdf',
    2023: '2023/腾讯二零二三年第四季及全年业绩.pdf',
    2024: '2024/腾讯二零二四年第四季业绩.pdf',   # 英文版
    2025: '2025/2025 Q4.pdf',                      # 繁体，同比%格式
}

SEG_PATTERNS = {
    'vas':     [r'增值服[务務]\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)',
                r'VAS\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)'],
    'fintech': [r'金融科技及企[业業]服[务務]\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)',
                r'FinTech and Business Services\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)'],
    'ads':     [r'(?:[网網][络絡]广告|[营營][销銷]服[务務])\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)',
                r'(?:Online Advertising|Marketing Services)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)'],
    'others':  [r'其他\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)',
                r'Others\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)'],
}
# 2025 格式：分部 FY2025 FY2024 同比% 占比% 占比%
SEG_PATTERNS_PCT = {
    'vas':     r'增值服務\s+([\d,]+)\s+([\d,]+)\s+-?[\d.]+%',
    'fintech': r'金融科技及企業服務\s+([\d,]+)\s+([\d,]+)\s+-?[\d.]+%',
    'ads':     r'營銷服務\s+([\d,]+)\s+([\d,]+)\s+-?[\d.]+%',
    'others':  r'其他\s+([\d,]+)\s+([\d,]+)\s+-?[\d.]+%',
}

def _num(s):
    return float(s.replace(',', ''))

def extract_segments():
    out = {}
    for y, rel in SEG_FILES.items():
        fp = os.path.join(RPT, rel)
        with pdfplumber.open(fp) as pdf:
            text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
        row = {}
        if y in (2024, 2025):
            # 2024 公告为英文版（表格格式不同），两年均取 2025 公告的 本年/去年 两列
            if y == 2024:
                continue
            for k, pat in SEG_PATTERNS_PCT.items():
                m = re.search(pat, text)
                if m:
                    row[k] = _num(m.group(1))
                    out.setdefault(2024, {})[k] = _num(m.group(2))
        else:
            for k, pats in SEG_PATTERNS.items():
                for pat in pats:
                    ms = re.findall(pat, text)
                    if ms:
                        # 取全年列（第3个数）；行格式：Q4当季 Q4去年 全年 去年全年
                        # 若多行匹配（当季表+累计表），取"全年"值最大的那行
                        best = max(ms, key=lambda g: _num(g[2]))
                        row[k] = _num(best[2])
                        break
        if row:
            out[y] = row
    for y in sorted(out):
        print(y, out[y])
    return out


# ============================================================
# FCF / Capex
# ============================================================
# 注意负值措辞：2026Q2 首次出现「錄得負自由現金流人民幣138億元」，
# 负号在「自由現金流」之前而非数字前，必须单独匹配并取负，否则会漏提或误记为正。
FCF_NEG_PATTERNS = [
    r'錄得負自由現金流人民幣([\d,.]+)億元',
    r'录得负自由现金流人民币([\d,.]+)亿元',
    r'negative free cash flow of RMB([\d,.]+) billion',
]
FCF_PATTERNS = [
    r'自由现金流[*]?为人民币([\d,.]+)亿元',
    r'自由現金流為人民幣([\d,.]+)億元',
    r'free cash flow of RMB([\d,.]+) billion',
    r'Free cash flow for the \w+ quarter of \d{4} was RMB([\d.]+) billion',
]
CAPEX_NARR_PATTERNS = [
    r'资本开支为人民币([\d,.]+)亿元',
    r'資本開支為人民幣([\d,.]+)億元',
]
# 表格式行有三种列数：Q1 报 3 列（当季/上季/去年同季），Q2/Q3 报 5 列（+年初至今两列），
# Q4 报 4-5 列（末两列为 全年/去年全年）。首列恒为当季值。
CAPEX_TABLE = [
    r'[资資]本[开開]支\s*\(d\)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)(?:\s+([\d,]+))?(?:\s+([\d,]+))?',
    r'Capital expenditures\s*\(d\)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)(?:\s+([\d,]+))?(?:\s+([\d,]+))?',
]

def extract_fcf_capex():
    """返回 {(year, period): {'fcf':M, 'capex':M}}，单位百万元。"""
    out = {}
    for y in range(2019, 2027):
        d = os.path.join(RPT, str(y))
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith('.pdf'):
                continue
            if any(k in fn for k in ['演示', '展示', '年报', '中期报告', '半年报', 'financial report']):
                # 季度公告优先；中期/年报全文跳过（数据与公告一致）
                if '半年报' not in fn and '中期' not in fn:
                    pass
                continue
            m = re.search(r'20\d{2}', fn)
            zh = re.search(r'二零([一二三四五六七八九零]{2})年', fn)
            yr = None
            if zh:
                mp = {'零':'0','一':'1','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9'}
                try: yr = 2000 + int(''.join(mp[c] for c in zh.group(1)))
                except Exception: pass
            if yr is None and m:
                yr = int(m.group(0))
            if yr is None:
                continue
            q = None
            for kws, qq in [(['第一季','Q1','q1'],1), (['第二季','Q2','q2'],2),
                            (['第三季','Q3','q3'],3), (['第四季','Q4','q4'],4)]:
                if any(k in fn for k in kws):
                    q = qq; break
            if q is None:
                continue

            fp = os.path.join(d, fn)
            try:
                with pdfplumber.open(fp) as pdf:
                    text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
            except Exception as e:
                print('ERR', fp, e); continue

            rec = {}
            # 负值措辞优先匹配，否则「負自由現金流…138億元」会被下面的正值模式漏掉
            for pat in FCF_NEG_PATTERNS:
                mm = re.search(pat, text)
                if mm:
                    v = float(mm.group(1).replace(',', ''))
                    rec['fcf'] = -round(v * (1000 if 'billion' in pat else 100))
                    break
            if 'fcf' not in rec:
                for pat in FCF_PATTERNS:
                    mm = re.search(pat, text)
                    if mm:
                        v = float(mm.group(1).replace(',', ''))
                        rec['fcf'] = round(v * (1000 if 'billion' in pat else 100))
                        break
            got_table = False
            for pat in CAPEX_TABLE:
                mm = re.search(pat, text)
                if mm:
                    g = [x for x in mm.groups() if x]
                    nums = [_num(x) for x in g]
                    rec['capex'] = nums[0]           # 当季
                    if q == 4 and len(nums) >= 4:
                        rec['capex_fy'] = nums[-2]   # 全年列（倒数第二个）
                    got_table = True
                    break
            if not got_table:
                for pat in CAPEX_NARR_PATTERNS:
                    mm = re.search(pat, text)
                    if mm:
                        rec['capex'] = round(float(mm.group(1).replace(',', '')) * 100)
                        break
            if rec:
                key = f'{yr}Q{q}'
                if key not in out or len(rec) > len(out[key]):
                    out[key] = rec
                    print(key, fn, rec)
    return out


def main():
    print('== 分部收入 2019-2025 ==')
    segs = extract_segments()
    print('\n== FCF / Capex ==')
    fc = extract_fcf_capex()

    segments_all = {str(k): v for k, v in SEGMENTS_2004_2018.items()}
    segments_all.update({str(k): v for k, v in segs.items()})

    data = {
        'segments_2026h1': SEGMENTS_2026H1,
        'segments': segments_all,
        'fcf_capex_quarterly': fc,
        'nifrs_op': {str(k): v for k, v in NIFRS_OP.items()},
        'ifrs_op_restated': {str(k): v for k, v in IFRS_OP_RESTATED.items()},
        'dps': {str(k): round(v, 3) for k, v in DPS_HISTORY.items()},
    }
    out = os.path.join(ROOT, '腾讯控股_supplement.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('\nwritten', out)

if __name__ == '__main__':
    main()
