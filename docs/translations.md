# 英文和日文日报的免费自动翻译

英文和日文 README 的固定指南由人工辅助翻译；日报正文由中文公开归档生成英文、日文版本，分别保存在 `daily/en/YYYY/` 和 `daily/ja/YYYY/`，最新一期同时进入对应 README 的专用翻译区块。中文 `README.md` 的 `daily:start/end`、`latest:start/end` 发布标记和中文日报、论文清单、`status.json` 均不由此流程修改。

## 默认关闭，由维护者启用

工作流默认关闭日报自动翻译和发布。合并到仓库默认分支后，维护者可在 **Settings → Secrets and variables → Actions → Variables** 添加仓库变量 `TRANSLATION_ENABLED`，值填 `true`。无需 API Key 或其他秘密。

维护者还需在仓库的 **Settings → Actions → General → Workflow permissions** 允许写入仓库内容；组织级策略、分支保护或规则集也必须允许该机器人正常提交。只有公开仓库、默认分支、变量已启用的定时任务或手动 `translate` 任务拥有发布权限。私有仓库的任务会跳过。`validate` 检查和 PR 检查只执行离线单元测试、只读计划和空白检查，不能下载模型、翻译或发布。手动任务默认选项也是 `dry-run`。

公开仓库向 `main` 或 `docs/readme-en-ja` 推送翻译核心、模型编排或样例脚本变更时，另有 `model-smoke` 检查；仅调整文档、缓存或离线测试不重复下载模型。该检查在免费 CPU runner 上翻译当前中文日报的八个英日样例，检查真实模型的格式和数值，并在日志中输出公开原文和译文供语义审查。检查只有只读权限，不修改 README、归档或缓存，不提交或发布，不使用秘密，也不上传 artifact。样例通过仅能证明这些样例通过，不能保证未来整期日报的语义准确性。

此工作流**不会同步 fork 的中文文件**。它只读获取 `wuyoscar/AISafetyHot-Hub` 的最新 `main`，把最近七天的中文文本放进 runner 临时目录，记录完整的四十位提交 SHA；不检出或执行上游仓库的代码。中文原文和相关论文链接在需要时指向该上游提交。

## 不使用付费模型服务

推理使用 Apache-2.0 许可的 [Qwen2.5-7B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF) 的 Q4_K_M 两分片模型，通过 [llama.cpp](https://github.com/ggml-org/llama.cpp) 在标准 `ubuntu-24.04` runner 的 CPU 上运行。公开仓库的标准 Linux runner 为 4 CPU、16 GB 内存，按 [GitHub 官方说明](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)可免费使用。

流程不支持私有仓库、付费 GPU 或 larger runner，不调用外部推理 API，也不上传 Actions cache 或 artifact，避免引入这类存储费用。模型和二进制每次只在需要补译时下载到 `RUNNER_TEMP`，运行结束后清理；完整译文缓存命中时仅离线重渲染元数据，不下载模型。

模型固定到版本 `bb5d59e06d9551d752d08b292a50eb208b07ab1f`，服务别名为 `Qwen2.5-7B-Instruct-Q4_K_M`。两个分片必须下载到同一临时目录，分别核验精确字节数和 SHA-256，再用第一片启动服务器，llama.cpp 会加载同目录的第二片。

| 分片文件 | 字节数 | SHA-256 |
|---|---|---|
| `qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` | 3993201344 | `dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db` |
| `qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf` | 689872288 | `539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a` |

llama.cpp 固定为 `b11499`，Ubuntu 二进制包 SHA-256 为 `19ce793dad78858ec5c89231975d0aa71de31219089bcd06dc5ebe01b403c00d`。下载后校验哈希，解包使用安全路径过滤。服务只监听 `127.0.0.1:8080`，使用四线程、8192 上下文、单并行槽、无 GPU、关闭推理模式；翻译请求固定连接本机，不接受外部服务地址或 API Key。

## 时间、覆盖范围与验证

中文配信方在每天北京时间 **08:00（UTC+8）** 发布日报。翻译工作流在每小时的 **17 分**检查，通常当天首轮为北京 **08:17**，译文在推理和校验完成后发布。08:00 是中文的发布时间，不是译文完成时间保证。[GitHub 定时任务可能延迟，公开仓库连续六十天无活动时会自动停用](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)，需要维护者重新启用。

首次初始化只翻译最新一期；之后检查最近七天内已纳入翻译起始日之后的缺失或更正，不自动补齐全部历史。`translations/en/` 和 `translations/ja/` 保存逐项译文缓存、版本与来源信息；其中 SHA-256 是中文日报的语义内容指纹，**不是** `status.json` 中的论文 ID 哈希。论文数等展示元数据更新可复用译文，不调用模型。

按日期从新到旧执行，优先完成最新一期，再补近期缺失或更正。每个日期最多发出 128 次本机推理请求，每批四个文本单元，包含受控的重试；任务总超时为 240 分钟。脚本检查项目完整性、数字和量纲、专名占位符、JSON、链接以及翻译区块标记。每个日期发布前再次只读获取中文原文并核验语义指纹；出现新一期或该日正文变化时拒绝提交该日期，留待下一次重新运行。仅元数据变化可在下次离线更新。

每个日期通过验证后，仅提交 `README.en.md`、`README.ja.md`、`daily/en/`、`daily/ja/`、`translations/`，提交说明为「发布：英文和日文 AI 安全日报」。使用普通推送；若与中文发布器或其他提交冲突，推送失败后下次重试，不强制推送。较早日期失败时任务仍报告失败，但已经验证并推送的最新一期与其他日期会保留，不因补历史失败而回退。不完整的本地缓存不会作为 artifact 上传或推送，也不会改动已发布的译文。机器翻译和中文源摘要都可能有误，重要事实、数字、结论请核对原始来源。

## 本地检查和离线重建

使用 Python 3.12，无需安装第三方依赖。只读检查上游最新内容，不下载模型、不改文件：

```bash
python -m unittest discover -s scripts/tests -v
python scripts/run_translation_workflow.py --mode dry-run
```

仅查看本地中文归档与缓存的翻译计划：

```bash
python scripts/translate_daily.py --dry-run
```

缓存完整时，可离线重建本地归档及 README 翻译区块，不启动模型：

```bash
python scripts/translate_daily.py --offline
git diff --check
```

不完整缓存会拒绝离线发布。若核验指定来源副本，可使用 `--source-root`、`--source-repository wuyoscar/AISafetyHot-Hub`、`--source-revision <40位SHA>` 和 `--verify-source`。修改模型版本或翻译提示时，必须同步递增 `scripts/translate_daily.py` 的 `PROMPT_VERSION`，记录新模型版本和哈希，并完成离线测试及实际推理样例的回归验证，再由维护者审查启用。旧版机器缓存因此需要重新验证和翻译，不能把更换模型直接当作已有译文的质量保证。
