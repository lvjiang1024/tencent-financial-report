#!/usr/bin/env python3
"""汇总腾讯 2004-2026 年度/半年度/季度财务数据为统一 JSON。
2004-2018 数据来自逐年精读年报/中期报告 PDF（合并利润表 + 财务概要资产负债表）。
2019-2025 年度数据沿用 financial_analysis.py 中已核实的 KNOWN_ANNUAL，并补充总资产/
净资产/非国际财务报告准则净利润（来自各年 Q4/全年业绩公告及 2025 年报财务概要）。
2019-2026 季度数据从对应季度 PDF 摘要表/业绩公告正文抓取。
"""
import os, re, json
import pdfplumber

ROOT = os.path.dirname(os.path.abspath(__file__))
RPT = os.path.join(ROOT, '财报')

# ============================================================
# 2004-2018 年度数据（精读年报合并利润表 + 财务概要资产负债表，人民币百万元）
# EPS 已按 2014 年 5 股拆 1 股调整为可比口径（2004-2013 原始 EPS / 5）
# ============================================================
ANNUAL_2004_2018 = [
    dict(year=2004, revenue=1143.533, gross=725.408, op_profit=468.696, pbt=463.653,
         net_profit=441.119, attr_profit=441.119, eps_basic=0.058, eps_diluted=0.0568,
         total_assets=2863.321, net_assets=2652.238),
    dict(year=2005, revenue=1426.395, gross=956.526, op_profit=484.359, pbt=437.055,
         net_profit=485.362, attr_profit=485.362, eps_basic=0.0548, eps_diluted=0.0534,
         total_assets=3427.122, net_assets=2928.413),
    dict(year=2006, revenue=2800.441, gross=1983.379, op_profit=1163.305, pbt=1116.771,
         net_profit=1063.800, attr_profit=1063.800, eps_basic=0.1206, eps_diluted=0.117,
         total_assets=4650.572, net_assets=3717.756),
    dict(year=2007, revenue=3820.923, gross=2703.366, op_profit=1635.026, pbt=1534.503,
         net_profit=1568.008, attr_profit=1566.020, eps_basic=0.176, eps_diluted=0.1706,
         total_assets=6925.444, net_assets=5170.396),
    dict(year=2008, revenue=7154.544, gross=4984.123, op_profit=3245.974, pbt=3104.895,
         net_profit=2815.650, attr_profit=2784.577, eps_basic=0.3104, eps_diluted=0.3028,
         total_assets=9855.557, net_assets=7020.926),
    dict(year=2009, revenue=12439.960, gross=8550.492, op_profit=6020.478, pbt=6040.731,
         net_profit=5221.611, attr_profit=5155.646, eps_basic=0.5724, eps_diluted=0.5582,
         total_assets=17505.765, net_assets=12178.507),
    dict(year=2010, revenue=19646.031, gross=13325.831, op_profit=9838.213, pbt=9913.133,
         net_profit=8115.209, attr_profit=8053.625, eps_basic=0.8864, eps_diluted=0.8656,
         total_assets=35830.114, net_assets=21756.946),
    dict(year=2011, revenue=28496.072, gross=18567.764, op_profit=12253.550, pbt=12099.069,
         net_profit=10224.831, attr_profit=10203.083, eps_basic=1.1218, eps_diluted=1.098,
         nifrs_net=10940.208,
         total_assets=56804.365, net_assets=28463.834),
    dict(year=2012, revenue=43893.711, gross=25686.351, op_profit=15479.413, pbt=15051.015,
         net_profit=12784.852, attr_profit=12731.871, eps_basic=1.393, eps_diluted=1.3666,
         nifrs_net=14286.423,
         total_assets=75255.811, net_assets=41297.507),
    dict(year=2013, revenue=60437, gross=32659, op_profit=19194, pbt=19281,
         net_profit=15563, attr_profit=15502, eps_basic=1.6928, eps_diluted=1.6596,
         nifrs_net=17008,
         total_assets=107235, net_assets=57945),
    dict(year=2014, revenue=78932, gross=48059, op_profit=30542, pbt=29013,
         net_profit=23888, attr_profit=23810, eps_basic=2.579, eps_diluted=2.545,
         nifrs_net=24737,
         total_assets=171166, net_assets=80013),
    dict(year=2015, revenue=102863, gross=61232, op_profit=40627, pbt=36216,
         net_profit=29108, attr_profit=28806, eps_basic=3.097, eps_diluted=3.055,
         nifrs_net=32410,
         total_assets=306818, net_assets=120035),
    dict(year=2016, revenue=151938, gross=84499, op_profit=56117, pbt=51640,
         net_profit=41447, attr_profit=41095, eps_basic=4.383, eps_diluted=4.329,
         nifrs_net=45420,
         total_assets=395899, net_assets=174624),
    dict(year=2017, revenue=237760, gross=116925, op_profit=90302, pbt=88215,
         net_profit=72471, attr_profit=71510, eps_basic=7.598, eps_diluted=7.499,
         nifrs_net=65126,
         total_assets=554672, net_assets=256074),
    dict(year=2018, revenue=312694, gross=142120, op_profit=97648, pbt=94466,
         net_profit=79984, attr_profit=78719, eps_basic=8.336, eps_diluted=8.228,
         nifrs_net=77469,
         total_assets=723521, net_assets=323510),
]

# 2019-2025 总资产/净资产/非国际财务报告准则归母净利润（补充到既有 KNOWN_ANNUAL）
BS_NONGAAP_2019_2025 = {
    2019: dict(total_assets=953986, net_assets=432706, nifrs_net=94351),
    2020: dict(total_assets=1333425, net_assets=703984, nifrs_net=122742),
    2021: dict(total_assets=1612364, net_assets=806299, nifrs_net=123788),
    2022: dict(total_assets=1578131, net_assets=721391, nifrs_net=115649),
    2023: dict(total_assets=1577246, net_assets=808591, nifrs_net=157688),
    2024: dict(total_assets=1780995, net_assets=973548, nifrs_net=222703),
    2025: dict(total_assets=2038986, net_assets=1154152, nifrs_net=259626),
}

# ============================================================
# 2004-2018 半年度数据（六个月止6月30日，人民币百万元，EPS 已作拆股调整）
# ============================================================
INTERIM_2004_2018 = [
    dict(year=2004, revenue=528.066),
    dict(year=2005, revenue=634.136, gross=423.245, op_profit=222.162, pbt=221.996,
         attr_profit=283.927, eps_basic=0.0322, eps_diluted=0.0312),
    dict(year=2006, revenue=1350.286, gross=975.558, op_profit=591.618, pbt=574.986,
         attr_profit=517.589, eps_basic=0.058, eps_diluted=0.0564),
    dict(year=2007, revenue=1641.077, gross=1137.517, op_profit=689.771, pbt=660.576,
         attr_profit=624.655, eps_basic=0.0704, eps_diluted=0.0682),
    dict(year=2008, revenue=3032.689, gross=2191.155, op_profit=1502.611, pbt=1365.669,
         attr_profit=1178.357),
    dict(year=2009, revenue=5382.788, gross=3662.261, op_profit=2563.479, pbt=2571.898,
         attr_profit=2227.850),
    dict(year=2010, revenue=8895.240, gross=6083.946, op_profit=4519.798, pbt=4539.511),
    dict(year=2011, revenue=13077.464, gross=8552.098, op_profit=6170.402, pbt=6164.626),
    dict(year=2012, revenue=20175.102, gross=12027.406, op_profit=7628.973, pbt=7431.398),
    dict(year=2013, revenue=27932.075, gross=15388.029, op_profit=9627.622, pbt=9710.541,
         attr_profit=7724, eps_basic=1.686, eps_diluted=1.656),  # 拆股前口径(/5=0.843*2 近似)
    dict(year=2014, revenue=38146, gross=22772, op_profit=15633, pbt=15108,
         attr_profit=12293, eps_basic=1.332, eps_diluted=1.313),
    dict(year=2015, revenue=45828, gross=27872, op_profit=19408, pbt=17872,
         attr_profit=14197, eps_basic=1.528, eps_diluted=1.512),
    dict(year=2016, revenue=67686, gross=39045, op_profit=27727, pbt=25478,
         attr_profit=19920, eps_basic=2.128, eps_diluted=2.102),
    dict(year=2017, revenue=106158, gross=53749, op_profit=41832, pbt=40430,
         attr_profit=32707, eps_basic=3.480, eps_diluted=3.436),
    dict(year=2018, revenue=147203, gross=71488, op_profit=52499, pbt=51901,
         attr_profit=41157, eps_basic=4.363, eps_diluted=4.303),
]

# ============================================================
# 季度/年报/中期 PDF 提取（2019-2026），表格式 + 叙述式两种正则
# ============================================================
def _classify(fname):
    fn = fname
    m = re.search(r'20\d{2}', fn)
    year = int(m.group(0)) if m else None
    zh = re.search(r'二零([一二三四五六七八九零]{2})年', fn)
    if zh:
        mp = {'零':'0','一':'1','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9'}
        try:
            year = 2000 + int(''.join(mp.get(c,'?') for c in zh.group(1)))
        except Exception:
            pass
    if any(k in fn for k in ['演示','展示','presentation','演示文稿']):
        return year, 'skip'
    if any(k in fn for k in ['年报','年度报告','年財報','年财报','financial report','年报.pdf']):
        return year, 'FY'
    if '中期' in fn or '半年' in fn:
        return year, 'H1'
    if any(k in fn for k in ['第四季','第四季度','Q4','q4']):
        return year, 'Q4'
    if any(k in fn for k in ['第三季','第三季度','Q3','q3']):
        return year, 'Q3'
    if any(k in fn for k in ['第二季','第二季度','Q2','q2']):
        return year, 'Q2'
    if any(k in fn for k in ['第一季','第一季度','Q1','q1']):
        return year, 'Q1'
    return year, None


def _table_extract(text, period_label_year, period_label_full):
    """财务表现摘要表格式（简体/繁体，人民币百万元）。"""
    # 去掉字段名内部的换行，避免 "本公司\n權益持有人應佔盈利" 之类跨行标签匹配失败
    norm = re.sub(r'(?<=[一-鿿])\n(?=[一-鿿])', '', text)
    r = {}
    def grab(pat):
        m = re.search(pat, norm)
        return float(m.group(1).replace(',', '')) if m else None
    r['revenue']    = grab(r'(?<!总)(?<!總)收入\s+([\d,]+)')
    r['gross']      = grab(r'毛利\s+([\d,]+)')
    r['op_profit']  = grab(r'(?<!準則)(?<!准则)[经經]营[盈盈]利\s+([\d,]+)')
    r['net_profit'] = grab(r'(?:期[内內]|年度)[盈盈]利\s+([\d,]+)')
    r['attr_profit']= grab(r'(?<!準則)(?<!准则)本公司[权權]益持有人[应應][占佔][盈盈]利\s+([\d,]+)')
    r['eps_basic']  = grab(r'[－-]\s*基本\s+([\d.]+)')
    r['eps_diluted']= grab(r'[－-]\s*[摊攤]薄\s+([\d.]+)')
    NIFRS = r'非[国國][际際][财財][务務][报報][告吿][准準][则則]'
    r['nifrs_op']   = grab(NIFRS + r'[经經]营[盈盈]利\s+([\d,]+)')
    r['nifrs_net']  = grab(NIFRS + r'本公司[权權]益持有人[应應][占佔][盈盈]利\s+([\d,]+)')

    # 英文版公告（2024Q3、2025Q1-Q3 等）用 FINANCIAL PERFORMANCE HIGHLIGHTS 表，
    # 中文关键词全部落空，需补一套英文模式。注意 Non-IFRS 行须先匹配，
    # 否则 "Operating profit" 会被 "Non-IFRS operating profit" 行抢先命中。
    if len([v for v in r.values() if v is not None]) < 3:
        r = {}
        r['nifrs_op']  = grab(r'Non-IFRS operating profit\s+([\d,]+)')
        r['nifrs_net'] = grab(r'Non-IFRS profit attributable to equity\s*holders of the Company\s+([\d,]+)')
        r['revenue']   = grab(r'(?<!Total )Revenues\s+([\d,]+)')
        r['gross']     = grab(r'Gross profit\s+([\d,]+)')
        r['op_profit'] = grab(r'(?<!Non-IFRS )Operating profit\s+([\d,]+)')
        r['net_profit']= grab(r'Profit for the (?:period|year)\s+([\d,]+)')
        r['attr_profit'] = grab(r'(?<!Non-IFRS )Profit attributable to equity\s*holders of the Company\s+([\d,]+)')
        r['eps_basic'] = grab(r'[–-]\s*basic\s+([\d.]+)')
        r['eps_diluted'] = grab(r'[–-]\s*diluted\s+([\d.]+)')
    return {k: v for k, v in r.items() if v is not None}


_NG_ANCHOR = r'按非(?:通用会计准则|国际财务报告准则)\d*[，,][^\n]{0,20}(?:已排除|撇除)'
_IF_ANCHOR = r'按国际财务报告准则[：:]'

def _narrative_extract(text):
    """中文叙述式新闻稿（亿元），2019-2022 部分季度使用。
    IFRS 与 Non-GAAP 两段在 Q1 稿与 Q4/全年稿中的先后顺序相反，且顶部摘要行会提前
    提到"非通用会计准则"这几个字但不带数字，容易误判分界点。因此改用更具体的锚点
    （"按非通用会计准则X，已排除.../按国际财务报告准则："）定位真正的明细段落起点，
    而不是任意一次"非通用会计准则"出现的位置。"""
    r = {}
    def nums_in(seg, pat):
        return [float(x.replace(',', '')) * 100 for x in re.findall(pat, seg)]

    ng_m = re.search(_NG_ANCHOR, text)
    if_m = re.search(_IF_ANCHOR, text)
    ng_pos = ng_m.start() if ng_m else -1
    if_pos = if_m.start() if if_m else -1

    if ng_pos >= 0 and if_pos >= 0:
        if ng_pos < if_pos:
            nifrs_seg, ifrs_seg = text[ng_pos:if_pos], text[if_pos:if_pos+900]
        else:
            ifrs_seg, nifrs_seg = text[if_pos:ng_pos], text[ng_pos:ng_pos+900]
    elif ng_pos >= 0:
        ifrs_seg, nifrs_seg = text[:ng_pos], text[ng_pos:ng_pos+900]
    elif if_pos >= 0:
        ifrs_seg, nifrs_seg = text[if_pos:if_pos+900], ''
    else:
        ifrs_seg, nifrs_seg = text, ''

    revs = nums_in(text, r'总收入为人民币([\d,.]+)亿元')
    if revs:
        r['revenue'] = revs[0]

    op = nums_in(ifrs_seg, r'经营盈利为人民币([\d,.]+)亿元')
    if op: r['op_profit'] = op[0]
    npf = nums_in(ifrs_seg, r'(?:期内|年度)盈利为人民币([\d,.]+)亿元')
    if npf: r['net_profit'] = npf[0]
    ap = nums_in(ifrs_seg, r'(?:期内|年度)本公司权益持有人应占盈利为人民币([\d,.]+)亿元')
    if ap: r['attr_profit'] = ap[0]
    be = re.findall(r'每股基本盈利为人民币([\d.]+)元', ifrs_seg)
    if be: r['eps_basic'] = float(be[0])
    de = re.findall(r'每股摊薄盈利为人民币([\d.]+)元', ifrs_seg)
    if de: r['eps_diluted'] = float(de[0])

    if nifrs_seg:
        nop = nums_in(nifrs_seg, r'经营盈利为人民币([\d,.]+)亿元')
        if nop: r['nifrs_op'] = nop[0]
        nap = nums_in(nifrs_seg, r'(?:期内|年度)本公司权益持有人应占盈利为人民币([\d,.]+)亿元')
        if nap: r['nifrs_net'] = nap[0]
    return r


def extract_period(fp, year, ptype):
    with pdfplumber.open(fp) as pdf:
        text = '\n'.join((p.extract_text() or '') for p in pdf.pages[:3])

    result = {}
    if ptype in ('Q1','Q2','Q3'):
        # 三个月摘要表通常在 "截至下列日期止三個月" 之后
        idx = text.find('三個月')
        if idx < 0:
            idx = text.find('三个月')
        seg = text[max(0,idx-200): idx+1200] if idx >= 0 else text[:1500]
        result = _table_extract(seg, None, None)
        if len(result) < 3:
            result = _narrative_extract(text)
    elif ptype == 'Q4':
        # 第一张表是单季，第二张"截至十二月三十一日止年度"是全年 -> 取全年段
        idx = text.find('止年度')
        if idx < 0:
            idx = text.find('全年')
        seg = text[idx:idx+900] if idx >= 0 else text
        result = _table_extract(seg, None, None)
        if len(result) < 3:
            result = _narrative_extract(text)
    elif ptype in ('FY','H1'):
        result = _table_extract(text, None, None)
        if len(result) < 3:
            result = _narrative_extract(text)
    return result


def scan_2019_2026():
    out = {}  # (year, ptype) -> dict
    for y in range(2019, 2027):
        d = os.path.join(RPT, str(y))
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith('.pdf'):
                continue
            yr, ptype = _classify(fn)
            if ptype in (None, 'skip') or yr is None:
                continue
            fp = os.path.join(d, fn)
            try:
                r = extract_period(fp, yr, ptype)
            except Exception as e:
                print('ERROR', fp, e)
                continue
            if len(r) >= 3:
                key = (yr, ptype)
                if key not in out or len(r) > len(out[key][1]):
                    out[key] = (fn, r)
    return out


def main():
    scanned = scan_2019_2026()
    quarterly_records = []
    for (yr, ptype), (fn, r) in sorted(scanned.items()):
        rec = dict(year=yr, period_type=ptype, source_file=fn, **r)
        quarterly_records.append(rec)

    data = {
        'annual_2004_2018': ANNUAL_2004_2018,
        'bs_nongaap_2019_2025': BS_NONGAAP_2019_2025,
        'interim_2004_2018': INTERIM_2004_2018,
        'periods_2019_2026': quarterly_records,
    }
    out_path = os.path.join(ROOT, '腾讯控股_raw_extract.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('written', out_path)
    print('quarterly/annual/H1 records 2019-2026:', len(quarterly_records))
    for rec in quarterly_records:
        print(' ', rec['year'], rec['period_type'], rec['source_file'], '->',
              {k:v for k,v in rec.items() if k in ('revenue','attr_profit','nifrs_net')})

if __name__ == '__main__':
    main()
