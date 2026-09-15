# ths-stock-screen

供 AI Agent 调用的固定多周期选股 Skill，内置 33 项选股条件，覆盖均线、日周 MACD、日周及 30 分钟 VPT、ASI、CCI、资金净额和自由流通市值。

## 使用

将本仓库放入 Agent 的 skills 目录，目录名保持为 `ths-stock-screen`。

```text
使用 $ths-stock-screen，按内置条件筛选。
```

默认日期为 2026-09-09；可明确指定其他筛选日期。全部条件见 [SKILL.md](SKILL.md)。

## 文件

- `SKILL.md`：固定策略与执行规则，策略条件的真源。
- `references/semantics.md`：时间、指标、字段口径及验证要求。
- `references/example-20260909.md`：初始实现记录和客户端操作说明。
- `assets/daily-core-candidate.txt`：仅覆盖部分日线条件的候选公式。

## 当前状态

已完成策略规则封装和 Skill 格式校验。实际筛选需接入行情及资金数据；同花顺公式尚未在目标客户端编译验证或安装。附带候选公式不代表完整策略，不能作为全条件筛选结果使用。
