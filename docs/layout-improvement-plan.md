# Resume Layout Improvement Plan — 日期右对齐 & 视觉层次优化

> **Status**: IMPLEMENTED & TESTED (9/9 tests pass)

## 一、现状分析

### 1. 渲染管线概览

```
LLM 生成 Markdown
    ↓
MCP Server (mcp_server.py) 接收 markdown 字符串
    ↓
resume_renderer.py 通过 Playwright 注入到 resume_preview.html
    ↓
浏览器端 markdown-it (js/resume_renderer.js) 转 HTML
    ↓ (零自定义渲染器/插件)
Paged.js 分页 → Playwright page.pdf() 输出
```

### 2. 当前 LLM 被引导生成的格式

Schema 中的示例:
```markdown
## Experience

**Google** · Software Engineer
*2020 - 2023*
- Built scalable systems...
```

渲染结果 = 全部左对齐，日期/地点单独一行，与公司名/职位在**不同的 `<p>` 标签**中。

### 3. markdown-it 转换行为

`markdown-it({ html: true })` + 零插件。输入→输出映射:

| Markdown 输入                          | HTML 输出                                       |
|---------------------------------------|------------------------------------------------|
| `**Google** · SWE`                     | `<p><strong>Google</strong> · SWE</p>`         |
| `*Jan 2022 – Present*`                | `<p><em>Jan 2022 – Present</em></p>`           |
| `**Google** · SWE *Jan 2022 – Present*` | `<p><strong>Google</strong> · SWE <em>Jan 2022 – Present</em></p>` |

**关键发现**: 如果公司/职位和日期在**同一行**，markdown-it 会生成一个 `<p>` 里同时包含 `<strong>` 和 `<em>`。这是实现右对齐的基础。

### 4. 当前 CSS 的问题

- 没有任何 `float:right`/`text-align:right`/flexbox 机制
- `em` 只有 `font-style:italic; color:#555`
- h1~h6 全部同样大小（`font-size` 公式一样）
- `p > strong:first-child` 的 `margin-top` 对 inline 元素无效（实际是 no-op）

---

## 二、目标效果（参考标准排版）

```
Company Name — Role Title                    Jan 2022 – Present
Location, State
- Achievement 1 with **key metric**
- Achievement 2
```

核心要求:
1. **日期右对齐**: 公司/职位在左，日期在右，同一行
2. **加粗公司/职位**: 视觉重点在公司和头衔
3. **数字/成果加粗**: `**15%**`, `**$2M**` 等关键数字突出
4. **一致的对齐**: 所有 section (Experience, Education, Projects) 统一格式

---

## 三、方案设计

### 核心思路: CSS `p em:last-child` 右浮动

**不改 markdown-it 配置, 不加插件, 不做 Python 预处理。**

仅通过 CSS 规则 + Schema 引导 LLM 格式 来实现。

### 3.1 LLM 输入格式约定 (Schema 引导)

要求 LLM 把日期用 `*italic*` 放在**同一行末尾**:

```markdown
**Google** · Senior Data Scientist · *Jan 2022 – Present*
Mountain View, CA
- Led A/B testing framework serving **100M+ users**
- Reduced churn by **12%** through ML pipeline
```

markdown-it 会把这渲染成:
```html
<p><strong>Google</strong> · Senior Data Scientist · <em>Jan 2022 – Present</em></p>
<p>Mountain View, CA</p>
```

### 3.2 CSS 变更 (resume_preview.html)

核心: 对"段落中最后一个 `<em>` 如果是行尾"做 float:right

```css
/* 日期右对齐: 段落末尾的 italic 文本浮动到右侧 */
p > em:last-child {
  float: right;
  color: #555;
  font-style: italic;
}

/* 包含 float 子元素的段落需要清除浮动 */
p {
  overflow: hidden; /* 或 clearfix */
}
```

**风险分析**: `p > em:last-child` 会命中**所有**段落末尾的 `<em>`，包括:
- ✅ `**Company** · Title · *Date*` → 正确右对齐
- ❌ `Expertise in *machine learning*` → 不应该右浮动

**解决方案**: 用更精确的选择器——只匹配"段落以 `<strong>` 开头且以 `<em>` 结尾"的情况:

```css
/* 仅当段落以 strong 开头、以 em 结尾时，右对齐末尾的 em */
p:has(> strong:first-child) > em:last-child {
  float: right;
  color: #555;
  font-style: italic;
}
```

`:has()` 在 Chromium 105+ 支持，我们用 Playwright + Chromium headless，完全可用。

### 3.3 Schema 描述修改 (mcp_server.py)

精简但明确告诉 LLM 格式约定:

```
SUPPORTED MARKDOWN FORMAT:
  # Name                    → candidate name (h1)
  ## Section                → section headers
  **bold**                  → company, title, key metrics
  *italic at end of line*   → dates (auto right-aligned in PDF)
  - bullet                  → achievements
  ---                       → section dividers
  [text](url)               → hyperlinks

ENTRY FORMAT (Experience/Education/Projects):
  **Company** · Role Title · *Jan 2022 – Present*
  Location, State
  - Achievement with **key number**
```

### 3.4 h1 vs h2 字体区分

当前 h1~h6 全部同大小。应分开:

```css
h1 {
  font-size: calc(var(--body-font-size, 12pt) * var(--heading-scale, 1.5) * 1.3);
  text-align: center;
  margin-bottom: 0.2em;
}
h2 {
  font-size: calc(var(--body-font-size, 12pt) * var(--heading-scale, 1.5));
  border-bottom: 1px solid #ccc;
  padding-bottom: 0.15em;
}
```

---

## 四、修改清单

### 文件 1: `resume_preview.html` (CSS)

| 位置 | 改动 |
|-----|------|
| `h1,h2,...h6` 规则 | 拆分 h1 和 h2 的 font-size，h1 居中+更大，h2 带下划线 |
| `em` 规则 | 保留现有 `font-style:italic; color:#555` |
| 新增规则 | `p:has(> strong:first-child) > em:last-child { float: right }` |
| `p` 规则 | 添加 `overflow: hidden` 清除浮动 |
| 删除 `hr` 或保留 | 如果 h2 自带下划线，可以在 Schema 中不再要求 `---`（减少空间浪费）|

### 文件 2: `mcp_server/mcp_server.py` (Schema)

| 位置 | 改动 |
|-----|------|
| `description` 参数 (tool level) | 替换为精简版，包含格式清单 + entry format 示例 |
| `markdown` 参数的 `description` | 明确格式约定：日期用 italic 放行尾 |

### 文件 3: `tests/test_inline_formatting.py` (测试)

| 改动 | 说明 |
|-----|------|
| 新增测试: `test_date_right_aligned` | 验证 `**Company** · Title · *Date*` 格式中 em 被 float:right |
| 新增测试: `test_inline_italic_not_floated` | 验证正文中的 `*italic*` 不被误浮动 |
| 现有测试 | 应全部保持通过（不改变 strong 行为）|

### 文件 4: `js/resume_renderer.js` — 不改

不添加任何自定义 markdown-it 渲染器或插件。纯 CSS 解决。

---

## 五、风险与兜底

| 风险 | 缓解措施 |
|-----|---------|
| LLM 不遵循格式（日期不放行尾） | Schema example 清晰引导；不影响渲染，只是不会右对齐 |
| `:has()` 兼容性 | Playwright 用 Chromium headless，`:has()` 完全支持 |
| `overflow:hidden` 截断内容 | 简历内容不会溢出 p 标签，实际无风险 |
| float 影响 Paged.js 分页 | 需实测；float 在 block formatting context 内，影响小 |
| Summary 段落中的 italic 误命中 | `:has(> strong:first-child)` 精确限定，Summary 段落开头不是 strong |

---

## 六、不做的事情

- 不添加 markdown-it 插件或自定义渲染器
- 不做 Python 端 markdown 预处理
- 不处理边缘 case（如日期在行中间的情况）
- 不改 auto-fit 算法
- 不加 config.js 新变量（保持简单）

---

## 七、Schema 最佳实践（基于 Anthropic 官方调研）

### 来源
- Anthropic Engineering Blog: "Advanced Tool Use"
- MCP 官方文档: modelcontextprotocol.io/docs/concepts/tools
- Anthropic Tool Use Docs: platform.claude.com

### 关键发现

1. **One-shot example 效果显著**: Anthropic 数据显示准确率从 72% → 90%
2. **属性描述用 `e.g.` + 内联示例**: 官方推荐模式
3. **Tool description**: 动词开头 + 说清返回值（含类型和枚举值）
4. **JSON Schema `examples` 字段**: 放完整 one-shot 示例

### 我们的 Schema 结构

```
Tool.description:
  - 一句话说功能 (动词开头)
  - Returns: 列出返回字段 + 类型 + 枚举值

inputSchema.properties.markdown:
  - description: 支持的格式清单 + entry format 说明
  - examples: [完整 one-shot 简历 markdown (~540 chars)]

inputSchema.properties.output_path:
  - description: 用途 + e.g. 示例 + 默认值
```

### LLM 只能看到的信息

通过 MCP `list_tools()` 返回:
1. `name` — 工具名
2. `description` — 工具描述
3. `inputSchema` — JSON Schema (含 property descriptions + examples)
4. `annotations` — 元信息 (title, hints)

LLM **看不到**: HTML/CSS/JS 模板、README、Python 渲染代码、测试文件。
