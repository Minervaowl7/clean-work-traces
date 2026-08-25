# Contributing

感谢你改进 `clean-work-traces`。

## 提交原则

- 新规则必须说明为何是“高置信删除项”或“需要人工判断项”。
- 避免把真实限制条件、免责声明和来源事实误判为工作痕迹。
- 不提交真实客户文件、内部路径、用户名、Token 或包含敏感片段的扫描报告。
- 修改扫描器时应补充不依赖 Microsoft Office 的测试。

## 本地检查

```powershell
python -m unittest discover -s tests -v
python -m py_compile scripts/scan_deliverable.py
```

Pull Request 请说明：触发场景、预期行为、误报风险和测试结果。
