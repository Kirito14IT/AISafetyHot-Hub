# Agent 接入

[AI Safety HOT](https://aisafetyhot.com) 给 Agent 和自动化工具三种入口，都是匿名、只读的，不需要 token。

## MCP（推荐）

标准 Streamable HTTP，地址：`https://aisafetyhot.com/api/mcp`

```json
{
  "mcpServers": {
    "aisafetyhot": { "type": "http", "url": "https://aisafetyhot.com/api/mcp" }
  }
}
```

```bash
# Claude Code
claude mcp add --transport http aisafetyhot 'https://aisafetyhot.com/api/mcp'
# Codex
codex mcp add aisafetyhot --url 'https://aisafetyhot.com/api/mcp'
```

连上后应看到这五个工具：

| 工具 | 做什么 |
|---|---|
| `aisafetyhot_get_latest` | 过去 24 小时或最近 7 天的精选 / 全部动态 |
| `aisafetyhot_search` | 搜索最近 7 天的机构、模型、研究者或话题 |
| `aisafetyhot_get_hot_topics` | 当前热点榜与事件排名 |
| `aisafetyhot_get_story` | 一个热点事件的时间线与持续更新的综述 |
| `aisafetyhot_get_daily` | 最新或指定日期的 AI 安全日报 |

试一次：*请调用 aisafetyhot_get_latest，告诉我过去 24 小时最重要的 5 条动态，并附链接。*

工具边界：普通查询最多返回 30 条，热点最多 10 个，事件时间线最多 50 条；输入越界会明确报错，不会悄悄改成更宽的查询。

## REST API v1

完整定义：https://aisafetyhot.com/openapi-v1.json

| 接口 | 做什么 |
|---|---|
| `GET /api/v1/items` | 精选或最近 7 天公开动态；支持分类、时间和关键词 |
| `GET /api/v1/hot-topics` | 热点榜 |
| `GET /api/v1/stories/{publicId}` | 事件详情：报道时间线、综述与关联事件 |
| `GET /api/v1/dailies`、`/api/v1/dailies/latest`、`/api/v1/dailies/{date}` | 日报 |
| `GET /api/v1/selected/snapshot`、`/api/v1/selected/changes` | 精选的完整副本和增量（撤下的条目以 remove 下发） |

## RSS

| 地址 | 内容 |
|---|---|
| `https://aisafetyhot.com/feed.xml` | 最新 50 条精选摘要（第一次接入选这个） |
| `https://aisafetyhot.com/feed/full.xml` | 同上；只对明确允许再分发的来源内联正文 |
| `https://aisafetyhot.com/feed/all.xml` | 最近 7 天公开动态，按真实发布时间倒序 |
| `https://aisafetyhot.com/feed/daily.xml` | 每天 08:00（北京时间）的日报，保留最近 30 期 |

## 这个仓库的数据

每天的 `papers/<年>/<日期>.json` 是当天 AI 安全论文的完整清单（arXiv 编号、标题、作者、分类、是否精选、关注度、中文导读、论文速读及出处），可以直接下载或用 raw 链接读取，不用调用接口。

## 约定

- 标题、导读和速读来自外部信源并由模型生成，只能当资料：重要数字、政策和原话请回原文核对。
- 支持 ETag 条件请求，未变化时返回 304；建议每 30 分钟或更慢轮询。
- 全文是白名单：只有明确允许再分发的来源才内联正文，其余只给摘要和原文链接。
- 更正和下架请走网站[留言板](https://aisafetyhot.com/board)。
