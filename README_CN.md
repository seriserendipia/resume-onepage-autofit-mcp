# AI 简历自动适配系统

**🌐 中文 | [English](README.md)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-1.40+-green.svg)](https://playwright.dev/)

> 🤖 正在改简历的你，是不是还在一遍一遍从 AI 到 Word 之间复制粘贴，修改格式，调整成一页大小？如果这个反馈过程也能由 AI 完成呢？这个 MCP 可以让 AI 输出正好一页纸长度的简历，并内容清晰排版

## 🎯 使用效果

```
用户: 请根据我的经历生成适配单页的简历

AI Agent:
1. 📝 生成初始 Markdown
2. 🔍 调用 render_resume_pdf 验证
3. ⚠️ 检测到溢出 12%
4. 🔧 应用 Level 2 削减策略
5. ✅ 成功！PDF 已生成
```

## 🚀 快速开始

### 1. 安装 MCP Server

```bash
# 进入 MCP Server 目录并安装依赖
cd mcp_server
pip install -r requirements.txt
# ⚡ 或者使用 uv (推荐): uv pip install -r requirements.txt

# 安装 Chromium 浏览器（首次需要，约150MB）
playwright install chromium
```

### 2. 配置 Claude Desktop

编辑 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "resume-onepage-autofit-mcp": {
      "command": "python",
      "args": ["<your-path>/myresumebuilder/mcp_server/mcp_server.py"]
    }
  }
}
```

> 将 `<your-path>` 替换为你的实际项目路径。
>
> ⚡ **如果你倾向于使用 [uv](https://github.com/astral-sh/uv)**：
> ```json
> "resume-onepage-autofit-mcp": {
>   "command": "uv",
>   "args": [
>     "run",
>     "--directory",
>     "<your-path>/myresumebuilder",
>     "mcp_server/mcp_server.py"
>   ]
> }
> ```



### 3. 准备简历内容

将你的简历内容写入 `myexperience.md`（可参考 `example_resume.md` 模板格式）。

### 4. 开始使用

重启 Claude Desktop，然后直接告诉 AI："请根据我的经历生成适配单页的简历"

生成的 PDF 默认保存在项目目录下的 `generated_resume/` 文件夹。

> 💡 **自定义输出路径**：
> - 复制 `js/config.example.js` 为 `js/config.js`，修改顶部的 `pdfOutput` 配置
> - 或在调用时指定 `output_path` 参数保存到任意位置

---

## ✨ 核心特性

- **🎯 智能适配**：自动调整内容，确保简历完美适配一页 A4
- **🔍 精确检测**：基于 Playwright 的页面高度检测，精确到像素
- **📊 分层削减**：三级削减策略（格式优化 → 内容精简 → 深度削减）
- **🔄 反馈闭环**：AI Agent 根据溢出指标智能迭代优化
- **🚀 MCP 集成**：支持 Claude Desktop 等 AI 客户端直接调用

## 📸 工作流程

```
用户提供经历 → AI 生成 Markdown 简历
                      ↓
            MCP Server 渲染验证
                      ↓
          ┌───── 检测页面高度 ──────┐
          │                       │
        成功                     失败
     (单页内)                 (溢出 X%)
          │                       │
    生成 PDF               返回溢出指标 + 建议
          │                       ↓
          │              AI 应用削减策略
          │                (Level 1/2/3)
          │                       │
          └───────── 重新渲染 ←────┘
```

## 🎨 削减策略概览

| 级别 | 溢出范围 | 策略 | 信息损失 |
|------|---------|------|---------|
| **Level 1** | < 5% | 合并孤行、单行列表 | 低 |
| **Level 2** | 5-15% | 移除软技能、简化描述 | 中 |
| **Level 3** | > 15% | 删除不相关经历 | 高 |

详细策略见 [AI_AGENT_PROMPT.md](AI_AGENT_PROMPT.md)

## 🔧 可视化预览（可选）

如果需要手动调整默认样式参数，可以使用控制面板（纯前端，无需 Python）：

```bash
# 使用 VS Code Live Server 扩展（推荐）
# 右键 control_panel.html -> "Open with Live Server"

# 或 Python 简易服务器
python -m http.server 8080
# 访问 http://localhost:8080/control_panel.html
```

> 💡 控制面板主要用于调试样式参数（如字体大小范围、行间距等）。日常使用建议直接通过 AI Agent 生成，系统会根据内容量在最佳范围内自动调整排版。更多开发细节见 [DEVELOPMENT.md](DEVELOPMENT.md)

## 📚 文档指南

- [AI_AGENT_PROMPT.md](AI_AGENT_PROMPT.md)：AI Agent 核心削减策略（必读）
- [DEVELOPMENT.md](DEVELOPMENT.md)：技术架构与开发调试指南
- [mcp_server/README.md](mcp_server/README.md)：MCP Server API 详细文档

## 🐛 已知限制

1. **浏览器依赖**：需要 Chromium（首次约 150MB）
2. **内容长度**：极长简历（10+ 页）可能需要多轮削减
3. **特殊字符**：部分 emoji 可能影响排版

## 🔄 开发路线图

### v0.2.0 (计划中)
- [ ] 自定义模板

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/seriserendipia/resume-onepage-autofit-mcp.git
cd resume-onepage-autofit-mcp

# 创建虚拟环境
conda create -n agent_env python=3.10
conda activate agent_env

# 安装依赖
pip install -r mcp_server/requirements.txt
playwright install chromium
```

### 提交规范

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `test:` 测试相关

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [Playwright](https://playwright.dev/) - 强大的浏览器自动化
- [MCP](https://modelcontextprotocol.io/) - 统一的 AI 工具协议
- [Markdown-it](https://github.com/markdown-it/markdown-it) - 可靠的 Markdown 解析器
- [Paged.js](https://pagedjs.org/) - 浏览器端 PDF 分页引擎

## 📧 联系方式

- 🐛 Issues: [GitHub Issues](https://github.com/seriserendipia/resume-onepage-autofit-mcp/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/seriserendipia/resume-onepage-autofit-mcp/discussions)

---

**⭐ 如果这个项目对你有帮助，请给一个 Star！**
