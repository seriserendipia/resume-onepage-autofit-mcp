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

### Entry 格式

#### Experience / Projects 条目（单行）
```markdown
**Company** · Role · Location *Date Range*

- **Label:** Description with **key metric**
```

#### Education 条目（双行，中间需空行）
```markdown
**University** *Date Range*

**Degree** (GPA) *Location*

- Relevant coursework: ...
```
两行都以行尾斜体结尾 → 被标为 `.entry-header`，日期和地点自动右对齐（flex，不是 float，原因见下一条）。
Markdown 空行是语法要求（分离为两个 `<p>`），CSS 规则会清零连续 entry-line 间距，视觉上 = line-height。

### CSS 布局特性
- **日期右对齐**: 段落以行尾 `<em>` 结尾时被标为 `.entry-header`（flex 行），`<em>` 靠右。不要改回 `float:right`：浮动会让日期在 PDF 内容流里脱离标题行，Workday 自动填充会丢掉所有日期（在真实 Workday 站点上实测）
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
│   ├── config.defaults.js     # 配置默认值（单一权威源）
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
1. 把当前样式（`defaultStyles`）当作「理想状态」，各参数上下限与步长取自 `sliderConfig`
2. 生成一条从「最宽松」到「最紧凑」的状态阶梯：理想状态向上按 `autoFit.expandOrder` 逐步放大，向下按 `autoFit.shrinkOrder` 逐步收紧，每一步只动一个参数
3. 二分查找能放进一页的最宽松状态（约 5–6 次渲染）
4. 最紧凑状态仍溢出时保持该状态并返回 `overflow`，由调用方删减内容，不再继续压缩排版

收紧顺序（对可读性伤害从小到大）：章节间距 → 页边距 → 条目间距 → 列表项间距 → 标题比例 → 行高 → 字号。

### D. 排版默认值（权威来源：`js/config.defaults.js`）

正文字体为随仓库分发的 Source Sans 3（`fonts/`，SIL OFL 1.1，静态字重，PDF 中以 CID TrueType 嵌入）。
字号与行高是按它的 x-height（0.478em，比 Arial 的 0.528em 矮）调的：12pt 的视觉大小约等于 Arial 10.9pt。换字体需一并重调。

垂直间距统一以 `u` = 一行正文高度（`fontSize × lineHeight`）为单位，并保持 章节间距 > 条目间距 > 列表项间距。
行高按角色设定：正文用 `--line-height`，章节标题固定 1.2，姓名固定 1.1。

| 参数 (`defaultStyles`) | CSS 变量 | 理想值 | Auto-Fit 范围 | 步长 |
|---|---|---|---|---|
| `fontSize` 正文字号 | `--body-font-size` | 12pt | 11.5–13pt | 0.25 |
| `lineHeight` 正文行高 | `--line-height` | 1.26 | 1.18–1.36 | 0.02 |
| `headingScale` 章节标题倍数 | `--heading-scale` | 1.1 | 1.0–1.2 | 0.05 |
| `margin` 页边距（实际边距） | `--page-margin` | 13mm | 10–18mm | 1 |
| `titleHrMargin` 章节间距 | `--title-hr-margin` | 0.8u | 0.5–1.0u | 0.1 |
| `bodyMargin` 条目间距 | `--body-margin` | 0.45u | 0.25–0.6u | 0.05 |
| `ulMargin` 列表项间距 | `--ul-margin` | 0.1u | 0–0.2u | 0.05 |
| `strongParagraphMargin` 条目头额外间距（叠加在条目间距之上，仅 `.entry-header`） | `--strong-paragraph-margin` | 0u | 0–0.2u | 0.1 |

容量参考（A4，实测一份典型简历）：约 485 词可用 12pt / 行高 1.22；约 515 词时行高压到下限 1.18；约 600 词以上在 11.5pt 下限仍溢出。

> 注：`--page-margin` 现在就是实际页边距。此前 `.page` 的 padding 与 `@page` margin 叠加，实际边距是配置值的 2 倍。

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
| `markdown_path` | string | ✅ | — | Absolute path to the resume Markdown file (UTF-8) |
| `output_path` | string | ❌ | `resume.pdf` | PDF output path (e.g. `JohnDoe_Google_SWE.pdf`) |

#### `markdown_path` field detail

The tool takes a file path, not the resume text: every character of a tool argument is generated by the model, so inline content would make the model rewrite the whole resume on every render. The agent writes the file once and edits it in place between renders.

`read_markdown_file()` in `mcp_server.py` reads the path, on Linux and Windows alike:

- strips surrounding whitespace and quotes (Windows Explorer's "Copy as path" adds `"`), expands `~`;
- rejects relative paths: they would resolve against the server process's working directory, not the agent's workspace. On Windows, drive-relative `C:resume.md` and root-relative `\resume.md` are rejected too;
- reads with `utf-8-sig` and universal newlines, so a BOM and CRLF are accepted and `format_warnings[].line` matches the file's line numbers.

The `description` of `markdown_path` also carries the canonical resume forms the renderer parses, followed by a complete example (`EXAMPLE_RESUME`). `mcp_server.py` is the source of truth for that text; `tests/test_structured_sidecar.py` checks that the example has no `format_warnings`. The schema's `examples` array lists one Linux and one Windows path.

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
| `INVALID_PATH` | `markdown_path` missing, relative, or a folder | Pass the absolute path of the `.md` file |
| `FILE_NOT_FOUND` | No file at `markdown_path` | Write the resume to the file first |
| `FILE_READ_FAILED` | File is not UTF-8 or not readable | Save as UTF-8 / check permissions |
| `EMPTY_CONTENT` | The file is empty | Write resume content into the file |
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
当 Entry 标题行过长时，标题会折成多行（旧的 `float: right` 实现下表现为日期被挤到下一行，即 Float Drop），导致排版塌陷。

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

## 8. 配置默认值统一方案 (Config Defaults Unification)

### 8.1 现状：7 处默认值来源

> ⚠️ 本节是重构前的历史分析，表中数值（9pt / 7mm / 1.45 等）已过期。当前默认值见 §2.D 与 `js/config.defaults.js`。

默认值散落在 7 个位置，分属两套独立系统，数值互相矛盾。

#### 系统 A：iframe 内部（MCP 渲染路径）

| # | 位置 | 生效条件 | font-size | margin |
|---|------|----------|-----------|--------|
| ① | `resume_preview.html` CSS `var(--x, fallback)` | JS 未设置 CSS 变量时 | **12pt** | **20mm** |
| ② | `config.js` → `defaultStyles` | `applyDefaultStyles()` 读到 `window.ResumeConfig` | **9pt** | **7mm** |
| ③ | `resume_renderer.js` → `fitToOnePage()` 硬编码 fallback | `sliderConfig` 为空时 | max **12pt** | max **15mm** |

**流程**：页面加载 → `applyDefaultStyles()` 检查 `window.ResumeConfig` → 有则 `setProperty()` 覆盖 ① → `fitToOnePage()` 从 `sliderConfig` 读范围，缺失走 ③

**问题**：`config.js` 是 gitignored → CI/新用户没有 → ② 跳过 → ① 生效（12pt/20mm）→ ③ 也用错误范围

#### 系统 B：外层控制面板（滑杆 UI 路径）

| # | 位置 | 生效条件 | 优先级 |
|---|------|----------|--------|
| ④ | `localStorage` | 用户曾拖过滑杆 | **最高** |
| ⑤ | `control_panel.html` slider `value` 属性 | 首次加载，localStorage 为空 | 中 |
| ⑥ | `config.js` → `defaultStyles` | ④⑤ 都无值时的最终 fallback | **最低** |
| ⑦ | `resumeStateManager.js` 初始 `styles` | 被 slider 初始化立即覆盖 | 无实际影响 |

**流程**（`sliderController.loadDefaultValues()`）：
```
localStorage.getItem(key)          ← ④ 最高优先
  ↓ 没有
slider.defaultValue                ← 永远 undefined
  ↓ 没有
slider.value                       ← ⑤ HTML 硬编码
  ↓ 没有
config.defaultStyles[key]          ← ⑥ 最低 fallback
```

另外 `setupSingleSlider()` 用 `config.sliderConfig` 的 min/max/step 覆盖 HTML 属性，但 **不覆盖 value**。

#### 数值冲突对照

| 变量 | ① CSS | ②⑥ config | ③ fitToOnePage | ⑤ HTML | ⑦ stateManager |
|------|-------|-----------|----------------|--------|----------------|
| font-size | 12pt | 9pt | max 12pt | 9 | 16 |
| margin | 20mm | 7mm | max 15mm | 7 | 20 |
| heading-scale | 1.5 | 1.7 | max 1.7 | 1.7 | — |
| line-height | 1.4 | 1.45 | max 1.6 | 1.45 | 1.6 |
| title-hr-margin | 1 | 0 | — | 0 | — |
| strong-paragraph-margin | 0.5 | 0.2 | — | 0.2 | — |

### 8.2 方案：config.defaults.js 为唯一权威来源

#### 核心改动

**A. 文件层**

1. **`config.example.js` → `config.defaults.js`**（git tracked，始终存在）
   - 定义完整 `window.ResumeConfig = { defaultStyles, sliderConfig, autoFit, ... }`
   - 这是唯一需要维护默认值的地方

2. **`config.js`（gitignored）简化为覆盖文件**：
   ```javascript
   // 只写要改的，其余继承 config.defaults.js
   ResumeConfig.pdfOutput.directory = 'D:\\Downloads';
   ResumeConfig.pdfOutput.filename = 'Jane Doe resume.pdf';
   ```

3. **HTML 加载顺序**（3 个 HTML 文件）：
   ```html
   <script src="js/config.defaults.js"></script>  <!-- 权威默认值 -->
   <script src="js/config.js"></script>            <!-- 可选覆盖，404 无害 -->
   ```

**B. 消除 ① CSS fallback 的不一致**

CSS `var()` fallback 改为 **debug 哨兵值**，例如：
```css
font-size: var(--body-font-size, 99pt);       /* 如果看到 99pt，说明 JS 未加载 */
padding: var(--page-margin, 0mm);              /* 如果边距消失，说明 JS 未加载 */
```
理由：`config.defaults.js` 保证 `applyDefaultStyles()` 一定执行，CSS fallback **永远不应触发**。
用哨兵值而非"看起来合理的错误值"，好处是：
- 如果真触发了，**一眼看出问题**（页面字体巨大 / 边距消失）
- 不会被误认为"正常渲染"而隐藏 bug
- 不需要和 config.defaults.js 保持同步（因为是刻意错误的）

**C. 消除 ③ fitToOnePage() 硬编码 fallback 的不一致**

`config.defaults.js` 保证 `sliderConfig` 始终存在 → `getLimit()` 走正常路径 → 硬编码 fallback 永不触发。
同样改为哨兵值：
```javascript
getLimit('fontSlider', true, 999)   // 如果走到这，说明 sliderConfig 丢失
getLimit('marginSlider', true, 999)
```

**D. 消除 ⑤ HTML slider value 属性的重复维护**

在 `setupSingleSlider()` 中增加一行：**从 config.defaultStyles 设置 slider 初始 value**。
```javascript
// setupSingleSlider() 已有：
slider.min = sliderConfig.min;
slider.max = sliderConfig.max;
slider.step = sliderConfig.step;
// 新增：
slider.value = this.config.defaultStyles[sliderConfig.storage] ?? slider.value;
```
然后 HTML 里的 `value="9"` 等可以删掉或留着（不再是维护负担，因为会被覆盖）。

**E. 简化 ⑥ loadDefaultValues() fallback 链**

从 4 级变 2 级：
```javascript
loadDefaultValues() {
  this.config.sliderConfig.forEach(cfg => {
    const slider = this.sliders.get(cfg.id);
    if (slider) {
      const defaultValue = this.styleController.get(cfg.storage,  // ← localStorage
        this.config.defaultStyles[cfg.storage]);                   // ← config 唯一 fallback
      slider.value = defaultValue;
      this.handleSliderChange(cfg, defaultValue);
    }
  });
}
```

**F. ⑦ resumeStateManager 初始值**

把 `fontSize: 16, lineHeight: 1.6, margins: 20` 删除或改为从 config 读取。
此值会被 slider 初始化立即覆盖，影响微乎其微，但统一后消除困惑。

#### 改后的默认值来源数量

| 改前 | 改后 | 说明 |
|------|------|------|
| ① CSS fallback (12pt) | 哨兵值 (99pt)，不维护 | 仅用于发现 JS 加载失败 |
| ② config.js defaultStyles | `config.defaults.js`（唯一来源） | git tracked |
| ③ fitToOnePage fallback (12pt) | 哨兵值 (999)，不维护 | 仅用于发现 sliderConfig 丢失 |
| ④ localStorage | 保持不变 | 用户状态，不是"默认值" |
| ⑤ HTML slider value | 由 setupSingleSlider 从 config 写入 | 不再独立维护 |
| ⑥ loadDefaultValues fallback | 简化为只读 config | 跳过 slider.defaultValue 和 HTML value |
| ⑦ stateManager 初始值 | 从 config 读取或删除 | 消除困惑 |

**实际需要维护的来源：`config.defaults.js` 一处。** localStorage 是用户状态，不算默认值。

#### 迁移影响

- **CI / 新用户**：`config.defaults.js` 随 checkout 存在 → 默认值正确 → Float Drop 问题消失
- **现有 config.js 用户**：`config.js` 继续覆盖 → 无感知
- **localStorage 已有旧值的用户**：localStorage 优先级最高 → 仍用旧值 → 符合预期（用户主动设过的值不应被 pull 覆盖）

### 8.3 不选择的方案

| 方案 | 为什么不用 |
|------|-----------|
| config.js tracked（不 gitignore） | 每次 pull 覆盖用户个人路径，冲突不断 |
| CI 拷贝 config.example.js → config.js | 治标不治本，新用户仍需手动复制 |
| CSS `var()` fallback 写正确值 | 需要和 config 同步维护两处，违背单一来源原则 |
| 删除 CSS `var()` fallback | JS 加载前页面闪烁为浏览器默认值，debug 时不好定位 |

## 9. TODO

- [x] **执行 §8 配置默认值统一方案**（config.defaults.js 重构）— 已完成
- [x] **Education 双行对齐**（§10）— 通过 Schema 引导 + CSS 间距规则实现，无需 Flexbox
- [ ] **列表/段间距微调**: 列表间距设为零仍有间隙，可能需要负 margin 或排查中间 CSS 元素

### 已关闭
- ~~双行 Flexbox Entry~~：被 §10 方案取代。（2026-10-02 更正：当时认为“Flexbox 对 ATS 不友好”，实测相反——float 才是 Workday 丢日期的原因，条目头已改为单行 flex。）

## 10. Education 双行对齐方案

### 问题
四行教育格式（校名/日期/专业/地点各占一行）不触发 CSS float:right 规则，因为 `strong` 和 `em` 不在同一个 `<p>` 中。

### 方案：复用 Experience 的 float 机制

Education 条目改为双行格式（Markdown 需空行分离为两个 `<p>`），每行以 `**bold**` 开头、`*italic*` 结尾：

```markdown
**Stanford University** *2017 – 2019*

**M.S. Statistics** (GPA: 3.9/4.0) *Stanford, CA*
```

生成 HTML：
```html
<p><strong>Stanford University</strong> <em>2017 – 2019</em></p>
<p><strong>M.S. Statistics</strong> (GPA: 3.9/4.0) <em>Stanford, CA</em></p>
```

两个 `<p>` 都匹配 `p:has(> strong:first-child) > em:last-child` → 日期和地点自动 float:right。
Markdown 空行是语法要求（分离为两个 `<p>`），CSS 规则清零连续 entry-line 间距，视觉上 = line-height。

### CSS 改动

连续 entry-line 之间 margin 清零，使间距 = line-height（与段内行距一致）：

```css
/* 连续 entry-line: 第一个的 bottom margin 清零 */
p:has(> strong:first-child):has(> em:last-child):has(+ p > strong:first-child) {
  margin-bottom: 0;
}
/* 连续 entry-line: 第二个的 top margin 清零 */
p:has(> strong:first-child):has(> em:last-child)
+ p:has(> strong:first-child):has(> em:last-child) {
  margin-top: 0;
}
```

### 为什么不用 Flexbox

| 维度 | Flexbox DOM 重构 | 复用 float 机制 |
|------|-----------------|----------------|
| ATS | ❌ Flexbox 容器可能被误读 | ✅ 纯文本流 |
| 代码改动 | Paged.js Handler + 正则 | 零 JS，2 条 CSS |
| 一致性 | 教育用特殊路径 | 全部统一一个机制 |
