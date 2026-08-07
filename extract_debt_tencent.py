#!/usr/bin/env python3
"""提取腾讯有息负债（借款 + 应付票据，流动+非流动）与现金，判断是否靠借钱运转。

口径：有息负债 = 非流动借款 + 非流动应付票据 + 流动借款 + 流动应付票据
     净现金 = 期末现金及现金等价物 + 定期存款(如可得) − 有息负债
注：本脚本只取现金及现金等价物，不含定期存款与投资，故「净现金」偏保守。
"""
import json, re, sys
from pathlib import Path
import pdfplumber

NUM = re.compile(r"\(?-?[\d,]+(?:\.\d+)?\)?")

def to_num(t):
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace(",", "")
    if t in ("", "-", "–", "—"):
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v

def nums(line):
    # 「–」占位列须转成 0 参与定位，否则金额列缺失时会把附注编号当成金额
    # （如「Notes payable 26 1,834 –」会误取 26）
    line = re.sub(r"(?<=\s)[–—-](?=\s|$)", " 0 ", line)
    return [v for v in (to_num(t) for t in NUM.findall(line)) if v is not None]

BS_TITLE = r"綜合財務狀況表|综合财务状况表|Consolidated Statement of Financial Position|CONSOLIDATED STATEMENT OF FINANCIAL POSITION|Consolidated Balance Sheet|CONSOLIDATED BALANCE SHEET"
# 标签逐年变化：早年有 Short-term bank borrowing / Long-term notes payable，
# 2012 后统一为 Borrowings / Notes payable，中文年报为 借款 / 應付票據。
# 注意排除 Long-term payables（长期应付款，非有息）与 Amounts due to（往来款）。
BORROW = r"^(?:短期|長期|长期)?(?:銀行|银行)?借款\s|^(?:Short-term |Long-term )?(?:bank )?[Bb]orrowings?\s"
NOTES = r"^(?:長期|长期)?應付票據\s|^(?:长期)?应付票据\s|^(?:Long-term |Short-term )?[Nn]otes payable\s"

def extract(path, year):
    out = {"年份": year, "来源": Path(path).name}
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        pages, first = [], None
        for i in range(int(n * 0.25), n):
            t = pdf.pages[i].extract_text() or ""
            if re.search(BS_TITLE, t) and re.search(r"\d,\d{3}", t) and \
               re.search(r"負債|负债|liabilities", t, re.I):
                first = i
                break
        if first is None:
            return out
        # 只读合并报表：遇到「權益及負債總額/Total equity and liabilities」即收尾，
        # 否则会把紧随其后的母公司资产负债表一并计入，导致借款/票据重复计数（2014 曾如此）
        chunks = []
        for i in range(first, min(first + 4, n)):
            t = pdf.pages[i].extract_text() or ""
            chunks.append(t)
            if re.search(r"權益及負債總額|权益及负债总额|Total equity and liabilities", t):
                break
        text = "\n".join(chunks)
    scale = 0.001 if re.search(r"RMB.?000|人民幣千元|人民币千元", text) else 1.0
    b = [v for ln in text.split("\n") if re.search(BORROW, ln.strip()) for v in [nums(ln)] if len(v) >= 2]
    p = [v for ln in text.split("\n") if re.search(NOTES, ln.strip()) for v in [nums(ln)] if len(v) >= 2]
    # 每行取倒数第二个数=本年列；借款/应付票据各出现两次（非流动+流动）
    borrow = sum(v[-2] for v in b) * scale
    notes = sum(v[-2] for v in p) * scale
    out["借款"] = round(borrow, 1)
    out["应付票据"] = round(notes, 1)
    out["有息负债"] = round(borrow + notes, 1)
    out["借款行数"] = len(b)
    out["票据行数"] = len(p)
    return out

if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "财报")
    best = {}
    for p in sorted(root.rglob("*.pdf")):
        nm = p.name
        if any(k in nm for k in ["演示", "展示", "presentation", "中期", "半年", "第一季", "第二季", "第三季", "第四季", "Q1", "Q2", "Q3", "Q4"]):
            continue
        if not any(k in nm for k in ["年报", "年報", "财报", "財報"]):
            continue
        m = re.search(r"(20\d{2})", nm)
        if not m:
            continue
        best[int(m.group(1))] = p
    res = []
    for y in sorted(best):
        r = extract(str(best[y]), y)
        res.append(r)
        print(f"{y}  借款={r.get('借款','—')!s:>12}  票据={r.get('应付票据','—')!s:>12}  "
              f"有息负债={r.get('有息负债','—')!s:>12}  (行数 {r.get('借款行数','?')}/{r.get('票据行数','?')})")
    Path("腾讯控股_有息负债.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已写入 腾讯控股_有息负债.json")
