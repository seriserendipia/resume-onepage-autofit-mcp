# Resume Auto-Fitting Engine (MCP Server)

A specialized toolset for AI Agents (like Claude Desktop) to generate, validate, and optimize Markdown resumes into professional, single-page PDFs.

## 🚀 Core Capabilities

1. **Intelligent Rendering (`render_resume_pdf`)**
   - **Auto-Fit Technology**: Automatically adjusts font sizes, line heights, and margins to fit content perfectly onto one page if the deviation is minor.
   - **Precise Overflow Detection**: Returns exact pixel counts and percentage of overflow to the AI agent.
   - **Feedback-Driven Optimization**: Provides specific "Hints" (e.g., "Level 2 reduction needed") based on the overflow severity.
   - **Content Analysis**: Reports word counts, section distributions, and page filling ratios to ensure visual balance.

2. **Automated Feedback Loop**
   - Bridges the gap between raw text generation and layout constraints.
   - Enables agents to apply multi-level reduction strategies (Low/Medium/High loss) with immediate visual validation.

3. **Debugging & Layout Snapshots**
   - Generates a sidecar `.debug.json` alongside every PDF, containing exact CSS variables and DOM measurements used during the render.

## 🛠️ Tool Interface

### `render_resume_pdf`
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `markdown` | string | Yes | The raw Markdown content of the resume. |
| `output_path` | string | No | Absolute path for the PDF. (e.g., `D:\Resumes\JohnDoe_Resume.pdf`). |

**Returns:**
- `status`: "success" or "overflow"
- `overflow_amount`: Percentage of overflow.
- `hint`: Actionable advice for the AI agent for the next iteration.
- `pdf_path`: Absolute path to the generated preview.
- `content_stats`: Summary of word counts and document structure.

## 📦 Installation & Setup

### 1. Prerequisites
- Python 3.8+
- Chromium browser (via Playwright)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Usage (MCP)
Add this to your `claude_desktop_config.json`:
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
*Note: Replace `<your-path>` with your actual project path.*

## 📐 Architecture
1. **AI Agent** generates Markdown.
2. **MCP Server** uses Playwright to load `resume_preview.html`.
3. **Internal Engine** triggers the resume renderer to render and optionally "Auto-Fit".
4. **Validation** checks scroll height against A4 standards.
5. **JSON Response** tells the Agent exactly how to improve the content.
