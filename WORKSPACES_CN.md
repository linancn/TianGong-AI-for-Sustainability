---
title: 课题工作区指南
---

# 课题工作区指南

本文档说明如何在课题缓存目录（`.cache/tiangong/<STUDY_ID>/`）内执行 TianGong 研究工作流。它是 `AGENTS_CN.md`（涵盖仓库级开发规范）和 `specs/prompts/default.md` 中 Codex 简报模板的补充。

## 1. 初始化工作区

1. 运行初始化脚本：
   ```bash
   uv run python scripts/ops/init_study_workspace.py --study-id <STUDY_ID>
   ```
   会生成如下目录结构：
   ```
   .cache/tiangong/<STUDY_ID>/
   ├── acquisition/   # 原始 CLI 输出（JSON/CSV）
   ├── processed/     # 规范化数据集与流水线说明
   ├── docs/          # Runbook、蓝图、研究笔记
   ├── models/        # 模型输入/输出
   ├── figures/       # 图表与可视化素材
   ├── logs/          # 执行历史、异常、准备情况
   └── scripts/       # 课题专用脚本或 Notebook
   ```
2. 在 `docs/runbook.md` 中列出确定性命令队列（按执行顺序），供 Codex 与人工操作员遵循。
3. 在 `docs/study_brief.md` 记录研究目标、阶段计划与约束条件。

## 2. 核心文件

- `config.yaml`：自动生成，包含 `study_id` 与 `auto_execute`。若需调整可重新运行初始化脚本并加 `--force`。
- `docs/runbook.md`：记录命令顺序、缓存路径、下一步行动，执行前保持最新。
- `docs/study_brief.md`：概述阶段目标、提示模版与交付要求。
- `logs/run_history.md`：每次执行命令后追加时间戳、命令、主要输出路径。
- `logs/exceptions.md`：在重试前记录速率限制、凭据缺失等异常及缓解方案。
- `docs/gaps.md`：汇总尚未解决的数据缺口与后续动作。
- `processed/README.md`：维护处理后产物与对应来源命令/脚本的对照表。

## 3. 执行规则

1. 默认使用 CLI：
   ```bash
   uv run tiangong-research <command> [...]
   ```
   若 CLI 尚不支持，方可在 `scripts/` 目录编写临时脚本，并在 runbook 备注原因，同时向 `tasks/backlog.yaml` 添加待办以补齐 CLI 能力。
2. 所有输出（JSON/Markdown/图表/模型）应存放在 `.cache/tiangong/<STUDY_ID>/` 内的对应子目录。
3. 课题专用脚本、Notebook 与输出不得提交至仓库；应保留在工作区 `scripts/` 目录内。
4. 使用 LLM 综合分析时：
   - 默认使用 `specs/prompts/default.md`（别名 `default`）。
   - 通过 CLI 参数传递提示变量（`--prompt-template`、`--prompt-language`、`--prompt-variable key=value`）。
   - 将响应（JSON/Markdown）保存至 `docs/` 或 `processed/`，确保可追溯至确定性输入。

## 4. Dry-Run 与可观测性

- 规划阶段设置 `--dry-run`（或 `ExecutionOptions.dry_run`）；将生成的计划存储至 `logs/run_history.md`。
- 使用 `logs/exceptions.md` 记录 API 速率限制、缺失凭据或降级行为，包含重试/退避说明。
- 启动复杂工作流时填充 `ExecutionOptions.observability_tags`，以对齐自动化计划。

## 5. 收尾流程

1. 确保所有报告、图表和数据集的引用路径均指向工作区内的文件。
2. 在 `docs/gaps.md` 更新待办事项，并通过仓库 PR 更新 `tasks/backlog.yaml`（如需后续工作）。
3. 仅在验证后将经过验证的输出（报告、数据）推广至长期存储或文档。
4. 保留完整工作区以支持可复现性；除非保留政策要求，否则不删除中间文件。

## 6. 快速参考

| 任务 | 命令 |
|------|------|
| 初始化工作区 | `uv run python scripts/ops/init_study_workspace.py --study-id <STUDY_ID>` |
| 列出数据源 | `uv run tiangong-research sources list` |
| 验证关键数据源 | `uv run tiangong-research sources verify <id>` |
| 运行研究工作流 | `uv run tiangong-research research workflow <...>` |
| 生成单行提示 | `uv run python scripts/tooling/compose_inline_prompt.py` |

仓库级开发指南请参阅 `AGENTS_CN.md`。本指南专门针对课题工作区操作。
