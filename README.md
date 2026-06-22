# PPT Maker

一个本地运行的 Web 应用，分两阶段（**大纲设计** → **PPT 生成**）用大模型自动制作 PPT，支持导出 `.pptx` 与 `.pdf`。

两阶段可独立配置不同大模型（OpenAI 兼容 API 或 Anthropic Claude）。

![Tabs](docs/superpowers/specs/screenshots-readme-placeholder.txt)

> 单页前端，零构建步骤：Tailwind 通过 CDN 加载，原生 JavaScript。

---

## 目录

- [特性](#特性)
- [架构](#架构)
- [快速开始](#快速开始)
- [使用流程](#使用流程)
- [支持的模型服务](#支持的模型服务)
- [环境变量](#环境变量)
- [API 概览](#api-概览)
- [项目结构](#项目结构)
- [测试](#测试)
- [常见问题](#常见问题)
- [系统依赖](#系统依赖)
- [文档](#文档)
- [许可证](#许可证)

---

## 特性

- **两阶段流水线**：先由"大纲模型"生成 PPT 结构，再由"PPT 生成模型"产出成品；两个阶段可独立选模型。
- **多模型兼容**：同一套代码支持 OpenAI 兼容协议（OpenAI / DeepSeek / Moonshot / Zhipu / Ollama …）和 Anthropic Claude。
- **结构可编辑**：前端支持增删改大纲页面，调整页面布局、要点。
- **风格与配图**：4 种风格（商务 / 学术 / 极简 / 创意）× 3 种配图模式（占位图 / AI 生成 / 不插图）。
- **.pptx + .pdf 双导出**：PDF 通过本地 LibreOffice 转换，失败时不阻塞 .pptx 下载。
- **本地优先**：API Key 仅保存在本机 SQLite 数据库（`data/app.db`），不上传任何服务端。

---

## 架构

```
┌─────────── Browser (single-page UI) ───────────┐
│  配置 │ 大纲 │ 生成 │ 历史                       │
└────────────────────┬───────────────────────────┘
                     │ HTTP/JSON
┌────────────────────▼───────────────────────────┐
│              FastAPI (app/main.py)              │
│  /api/config │ /api/outline │ /api/ppt          │
│  /api/history │ /api/download                  │
└─────┬─────────────┬─────────────┬───────────────┘
      │             │             │
      ▼             ▼             ▼
 ┌─────────┐  ┌──────────┐  ┌──────────┐
 │ Config  │  │ Outline  │  │   PPT    │
 │ Store   │  │ Service  │  │ Service  │
 │ (SQLite)│  │          │  │          │
 └─────────┘  └────┬─────┘  └────┬─────┘
                   │             │
                   ▼             ▼
              ┌────────┐    ┌────────┐    ┌──────────┐
              │  LLM   │    │ python │    │LibreOffi-│
              │Provider│    │ -pptx  │    │ce (.pdf) │
              └────────┘    └────────┘    └──────────┘
```

详细的模块拆分见 [docs/superpowers/specs/2026-06-21-ppt-maker-design.md](docs/superpowers/specs/2026-06-21-ppt-maker-design.md)。

---

## 快速开始

### 1. 克隆与安装

```bash
git clone git@github.com:longyaoyoudu/ppt_maker.git
cd ppt_maker
pip install -r requirements.txt
```

### 2. （可选）安装 LibreOffice

`.pptx → .pdf` 转换依赖 LibreOffice。未安装时仍可正常生成 `.pptx`，只是没有 PDF 下载。

- **macOS**：`brew install --cask libreoffice`
- **Ubuntu / Debian**：`sudo apt-get install libreoffice`
- **Windows**：从 <https://www.libreoffice.org/download> 安装，并把 `soffice.exe` 加入 PATH

### 3. 启动

```bash
python run.py
```

浏览器访问 <http://127.0.0.1:8000>。

---

## 使用流程

1. **模型配置**（首次必做）：为"大纲设计"和"PPT 生成"两个阶段分别填写 Provider、Base URL（仅 OpenAI 兼容需要）、API Key、Model Name，点击「保存」。
2. **大纲设计**：输入主题（可选补充要求、PDF/Word 附件），点击「生成大纲」。生成后可直接增删改页面。附件中的文本会被自动提取并加入 LLM 上下文。
3. **生成 PPT**：选择大纲 → 选风格 → 选配图模式 → 点击「生成 PPT」。完成后会显示 `.pptx` 与 `.pdf` 下载链接。
4. **历史记录**：所有大纲与生成结果持久化保留，可随时回看或重新下载附件。

---

## 支持的模型服务

任何暴露 OpenAI 兼容 `chat/completions` 接口的服务都支持。

| 服务 | Provider 选项 | Base URL 示例 | 备注 |
|---|---|---|---|
| OpenAI | `openai` | `https://api.openai.com/v1` | 官方 |
| DeepSeek | `openai` | `https://api.deepseek.com` | 不带 `/v1` 也可 |
| Moonshot (Kimi) | `openai` | `https://api.moonshot.cn/v1` | |
| Zhipu (GLM) | `openai` | `https://open.bigmodel.cn/api/paas/v4` | |
| Ollama（本地） | `openai` | `http://127.0.0.1:11434/v1` | 任意 key 即可 |
| Anthropic Claude | `claude` | 留空 | `claude-sonnet-4-6`、`claude-opus-4-7` 等 |

---

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `PPTM_DATA_DIR` | `data/` | SQLite 数据库存放目录 |
| `PPTM_OUTPUTS_DIR` | `outputs/` | 生成的 `.pptx` / `.pdf` 与临时图片目录 |

默认配置开箱即用；自定义示例：

```bash
PPTM_DATA_DIR=/var/lib/pptm PPTM_OUTPUTS_DIR=/var/lib/pptm/outputs python run.py
```

---

## API 概览

完整契约见 [docs/superpowers/specs/2026-06-21-ppt-maker-design.md](docs/superpowers/specs/2026-06-21-ppt-maker-design.md) §8。

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/api/health` | 健康检查 |
| `GET` / `PUT` | `/api/config/{stage}` | 读写阶段模型配置（`stage=outline\|ppt`） |
| `POST` | `/api/outline/generate` | 调用大纲 LLM 生成结构化大纲（multipart：topic + 可选 requirements + 可选 files） |
| `PUT` | `/api/outline/{id}` | 更新已存在的大纲 |
| `GET` | `/api/outline/{id}/source/{filename}` | 下载大纲关联的原始附件 |
| `POST` | `/api/ppt/generate` | 基于大纲生成 `.pptx`（可选转 `.pdf`） |
| `GET` | `/api/history/outlines` | 大纲历史列表 |
| `GET` | `/api/history/generations` | 生成历史列表 |
| `GET` | `/api/download/{generation_id}/{pptx\|pdf}` | 下载产物文件 |

错误约定：

- `400` — 配置缺失或请求参数无效
- `404` — 资源不存在（大纲 / 生成记录 / 文件）
- `500` — 大纲解析失败
- `502` — LLM 上游错误（含余额不足、鉴权失败、网络等）

---

## 项目结构

```
ppt_maker/
├── app/
│   ├── main.py                  # FastAPI 入口与所有路由
│   ├── models.py                # Pydantic 模型（Outline / OutlinePage / ...）
│   ├── prompts.py               # LLM Prompt 模板
│   ├── errors.py                # 域异常 → HTTPException 映射
│   ├── db.py                    # SQLite 连接与建表
│   ├── config_store.py          # 模型配置持久化
│   ├── history_store.py         # 大纲 / 生成历史持久化
│   ├── llm/
│   │   ├── base.py              # LLMProvider 抽象与 LLMError
│   │   ├── openai_provider.py   # OpenAI 兼容（含 DeepSeek / Moonshot ...）
│   │   ├── claude_provider.py   # Anthropic Claude
│   │   └── factory.py           # 配置 → provider 构建
│   └── services/
│       ├── outline_service.py   # 大纲生成 + JSON 解析重试
│       ├── ppt_service.py       # python-pptx 渲染
│       ├── image_service.py     # 占位图 / AI 配图
│       └── pdf_service.py       # LibreOffice .pptx → .pdf
├── static/
│   └── index.html               # 单页前端（无构建步骤）
├── tests/                       # pytest 套件（56+ 用例）
├── docs/
│   └── superpowers/
│       ├── specs/               # 设计文档
│       └── plans/               # 实施计划
├── run.py                       # 启动入口
├── requirements.txt
└── README.md
```

---

## 测试

```bash
pytest -v
```

测试覆盖：单元测试（LLM provider 抽象、ConfigStore、HistoryStore、Pydantic 模型校验）+ 集成测试（API 端点、PDF 转换桩）。LLM 与 LibreOffice 都被桩掉，无需真实 key 或 LibreOffice 即可跑全套。

---

## 常见问题

<details>
<summary><b>启动后浏览器 alert 弹出 <code>OpenAI provider error: Error code: 402 ... Insufficient Balance</code></b></summary>

API Key 对应的账号余额为 0。充值即可，<strong>不需要改任何配置</strong>。

- DeepSeek：<https://platform.deepseek.com/top_up>
- OpenAI：<https://platform.openai.com/account/billing>
</details>

<details>
<summary><b>生成 .pptx 成功但没有 PDF 下载链接</b></summary>

PDF 由 LibreOffice 转换；常见原因：
1. 未安装 LibreOffice 或 `soffice` 不在 PATH
2. LibreOffice 子进程被系统权限拦截

`.pptx` 仍可正常下载与使用，不影响主要功能。
</details>

<details>
<summary><b>点击「生成大纲」后报错 <code>404 ... model ... does not exist</code></b></summary>

Model Name 拼写错误或厂商未提供该模型。请前往对应服务官网查询当前可用模型列表。
</details>

<details>
<summary><b>想换一台机器 / 不想让数据库长在仓库里</b></summary>

设置 `PPTM_DATA_DIR` 与 `PPTM_OUTPUTS_DIR` 指向任意持久化目录，默认仓库目录已加入 `.gitignore`。
</details>

---

## 系统依赖

- **Python** ≥ 3.10
- **LibreOffice**（可选，仅需 PDF 导出时安装）
- 现代浏览器（Chrome / Edge / Firefox / Safari 近 2 年版本均可）

---

## 文档

- 设计文档：[docs/superpowers/specs/2026-06-21-ppt-maker-design.md](docs/superpowers/specs/2026-06-21-ppt-maker-design.md)
- 实施计划：[docs/superpowers/plans/2026-06-21-ppt-maker-impl.md](docs/superpowers/plans/2026-06-21-ppt-maker-impl.md)

---

## 许可证

MIT