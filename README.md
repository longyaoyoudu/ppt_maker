# PPT Maker

一个本地运行的 Web 应用，分两阶段（**大纲设计** → **PPT 生成**）用大模型自动制作 PPT，支持 .pptx 与 .pdf 导出。

两阶段可独立配置不同大模型（OpenAI 兼容 API 或 Anthropic Claude）。

## 文档

- 设计文档：[docs/superpowers/specs/2026-06-21-ppt-maker-design.md](docs/superpowers/specs/2026-06-21-ppt-maker-design.md)

## 快速开始（待实现）

```bash
pip install -r requirements.txt
python run.py           # 浏览器访问 http://localhost:8000
```

## 系统依赖

- Python 3.10+
- LibreOffice（用于 .pptx → .pdf 转换，需加入 PATH）
