# PPT 制作工具 — 设计文档

**日期**：2026-06-21
**项目目录**：`d:\jinproject\ppt_maker`
**状态**：已通过头脑风暴，待用户审阅

## 1. 项目目标

构建一个本地运行的 Web 应用，让用户通过两步完成 PPT 制作：
1. **大纲设计**：用一个大模型根据主题生成结构化大纲，用户可编辑。
2. **PPT 生成**：用另一个（可同可不同）大模型润色内容后生成 .pptx（可同时生成 .pdf）。

两个阶段使用的大模型、API Key、Base URL 等完全独立配置，存于本地 SQLite。界面强调"简洁明了"，单页 + 标签页切换。

## 2. 用户决策记录

| 决策点 | 选定方案 | 备选 |
|--------|----------|------|
| 输出格式 | .pptx + .pdf | 仅 .pptx / 仅 PDF / 仅 HTML |
| 应用类型 | Web 应用 | 桌面 / CLI / 前后端分离 |
| 大模型 | 同时支持 OpenAI 兼容 + Anthropic Claude | 仅 OpenAI / 仅 Claude / 仅本地 |
| 工作流 | 顺序式（先大纲 → 编辑 → 生成） | 一键自动 / 两段独立并行 |
| 前端 | 纯 HTML + JavaScript（TailwindCSS CDN） | Vue / React / Streamlit |
| 历史记录 | SQLite | 不保存 |
| 配图 | AI 生成 + 占位图均可 | 仅 AI / 仅占位 |
| 配置管理 | 仅 Web 页面填写 | 仅 .env / 两种都支持 |
| 后端 | Python + FastAPI | Node.js + Express / Python + 异步队列 |
| PDF 转换 | LibreOffice headless | pdfkit / weasyprint |
| 交互形式 | 单页 + 三个标签页 | 向导式 / 多页面 |

## 3. 整体架构

```
┌──────────────────────────────────────────────────┐
│          浏览器 (单页 HTML + TailwindCSS)          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ 模型配置 │  │ 大纲设计 │  │ PPT 生成/下载 │    │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
└───────┼─────────────┼───────────────┼────────────┘
        │ HTTP/JSON   │               │
┌───────▼─────────────▼───────────────▼────────────┐
│              FastAPI 后端 (Python)                │
│  /api/config   /api/outline   /api/ppt           │
│  ┌─────────┐ ┌──────────────┐ ┌─────────────┐   │
│  │配置管理 │ │ 大纲生成服务  │ │ PPT 生成服务 │   │
│  │(SQLite) │ │ (LLM 抽象层)  │ │(python-pptx)│   │
│  └─────────┘ └──────┬───────┘ └──────┬──────┘   │
│                     │                │          │
│              ┌──────▼────────────────▼────┐      │
│              │   LLM 适配层 (OpenAI/Claude) │      │
│              └─────────────────────────────┘      │
└──────────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌──────────┐
   │ SQLite  │   │ 文件存储 │   │ LibreOffice│
   │ (历史)  │   │ (输出)   │   │ (.pdf转换) │
   └─────────┘   └──────────┘   └──────────┘
```

## 4. 技术栈

- **后端**：Python 3.10+、FastAPI、Uvicorn
- **大模型 SDK**：`openai`、`anthropic`
- **PPT 生成**：`python-pptx`
- **PDF 转换**：LibreOffice（系统安装，命令行 headless 模式）
- **数据库**：SQLite（标准库 `sqlite3`）
- **前端**：单文件 `static/index.html` + TailwindCSS（CDN）+ 原生 JavaScript
- **依赖管理**：`requirements.txt`

## 5. 模块拆分

每个单元一个明确职责，对外暴露清晰接口，可独立测试。

### 后端模块

| 模块 | 职责 | 关键接口 |
|------|------|----------|
| `app/main.py` | FastAPI 应用入口、路由挂载、静态文件服务 | `app = FastAPI()` |
| `app/models.py` | Pydantic 数据模型（请求/响应） | `OutlineRequest`、`PPTRequest` 等 |
| `app/prompts.py` | 大纲/PPT 提示词模板 | `OUTLINE_PROMPT`、`PPT_REFINEMENT_PROMPT` |
| `app/config_store.py` | 模型配置 CRUD，API Key 至少 Base64 编码 | `get_config(stage)`、`save_config(stage, cfg)` |
| `app/history_store.py` | 历史大纲/生成记录 CRUD | `save_outline`、`list_generations` 等 |
| `app/llm/base.py` | LLM 提供方抽象基类 | `class LLMProvider: chat(messages) -> str` |
| `app/llm/openai_provider.py` | OpenAI 兼容实现 | `class OpenAIProvider(LLMProvider)` |
| `app/llm/claude_provider.py` | Anthropic Claude 实现 | `class ClaudeProvider(LLMProvider)` |
| `app/llm/factory.py` | 根据配置返回对应 provider | `get_provider(stage) -> LLMProvider` |
| `app/services/outline_service.py` | 调用 LLM 生成大纲 + 解析/校验 JSON | `generate_outline(topic, requirements) -> dict` |
| `app/services/ppt_service.py` | 根据大纲调用 python-pptx 生成 .pptx | `build_pptx(outline, style, image_mode) -> path` |
| `app/services/pdf_service.py` | 调用 LibreOffice 转 .pdf | `convert_to_pdf(pptx_path) -> pdf_path` |
| `app/services/image_service.py` | 可选：AI 配图（DALL-E 或其他） | `generate_image(prompt) -> path` |

### 前端（单页）

单页 `static/index.html`，包含四个标签页：
1. **模型配置** — 两个阶段各填 provider / base_url / api_key / model_name / 额外参数
2. **大纲设计** — 主题输入 → 生成 → 大纲卡片列表（可增删改、拖拽排序） → 保存
3. **生成 PPT** — 选风格模板、配图模式 → 生成进度条 → 下载 .pptx / .pdf
4. **历史记录** — 列出过往大纲和生成，可重新加载/下载

## 6. 数据流

### 阶段 1：生成大纲

```
用户输入主题 + (可选) 补充要求
    ↓ POST /api/outline/generate {topic, requirements}
后端调用 outline_model 配置的 LLM（factory → provider.chat）
    ↓ 提示词要求输出严格 JSON：[{title, key_points: [...], layout: ...}, ...]
返回大纲 JSON 给前端
    ↓
前端展示大纲卡片，每页可编辑/重排/删除/新增
    ↓ 用户点"保存"或"下一步"
INSERT INTO outlines
```

### 阶段 2：生成 PPT

```
用户点击"生成 PPT"，选择：风格模板、配图模式
    ↓ POST /api/ppt/generate {outline_id, style, image_mode}
后端调用 ppt_model 配置的 LLM（可选：润色/扩展每页文案）
    ↓
ppt_service 读取大纲，遍历每一页：
  - 根据 layout 选择模板布局（title/title-content/two-column/quote 等）
  - 调用 python-pptx 写入标题、正文、占位图
  - 若 image_mode=ai，调用 image_service 生成图片
    ↓
保存为 .pptx 到 outputs/ 目录
    ↓ 调用 LibreOffice 转 .pdf（异步、可失败但不影响 .pptx）
INSERT INTO generations 记录元数据
    ↓ 返回下载链接
```

## 7. 数据库设计

```sql
-- 模型配置（每个阶段一行）
CREATE TABLE model_configs (
  stage TEXT PRIMARY KEY,           -- 'outline' | 'ppt'
  provider TEXT NOT NULL,           -- 'openai' | 'claude'
  base_url TEXT,                    -- OpenAI 兼容服务用
  api_key TEXT NOT NULL,
  model_name TEXT NOT NULL,         -- e.g. 'gpt-4o', 'claude-sonnet-4-6'
  extra_params TEXT,                -- JSON: temperature, max_tokens 等
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 历史大纲
CREATE TABLE outlines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT NOT NULL,
  requirements TEXT,
  content_json TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 生成记录
CREATE TABLE generations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  outline_id INTEGER REFERENCES outlines(id),
  style TEXT,                       -- 'business' | 'academic' | 'minimal' ...
  image_mode TEXT,                  -- 'placeholder' | 'ai'
  pptx_path TEXT,
  pdf_path TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 8. API 设计

| 方法 | 路径 | 用途 | 请求体 | 响应 |
|------|------|------|--------|------|
| GET  | `/api/config/{stage}` | 获取某阶段配置 | — | `ModelConfig` |
| PUT  | `/api/config/{stage}` | 更新某阶段配置 | `ModelConfig` | `{ok: true}` |
| POST | `/api/outline/generate` | 生成大纲 | `{topic, requirements}` | `{outline_id, content}` |
| PUT  | `/api/outline/{id}` | 更新大纲 | `{content}` | `{ok: true}` |
| POST | `/api/ppt/generate` | 生成 PPT | `{outline_id, style, image_mode}` | `{generation_id, status}` |
| GET  | `/api/history/outlines` | 历史大纲 | — | `[Outline]` |
| GET  | `/api/history/generations` | 历史生成 | — | `[Generation]` |
| GET  | `/api/download/{gen_id}/{format}` | 下载 | `format: pptx\|pdf` | 文件流 |
| POST | `/api/image/generate` | （可选）AI 配图 | `{prompt}` | `{image_url}` |

## 9. 错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| 配置缺失 | 400 + "请先在'模型配置'中配置 {stage} 模型" |
| LLM 调用失败（网络/限流/无效 key） | 502 + 原始错误信息 |
| 大纲 JSON 解析失败 | 自动重试 1 次（提示 LLM "请严格输出 JSON"），仍失败则 500 |
| python-pptx 异常 | 500 + 保留部分输出文件 + 错误堆栈 |
| LibreOffice 缺失或转换超时 | 提示用户安装，.pptx 仍可下载 |
| 文件下载路径不存在 | 404 |

## 10. 测试策略

- **单元测试**（`tests/`）：
  - `test_config_store.py` — 配置读写，API Key 编码
  - `test_llm_factory.py` — provider 选择逻辑（用 mock）
  - `test_outline_service.py` — JSON 解析、容错（用 mock LLM 响应）
  - `test_ppt_service.py` — 用固定大纲生成 .pptx，验证文件结构（页数、文本内容）
- **集成测试**：
  - `test_api.py` — FastAPI `TestClient` 端到端走通大纲→生成→下载
- **手动验证**：
  - 启动 `uvicorn app.main:app --reload`
  - 浏览器走完"配置 → 大纲 → 生成 → 下载 .pptx + .pdf"全流程

## 11. 目录结构

```
d:\jinproject\ppt_maker\
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── prompts.py
│   ├── config_store.py
│   ├── history_store.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   └── factory.py
│   └── services/
│       ├── __init__.py
│       ├── outline_service.py
│       ├── ppt_service.py
│       ├── pdf_service.py
│       └── image_service.py
├── static/
│   └── index.html                 # 单页前端（含 JS）
├── outputs/                        # 生成的 .pptx / .pdf（运行时创建）
├── data/
│   └── app.db                      # SQLite（运行时创建）
├── tests/
│   ├── test_config_store.py
│   ├── test_llm_factory.py
│   ├── test_outline_service.py
│   ├── test_ppt_service.py
│   └── test_api.py
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-06-21-ppt-maker-design.md
├── requirements.txt
├── run.py                          # 启动脚本：python run.py
└── README.md
```

## 12. 启动与依赖

### 依赖

```
fastapi
uvicorn[standard]
python-multipart
openai>=1.0
anthropic
python-pptx
Pillow                # python-pptx 处理图片用
httpx                 # 测试用
pytest
pytest-asyncio
```

### 外部依赖

- **LibreOffice**（用于 .pptx → .pdf）：需用户自行安装，并加入 PATH
  - Windows：https://www.libreoffice.org/download
  - macOS：`brew install --cask libreoffice`
  - Linux：`apt install libreoffice`

### 启动

```bash
pip install -r requirements.txt
python run.py           # 浏览器访问 http://localhost:8000
```

## 13. 关键枚举值定义

为避免歧义，明确定义大纲 JSON 与生成参数中的枚举值。

### `layout`（大纲每页的版式）

| 值 | 含义 | 适用场景 |
|----|------|----------|
| `title` | 仅大标题居中 | 封面、章节分隔 |
| `title-content` | 标题 + 关键点列表 | 常规内容页 |
| `two-column` | 标题 + 左右两栏 | 对比、并列 |
| `quote` | 标题 + 引用块 | 重点强调 |
| `section` | 大标题 + 副标题 | 章节封面 |

LLM 生成大纲时必须从此 5 个值中选择。前端编辑时也只允许选择这些值。

### `style`（生成 PPT 的整体风格）

| 值 | 含义 | 配色与字体倾向 |
|----|------|----------------|
| `business` | 商务通用 | 深蓝主色 + 白色背景 + 微软雅黑 / Calibri |
| `academic` | 学术严谨 | 深灰主色 + 浅米色背景 + 宋体 / Times |
| `minimal` | 极简现代 | 黑白灰 + 高对比 + Helvetica |
| `creative` | 创意活泼 | 渐变色 + 圆角 + 思源黑体 |

不在枚举中时，默认使用 `business`。

### `image_mode`（配图模式）

| 值 | 行为 |
|----|------|
| `placeholder` | 在需要图片的位置插入纯色矩形 + "图片占位"文字 |
| `ai` | 调用 DALL-E/其他图像 API 生成图片（需 outline model 或 ppt model 的 provider 为 OpenAI 兼容且支持图像） |
| `none` | 完全不插入图片 |

## 14. 未来扩展（不在本期范围）

- 多用户/登录
- 自定义模板上传
- 演示模式（直接在网页播放）
- 导出为 Markdown/HTML
- 大纲版本管理（修订历史）
