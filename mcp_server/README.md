# MCP Server for Resume Auto-Fitting

## 功能说明

这是一个 MCP (Model Context Protocol) 服务器，为 AI Agent 提供简历自动适配工具。

### 主要功能

1. **render_resume_pdf**: 渲染 Markdown 简历为 PDF
   - 检测内容是否超过一页
   - 返回详细的溢出指标和削减建议

## 安装

### 1. 安装 Python 依赖

```bash
conda activate agent_env
cd mcp_server
pip install -r requirements.txt
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

## 使用方式

### 方式一：作为 MCP Server 运行

在 Claude Desktop 或其他 MCP 客户端配置中添加：

```json
{
  "mcpServers": {
    "resume-autofit": {
      "command": "python",
      "args": ["path/to/mcp_server/mcp_server.py"],
      "cwd": "path/to/myresumebuilder"
    }
  }
}
```

### 方式二：直接测试

```bash
cd mcp_server
python resume_renderer.py
```

## 工具接口

### render_resume_pdf

**输入参数：**
- `markdown` (string, required): Markdown 格式的简历内容
- `output_path` (string, optional): PDF 输出路径，默认 "resume.pdf"

**返回格式（成功）：**
```json
{
  "status": "success",
  "pdf_path": "/absolute/path/to/resume.pdf",
  "current_pages": 1,
  "message": "简历已成功渲染为单页 PDF"
}
```

**返回格式（失败 - 溢出）：**
```json
{
  "status": "failed",
  "reason": "overflow",
  "current_pages": 2,
  "overflow_amount": 15,
  "overflow_px": 168,
  "hint": "中等溢出（15%）。建议：应用 Level 2 削减（简化描述、移除软技能表述）"
}
```

## AI Agent 削减策略

当收到溢出错误时，Agent 应按以下层级削减内容：

### Level 1 - 低损失削减（溢出 < 5%）
- 合并孤立单词（1-2 个单词单独成行的情况）
- 将"技能"或"教育"部分格式化为单行管道分隔列表

### Level 2 - 中等削减（溢出 5-15%）
- 移除软技能描述（如"优秀的沟通能力"）
- 简化 STAR 描述（仅保留 Action + Result）
- 移除 5 年以上的非关键经历

### Level 3 - 高损失削减（溢出 > 15%）
- 根据职位描述分析相关性
- 移除整个最不相关的项目或经历块

## 技术架构

```
AI Agent (Reasoning)
    ↓ 生成 Markdown V1
    ↓
MCP Server (Acting)
    - Playwright Headless Browser
    - 加载 generated_resume.html
    - 注入 Markdown
    - 等待 simple_viewer.js 完成渲染
    - 检测页面高度
    ↓
返回结果
    - 成功 → PDF 路径
    - 失败 → 溢出指标 + 削减建议
    ↓
AI Agent 分析并削减内容
    ↓
重试渲染
```

## 依赖项

- Python 3.8+
- Playwright (Chromium)
- MCP Python SDK

## 注意事项

1. 确保 `generated_resume.html` 在项目根目录
2. 确保 `js/simple_viewer.js` 已添加 `render-complete` 类标记
3. 首次运行需要下载 Chromium 浏览器（约 150MB）
