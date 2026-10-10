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
1. 📝 把简历写进 resume.md
2. 🔍 用文件路径调用 render_resume_pdf
3. ⚠️ 失败：溢出 6%（约 4 行）；第 58 行的 bullet 最后一行只有 6 个字符
4. 🔧 只改 resume.md 里的这几行
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

AI 会先把简历写进一个 `.md` 文件，再把这个文件的绝对路径（`markdown_path`）传给工具。Linux/macOS 如 `/home/you/resume.md`，Windows 如 `C:\Users\you\resume.md`。之后每轮只改文件里需要改的行，不用把整份简历重新传一遍。详见 [mcp_server/README.md](mcp_server/README.md#render_resume_pdf)。

PDF 默认写在 Markdown 文件旁边，文件名相同（`resume.md` → `resume.pdf`）。每个 PDF（例如 `resume.pdf`）旁边还会写一份 `resume.structured.json`：把摘要、技能、工作经历和项目拆成字段（公司、职位、地点、起止年月）。工具返回值的 "Format warnings" 部分列出没有按规范写法书写的行，每项都给出应改成的写法。

> 💡 **自定义输出路径**：调用时传绝对路径的 `output_path`，即可把 PDF 存到别处。

---

## ✨ 核心特性

- **🎯 智能适配**：自动调整内容，确保简历完美适配一页 A4
- **🔍 精确检测**：基于 Playwright 的页面高度检测，精确到像素
- **📏 逐行反馈**：报告每个板块、每条 bullet 占几行，最后一行有几个字符，超出了多少行。工具只给事实，删什么由 AI 决定
- **🔄 反馈闭环**：AI 在原文件上局部修改后重新渲染
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
    生成 PDF              返回逐块行数
          │                       ↓
          │              AI 自行决定改哪几行
          │                       │
          └───────── 重新渲染 ←────┘
```

## 🧭 给 AI 的提示词

工具只报告排版事实，不会告诉 AI 删什么。可以给你的 AI 一段类似下面的提示词（按自己的流程调整）：

```text
你用 render_resume_pdf 工具制作一页纸简历。

1. 把简历写进一个 Markdown 文件，例如 /home/you/resumes/acme/resume.md，写法遵循工具
   markdown_path 参数说明里的规范格式。这个文件只整份写一次。
2. 用这个文件的绝对路径调用 render_resume_pdf。
3. 每次渲染后，只用编辑工具改需要改的行，再用同一个路径重新渲染。不要整份重写文件，
   也不要把简历内容放进调用参数。
   - 先看 pdf_path 下面那段话：它说明这次成功还是失败、为什么，以及下一次渲染要达到什么。
   - overflow："Page fit" 给出 overflow_percent 和 overflow_body_lines。"Space by section and
     entry" 表格列出每个板块、每份工作、每个项目、每所学校占几行；"wrapped items" 一列列出折行
     的条目，格式是"源文件行号: 最后一行字符数"，"58: 6" 表示第 58 行最后一行只有 6 个字符却
     白占一整行，删掉这几个字符就能省一行。优先删和目标岗位最不相关的内容。
   - success 且 empty_space_percent 较大：页面有空余，可以补充相关内容，也可以就此结束。
   - layout_error："Layout warnings" 下列出的每一行都是折成多行的条目头，必须回到一行。
   - Format warnings：在同一次修改里把列出的每一行改成 expected 的写法。缺月份就问用户，
     不要编造。
4. status 为 success 且没有 Format warnings 时结束。渲染 5 次仍放不下，就告诉用户你打算删
   什么，问过再删。

不要为了放进一页而改动事实（数字、日期、公司名、职位）。
```

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

- [DEVELOPMENT.md](DEVELOPMENT.md)：技术架构与开发调试指南
- [mcp_server/README.md](mcp_server/README.md)：MCP Server API 详细文档

## 🐛 已知限制

1. **浏览器依赖**：需要 Chromium（首次约 150MB）
2. **内容长度**：极长简历（10+ 页）可能需要多轮渲染
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
- [Source Sans 3](https://github.com/adobe-fonts/source-sans) - 随仓库分发的正文字体（SIL OFL 1.1，见 `fonts/OFL.txt`）
- [MCP](https://modelcontextprotocol.io/) - 统一的 AI 工具协议
- [Markdown-it](https://github.com/markdown-it/markdown-it) - 可靠的 Markdown 解析器
- [Paged.js](https://pagedjs.org/) - 浏览器端 PDF 分页引擎

## 📧 联系方式

- 🐛 Issues: [GitHub Issues](https://github.com/seriserendipia/resume-onepage-autofit-mcp/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/seriserendipia/resume-onepage-autofit-mcp/discussions)

---

**⭐ 如果这个项目对你有帮助，请给一个 Star！**
