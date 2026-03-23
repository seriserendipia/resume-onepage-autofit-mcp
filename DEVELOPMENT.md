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

示例:
```markdown
**Google** · Senior Data Scientist · Mountain View, CA *Jan 2022 – Present*

- **A/B Testing:** Led experimentation framework serving **100M+ users**
- **Churn Modeling:** Built ML pipeline, reducing churn by **12%**
```

### CSS 布局特性
- **日期右对齐**: 当段落以 `<strong>` 开头、以 `<em>` 结尾时，`<em>` 自动 `float:right`
- **联系信息居中**: h1 后的第一个 `<p>` 自动居中
- **h2 下划线**: 章节标题自带底部边框，不需要 `---` 分隔符

### 不支持的格式
- `---` 水平线（h2 已有下划线，用 `---` 会浪费空间）
- 代码块、引用块、图片（无 CSS 支持）

## 1. 项目结构与职责

```text
resume-onepage-autofit-mcp/
├── control_panel.html         # [入口] 控制台页面，宿主环境
├── resume_preview.html        # [入口] 简历预览/渲染页面，被嵌入的iframe
├── example_resume.md          # 示例简历模板 (公开发布用)
├── myexperience.md            # 你的个人简历数据 (已在 .gitignore 中忽略)
├── mcp_server/                # MCP Server - AI 自动化渲染
│   ├── mcp_server.py          # MCP 协议服务器入口
│   ├── resume_renderer.py     # Playwright 渲染引擎
│   ├── requirements.txt       # Python 核心依赖
│   ├── requirements-dev.txt   # 开发依赖
│   └── README.md              # MCP Server 使用文档
├── js/                        # 核心逻辑
│   ├── resume_renderer.js     # ⭐ 主渲染器：Paged.js 模式 + 握手协议
│   ├── paged.polyfill.js      # Paged.js 库（分页渲染）
│   ├── controller.js          # 外层主控：初始化UI、监听消息、控制流程
│   ├── resumeStateManager.js  # 状态管理：Redux-like 状态容器
│   ├── styleController.js     # 样式逻辑：CSS变量计算与应用
│   ├── sliderController.js    # UI组件：滑杆事件绑定与数值映射
│   ├── pagedJsMiddleware.js   # 渲染队列：管理 Paged.js 的异步渲染任务
│   ├── domUpdater.js          # DOM 更新监听器
│   ├── config.js              # 配置文件（已在 .gitignore 中忽略）
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
    ├─ 加载 resume_renderer.js
    ├─ 加载 paged.polyfill.js
    └─ 等待握手信号
    ↓
resume_renderer.py 发送 SET_CONTENT
    ↓
resume_renderer.js 接收消息
    ├─ Markdown → HTML 转换
    ├─ 调用 Paged.js 分页渲染
    └─ 添加 render-complete 类
    ↓
resume_renderer.py 检测完成 → 生成 PDF
```

### B. 外层控制页面流程
1. 打开 `control_panel.html`。
2. `controller.js` 初始化，加载 `config.js` 配置。
3. 创建 `ResumeStateManager` 实例。
4. 加载 `resume_preview.html` 到 iframe。
5. `resume_renderer.js` 在 iframe 内启动，处理消息。

### C. 样式更新机制
1. 用户拖动滑杆 -> `sliderController.js` 捕获事件。
2. 通过 postMessage 发送 `UPDATE_CSS_VAR` 到 iframe。
3. `resume_renderer.js` 更新 CSS 变量并触发 Paged.js 重渲染。

### D. 自动一页 (Auto One-Page) 原理
逻辑位置：`js/resume_renderer.js` 中的 `window.simpleViewer.fitToOnePage`

当渲染完成且页数 > 1 或填充率 < 85% 时触发：
1. **方向判断**：确定是需要"收缩"还是"扩展"。
2. **循环迭代**：
   - 按策略顺序（字体大小 → 行高 → 边距等）调整参数。
   - 每次调整后重新渲染并检查页数/填充率。
3. **终止条件**：达到最佳状态或达到最大迭代次数。

## 3. MCP 集成架构

### AI & MCP 自动化渲染流程

```
AI Agent (推理层)
    ↓ 生成 Markdown 简历 V1
    ↓
调用 MCP Tool: render_resume_pdf
    ↓
MCP Server (执行层)
    - Playwright 启动 Headless Chrome
    - 加载 generated_resume.html
    - 注入 Markdown 内容
    - resume_renderer.js 触发 Paged.js 渲染
    - 等待 body.render-complete 信号
    - 检测页数和填充率
    ↓
返回结果到 AI Agent
    ├─ 成功：{ status: "success", pdf_path: "..." }
    └─ 失败：{ 
          status: "failed", 
          overflow_amount: 12,
          hint: "中等溢出（12%），应用 Level 2 削减"
       }
    ↓
AI Agent 分析反馈
    - 根据 overflow_amount 选择削减级别
    - 应用分层削减策略（见 AI_AGENT_PROMPT.md）
    - 生成 Markdown V2
    ↓
重新调用 render_resume_pdf 验证
    ↓
循环直到成功或达到最大迭代次数
```

### 削减策略（三级协议）

详见 `AI_AGENT_PROMPT.md`，核心原则：

- **Level 1（<5% 溢出）**：格式优化（合并孤行、单行列表）
- **Level 2（5-15% 溢出）**：内容精简（移除软技能、简化 STAR 描述）
- **Level 3（>15% 溢出）**：深度削减（移除整块不相关经历）

## 4. 关键技术细节

### A. 渲染完成信号机制
为了解决 Playwright 在内容加载完成前就进行溢出检测的问题，系统引入了状态信号：
- `resume_renderer.js` 在渲染完成后，会在 body 上添加 `render-complete` 类。
- 在 `fitToOnePage()` 自动适配逻辑完成后，最终样式应用完毕。
- MCP Server 通过 `page.wait_for_selector('body.render-complete')` 来确保检测时数据已就绪。

### B. 跨窗口通信与握手协议
由于外层控制页面 (`control_panel.html`) 和内层简历页面 (`resume_preview.html`) 是独立的浏览上下文，存在初始化竞态风险。
- **握手协议**：子窗口加载完成后向父窗口发送 `READY` 信号，父窗口收到后发送 `ACK` 确认。
- **消息类型**：
  - `SET_CONTENT`：注入 Markdown 内容
  - `UPDATE_CSS_VAR`：更新单个 CSS 变量
  - `UPDATE_STYLES`：批量更新样式
  - `print`：触发打印/导出

### C. 状态管理器 (resumeStateManager.js)
采用 Redux 风格的集中式状态管理：
- **dispatch(action)**：派发状态变更动作
- **subscribe(key, callback)**：订阅状态变化
- **中间件支持**：`pagedJsMiddleware` 拦截动作并管理渲染队列
- **调试**：`getHistory()` 查看状态变更历史

适用场景：外层控制页面的 UI 状态同步。MCP 直接渲染流程不依赖此模块。

## 5. Agent 执行与编码规范

为确保 AI Agent 在本项目中高效、安全地工作，须遵循以下规则：

- **Git 分支管理隔离 (CRITICAL)**：
    - **本地修改 (Local)**：所有的定制化开发、调试、个人偏好配置必须在 local-main 分支上进行。
    - **公开同步 (Public)**：如需将通用特性推送至外部仓库，切到 public 之后只负责 Merge 和 Push。**每次在 public 树处理完毕后，务必立刻 git checkout local-main 切回本地分支**，绝对禁止在 public 分支上直接做业务改动！

- **编码**：始终以 UTF-8 方式读写文件，避免中文乱码。
- **环境**：默认使用 Anaconda 环境 `agent_env`。
- **Windows 指令**：
    - PowerShell 命令必须带上 `[Console]::OutputEncoding = [Text.Encoding]::UTF8` 等前缀确保输出不乱码。
    - 优先使用 `pwsh` (PowerShell 7) 如果可用。
- **文档维护**：关联代码变更时，务必同步更新 README.md 和本开发文档。

## 6. 开发指南

### 如何添加一个新的样式控制？
1. **修改 CSS**：在 CSS 文件中定义新的 CSS 变量 (如 `--my-new-spacing`)。
2. **配置 Config**：在 `js/config.js` 的 `sliderConfig` 数组中添加配置对象：
   ```javascript
   {
     id: 'newSpacingSlider',      // DOM ID
     label: '新间距',
     cssVar: '--my-new-spacing',  // 对应的 CSS 变量
     unit: 'em',
     min: 0.1, max: 2.0, step: 0.1,
     defaultValue: 1.0
   }
   ```
3. **添加 HTML**：在 `control_panel.html` 中添加对应的 `<div id="newSpacingSlider">...</div>` 结构。

### 如何修改“自动一页”的策略？
编辑 `js/config.js` 中的 `autoFit` 对象：
- **修改顺序**：调整 `strategyOrder` 数组（例如优先压缩字体而不是边距）。
- **修改阈值**：调整 `bounds` 对象中各属性的 `min` (最小值) 和 `step` (步长)。

### 接入 AI 内容调整 (Future Hook)
在 `js/resume_renderer.js` 的 `window.simpleViewer.fitToOnePage` 方法中，
当自动调整无法满足单页需求时，可添加回调触发 AI 内容削减。

## 5. 调试技巧

### Python 脚本直接调用（调试用）

如果需要绕过 MCP 协议直接测试渲染功能：

```python
import asyncio
from mcp_server.resume_renderer import ResumeRenderer

async def main():
    renderer = ResumeRenderer()
    await renderer.start()
    
    markdown = """
    # 张三
    **邮箱**: zhangsan@email.com
    
    ## 工作经历
    **ABC 公司** · 软件工程师
    - 开发了高性能后端服务
    """
    
    result = await renderer.render_resume_pdf(markdown, "test_output.pdf")
    
    if result['status'] == 'success':
        print(f"✅ PDF: {result['pdf_path']}")
    else:
        print(f"⚠️ 溢出: {result['overflow_amount']}%")
    
    await renderer.stop()

asyncio.run(main())
```

### 可视化控制面板

在浏览器中打开控制面板实时调整样式：

```bash
# Windows
start control_panel.html

# 或使用 VS Code Live Server 扩展
```

### 其他调试技巧

- **状态快照**：在控制台输入 `window.ResumeState.getState()` 查看全量状态。
- **AutoFit 日志**：控制台过滤 `[Renderer]` 标签，可查看自动调整的每一步决策过程。
- **MCP 测试**：运行 `python tests/test_mcp_server.py` 验证渲染功能。
- **发布检查**：运行 `python tests/test_release_safety.py` 确保敏感信息已排除。

## 7. Git 分支策略

本项目使用**双线平行**分支策略：

| 分支 | 用途 | 推送目标 |
|------|------|---------|
| `local-main` | 本地开发，包含完整开发历史 | 不推送 |
| `public` | 公开发布，干净的提交历史 | `origin/main` |

### 工作流程

1. **日常开发**：在 `local-main` 分支上工作，正常 commit
2. **准备发布**：切换到 `public` 分支，**手动重新应用改动**（不用 merge/cherry-pick）
3. **推送**：`git push origin public:main`

### 重要原则

- **永远不要 merge 或 cherry-pick** `local-main` 到 `public`
- 两条线保持**平行**，`public` 只包含干净的、准备公开的提交
- `local-main` 可以有实验性代码、调试日志等，不会污染公开历史

### 发布时的操作

```bash
# 在 local-main 完成开发后
git checkout public

# 手动把改动文件复制过来，或用 git checkout 单个文件
git checkout local-main -- path/to/file1 path/to/file2

# 提交（写新的干净 commit message）
git add .
git commit -m "feat: your clean commit message"

# 推送
git push origin public:main
```

# TODO
列表间距的范围我希望改小一点，我现在设置为零，依然觉得有点宽

这里可能有两种原因，一种是现在列表间距的定义，在视觉上看起来不是直接反映列表这一段和上一段之间的间距的,中间还有别的元素，我们没有操作到,还有一种可能是列表间距，有可能是负的，先帮我调研 css 的结构，然后再做修改

强调段落间距也是同一个问题## 7. TODO: Layout & Formatting Enhancement Plan (Reference-Based)

### 目标与核心理念
当前的布局采用了一行式的标题组合，例如：`**公司** · 职位 · 地点 *时间*`。而参考设计（朋友简历）的核心在于**高密度的信息层级拆分和清晰的视觉对齐（双行排版、两端对齐）**，配合传统的衬线字体（Serif），营造出专业、学术的质感。

为了实现更好的视觉区分度，使得每个层次的小标题、时间地点都有清晰的界限，我们需要在输入 Schema (Markdown) 和 CSS 渲染层面分别进行优化：

### 1. Markdown 输入 Schema 优化方向计划
我们需要将原本拥挤在单行里的经历/教育标题，拆分为结构化的多行，以便 CSS 进行更清晰的对齐控制：

- [ ] **重构 Entry 级别的 Schema：**
    当前 Schema 工作流：`**公司名称** · 职位 · 地点 *时间区间*` 
    引入新的 Markdown 解析规则或微调整输入格式，要求严格按两行输出：
    ```markdown
    **公司名称** *地点*
    *职位/学位* **时间区间**
    ```
    *逻辑说明:* 然后我们需要修改 Markdown 渲染引擎拦截器（如在 JS 中注入特定的 class），或者通过 CSS 结构选择器选中连续的组合头，实现两行完全独立的两端对齐。第一层级为主体（公司/学校），第二层级为补充（职位/学位）。

- [ ] **技能区 (Skills) Schema 的复用：**
    ```markdown
    - **Programming/Languages:** Python, JavaScript, C++, SQL
    - **AI/ML:** LLMs, RAG, Prompt Engineering
    ```
    *逻辑说明:* 这一块内容的输入 Schema 可保持原样，直接通过更新 CSS 样式层去“劫持”无序列表的渲染。

### 2. CSS 样式优化方向计划
配合新的 Schema，CSS 需要发生结构性的改变以达到目标效果：

- [ ] **全局排版与字体 (Typography):**
    - 更换主字体为经典的衬线字体，比如 `Times New Roman`、`Garamond`。
    - 降低字号（如控制在 10pt-11pt），通过紧凑的行高 (`line-height: 1.2-1.3`) 极大地提高一页纸的信息密度。
- [ ] **模块大标题 (Section Headers / H2):**
    - 增加 `text-transform: uppercase;` (全大写)。
    - 使用贯穿的实线边框 `border-bottom: 1.2px solid #000;` 替代原有的隐式下划线风格。
    - 将下划线紧贴文本下方调整 `padding-bottom`。
- [ ] **经历/教育的信息头对齐 (Flexbox 替代 Float):**
    - 废弃不可控的基于 `float: right` 的方案，改写 CSS 让组合头变为 Flex 容器。
    - **Row 1:** `display: flex; justify-content: space-between;`
      - 左侧：加粗的机构/公司 (`font-weight: bold;`)
      - 右侧：常规或斜体的地点
    - **Row 2:** `display: flex; justify-content: space-between;`
      - 左侧：斜体的职位/项目名称 (`font-style: italic;`)
      - 右侧：加粗或常规的日期
- [ ] **技能部分表格化布局 (Skills Layout):**
    - 隐藏原有的列表圆点样式：`ul { list-style: none; padding-left: 0; }`。
    - Flex 网格化：将 `<li>` 强制转为 `display: flex; gap: 10px;`。
    - 将 `<strong>` 标签（即分类名）设定为一个固定宽度（如 `flex-basis: 130px; text-align: left;` ），从而形成左右分明、左侧词宽固定的两列对齐效果。
- [ ] **细节与点缀 (Visual Tweaks):**
    - **顶部头部 (Top Header):** 名字居中、超大字号、全部大写；下方的联系方式（邮箱/电话/LinkedIn/GitHub）通过分隔符 `|` 相连，并在屏幕中央严格对齐。
    - **外链提示:** 为项目区的外链 (`<a>` 标签) 通过类似 `::after { content: " ↗"; font-size: 0.8em; }` 添加超链接箭头指示符，增强现代感。

### 3. 排版与学术调研反馈 (Font & Spacing Analysis)

#### A. 字体调研: 衬线 (Serif) vs 非衬线 (Sans-Serif)
- **时代背景与阅读介质:** 过去为了应对低分辨率屏幕，数字端确实更偏爱无衬线体（如 Arial, Calibri），因为它们缺少锐利的边角，相对糊化的屏幕对它们的宽容度更高。但现代设备（Retina/4K 屏幕）已经完全解决了衬线字体的屏显锯齿问题。
- **专业度与行业心智:** 诸如金融（投行）、咨询（MBB）、学术科研及部分硅谷大厂等高净值行业，**高度偏爱经典的衬线字体（如 Garamond, Times New Roman, Georgia）**。这传递出一种审慎、专业、传统的精英气质和权威感。
- **ATS 支持度:** 两者对 ATS 系统（Applicant Tracking System）解析没有任何影响，因为解析是读取文件底层文本，而不是 OCR 渲染。
- **结论:** 使用衬线体作为基准字体（Base Font）并在排版上做到极致的紧凑，将会是一份高级、有实力的外推型简历的标志。

#### B. H2 下划线设计方案: order-bottom vs <hr>
在实现 1.2px solid #000 时，推荐**直接挂载在 h2 的 border-bottom 上**，而非通过单独注入 <hr> 标签实现：
1. **一致性:** Markdown 往往不会自然地在标题后紧跟 --- (解析为 <hr>)，直接写全局 h2 的 order-bottom 不需要改动原始 Markdown 数据，做到了逻辑内容和视觉渲染的彻底分离。
2. **盒模型控制:** 设置 order-bottom 配合 padding-bottom: 2px; 能以像素级精度控制线离文字的间隙 (Box Model)，不会像单独的块级元素 <hr> 一般受周围兄弟元素外边距叠加（margin-collapse）的干扰。

#### C. AI 看图调距反馈 (关于截图判断间距的局限力)
目前的滑杆系统提供了诸如字号(--body-font-size)、行高(--line-height)、段落间距(--body-margin) 等控制，这非常优秀。
关于**AI 能否通过看截图帮你调整滑竿**，我的真实反馈是：
1. **视野能感知整体紧凑度限制：** 作为多模态模型，我可以通过截图判断行与行之间太逼仄了、模块之间没有呼吸感，但我**无法反推给出精确的 CSS/滑竿数值调整口径**（比如看出这是1.2还是1.25行高）。这也是计算机视觉判断和渲染引擎之间的差异限制。
2. **最终决定权应该在滑杆与算法：** 借助你项目中已有的 itToOnePage 动态调整机制，以及预留好的拖动滑竿，实际上我们只需给定一个合理的默认安全范围（例如行高默认限制在 1.15 到 1.45），然后通过微调交给用户的直觉或程序的 Auto-fit 去收敛，这远比指望看图反推具体数值更科学稳定。
#### D. 默认滑杆区间 (Slider Ranges) 反馈与评测
在配合 Serif (衬线体) + 紧凑式学术排版时，CSS 变量滑杆的默认区间需要进行一些克制和微调，当前 `js/config.example.js` 的设定基本合理，但我建议按下述思路收拢范围以免布局崩溃：

1. **`--body-font-size` (基础字号)**: 
   - 现值：`min: 9, max: 13`
   - **反馈**: 9pt 在物理打印或 PDF 渲染中已经到了视觉极限。英文简历最稳妥的衬线字号是 **10pt - 11.5pt**。13pt 做基础字号则过大，会导致一行装不下几个单词。建议范围：`min: 9.5, max: 12`，**默认推荐值：10.5pt**。
2. **`--line-height` (行高)**: 
   - 现值：`min: 1.0, max: 1.7`
   - **反馈**: 行高绝对不能是 1.0，这会导致上下两行的英文字母（如上下延伸的 y, p 和大写字母等）黏连甚至重叠！衬线体的安全行高范围非常窄。建议范围：`min: 1.15, max: 1.5`，**默认推荐值：1.25**。
3. **`--page-margin` (纸张边距)**: 
   - 现值：`min: 7, max: 21`
   - **反馈**: 7mm 极容易被实体打印机的硬件安全边距（通常是 4mm~6mm）裁切，且视觉上非常有压迫感（页边像黑框一样）。建议范围：`min: 10, max: 25` (约 0.4英寸 到 1英寸)，**默认推荐值：15mm**。
4. **各个段间距组件 (Margin/Padding)**:
   - 由于我们切换到了下划线直接附着在 H2 上的方案（不再用横线标签），`--title-hr-margin` 等值应当克制，因为大留白会破坏衬线体那种紧凑的高级感，建议这些关于留白的 config 最大值最多不要超过 `0.6em`。

*备注：我已经为你写了一个专用的测试文件 `tests/test_slider_limits.html`。你可以直接双击运行它，里面通过写死的极限 CSS 变量，直观同屏呈现了三种状态 (Extreme Tight / Default Sweet Spot / Extreme Loose)，方便你进行感官比对和校准。*
