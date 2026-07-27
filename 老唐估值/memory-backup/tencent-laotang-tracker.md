---
name: tencent-laotang-tracker
description: 腾讯控股(00700.HK)老唐估值跟踪项目——文件位置、估值口径、结论、已设提醒
metadata: 
  node_type: memory
  type: project
  originSessionId: e0780902-a694-4911-8c40-4effe0cea4f7
  modified: 2026-07-27T04:49:05.463Z
---

用户在 `/Users/lvjiang/Documents/Projects/tencent/` 维护一套腾讯控股(00700.HK)的老唐估值跟踪，含三个配套文件：
- `腾讯_老唐估值_总览.md` — 一页总览（结论、三情景表、SOTP、敏感性、链接、触发话术）
- `腾讯_老唐估值_可跟踪.xlsx` — 三个工作表：估值模型 / SOTP分部估值 / 季度跟踪；带公式，改假设自动重算。改动后必须用 xlsx 技能的 `recalc.py` 重算确保 0 公式错误。SOTP 表复用「估值模型」表的 B5净利/B7股本/B8汇率/B11现价。
- `腾讯_老唐估值_SOTP_跟踪台.html` — 自包含交互页，数据存浏览器 localStorage。在线版：https://claude.ai/code/artifact/254a044e-90d0-452a-a46b-18f10f2f4c2a （republish 同一文件路径可原地更新此 URL）

**固定口径**：人民币亿元 / 股价港元；总股本 90.1 亿股；汇率 1港元=0.91人民币；合理PE低利率封顶保守取 25×（敏感假设，改20×安全边际基本抹平）。基准数据：2025年报 Non-IFRS 归母 2596 亿、2026Q1 归母 680 亿(TTM≈2663)。

**结论(2026-07-27)**：现价 HK$460，简化法中性合理值 HK$1112/买点 HK$556，SOTP HK$1144/买点 HK$572，两法印证 → 深度低估。

已设一次性提醒任务 `tencent-q2-2026-valuation-update`，2026-08-12 20:00(UTC+8) 触发，自动抓取中期财报并更新跟踪表。参见 [[laotang-valuation-prefs]]。
