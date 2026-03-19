# Deep V Studio

[🇬🇧 English](README.md)

> **多模型视频生成工作站** — 基于 [LTX-2](https://github.com/Lightricks/LTX-2) 构建，扩展 BYOK 云端模型接入能力。

[![上游仓库](https://img.shields.io/badge/upstream-Lightricks%2FLTX--2-blue?logo=github)](https://github.com/Lightricks/LTX-2)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

## 愿景

Deep V Studio 将 LTX-2 从单模型推理管线升级为**统一视频生成中心**，通过一套接口同时支持本地模型和云端 API。

**核心目标：**

| 能力 | 状态 | 说明 |
|---|---|---|
| 🏠 本地推理 | ✅ 继承自上游 | 通过 `ltx-pipelines` 运行 LTX-2/2.3 DiT 模型 |
| ☁️ BYOK 云端模型 | 🚧 第一阶段 | Seedance 2.0、Veo 3.1、NanoBanana 2/Pro |
| 🔌 Provider 抽象层 | ✅ 已完成 | 统一 ABC 接口 + 自动配置 |
| 🖥️ 桌面应用 | 📋 规划中 | 本地 UI：模型选择、生成、对比 |

### 为什么选择 BYOK？

**Bring Your Own Key**（自带密钥）— 使用你已有的 API 订阅，接入任意支持的模型。不锁定供应商、不加价转售。一条提示词 → 选择引擎 → 生成视频。

## 架构

```
packages/
├── ltx-core/                  # 核心模型组件（来自上游）
├── ltx-pipelines/             # 推理管线
│   └── src/ltx_pipelines/
│       ├── providers/         # ★ BYOK Provider 抽象层（新增）
│       │   ├── base.py        # VideoGenerationProvider 抽象基类
│       │   ├── config.py      # API 密钥解析（环境变量 → .env → TOML）
│       │   ├── registry.py    # Provider 发现与实例化
│       │   ├── veo.py         # Google Veo 3.1
│       │   ├── seedance.py    # 字节跳动 Seedance 2.0
│       │   └── nanobanana.py  # NanoBanana 2 & Pro
│       └── *.py               # LTX-2 管线实现
└── ltx-trainer/               # 训练与微调工具
```

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/ldc861117/deep-v-studio.git
cd deep-v-studio

# 配置环境
uv sync --frozen
source .venv/bin/activate

# 配置云端 Provider（以 Veo 3.1 为例）
export VEO_API_KEY="your-api-key-here"
```

### API 密钥配置

密钥按以下优先级解析：

1. **环境变量** — `export VEO_API_KEY=...`
2. **`.env` 文件** — 放在项目根目录
3. **TOML 配置文件** — `~/.config/deep-v-studio/providers.toml`

```toml
# ~/.config/deep-v-studio/providers.toml
[providers.veo]
api_key = "your-key"

[providers.seedance]
api_key = "your-key"
```

## 与上游仓库的关系

本项目是 [Lightricks/LTX-2](https://github.com/Lightricks/LTX-2) 的 **diverging fork（分化型分支）**。我们持续从上游同步核心模型改进，同时在其上构建独立的产品层。

### Fork 管理策略

```
Lightricks/LTX-2 (upstream)          ldc861117/deep-v-studio (origin)
     │                                        │
     │  核心模型更新                            │  BYOK Provider、桌面应用、
     │  (ltx-core, pipelines)                 │  产品功能
     │                                        │
     └──── 定期同步 ─────────────────────────►│
           (merge upstream/main)              │
```

**同步策略：**
- `upstream` remote 指向 `Lightricks/LTX-2`
- 核心包（`ltx-core`、`ltx-trainer`）定期从上游合并
- 我们新增的内容（`providers/`、`scripts/`、规范文件）与上游零冲突
- 同步命令：
  ```bash
  git fetch upstream
  git merge upstream/main --no-edit
  # 解决冲突（如有），然后推送
  git push origin main
  ```

**不修改上游代码：**
- `ltx-core/` 包内部实现
- `ltx-pipelines/` 中已有的管线实现
- 模型检查点格式和兼容性

**在上游基础上新增：**
- `providers/` — BYOK 云端 Provider 抽象层
- `AGENTS.md`、`GEMINI.md` — AI 辅助开发规范
- `scripts/` — 自动化与任务分发工具
- `docs/superpowers/` — 设计文档与实施计划
- 桌面应用（规划中）

## 开发范式

本项目采用 **AI 辅助开发范式**，整合 [Superpowers](https://github.com/obra/superpowers) 工作流与 Jules CLI 并行任务执行。

| 角色 | 职责 |
|---|---|
| **架构师** (Gemini) | 研究、设计、规划、代码审查、任务分发 |
| **建造者** (Jules) | 在隔离文件边界内执行 TDD 开发 |
| **决策者** (User) | 审批、优先级排序、触发合并 |

详见 [`AGENTS.md`](AGENTS.md)。

### 常用命令

```bash
# 规范检查与格式化
uv run ruff check .
uv run ruff format .

# 运行测试
uv run pytest                              # 全部测试
uv run pytest -k "test_providers"          # 仅 Provider 测试

# 同步上游
git fetch upstream && git merge upstream/main
```

## 可用管线（继承自 LTX-2）

| 管线 | 说明 |
|---|---|
| [TI2VidTwoStagesPipeline](packages/ltx-pipelines/src/ltx_pipelines/ti2vid_two_stages.py) | 生产级文本/图像到视频，支持 2x 上采样 |
| [TI2VidTwoStagesHQPipeline](packages/ltx-pipelines/src/ltx_pipelines/ti2vid_two_stages_hq.py) | 二阶采样器（更少步数，更高质量） |
| [DistilledPipeline](packages/ltx-pipelines/src/ltx_pipelines/distilled.py) | 最快推理，8 个预定义 sigma |
| [ICLoraPipeline](packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py) | LoRA 驱动的视频到视频 / 图像到视频 |
| [A2VidPipelineTwoStage](packages/ltx-pipelines/src/ltx_pipelines/a2vid_two_stage.py) | 音频条件视频生成 |

模型下载和详细管线文档请参阅[上游 README](https://github.com/Lightricks/LTX-2#readme)。

## 许可证

本项目继承上游 LTX-2 的 [Apache 2.0 许可证](LICENSE)。

---

<sub>Forked from [Lightricks/LTX-2](https://github.com/Lightricks/LTX-2) • 核心模型由 [Lightricks](https://ltx.io) 开发</sub>
