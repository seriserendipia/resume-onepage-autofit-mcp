# AI Resume Auto-Fitting - 快速开始

## 🎯 功能概述

本项目实现了 AI 驱动的简历自动适配系统：
- AI Agent 生成 Markdown 简历
- MCP Server 通过 Playwright 渲染并检测页面溢出
- AI 根据反馈智能削减内容，确保简历完美适配一页 A4

## 📦 安装步骤

### 1. 设置 MCP Server

**Windows 用户（推荐）：**
```batch
# 双击运行
setup_mcp.bat
```

**或手动执行：**
```bash
# 创建 MCP Server 结构
python setup_mcp.py

# 进入目录
cd mcp_server

# 安装依赖
pip install -r requirements.txt

# 安装 Chromium 浏览器（首次需要，约150MB）
playwright install chromium
```

### 2. 测试 MCP Server

```bash
cd mcp_server
python resume_renderer.py
```

预期输出：
```json
{
  "status": "success",
  "pdf_path": "D:\\...\\test_output.pdf",
  "current_pages": 1,
  "message": "简历已成功渲染为单页 PDF"
}
```

## 🔧 配置 AI Agent

### Claude Desktop 配置

编辑 Claude Desktop 配置文件（`claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "resume-autofit": {
      "command": "python",
      "args": [
        "D:/PythonEx/VirtualJobSeekerAgent/myresumebuilder.worktrees/copilot-worktree-2026-01-16T19-26-21/mcp_server/mcp_server.py"
      ],
      "cwd": "D:/PythonEx/VirtualJobSeekerAgent/myresumebuilder.worktrees/copilot-worktree-2026-01-16T19-26-21"
    }
  }
}
```

**配置文件位置：**
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

### 系统提示设置

将 `AI_AGENT_PROMPT.md` 的内容复制到 AI Agent 的系统提示中，或使用自定义指令功能。

## 🚀 使用流程

### 方式一：通过 Claude Desktop

1. 启动 Claude Desktop
2. 验证 MCP Server 连接（应在工具列表中看到 `render_resume_pdf`）
3. 发送请求：

```
请根据我的经历生成一份适配单页的简历：

【粘贴你的经历信息】

目标职位：Python 后端工程师
```

4. AI 会自动：
   - 生成初始 Markdown
   - 调用 `render_resume_pdf` 验证
   - 根据反馈迭代削减内容
   - 生成最终 PDF

### 方式二：Python 脚本调用

```python
import asyncio
from mcp_server.resume_renderer import ResumeRenderer

async def main():
    renderer = ResumeRenderer()
    await renderer.start()
    
    markdown = """
    # 张三
    
    **联系方式**：zhangsan@email.com | 13800138000
    
    ## 工作经历
    
    ### Python 开发工程师 | ABC 公司 | 2020-2023
    
    - 开发并维护后端 API 服务，支持 100w+ DAU
    - 优化数据库查询性能，响应时间降低 40%
    ...
    """
    
    result = await renderer.render_resume_pdf(markdown, "output.pdf")
    print(result)
    
    await renderer.stop()

asyncio.run(main())
```

## 📊 反馈示例

### 成功案例
```json
{
  "status": "success",
  "pdf_path": "/path/to/resume.pdf",
  "current_pages": 1,
  "message": "简历已成功渲染为单页 PDF"
}
```

### 溢出反馈（需削减）
```json
{
  "status": "failed",
  "reason": "overflow",
  "current_pages": 2,
  "overflow_amount": 12,
  "overflow_px": 134,
  "hint": "中等溢出（12%）。建议：应用 Level 2 削减（简化描述、移除软技能表述）"
}
```

## 🎨 削减策略速查

| 溢出程度 | 级别 | 策略 |
|---------|------|------|
| < 5% | Level 1 | 合并孤行、单行列表格式 |
| 5-15% | Level 2 | 移除软技能、简化 STAR 描述 |
| > 15% | Level 3 | 删除不相关经历块 |

详细策略见 `AI_AGENT_PROMPT.md`

## 🛠️ 故障排查

### 问题：MCP Server 无法启动

**检查清单：**
1. Python 版本 >= 3.8
   ```bash
   python --version
   ```

2. 依赖已安装
   ```bash
   pip list | findstr playwright
   pip list | findstr mcp
   ```

3. Chromium 已安装
   ```bash
   playwright install --list
   ```

### 问题：渲染超时

**解决方案：**
- 增加超时时间参数：
  ```python
  result = await renderer.render_resume_pdf(
      markdown, 
      "output.pdf",
      timeout_ms=20000  # 默认 10000
  )
  ```

### 问题：生成的 PDF 为空

**可能原因：**
1. `generated_resume.html` 路径不正确
2. `simple_viewer.js` 未正确加载
3. Markdown 内容格式错误

**调试方法：**
```python
# 在 resume_renderer.py 中添加截图
await page.screenshot(path="debug.png")
```

## 📚 相关文档

- **AI_AGENT_PROMPT.md**: AI Agent 系统提示完整版
- **DEVELOPMENT.md**: 技术架构详解
- **mcp_server/README.md**: MCP Server 详细文档
- **SLIDER_CONFIG_DOCS.md**: 样式配置说明

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

### 开发环境
```bash
# 克隆仓库
git clone <repo-url>

# 创建虚拟环境
conda create -n agent_env python=3.10
conda activate agent_env

# 安装依赖
pip install -r mcp_server/requirements.txt
playwright install chromium
```

## 📄 许可证

MIT License
