# Resume One-Page Autofit MCP 开发文档

## 0. Markdown 格式规范

### 支持的格式
| Markdown 语法 | 渲染效果 | 用途 |
|--------------|---------|------|
| `# Name` | 居中大标题 | 候选人姓名 |
| `## Section` | 带下划线的章节标题 | Experience, Education, Skills 等 |
| `**bold**` | 加粗 | 公司名、职位、关键数字（如 **15%**） |
| `*italic at line end*` | 斜体 + 自动右对齐 | 日期（仅在行尾时生效） |
| `- bullet` | 列表项 | 成就/职责 |
| `[text](url)` | 蓝色可点击链接 | LinkedIn, GitHub 等 |

### Entry 格式（公司/学校条目）
```markdown
**Company** · Role · Location *Date Range*

- **Label:** Description with **key metric**
```

### CSS 布局特性
- **日期右对齐**: 当段落以 `<strong>` 开头、以 `<em>` 结尾时，`<em>` 自动 `float:right`
- **联系信息居中**: h1 后的第一个 `<p>` 自动居中
- **h2 下划线**: 章节标题自带底部边框，不需要 `---` 分隔符

### 不支持的格式
- `---` 水平线（h2 已有下划线，用 `---` 会浪费空间）
- 代码块、引用块、图片（无 CSS 支持）

## 1. 项目结构

```text
resume-onepage-autofit-mcp/
├── control_panel.html         # [入口] 控制台页面，宿主环境
├── resume_preview.html        # [入口] 简历预览/渲染页面，被嵌入的 iframe
├── example_resume.md          # 示例简历模板 (公开发布用)
├── mcp_server/                # MCP Server - AI 自动化渲染
│   ├── mcp_server.py          # MCP 协议服务器入口
│   ├── resume_renderer.py     # Playwright 渲染引擎
│   └── README.md              # MCP Server 使用文档
├── js/                        # 核心逻辑
│   ├── resume_renderer.js     # ⭐ 主渲染器：Paged.js + 握手协议
│   ├── paged.polyfill.js      # Paged.js 库（分页渲染）
│   ├── controller.js          # 外层主控：初始化 UI、监听消息
│   ├── resumeStateManager.js  # Redux-like 状态容器
│   ├── styleController.js     # CSS 变量计算与应用
│   ├── sliderController.js    # 滑杆事件绑定与数值映射
│   ├── pagedJsMiddleware.js   # Paged.js 异步渲染队列
│   ├── domUpdater.js          # DOM 更新监听器
│   ├── config.example.js      # 配置示例模板
│   └── markdown-it.min.js     # Markdown 解析库
├── tests/                     # 测试目录
│   ├── test_mcp_server.py     # MCP Server 功能测试
│   └── test_release_safety.py # 发布前安全检查
├── AI_AGENT_PROMPT.md         # AI Agent 系统提示（削减策略）
└── README.md                  # 项目主文档
```

## 2. 核心工作流

### A. MCP 渲染流程（主要使用方式）
```
Playwright (resume_renderer.py)
    ↓ 加载 resume_preview.html
    ↓
resume_preview.html
    ├─ 加载 resume_renderer.js + paged.polyfill.js
    └─ 等待握手信号
    ↓
resume_renderer.py 发送 SET_CONTENT
    ↓
resume_renderer.js 接收消息
    ├─ Markdown → HTML (markdown-it)
    ├─ Paged.js 分页渲染
    └─ 添加 render-complete 类
    ↓
resume_renderer.py 检测完成 → 生成 PDF
```

### B. 样式更新（控制面板）
用户拖动滑杆 → `sliderController.js` → postMessage `UPDATE_CSS_VAR` → iframe 内 `resume_renderer.js` 更新 CSS 变量 → 触发 Paged.js 重渲染。

### C. 自动一页 (Auto One-Page)
逻辑位置：`js/resume_renderer.js` → `window.simpleViewer.fitToOnePage`

渲染完成且页数 > 1 或填充率 < 85% 时触发：
1. 方向判断：收缩或扩展
2. 按策略顺序（字体 → 行高 → 边距等）循环迭代调整
3. 终止：达到最佳状态或最大迭代次数

## 3. MCP 集成架构

```
AI Agent → 生成 Markdown V1 → 调用 render_resume_pdf
    ↓
MCP Server (Playwright)
    ├─ 加载 HTML → 注入 Markdown → Paged.js 渲染
    ├─ 等待 render-complete + Auto-Fit
    ├─ 布局后置检查 (Float Drop Detection)
    └─ 检测溢出 → 生成 PDF
    ↓
返回结果
    ├─ success: 单页适配成功
    ├─ layout_warning: 单页但有排版塌陷（如标题过长导致日期掉行）
    ├─ overflow: 超出一页，带削减建议
    └─ error: 渲染失败（空内容、超时、浏览器异常等）
    ↓
AI Agent 根据反馈自我修正 → 循环直到成功
```

### 削减策略（三级）
详见 `AI_AGENT_PROMPT.md`：
- **Level 1（<5%）**：格式优化（合并孤行、单行列表）
- **Level 2（5-15%）**：内容精简（移除软技能、简化 STAR）
- **Level 3（>15%）**：深度削减（移除整块不相关经历）

### 3.1 MCP Input Schema

Tool name: `render_resume_pdf`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `markdown` | string | ✅ | — | Resume content in Markdown |
| `output_path` | string | ❌ | `resume.pdf` | PDF output path (e.g. `JohnDoe_Google_SWE.pdf`) |

#### `markdown` field detail

The `inputSchema.description` communicates formatting rules to the AI Agent (verbatim):

> Resume in Markdown. Supported:
> `# Name` (centered), `## Section` (underlined, no `---` needed),
> `**bold**` (company/title/key metrics like **15%**),
> `*italic at end of line*` (dates, auto right-aligned in PDF),
> `- bullets`, `[text](url)`.
> Entry format: `**Company** · Role · Location *Date range*`
> (all one line, NO dot before italic date), blank line, then `- bullets`.
> Bullet format: `- **Label:** description with **key metric**`
> (e.g., `- **Churn Modeling:** Built ML pipeline, reducing churn by **12%**`).

The `inputSchema` also includes an `examples` array (single element) showing a complete resume structure:

```markdown
# Jane Doe
SF, CA | jane@email.com | [LinkedIn](https://linkedin.com/in/jane)

## Summary
Data Scientist with expertise in **ML** and **Experimentation**, driving **15% revenue growth**.

## Experience

**Google** · Senior Data Scientist · Mountain View, CA *Jan 2022 – Present*

- **A/B Testing:** Led experimentation framework serving **100M+ users**
- **Churn Modeling:** Built ML pipeline, reducing churn by **12%**

## Education

**Stanford University** · M.S. Statistics · Stanford, CA *2017 – 2019*

## Skills
- **Languages**: Python, R, SQL
- **Tools**: Spark, Airflow, Tableau
```

#### `output_path` field detail

`description`: `"PDF save path (e.g., JohnDoe_Google_SWE.pdf). Default: ./generated_resume/output_resume.pdf"`

> Note: The actual default in `handle_call_tool` is `"resume.pdf"` (via `arguments.get("output_path", "resume.pdf")`), which differs from the description. Code behavior takes precedence.

#### Tool Annotations

```json
{
  "title": "Resume PDF Renderer",
  "readOnlyHint": false,
  "destructiveHint": false,
  "idempotentHint": true,
  "openWorldHint": false
}
```
- `idempotentHint: true`: Same Markdown input produces same result; AI Agent can safely retry.
- `openWorldHint: false`: Tool does not access external networks.

### 3.2 MCP Output: All Possible Statuses

#### Common fields (present in all non-error responses)

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"success"` \| `"layout_warning"` \| `"overflow"` |
| `message` | string | Human-readable status description |
| `suggestion` | string | Corrective guidance for the AI Agent |
| `next_action` | string | Recommended next step for the AI Agent |
| `pdf_path` | string | Absolute path to the generated PDF (always generated, even on overflow) |
| `current_pages` | int | Total page count after rendering |
| `fill_ratio` | float | First-page content fill ratio (0.0–1.0) |
| `total_height_px` | int | Total content height in pixels |
| `overflow_amount` | int | Overflow percentage (0 = no overflow) |
| `overflow_px` | int | Overflow in pixels |
| `content_stats` | object | `{word_count, char_count, h1_count, h2_count, li_count, p_count}` |
| `hint` | string | Level-based adjustment advice with concrete metrics |
| `layout_warnings` | array | List of layout warnings such as Float Drop (empty array = clean) |
| `auto_fit_status` | object | `{run: bool, result: string}` Auto-Fit execution info |

#### Status 1: `success` — Single-page fit achieved

Trigger: `current_pages == 1` and no `layout_warnings`

**Case A: Normal success** (`fill_ratio ≥ 0.8`)
```json
{
  "status": "success",
  "message": "Resume successfully fitted to single page PDF.",
  "suggestion": "The resume is ready. You can save it or make further adjustments if needed.",
  "next_action": "Deliver the PDF to user or continue refining content."
}
```

**Case B: Success but sparse content** (`fill_ratio < 0.8`)
```json
{
  "status": "success",
  "message": "Resume fitted to single page, but content is sparse (fill ratio: 72%). Consider adding more content for better visual balance.",
  "suggestion": "Add more achievements, skills, or project details to fill the page better.",
  "next_action": "Review the hint field for specific expansion suggestions, or accept the current result."
}
```

#### Status 2: `layout_warning` — Single-page but layout collapsed

Trigger: `current_pages == 1` and `layout_warnings` is non-empty (Float Drop detected)
```json
{
  "status": "layout_warning",
  "message": "Resume fitted to single page, but layout issues detected (e.g., float drop).",
  "suggestion": "Shorten the job titles or bold texts mentioned in the layout_warnings to prevent dates from dropping to the next line.",
  "next_action": "Fix the layout warnings by shortening the problematic lines and call render_resume_pdf again.",
  "layout_warnings": [
    "Layout warning: line (\"National Aeronautics and Space Administratio...\") is too long, causing the right-aligned date to drop to the next line. Shorten this text!"
  ]
}
```

#### Status 3: `overflow` — Content exceeds one page

Trigger: `current_pages > 1`
```json
{
  "status": "overflow",
  "reason": "content_exceeds_one_page",
  "message": "Content overflows by 12%, rendered 2 pages.",
  "suggestion": "Apply reduction strategy based on overflow amount. See hint field for specific recommendations.",
  "next_action": "Reduce content by approximately 12% following the Level strategy in hint, then call render_resume_pdf again."
}
```

### 3.3 MCP Output: Error States

All error responses share a uniform format and **do not** include the common fields above (no PDF generated).

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"error"` |
| `error_code` | string | Error code (see table below) |
| `message` | string | Error description |
| `suggestion` | string | Fix recommendation |
| `next_action` | string | Recommended next step |

#### Error codes

| error_code | Trigger | suggestion |
|------------|---------|------------|
| `EMPTY_CONTENT` | `markdown` is empty or missing | Provide resume content in Markdown format |
| `RENDER_FAILED` (timeout) | Rendering timed out (default 15s) | Reduce content length and retry, or check Chromium installation |
| `RENDER_FAILED` (browser) | Chromium initialization failed | Run `playwright install chromium` |
| `RENDER_FAILED` (file/path) | Invalid or non-writable output path | Verify output directory exists and is writable |
| `RENDER_FAILED` (generic) | Other rendering exceptions | Check that Markdown content is valid and properly formatted |

#### Error example
```json
{
  "status": "error",
  "error_code": "EMPTY_CONTENT",
  "message": "Markdown content cannot be empty",
  "suggestion": "Provide resume content in Markdown format with sections like ## Experience, ## Education, ## Skills",
  "next_action": "Generate resume content first using user's experience data, then call render_resume_pdf again",
  "example": "## Experience\n\n**Company Name** · Job Title\n- Achievement 1\n- Achievement 2"
}
```

### 3.4 Debug Sidecar

On every successful render (non-error), a `.debug.json` file is written alongside the PDF:
```
output_resume.pdf        ← PDF file
output_resume.debug.json ← Debug info (metrics, content_stats, auto_fit_status, layout_debug, etc.)
```

## 4. 布局后置检查 (Layout Validation)

### Float Drop 问题
当 Entry 标题行过长时，CSS `float: right` 的日期 `<em>` 会被挤到下一行（Float Drop），导致排版塌陷。

### 检测机制
渲染完成（Auto-Fit 之后），通过 Playwright `page.evaluate()` 注入 JS 检测：
1. 遍历 `.pagedjs_page p` 中所有符合 `strong:first-of-type + em:last-of-type` 特征的段落
2. 比较 `strong` 和 `em` 的 `getBoundingClientRect().bottom`
3. 差值 > 5px 即判定为 Float Drop，生成警告

### MCP 返回值
```json
{
  "status": "layout_warning",
  "layout_warnings": [
    "排版警告：所在行 (\"标题文本...\") 因名称过长导致日期塌陷。请缩短文本！"
  ]
}
```

### 未来方向：Flexbox 替代 Float（Pending）
目标：通过 Paged.js `beforeParsed` Handler 将符合特征的段落 DOM 重构为 Flexbox 容器，从根本上消除 Float Drop。
当前状态：**暂缓**，需先设计通用的 Markdown Schema 映射规则，避免依赖脆弱的正则匹配。

## 5. 关键技术细节

### 渲染完成信号
- `resume_renderer.js` 渲染完成后在 body 上添加 `render-complete` 类
- MCP Server 通过 `page.wait_for_selector('body.render-complete')` 等待

### 跨窗口握手协议
子窗口发送 `READY` → 父窗口回复 `ACK`。消息类型：`SET_CONTENT`, `UPDATE_CSS_VAR`, `UPDATE_STYLES`, `print`

### 状态管理器 (resumeStateManager.js)
Redux 风格，支持 dispatch/subscribe/中间件。仅用于外层控制面板 UI，MCP 渲染流程不依赖。

## 6. Agent 执行规范

- **Git 分支隔离 (CRITICAL)**：
    - `local-main`：所有开发在此进行
    - `public`：仅用于 Merge + Push 到 `origin/main`，处理完立刻切回 `local-main`
- **编码**：始终 UTF-8
- **环境**：Anaconda `agent_env`
- **文档维护**：代码变更时同步更新 README.md 和本文档

## 7. 调试技巧

```python
# 直接调用渲染器（绕过 MCP 协议）
import asyncio
from mcp_server.resume_renderer import ResumeRenderer

async def main():
    renderer = ResumeRenderer()
    result = await renderer.render_resume_pdf(markdown, "test.pdf")
    print(result)

asyncio.run(main())
```

- **状态快照**：控制台输入 `window.ResumeState.getState()`
- **AutoFit 日志**：控制台过滤 `[Renderer]` 标签
- **测试**：`python -m pytest tests/`

## 8. TODO

- [ ] **双行 Flexbox Entry**: 通过 Paged.js Handler `beforeParsed` 实现安全的 DOM 重构，需先设计通用 Markdown Schema
- [ ] **列表/段间距微调**: 列表间距设为零仍有间隙，可能需要负 margin 或排查中间 CSS 元素
