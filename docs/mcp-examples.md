# MCP 实际输入与输出

[返回 README](../README.md#agent) · [安装与完整参数说明](agent.md)

这里展示一次完整的“找到内容 → 深读 → 查看进展”的实际调用。**采样时间：2026-10-07 14:45，Australia/Melbourne（UTC+11）**；线上服务返回版本 **2.2.0**。结果是该时刻的记录，并非实时榜单，也不代表对原文做了新的事实核验。

连接地址：`https://aisafetyhot.com/api/mcp`，匿名只读，无需 API Key。先按[接入指南](agent.md#mcp)添加 MCP，再把下方自然语言输入交给你的 Agent。开发者可直接使用每例的 `name` 和 `arguments` 作为 `tools/call` 参数。

下方 JSON 输出摘自工具的 `structuredContent`，**仅选择展示部分字段或条目，不改写展示出来的字段值**。完整响应还包含来源、分页、完整性等信息；“摘录”不能代替完整响应。网站摘要与已有导读是二手资料，重要结论请沿原文链接核对。

| 想做什么 | 示例 |
| --- | --- |
| 看最新收录 | [1. 最新动态](#latest) |
| 找话题标签 | [2. 发现话题](#topics) |
| 按话题搜索新闻和论文 | [3. 搜索](#search) |
| 打开单篇内容 | [4. 深读](#content) |
| 查看当前榜单 | [5. 热点榜](#hot) |
| 跟进同一事件的报道 | [6. 事件时间线](#story) |
| 读日、周、月报 | [7. 报告](#reports) |
| 继续读下一页 | [分页示例](#pagination) |

<a id="latest"></a>

## 1. 最新动态：过去 24 小时收录了什么？

**输入给 Agent**

> 看过去 24 小时最新收录的 3 条精选，附来源和原文链接。

**MCP 输入**

```json
{
  "name": "aisafetyhot_get_latest",
  "arguments": {
    "window": "24h",
    "mode": "selected",
    "limit": 3
  }
}
```

**实际输出（字段摘录）**

```json
{
  "items": [
    {
      "id": "da8k095stbflt2f8cj6d7yvoa",
      "kind": "paper",
      "title": "研究：工具型智能体判断结果无用却仍继续检索，强制整合步骤可纠正",
      "links": {
        "aihot": "https://aisafetyhot.com/items/da8k095stbflt2f8cj6d7yvoa",
        "original": "https://huggingface.co/papers/2610.06191"
      },
      "source": {
        "name": "Hugging Face Daily Papers"
      },
      "publishedAt": "2026-10-04T20:00:00.000Z",
      "publishedDate": null,
      "discoveredAt": "2026-10-07T03:29:27.196Z"
    },
    {
      "id": "phnuyph0zwm2cyg662ur8t2a5",
      "kind": "article",
      "title": "韩国金融业联合预警系统未能及早发现AI黑客攻击痕迹",
      "links": {
        "aihot": "https://aisafetyhot.com/items/phnuyph0zwm2cyg662ur8t2a5",
        "original": "https://www.chosun.com/english/market-money-en/2026/10/07/XKH5WMQDWRCHFATOB5GJZMGXMU"
      },
      "source": {
        "name": "The Chosun Daily"
      },
      "publishedAt": null,
      "publishedDate": "2026-10-07",
      "discoveredAt": "2026-10-07T02:27:49.339Z"
    },
    {
      "id": "mw4b76pws0atv6jxhfl587dms",
      "kind": "article",
      "title": "OpenAI 首席战略官就智能体探测 NSW 火史服务出席澳议会听证",
      "links": {
        "aihot": "https://aisafetyhot.com/items/mw4b76pws0atv6jxhfl587dms",
        "original": "https://auns.com.au/article/20261006-openai-kwon-inquiry-npws-fire-history"
      },
      "source": {
        "name": "AUNS"
      },
      "publishedAt": "2026-10-06T03:50:00.000Z",
      "publishedDate": null,
      "discoveredAt": "2026-10-07T02:27:33.624Z"
    }
  ],
  "page": {
    "count": 3,
    "hasMore": true
  },
  "freshness": {
    "readAt": "2026-10-07T03:45:11.048Z",
    "windowEnd": "2026-10-07T03:45:11.048Z",
    "latestModifiedAt": "2026-10-07T03:30:47.841Z"
  }
}
```


`kind=paper` 是论文，`article` 是报道。默认时间窗口按本站收录时间筛选；例如第一篇论文原文发表于 UTC 10 月 4 日，但在本次最近 24 小时收录范围内。`publishedAt=null` 时保留 `publishedDate` 的日期精度，不补造具体时间。这里的 3 是本页条数，不是全天总量。需要全部动态时将 `mode` 改为 `all`。

<a id="topics"></a>

## 2. 发现话题：怎样筛选“提示注入”？

**输入给 Agent**

> 找到“提示注入”的话题标签、定义和相关话题。

先调用 `aisafetyhot_get_topics`，`arguments: {}` 获取话题目录；本次目录中返回了 `prompt-injection`。接着按这个 slug 读取：

**MCP 输入**

```json
{
  "name": "aisafetyhot_get_topics",
  "arguments": {
    "slug": "prompt-injection"
  }
}
```

**实际输出（字段摘录）**

```json
{
  "topics": [
    {
      "slug": "prompt-injection",
      "name": "提示注入",
      "group": "field",
      "definition": "直接与间接提示注入：攻击面、真实案例与防御思路。",
      "tags": [
        "提示注入"
      ],
      "related": [
        "agent-security",
        "jailbreak",
        "defense"
      ],
      "links": {
        "aihot": "https://aisafetyhot.com/topics/prompt-injection",
        "items": "https://aisafetyhot.com/api/v1/items?mode=all&window=all&topic=prompt-injection"
      }
    }
  ],
  "completeness": {
    "partial": false,
    "scope": "configured_topic_catalog"
  }
}
```


把返回的 `slug` 传给下一步的 `topic`。话题标签用来筛选；单个事件有自己的 `publicId` 和时间线，两者不可混用。

<a id="search"></a>

## 3. 搜索：在一个话题下找相关新闻和论文

**输入给 Agent**

> 查最近 7 天收录的“提示注入”精选，搜索 prompt injection，先给我 3 条，区分报道和论文。

**MCP 输入**

```json
{
  "name": "aisafetyhot_search",
  "arguments": {
    "q": "prompt injection",
    "topic": "prompt-injection",
    "mode": "selected",
    "window": "7d",
    "limit": 3
  }
}
```

**实际输出（字段摘录）**

```json
{
  "query": {
    "mode": "selected",
    "category": null,
    "window": "7d",
    "q": "prompt injection",
    "by": "timeline",
    "ordering": "timelineDesc",
    "topic": "prompt-injection",
    "from": null,
    "until": null,
    "dateBasis": "filters:discoveredAt; ordering:site_timeline"
  },
  "items": [
    {
      "id": "fq81ksfn1p9l89s721i9bocp1",
      "kind": "article",
      "title": "GhostCommit 研究展示图像内容与 AI 代码审查之间的信任边界风险",
      "links": {
        "aihot": "https://aisafetyhot.com/items/fq81ksfn1p9l89s721i9bocp1",
        "original": "https://labs.cloudsecurityalliance.org/research/csa-research-note-ghostcommit-image-prompt-injection-ai-code"
      }
    },
    {
      "id": "jgfk4qjpd79q6ep9iwhnetm6o",
      "kind": "paper",
      "title": "研究揭示 CaMeL 防护在多智能体系统中失效并提出 multi-CaMeL",
      "links": {
        "aihot": "https://aisafetyhot.com/items/jgfk4qjpd79q6ep9iwhnetm6o",
        "original": "https://arxiv.org/abs/2610.05640"
      }
    },
    {
      "id": "tge6h6ie6dizwtb5ifzc9q936",
      "kind": "article",
      "title": "Zenity Labs 披露 Salesforce Agentforce 间接提示注入与零点击数据外泄漏洞",
      "links": {
        "aihot": "https://aisafetyhot.com/items/tge6h6ie6dizwtb5ifzc9q936",
        "original": "https://labs.zenity.io/post/salesbleed-0-click-data-exfiltration-on-agentforce"
      }
    }
  ],
  "page": {
    "count": 3,
    "hasMore": true
  }
}
```


结果包括 2 篇报道和 1 篇论文。搜索词 `q` 和话题 `topic` 同时生效；不要把这 3 条当作话题全集。想扩大范围可用 `mode:"all"`；想找更早的论文可用 `window:"all"`。明确要求原文发表时间时用 `by:"published"`，具体日期边界见[接入指南](agent.md#研究一个话题包括旧论文)。

<a id="content"></a>

## 4. 单篇深读：这篇论文解决什么问题？

**输入给 Agent**

> 打开上一页的 multi-CaMeL 论文，给我已有导读中的问题、方法和一句话结论，附论文原文。说明是否拿到了全文。

使用上一步返回的论文 `id`，不通过标题猜 ID：

**MCP 输入**

```json
{
  "name": "aisafetyhot_get_content",
  "arguments": {
    "id": "jgfk4qjpd79q6ep9iwhnetm6o",
    "depth": "full",
    "max_chars": 5000
  }
}
```

**实际输出（字段摘录）**

```json
{
  "item": {
    "id": "jgfk4qjpd79q6ep9iwhnetm6o",
    "kind": "paper",
    "title": "研究揭示 CaMeL 防护在多智能体系统中失效并提出 multi-CaMeL",
    "originalTitle": "Can CaMeLs Talk? Securing Multi-Agent Systems Against Indirect Prompt Injection Attacks",
    "links": {
      "aihot": "/items/jgfk4qjpd79q6ep9iwhnetm6o",
      "original": "https://arxiv.org/abs/2610.05640",
      "api": "https://aisafetyhot.com/api/v1/items/jgfk4qjpd79q6ep9iwhnetm6o"
    },
    "body": null,
    "paperReading": {
      "tldr": "论文提出 multi-CaMeL 防御，在 MultiAgentDojo 上将平均 ASR 从 12.9% 降至 0.0%。",
      "questions": [
        {
          "q": "这篇论文试图解决什么问题？",
          "lead": "单个智能体的控制流完整性无法在分层多智能体系统中直接组合，非可信数据跨边界会被下游智能体当作可信指令而劫持控制流。"
        },
        {
          "q": "论文如何解决这个问题？",
          "lead": "提出 multi-CaMeL 协议，将智能体间调用拆分为可信指令与非可信变量两个通道，并由解释器在运行时保持溯源。"
        }
      ],
      "sourceUrl": "https://arxiv.org/abs/2610.05640"
    }
  },
  "completeness": {
    "depth": "full",
    "partial": true,
    "textBudget": {
      "limit": 5000,
      "used": 5000,
      "scope": "body_and_reading_text_excluding_provenance"
    },
    "reason": "text_budget",
    "sourceText": "not_available_or_not_permitted",
    "paperReading": "available",
    "sourceTextIncluded": false,
    "paperReadingIncluded": true
  }
}
```


这次有已有论文解读，但没有返回论文全文；`partial=true` 且 `reason=text_budget` 表示 5,000 字符预算截断了解读。需要更多已存内容时可提高 `max_chars`（最多 30,000），但不会因此获取原本不可用的全文。快速浏览用 `depth:"summary"`；`full` 只读取已有内容，不会现场生成解读。

`links.aihot` 在这次单篇响应中是相对路径，使用站点根地址解析后为 [站内阅读](https://aisafetyhot.com/items/jgfk4qjpd79q6ep9iwhnetm6o)；[论文原文](https://arxiv.org/abs/2610.05640)保持原链接。

<a id="hot"></a>

## 5. 热点榜：现在关注哪些事件？

**输入给 Agent**

> 看 AI Safety HOT 当前热点榜前 3 名，给我事件名称和事件页链接。

**MCP 输入**

```json
{
  "name": "aisafetyhot_get_hot_topics",
  "arguments": {
    "limit": 3
  }
}
```

**实际输出（字段摘录）**

```json
{
  "count": 3,
  "items": [
    {
      "rank": 1,
      "title": "OpenAI 智能体越权访问澳大利亚政府网站事件",
      "publicId": "5220a39a-4f8f-473a-afb4-fdbe82bd371b",
      "links": {
        "story": "https://aisafetyhot.com/story/5220a39a-4f8f-473a-afb4-fdbe82bd371b",
        "original": "https://openai.com/index/how-we-will-do-better-for-australia"
      }
    },
    {
      "rank": 2,
      "title": "OpenAI智能体在维基平台未授权活动",
      "publicId": "e241dc2d-727a-453c-9d0c-6915d5844acb",
      "links": {
        "story": "https://aisafetyhot.com/story/e241dc2d-727a-453c-9d0c-6915d5844acb",
        "original": "https://collusion.wiki/"
      }
    },
    {
      "rank": 3,
      "title": "纽约市议会AI安全听证并传唤xAI",
      "publicId": "c6d01885-959b-416d-bfd1-170405909e93",
      "links": {
        "story": "https://aisafetyhot.com/story/c6d01885-959b-416d-bfd1-170405909e93",
        "original": "https://www.rdworldonline.com/under-oath-google-confirms-three-ai-agent-test-escapes-as-openai-anthropic-and-meta-face-nyc-lawmakers"
      }
    }
  ],
  "freshness": {
    "readAt": "2026-10-07T03:45:12.313Z",
    "computedAt": "2026-10-07T03:40:25.670Z"
  }
}
```


这是本站当前榜单的采样，不是全网热度统计。下一步用返回的 `publicId` 打开事件，不用重新搜索标题。

<a id="story"></a>

## 6. 事件时间线：这件事最近有什么进展？

**输入给 Agent**

> 打开榜首的澳大利亚政府网站事件，给我最新进展和最近 3 篇报道，保留原文时间与链接。

**MCP 输入**

```json
{
  "name": "aisafetyhot_get_story",
  "arguments": {
    "public_id": "5220a39a-4f8f-473a-afb4-fdbe82bd371b",
    "report_limit": 3,
    "depth": "full"
  }
}
```

**实际输出（字段摘录）**

```json
{
  "story": {
    "publicId": "5220a39a-4f8f-473a-afb4-fdbe82bd371b",
    "title": "OpenAI 智能体越权访问澳大利亚政府网站事件",
    "reportCount": 34,
    "sourceCount": 23,
    "latestAt": "2026-10-07T01:00:37.000Z",
    "latest": "OpenAI 高管在澳大利亚议会听证会上道歉并承认通报失误，公司支持强制 AI 事件报告制度。",
    "reports": [
      {
        "title": "Toby Walsh：OpenAI 赴澳道歉，却未回答智能体入侵政府网站的关键问题",
        "sourcePublishedAt": "2026-10-07T01:00:37.000Z",
        "publishedDate": null,
        "source": {
          "name": "The Guardian · 人工智能"
        },
        "links": {
          "aihot": "https://aisafetyhot.com/items/xuxkvu8ll4wvly6bfx87tk0id",
          "original": "https://www.theguardian.com/commentisfree/2026/oct/07/openai-australia-apology-without-answering-key-questions"
        }
      },
      {
        "title": "澳大利亚数字经济部长接受 OpenAI 道歉但称不会依赖，政府工作组数周内提交报告",
        "sourcePublishedAt": "2026-10-07T00:06:00.000Z",
        "publishedDate": null,
        "source": {
          "name": "AAP via The Canberra Times"
        },
        "links": {
          "aihot": "https://aisafetyhot.com/items/xijbtvl606co24nls03bgczym",
          "original": "https://www.canberratimes.com.au/story/9363930/dont-rely-on-it-eyes-narrow-at-openai-apology"
        }
      },
      {
        "title": "OpenAI 在澳大利亚议会听证中说明训练期实时监控机制",
        "sourcePublishedAt": "2026-10-06T23:58:00.000Z",
        "publishedDate": null,
        "source": {
          "name": "Simon Willison"
        },
        "links": {
          "aihot": "https://aisafetyhot.com/items/acfujwtjde1n5ms0gddtxdzns",
          "original": "https://simonwillison.net/2026/Oct/6/victoria-kim"
        }
      }
    ]
  },
  "page": {
    "count": 3,
    "hasMore": true
  },
  "completeness": {
    "scope": "public_story_reports_and_collected_discussions",
    "partial": true,
    "reportsPartial": true,
    "discussionsPartial": false,
    "discussionLimit": 50,
    "dates": "reports.publishedAt is a legacy timeline timestamp; sourcePublishedAt and publishedDate are original dates"
  }
}
```


这次事件详情统计到 34 篇报道、23 个来源，本页只展示最近 3 篇。报道有观点文章，也有新闻跟进，不能把每篇报道都算成一次新事故。`sourcePublishedAt` / `publishedDate` 是原文日期；旧字段 `publishedAt` 是兼容的时间线时刻。若要完整时间线，应沿 `page.nextCursor` 翻页；讨论区是本站已经收集的讨论，不代表全网讨论。

<a id="reports"></a>

## 7. 报告：读最新周报，也能查日/月报

**输入给 Agent**

> 读最新一期周报，告诉我覆盖哪一周、有哪些主题，并给出报告链接。

先列出现有期号，不猜今天是否已经生成了报告：

**MCP 输入**

```json
{
  "name": "aisafetyhot_get_daily",
  "arguments": {
    "period": "weekly",
    "mode": "list",
    "limit": 1
  }
}
```

**实际输出（字段摘录）**

```json
{
  "period": "weekly",
  "items": [
    {
      "key": "2026-W40",
      "period": "weekly",
      "revision": 1,
      "title": "智能体越界事件密集披露，监管与评测同步收紧",
      "generatedAt": "2026-10-05T02:00:19.417Z",
      "windowStart": "2026-09-27T16:00:00.000Z",
      "windowEnd": "2026-10-04T16:00:00.000Z",
      "links": {
        "aihot": "https://aisafetyhot.com/weekly/2026-W40",
        "api": "https://aisafetyhot.com/api/v1/reports/weekly/2026-W40"
      }
    }
  ]
}
```


再读取返回的期号：

**MCP 输入**

```json
{
  "name": "aisafetyhot_get_daily",
  "arguments": {
    "period": "weekly",
    "key": "2026-W40"
  }
}
```

**实际输出（字段摘录）**

```json
{
  "report": {
    "period": "weekly",
    "key": "2026-W40",
    "title": "AI Safety HOT 周报 · 2026-W40",
    "windowStart": "2026-09-27T16:00:00.000Z",
    "windowEnd": "2026-10-04T16:00:00.000Z",
    "links": {
      "aihot": "https://aisafetyhot.com/weekly/2026-W40",
      "api": "https://aisafetyhot.com/api/v1/reports/weekly/2026-W40"
    },
    "lead": {
      "title": "智能体越界事件密集披露，监管与评测同步收紧"
    },
    "sections": [
      {
        "label": "智能体越界事件密集披露",
        "items": [
          {
            "title": "HiddenLayer 分析 AI 智能体入侵 Hugging Face 时留在公开仓库的作案工具",
            "links": {
              "original": "https://www.hiddenlayer.com/research/hugging-face-agent-intrusion-analysis",
              "aihot": "https://aisafetyhot.com/items/gbzkostf1w8upzf0m46me7new"
            }
          }
        ]
      },
      {
        "label": "奖励作弊泛化为攻击行为",
        "items": [
          {
            "title": "Anthropic 训练出奖励寻求者 Hacker-Opus，奖励作弊泛化为越权网络攻击",
            "links": {
              "original": "https://alignment.anthropic.com/2026/reward-seeker/",
              "aihot": "https://aisafetyhot.com/items/tkvs0g6dh8lngoenp434ubrrh"
            }
          }
        ]
      },
      {
        "label": "前沿模型网络能力升级与评测",
        "items": [
          {
            "title": "UK AISI 评测 GPT-6 Astra 是否会发起未经授权的供应链攻击",
            "links": {
              "original": "https://arxiv.org/abs/2609.38415v1",
              "aihot": "https://aisafetyhot.com/items/rviswmq8ccsfx1oqsyumccrwy"
            }
          }
        ]
      },
      {
        "label": "推理链与工具链攻击面",
        "items": [
          {
            "title": "研究者利用加密推理块跨模型兼容性窃取专有 LLM 推理链",
            "links": {
              "original": "https://arxiv.org/abs/2608.09867",
              "aihot": "https://aisafetyhot.com/items/mceic1zdxf3w73k37d207b64l"
            }
          }
        ]
      },
      {
        "label": "监管调查与问责压力上升",
        "items": [
          {
            "title": "OpenAI 智能体入侵数十家机构后，法律与监管风险持续累积",
            "links": {
              "original": "https://www.ft.com/content/2c24ece3-ac99-43a8-b0e6-4a3867e37ebf?syn-25a6b1a6=1",
              "aihot": "https://aisafetyhot.com/items/wbm0grojlw4fzsz8n19f7uuo0"
            }
          }
        ]
      }
    ]
  }
}
```


为便于阅读，上面每个主题只摘录第一条内容。报告的完整返回包含更多条目。本期窗口换算为北京时间是 **9 月 28 日 00:00 至 10 月 5 日 00:00（不含终点）**。最新已发布周报不一定包含今天的新闻；要实时信息，用示例 1。

**日报与月报也已实际读取**

同一个工具切换 `period` 即可。下面分别给出实际调用和报告元信息，正文通过同一调用返回：

**MCP 输入**

```json
{
  "name": "aisafetyhot_get_daily",
  "arguments": {
    "period": "daily",
    "key": "2026-10-07"
  }
}
```

**实际输出（字段摘录）**

```json
{
  "report": {
    "period": "daily",
    "key": "2026-10-07",
    "title": "AI 安全日报 · 2026-10-07",
    "windowStart": "2026-10-06T00:00:00.000Z",
    "windowEnd": "2026-10-07T00:00:00.000Z",
    "links": {
      "aihot": "https://aisafetyhot.com/daily/2026-10-07",
      "api": "https://aisafetyhot.com/api/v1/reports/daily/2026-10-07"
    },
    "lead": {
      "title": "法院维持五角大楼将 Anthropic 列为供应链风险的决定"
    }
  }
}
```


**MCP 输入**

```json
{
  "name": "aisafetyhot_get_daily",
  "arguments": {
    "period": "monthly",
    "key": "2026-09"
  }
}
```

**实际输出（字段摘录）**

```json
{
  "report": {
    "period": "monthly",
    "key": "2026-09",
    "title": "AI Safety HOT 月报 · 2026-09",
    "windowStart": "2026-08-31T16:00:00.000Z",
    "windowEnd": "2026-09-30T16:00:00.000Z",
    "links": {
      "aihot": "https://aisafetyhot.com/monthly/2026-09",
      "api": "https://aisafetyhot.com/api/v1/reports/monthly/2026-09"
    },
    "lead": {
      "title": "GLM-5.3 自主漏洞利用能力引评测警示"
    }
  }
}
```


省略 `key` 会读取该周期最新已发布报告；`mode:"list"` 可以先列期号。报告是已有版本，不是临时生成，也不是未来新闻预测。

<a id="pagination"></a>

## 继续读：不要把第一页当成全部结果

示例 3 返回 `hasMore=true`。本次已经用它的 `page.nextCursor` 接着读了第二页，保持搜索词、话题、模式和时间窗口不变。以下游标是这次调用得到的实际值；日后复现时，使用你刚收到的新游标。

<details>
<summary>第二页的实际 MCP 输入（包含完整游标）</summary>

```json
{
  "name": "aisafetyhot_search",
  "arguments": {
    "q": "prompt injection",
    "topic": "prompt-injection",
    "mode": "selected",
    "window": "7d",
    "limit": 3,
    "cursor": "it4.eyJhIjoxNzkxMjE5ODczMzU0LCJpIjoidGdlNmg2aWU2ZGl6d3RiNWlmemM5cTkzNiIsImMiOiJhOGUzYWYwYzhhOTIiLCJ0IjoxNzkxMzQ0NzQ4MDc1fQ"
  }
}
```

</details>

**实际输出（字段摘录）**

```json
{
  "items": [
    {
      "id": "ynwg1rgqi6x8y1unz4gea6al1",
      "kind": "paper",
      "title": "研究重测 15 个提示注入检测器：基准分数难以预测 Agent 部署表现",
      "links": {
        "aihot": "https://aisafetyhot.com/items/ynwg1rgqi6x8y1unz4gea6al1",
        "original": "https://arxiv.org/abs/2610.03448"
      }
    },
    {
      "id": "q2y5bci1imhe6tcm3nf8x4w5s",
      "kind": "article",
      "title": "Flowise CSV Agent 节点存在提示注入远程代码执行漏洞（CVE-2026-70477）",
      "links": {
        "aihot": "https://aisafetyhot.com/items/q2y5bci1imhe6tcm3nf8x4w5s",
        "original": "https://github.com/FlowiseAI/Flowise/security/advisories/GHSA-5xvg-pmgg-3mxr"
      }
    },
    {
      "id": "ml5uqw32x8ztatfci481b37b0",
      "kind": "article",
      "title": "研究者在 MCP 连接阶段复现提示注入与跨调用方缓存投毒",
      "links": {
        "aihot": "https://aisafetyhot.com/items/ml5uqw32x8ztatfci481b37b0",
        "original": "https://webofmike.com/mcp-discovery-prompt-injection"
      }
    }
  ],
  "page": {
    "count": 3,
    "hasMore": true
  }
}
```

第二页仍有后续。如果用户要求完整列表，应继续到 `hasMore=false`；只需要几条时，可以停止，并说明本次范围。精选集合的长期增量同步是另一种用法，见[快照与变化同步](agent.md#续接精选变化)。
