#!/usr/bin/env python3
"""从腾讯控股年报 PDF 提取现金流质量指标（IFRS 港股版）。

与 cashflow-quality 技能自带的 A 股脚本的关键差异——换任何港股/中概公司都会遇到：

1. **间接法 vs 直接法**：A 股中国会计准则要求直接法列示「销售商品、提供劳务收到的现金」，
   IFRS 用间接法，从税前利润倒推，**根本不存在该科目**。故收现比对腾讯不可计算，
   只能用净现比 + 现金生成质量（經營活動所得現金/净利润）替代。

2. **数字格式**：A 股脚本的 NUM 正则要求两位小数（`-?[\\d,]+\\.\\d{2}`），
   腾讯以「人民币百万元」整数列示（751,766），必须改为整数+千分位。

3. **语言**：2004-2018 年报为英文，2021-2025 为繁体中文，2019-2020 缺独立年报
   （用当年 Q4 业绩公告的完整报表替代）。三套关键词都要备。

4. **括号负数**：IFRS 报表负数用括号 (44,699)，需转为负值。
"""
import argparse, json, re, sys
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    sys.exit("缺少依赖，请先运行：pip3 install pdfplumber")

# 腾讯以百万元整数列示，允许可选两位小数
NUM = re.compile(r"\(?-?[\d,]+(?:\.\d+)?\)?")


def to_num(tok):
    """'(44,699)' -> -44699.0 ; '303,052' -> 303052.0"""
    neg = tok.startswith("(") and tok.endswith(")")
    tok = tok.strip("()").replace(",", "")
    if tok in ("", "-", "–", "—"):
        return None
    try:
        v = float(tok)
    except ValueError:
        return None
    return -v if neg else v


def nums_in(line):
    return [v for v in (to_num(t) for t in NUM.findall(line)) if v is not None]


# 科目关键词：(字段名, [中文繁简变体], [英文变体])
ITEMS = [
    ("经营活动现金流净额",
     [r"經營活動所得現金流量淨額", r"经营活动所得现金流量净额", r"經營活動產生的現金流量淨額"],
     # 措辞逐年变化：2004「Net cash (used in)/generated from…」、
     # 2005「Net cash generated from/(used in) operating activities」，统一用宽松中缀
     [r"Net cash flows generated from operating activities",
      r"Net cash generated from operating activities",
      r"Net cash.{0,32}operating activities"]),
    ("经营活动所得现金",
     [r"^經營活動所得現金\s", r"^经营活动所得现金\s"],
     [r"^Cash generated from operations", r"^Cash .{0,24}operations\s"]),
    ("已付所得税",
     [r"已付所得稅", r"已付所得税"],
     [r"Income tax paid"]),
    ("购建固定资产",
     [r"購買物業、設備及器材、在建工程與投資物業的付款",
      r"购买物业、设备及器材、在建工程与投资物业的付款",
      r"購買物業、設備及器材、在建工程"],
     # 2024 起写作「Purchase of/prepayments for property, plant and equipment,…」
     [r"Purchase of.{0,20}property, plant and equipment",
      r"Purchase of fixed assets, construction in progress",
      r"Purchase of fixed assets and construction in progress",
      r"Purchase of fixed assets"]),   # 2004 最简写法，须置末以免遮蔽上面更具体的变体
    ("购买无形资产",
     [r"購買無形資產的付款", r"购买无形资产的付款"],
     [r"Purchase of.{0,20}intangible assets"]),
    ("支付股息",
     [r"向本公司股東支付股息", r"向本公司股东支付股息"],
     [r"Dividends paid to the Company.s shareholders",
      r"Dividends paid to shareholders of the Company",
      r"Dividends paid to the equity holders of the Company"]),
    ("回购股份",
     [r"回購股份", r"回购股份"],
     [r"Payments for repurchase of shares", r"Repurchase of shares"]),
    ("期末现金及等价物",
     [r"年末的現金及現金等價物", r"年末的现金及现金等价物"],
     [r"Cash and cash equivalents at end of the year",
      r"Cash and cash equivalents at the end of the year"]),
]

TITLE = r"綜合現金流量表|综合现金流量表|CONSOLIDATED STATEMENT OF CASH FLOWS|CONSOLIDATED CASH FLOW STATEMENT|Consolidated Statement of Cash Flows|Consolidated Cash Flow Statement"
# 报表正文特征：必须同时出现分节标题与金额，才能与核数师报告/目录里的表名区分
BODY = r"經營活動現金流量|经营活动现金流量|Cash flows from operating activities"


def find_cashflow_pages(pdf):
    """定位综合现金流量表首页并连读后续页。
    坑：核数师报告、目录、附注索引都会提到表名，必须靠正文特征(BODY)+金额过滤。"""
    n = len(pdf.pages)
    # 2008 年报现金流量表位于全文 32.9% 处，阈值须低于此；BODY+金额双重条件已足够排除正文误匹配
    start = int(n * 0.25)
    first = None
    for i in range(start, n):
        t = pdf.pages[i].extract_text() or ""
        if re.search(TITLE, t) and re.search(BODY, t) and re.search(r"\d,\d{3}", t):
            first = i
            break
    if first is None:
        return []
    # 现金流量表通常跨 2-3 页（投资/融资活动续页）
    return list(range(first, min(first + 3, n)))


def detect_unit(text):
    """RMB'000 / 人民幣千元 -> 需除以 1000 换算为百万元；RMB'Million/人民幣百萬元 -> 1"""
    if re.search(r"RMB.?000|人民幣千元|人民币千元", text):
        return 0.001
    return 1.0


def extract(path, year):
    out = {"年份": year, "来源": Path(path).name}
    with pdfplumber.open(path) as pdf:
        pages = find_cashflow_pages(pdf)
        if not pages:
            return out
        text = "\n".join((pdf.pages[i].extract_text() or "") for i in pages)
    scale = detect_unit(text)
    out["单位换算"] = "千元→百万元" if scale != 1 else "百万元"

    lines = text.split("\n")
    for field, zh_pats, en_pats in ITEMS:
        for pat in zh_pats + en_pats:
            found = False
            for idx, line in enumerate(lines):
                if re.search(pat, line.strip()):
                    vals = nums_in(line)
                    # 跨行科目：数字在下一行
                    if not vals and idx + 1 < len(lines):
                        vals = nums_in(lines[idx + 1])
                    # 排除附注编号（如 43(a)、19(b)）——取最后两个数为本年/上年两列
                    if len(vals) >= 2:
                        out[field] = round(vals[-2] * scale, 1)   # 本年列
                        out[field + "_上年"] = round(vals[-1] * scale, 1)
                        found = True
                        break
                    elif len(vals) == 1:
                        out[field] = round(vals[0] * scale, 1)
                        found = True
                        break
            if found:
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--out", default="腾讯控股_现金流数据.json")
    ap.add_argument("--years", nargs="*", type=int)
    args = ap.parse_args()

    root = Path(args.dir)
    targets = []
    for p in sorted(root.rglob("*.pdf")):
        name = p.name
        if any(k in name for k in ["演示", "展示", "presentation", "中期", "半年"]):
            continue
        m = re.search(r"(20\d{2})", name)
        y = int(m.group(1)) if m else None
        if y is None:
            # 2019/2020 无独立年报，其 Q4 公告文件名用中文数字（腾讯二零一九年第四季度…）
            zh = re.search(r"二零([一二三四五六七八九零]{2})年", name)
            if zh:
                mp = {"零":"0","一":"1","二":"2","三":"3","四":"4",
                      "五":"5","六":"6","七":"7","八":"8","九":"9"}
                try:
                    y = 2000 + int("".join(mp[c] for c in zh.group(1)))
                except (KeyError, ValueError):
                    y = None
        if y is None:
            continue
        # 年报优先；2019/2020 无独立年报，用 Q4 全年业绩公告
        is_annual = any(k in name for k in ["年报", "年報", "财报", "財報", "annual"])
        is_q4 = any(k in name for k in ["第四季", "Q4"])
        if not (is_annual or is_q4):
            continue
        if args.years and y not in args.years:
            continue
        targets.append((y, is_annual, p))

    # 同一年优先用年报
    best = {}
    for y, is_annual, p in targets:
        if y not in best or (is_annual and not best[y][0]):
            best[y] = (is_annual, p)

    results = []
    for y in sorted(best):
        is_annual, p = best[y]
        rec = extract(str(p), y)
        results.append(rec)
        got = [k for k in rec if k not in ("年份", "来源") and not k.endswith("_上年")]
        flag = "" if len(got) >= 5 else "  ⚠️ 提取不足"
        print(f"{y}  {p.name[:40]:42s} 命中 {len(got)} 项{flag}")

    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {args.out}")


if __name__ == "__main__":
    main()
