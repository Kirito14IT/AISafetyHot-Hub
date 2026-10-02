<p align="center"><img src="assets/logo.svg" width="88" alt="AI Safety HOT"></p>

<h1 align="center">AI Safety HOT Hub</h1>

<p align="center">每天的 AI 安全精选和论文清单：攻击、防御、对齐、评测、漏洞与治理</p>

<p align="center">
  <a href="https://aisafetyhot.com">网站</a> ·
  <a href="https://aisafetyhot.com/feed.xml">RSS</a> ·
  <a href="docs/agent.md">Agent 接入（MCP）</a> ·
  <a href="#下载论文清单">下载论文清单</a> ·
  <a href="#支持">支持</a>
</p>

## 简介

[AI Safety HOT](https://aisafetyhot.com) 每天盯着实验室安全博客、arXiv、研究者、评测机构和政策机构的信源，由模型筛选、打分，北京时间每天 08:00 出一份 AI 安全日报。这个仓库每天收一份：

- **每日精选**（[`daily/`](daily)）：当天的日报，按攻击与越狱、防御与护栏、对齐与可解释性、安全评测、真实事件、治理与政策分节，每条是中文标题、导读、来源和原文链接。
- **论文清单**（[`papers/`](papers)）：这一天进站、判定为 AI 安全的全部论文，每篇带中文导读和论文速读（问题、方法、实验、局限），可以整份下载。

每小时检查一次、有新内容就推送（当天的论文清单会随论文进站陆续变长），从 2026-09-24（第一期日报）开始，内容都来自网站，原文链接指向各自的来源。

这里只收日报和论文。网站还盯着实验室和机构的安全博客、新闻媒体、研究者和机构的 X 账号、公众号、小红书、Reddit 等信源，这些动态都在网站上：[全部动态](https://aisafetyhot.com/all) 按时间列出所有入选的内容，[热点榜](https://aisafetyhot.com/hot) 是正在发酵的事件，[主题](https://aisafetyhot.com/topics) 按方向归类。

## 最近

<!-- latest:start -->
| 日期 | 每日精选 | 论文清单 |
|---|---|---|
| 2026-10-02 | [日报](daily/2026/2026-10-02.md) | [39 篇](papers/2026/2026-10-02.md) · [bib](papers/2026/2026-10-02.bib) · [json](papers/2026/2026-10-02.json) |
| 2026-10-01 | [日报](daily/2026/2026-10-01.md) | [57 篇](papers/2026/2026-10-01.md) · [bib](papers/2026/2026-10-01.bib) · [json](papers/2026/2026-10-01.json) |
| 2026-09-30 | [日报](daily/2026/2026-09-30.md) | [1 篇](papers/2026/2026-09-30.md) · [bib](papers/2026/2026-09-30.bib) · [json](papers/2026/2026-09-30.json) |
| 2026-09-29 | [日报](daily/2026/2026-09-29.md) | [39 篇](papers/2026/2026-09-29.md) · [bib](papers/2026/2026-09-29.bib) · [json](papers/2026/2026-09-29.json) |
| 2026-09-28 | [日报](daily/2026/2026-09-28.md) | [48 篇](papers/2026/2026-09-28.md) · [bib](papers/2026/2026-09-28.bib) · [json](papers/2026/2026-09-28.json) |
| 2026-09-27 | [日报](daily/2026/2026-09-27.md) | [16 篇](papers/2026/2026-09-27.md) · [bib](papers/2026/2026-09-27.bib) · [json](papers/2026/2026-09-27.json) |
| 2026-09-26 | [日报](daily/2026/2026-09-26.md) | [22 篇](papers/2026/2026-09-26.md) · [bib](papers/2026/2026-09-26.bib) · [json](papers/2026/2026-09-26.json) |
| 2026-09-25 | [日报](daily/2026/2026-09-25.md) | [21 篇](papers/2026/2026-09-25.md) · [bib](papers/2026/2026-09-25.bib) · [json](papers/2026/2026-09-25.json) |
| 2026-09-24 | [日报](daily/2026/2026-09-24.md) | [19 篇](papers/2026/2026-09-24.md) · [bib](papers/2026/2026-09-24.bib) · [json](papers/2026/2026-09-24.json) |

更早的见 [2026 年目录](archive/2026.md)。

[status.json](status.json) 记录每天的论文数和 ID 摘要，以及同步时限（slaMinutes：网站上的论文最迟多少分钟内出现在这里）。
<!-- latest:end -->

## 下载论文清单

每天的论文清单有三种格式，放在 `papers/<年>/<日期>.*`：

| 格式 | 用途 |
|---|---|
| `.md` | 在 GitHub 上直接看：表格加每篇的导读和速读 |
| `.bib` | BibTeX，直接导入 Zotero、EndNote 这类文献管理工具 |
| `.json` | 给脚本和 Agent 读：arXiv 编号、标题、作者、分类、是否精选、关注度、导读、速读 |

★ 表示进了精选，并标出关注度。关注度衡量这篇论文对 AI 安全读者有多值得看（0–100），不是论文质量评分：一篇好论文如果和 AI 安全关系不大，分数也会很低。

## Agent 接入

网站提供匿名、只读的 MCP 服务，Agent 加一个地址就能查最新精选、搜索、热点和日报：

```json
{
  "mcpServers": {
    "aisafetyhot": { "type": "http", "url": "https://aisafetyhot.com/api/mcp" }
  }
}
```

工具列表、REST API、RSS 和使用约定见 [docs/agent.md](docs/agent.md)。不想连接口的话，直接读这个仓库里每天的 JSON 也可以。

## 订阅

- 精选：[RSS](https://aisafetyhot.com/feed.xml) · 全部动态：[RSS](https://aisafetyhot.com/feed/all.xml) · 日报：[RSS](https://aisafetyhot.com/feed/daily.xml)
- Watch 这个仓库，每天有新提交。

## 支持

网站和这个仓库都免费。服务器和模型调用每个月都有开销，如果它对你有用，欢迎请作者喝杯咖啡：

| 国内：微信扫一扫 | 海外 |
|---|---|
| <img src="assets/wechat-pay.png" width="140" alt="微信收款码"> | [Buy Me a Coffee](https://buymeacoffee.com/wuyoscar) |

## 声明

- **致谢**：AI Safety HOT 基于开源框架 [AIHOT](https://github.com/KKKKhazix/AIHOT) 搭建，感谢作者把它开源。
- **论文导读**由模型生成。
- **论文速读**由模型据论文本身整理：读论文 PDF（Gemini），或者在还没有 PDF 解读时读 arXiv 上的全文。每篇都写明了出处。
- 导读和速读都是二手材料，重要的数字和结论请以论文原文为准。
- 仓库里的导读、速读和日报文字以 [CC BY-NC 4.0](LICENSE) 发布，转载请署名并注明来自 AI Safety HOT，不要用于商业用途。原文和论文的版权归各自的作者与来源。
- 发现错误、希望更正或下架，请在网站[留言板](https://aisafetyhot.com/board)选"下架/更正"。
