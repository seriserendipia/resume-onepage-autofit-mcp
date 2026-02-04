
# AI Resume Auto-Fitting System

**🌐 [中文](README_CN.md) | English**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-1.40+-green.svg)](https://playwright.dev/)

> 🤖 Tired of copying between AI and Word, tweaking formats, and adjusting to fit one page? What if AI could handle that feedback loop for you? This MCP lets AI render PDFs and auto-adjust content to perfectly fit one page with clean formatting.

## 🎯 How It Works

```
User: Please generate a single-page resume from my experience

AI Agent:
1. 📝 Generate initial Markdown
2. 🔍 Call render_resume_pdf to validate
3. ⚠️ Detected 12% overflow
4. 🔧 Apply Level 2 reduction strategy
5. ✅ Success! PDF generated
```

## 🚀 Quick Start

### 1. Install MCP Server

```bash
# Enter MCP Server directory and install dependencies
cd mcp_server
pip install -r requirements.txt
# ⚡ Or using uv (recommended): uv pip install -r requirements.txt

# Install Chromium browser (first time only, ~150MB)
playwright install chromium
```

### 2. Configure Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

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

> Replace `<your-path>` with your actual project path.
>
> ⚡ **If you prefer using [uv](https://github.com/astral-sh/uv)**:
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

### 3. Prepare Your Resume Content

Write your resume content in `myexperience.md` (refer to `example_resume.md` for format).

### 4. Start Using

Restart Claude Desktop, then simply tell the AI: "Please generate a single-page resume from my experience"

Generated PDFs are saved to the `generated_resume/` folder in the project directory by default.

> 💡 **Custom Output Path**:
> - Copy `js/config.example.js` to `js/config.js` and modify the `pdfOutput` settings at the top
> - Or specify `output_path` parameter when calling to save to any location

---

## ✨ Core Features

- **🎯 Smart Fitting**: Automatically adjusts content to fit resume perfectly on one A4 page
- **🔍 Precise Detection**: Pixel-accurate page height detection based on Playwright
- **📊 Layered Reduction**: Three-tier reduction strategy (format optimization → content simplification → deep reduction)
- **🔄 Feedback Loop**: AI Agent intelligently iterates based on overflow metrics
- **🚀 MCP Integration**: Supports direct calls from Claude Desktop and other AI clients

## 📸 Workflow

```
User provides experience → AI generates Markdown resume
                                    ↓
                        MCP Server renders & validates
                                    ↓
                    ┌─────── Detect page height ───────┐
                    │                                  │
                  Success                           Failure
               (within one page)                 (overflow X%)
                    │                                  │
              Generate PDF                  Return overflow metrics + hints
                    │                                  ↓
                    │                       AI applies reduction strategy
                    │                           (Level 1/2/3)
                    │                                  │
                    └──────────── Re-render ←──────────┘
```

## 🎨 Reduction Strategy Overview

| Level | Overflow Range | Strategy | Information Loss |
|-------|----------------|----------|------------------|
| **Level 1** | < 5% | Merge orphan lines, single-line lists | Low |
| **Level 2** | 5-15% | Remove soft skills, simplify descriptions | Medium |
| **Level 3** | > 15% | Delete irrelevant experiences | High |

See [AI_AGENT_PROMPT.md](AI_AGENT_PROMPT.md) for detailed strategies.

## 🔧 Visual Preview (Optional)

To manually adjust default style parameters, use the control panel (pure frontend, no Python needed):

```bash
# Use VS Code Live Server extension (recommended)
# Right-click control_panel.html -> "Open with Live Server"

# Or Python simple server
python -m http.server 8080
# Visit http://localhost:8080/control_panel.html
```

> 💡 The control panel is primarily for manually debugging style limits (e.g., font size ranges, line spacing). For daily use, rely on the AI Agent, which automatically adapts layout within optimal ranges based on content. For technical details, see [DEVELOPMENT.md](DEVELOPMENT.md).

## 📚 Documentation

- [AI_AGENT_PROMPT.md](AI_AGENT_PROMPT.md): AI Agent core reduction strategies (must read)
- [DEVELOPMENT.md](DEVELOPMENT.md): Technical architecture & development guide
- [mcp_server/README.md](mcp_server/README.md): MCP Server API documentation

## 🐛 Known Limitations

1. **Browser Dependency**: Requires Chromium (~150MB first time)
2. **Content Length**: Very long resumes (10+ pages) may need multiple reduction rounds
3. **Special Characters**: Some emoji may affect layout

## 🔄 Development Roadmap

### v0.2.0 (Planned)
- [ ] Custom templates


## 🤝 Contributing

Issues and Pull Requests welcome!

### Development Setup

```bash
# Clone repository
git clone https://github.com/seriserendipia/resume-onepage-autofit-mcp.git
cd resume-onepage-autofit-mcp

# Create virtual environment
conda create -n agent_env python=3.10
conda activate agent_env

# Install dependencies
pip install -r mcp_server/requirements.txt
playwright install chromium
```

### Commit Convention

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `test:` Test related

## 📄 License

MIT License - See [LICENSE](LICENSE)

## 🙏 Acknowledgments

- [Playwright](https://playwright.dev/) - Powerful browser automation
- [MCP](https://modelcontextprotocol.io/) - Unified AI tool protocol
- [Markdown-it](https://github.com/markdown-it/markdown-it) - Reliable Markdown parser
- [Paged.js](https://pagedjs.org/) - PDF pagination in the browser

## 📧 Contact

- 🐛 Issues: [GitHub Issues](https://github.com/seriserendipia/resume-onepage-autofit-mcp/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/seriserendipia/resume-onepage-autofit-mcp/discussions)

---

**⭐ If this project helps you, please give it a Star!**

**⭐ 如果这个项目对你有帮助，请给一个 Star！**
