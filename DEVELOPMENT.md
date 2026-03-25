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
    └─ overflow: 超出一页，带削减建议
    ↓
AI Agent 根据反馈自我修正 → 循环直到成功
```

### 削减策略（三级）
详见 `AI_AGENT_PROMPT.md`：
- **Level 1（<5%）**：格式优化（合并孤行、单行列表）
- **Level 2（5-15%）**：内容精简（移除软技能、简化 STAR）
- **Level 3（>15%）**：深度削减（移除整块不相关经历）

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
