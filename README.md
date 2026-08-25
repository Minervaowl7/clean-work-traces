# clean-work-traces

面向领导、客户和正式交付场景的 Office 文档工作痕迹清理 Skill。

它帮助 AI Agent 在不改变事实、数字、结论和正式来源的前提下，识别并清理：草稿话术、修订批注、演讲者备注、隐藏 Sheet/幻灯片、本机路径、内部核验表、源行号、哈希、调试信息以及版式问题。

> This skill audits and cleans drafting, review, metadata, hidden-content, and workpaper traces from finished Office deliverables while preserving facts and clean citations.

## 主要能力

- 区分“应删除的工作痕迹”“必须保留的事实限制”“需要人工判断的内容”。
- 支持 DOCX/DOC、PPTX/PPT、XLSX/XLSM/XLS 和 PDF。
- 检查正文、表格、评论、修订、备注、隐藏内容、元数据、本机路径和工作底表。
- 保护数字、结论、单位、企业名称、来源和用户指定不可修改内容。
- 要求实际渲染验收，避免只检查 XML 却遗漏截断、重叠和异常分页。
- 附带纯 Python 扫描器；OpenXML 扫描无需 Microsoft Office，也不会上传文件。

## 它不会做什么

- 扫描器不会自动重写文档或机械删除内容。
- 不会把“未查得”偷偷改成“没有发生”。
- 不会为了显得正式而删除真实的限制条件、免责声明或“尚未上市”等事实。
- 旧版 DOC/PPT/XLS 只做初步二进制字符串扫描；可靠清理前应先复制并转换为开放格式。

## 安装

将仓库复制到 Agent 的技能目录：

```powershell
$skillsRoot = Join-Path $env:USERPROFILE '.agents\skills'
New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
git clone https://github.com/Minervaowl7/clean-work-traces.git (Join-Path $skillsRoot 'clean-work-traces')
```

也可以直接把仓库目录放入其他兼容 `SKILL.md` 的技能加载路径。

## 快速使用

在对话中说：

```text
使用 clean-work-traces，把这份报告清理成可发领导的最终版，保留正式来源。
```

单独运行扫描器：

```powershell
python scripts/scan_deliverable.py "报告.docx"
python scripts/scan_deliverable.py "清单.xlsx" --json "清单-cleanup-audit.json"
python scripts/scan_deliverable.py "领导版.xlsx" --allow-source-comments
```

退出码：

- `0`：未发现高风险痕迹。
- `1`：发现草稿词或结构性痕迹，需要处理或人工判断。
- `2`：文件无法解析或格式不受支持。

## 支持范围

| 格式 | 扫描 | 清理策略 |
|---|---|---|
| DOCX/DOCM | OpenXML 深度扫描 | 修订、评论、隐藏文字、页眉页脚、属性、渲染 |
| DOC | 初步二进制扫描 | 保留原件，转换 DOCX 后清理 |
| PPTX/PPTM | OpenXML 深度扫描 | 备注、评论、隐藏页、页外对象、母版、渲染 |
| PPT | 初步二进制扫描 | 保留原件，转换 PPTX 后清理 |
| XLSX/XLSM | OpenXML 深度扫描 | 批注、隐藏 Sheet、外链、工作底表、公式和打印区域 |
| XLS | 初步二进制扫描 | 保留原件，转换 XLSX 后清理 |
| PDF | 文本、元数据和批注扫描 | 回到源文件修改后重新导出 |

## 仓库结构

```text
SKILL.md                    技能入口与交付门禁
REFERENCE.md                各格式清理边界
EXAMPLES.md                 DOCX/PPTX/XLSX 示例
scripts/scan_deliverable.py 本地扫描器
tests/                      标准库单元测试
```

## 隐私

扫描器只读取本地文件，不发起网络请求。JSON 审计报告可能包含命中片段和本机路径，公开或发送前请再次检查。

## 开发

```powershell
python -m unittest discover -s tests -v
python -m py_compile scripts/scan_deliverable.py
```

欢迎提交 Issue 和 Pull Request。贡献前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## License

[MIT](LICENSE)
