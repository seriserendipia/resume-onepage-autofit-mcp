
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
1. 📝 Write the resume to resume.md
2. 🔍 Call render_resume_pdf with its path
3. ⚠️ Failed: overflows by 6% (about 4 body lines); the bullet on line 58 ends with a 6-character line
4. 🔧 Edit only those lines in resume.md
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

The agent writes the resume to a `.md` file and passes the tool that file's absolute path (`markdown_path`), on Linux/macOS (`/home/you/resume.md`) or Windows (`C:\Users\you\resume.md`). Between renders it edits the file in place instead of resending the whole resume. See [mcp_server/README.md](mcp_server/README.md#render_resume_pdf) for details.

The PDF is written next to the Markdown file with the same name (`resume.md` → `resume.pdf`). Next to each PDF (for example `resume.pdf`) the renderer also writes `resume.structured.json`: the summary, skills, experience and projects split into fields (company, title, location, start and end month). The tool result lists, under "Format warnings", any lines that do not follow the canonical resume format, each with the form to rewrite it to.

> 💡 **Custom Output Path**: pass an absolute `output_path` to save the PDF anywhere else.

---

## ✨ Core Features

- **🎯 Smart Fitting**: Automatically adjusts content to fit resume perfectly on one A4 page
- **🔍 Precise Detection**: Pixel-accurate page height detection based on Playwright
- **📏 Line-level Feedback**: Reports how many lines each section and bullet takes, how many characters sit on its last line, and how many lines overflow. The tool states facts only; what to cut is the agent's call
- **🔄 Feedback Loop**: The agent edits the Markdown file in place and re-renders
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
              Generate PDF                Return per-block line counts
                    │                                  ↓
                    │                       AI edits the lines it chooses
                    │                                  │
                    └──────────── Re-render ←──────────┘
```

## 🧭 Agent Prompt

The tool reports layout facts and never says what to cut. Give your agent a prompt like this one (adapt it to your workflow):

```text
You build a one-page resume with the render_resume_pdf tool.

1. Write the resume to a Markdown file, e.g. /home/you/resumes/acme/resume.md, in the
   canonical forms described in the tool's markdown_path parameter. Write the file once.
2. Call render_resume_pdf with the file's absolute path.
3. After each render, change only the lines that need it with your edit tool and render
   again with the same path. Never rewrite the whole file or paste the resume into the call.
   - Start with the paragraph under pdf_path: it says whether the render succeeded, why not,
     and what the next render must achieve.
   - overflow: "Page fit" gives overflow_percent and overflow_body_lines. The table "Space by
     section and entry" shows how many lines each section, job, project and school takes. Its
     "wrapped items" column lists items that wrap, as "source line: characters on last line";
     "58: 6" means 6 characters on line 58 cost a whole line, so trimming them saves it. Cut
     what is least relevant to the target job first.
   - success with a large empty_space_percent: there is room; add relevant detail or stop.
   - layout_error: each line under "Layout warnings" is an entry header that wrapped. It must
     fit on one line.
   - Format warnings: in the same edit, rewrite each listed line to its expected form. If a
     month is missing, ask the user; never invent one.
4. Stop when status is success and there are no format warnings. If it still does not fit
   after 5 renders, tell the user what you would cut and ask.

Never change facts (numbers, dates, company names, titles) to make the page fit.
```

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

- [DEVELOPMENT.md](DEVELOPMENT.md): Technical architecture & development guide
- [mcp_server/README.md](mcp_server/README.md): MCP Server API documentation

## 🐛 Known Limitations

1. **Browser Dependency**: Requires Chromium (~150MB first time)
2. **Content Length**: Very long resumes (10+ pages) may need several render rounds
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
- [Source Sans 3](https://github.com/adobe-fonts/source-sans) - bundled body typeface (SIL OFL 1.1, see `fonts/OFL.txt`)
- [MCP](https://modelcontextprotocol.io/) - Unified AI tool protocol
- [Markdown-it](https://github.com/markdown-it/markdown-it) - Reliable Markdown parser
- [Paged.js](https://pagedjs.org/) - PDF pagination in the browser

## 📧 Contact

- 🐛 Issues: [GitHub Issues](https://github.com/seriserendipia/resume-onepage-autofit-mcp/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/seriserendipia/resume-onepage-autofit-mcp/discussions)

---

**⭐ If this project helps you, please give it a Star!**

**⭐ 如果这个项目对你有帮助，请给一个 Star！**
