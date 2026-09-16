# ths-stock-screen

固定 33 条选股规则的 Agent Skill。输出以 **股票 × 条件热力图、候选名单和近期走势** 为主，审计细节折叠。Python 3 标准库即可运行；HTML 离线可用。

## 调用

安装到 Agent skills 目录，命名为 `ths-stock-screen`：

> 使用 ths-stock-screen，按内置条件筛选，输出热力图和匹配度较高候选的近期走势。

运行时先展示实际股票池数量和覆盖范围，用户确认后开始；沿用原策略，不逐项询问技术参数。缺项会标待核验，范围发生变化才重新确认。

默认日期 2026-09-09；只有用户明确指定才更改。数据接入与指标口径仍需核实。所有条件见 [SKILL.md](SKILL.md)。

## 固定执行流程

按 [数据契约](references/data-contract.md) 准备内部 .work/normalized.json，然后：

```sh
python3 scripts/build_report.py --input .work/normalized.json --out-dir output
python3 -m unittest discover -s tests
```

唯一交付文件为 **output/选股结果.html**，不附加CSV、JSON、审计文档或压缩包。中间数据在内部`.work/`目录保留，页面本身离线可用。

打开 output/选股结果.html。顶部先展示筛选股票数及每组剔除/剩余数的面包屑，可展开全部33步；未知数据保留，股票不重复扣除。点击股票切换图表、点击色块查看依据，可筛选和导出名单。完整开高低收数据绘制蜡烛 K 线；只有收盘数据则展示收盘走势，不伪造 K 线。

- 通过、不通过、待核验严格分开，固定分母 33。
- 当前候选池不冒充全市场；数据不足不下“全市场无股符合”的结论。
- 固定交易日期和自然周，不按指标值变化划分周。
- 未核实的资金分类、VPT/PVT 映射及指标参数维持未知。
- 特定 WorkBuddy v2 CSV 可由 `scripts/import_workbuddy.py` 导入，口径证据与原始文件哈希绑定。
- 本仓库不含真实行情、个人运行日志或账户数据，不附带数据权限。

同花顺公式仅在明确请求时生成；附带日线候选模板未在目标客户端验证，不代表完整策略。筛选匹配度不是收益预测。
