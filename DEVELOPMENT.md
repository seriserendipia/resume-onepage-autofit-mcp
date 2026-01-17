# VirtualJobSeeker Resume Builder 开发文档

## 1. 项目结构与职责

```text
myresumebuilder/
├── outer_resume_display.html  # [入口]控制台页面，宿主环境
├── generated_resume.html      # [入口] 简历渲染页面，被嵌入的iframe
├── resumes/                   # 数据源文件夹 (Markdown)
├── mcp_server/                # MCP Server - AI 自动化渲染
│   ├── mcp_server.py          # MCP 协议服务器入口
│   ├── resume_renderer.py     # Playwright 渲染引擎
│   ├── requirements.txt       # Python 依赖
│   └── README.md              # MCP Server 使用文档
├── js/                        # 核心逻辑
│   ├── controller.js          # 外层主控：初始化UI、监听消息、控制流程
│   ├── simple_viewer.js       # 简化渲染器：原生 CSS 打印 + 自动适配
│   ├── viewer.js              # (Legacy) Paged.js 渲染器
│   ├── resumeStateManager.js  # 状态管理：Redux-like 状态容器
│   ├── styleController.js     # 样式逻辑：CSS变量计算与应用
│   ├── sliderController.js    # UI组件：滑杆事件绑定与数值映射
│   ├── renderer.js            # 内容转换：Markdown -> HTML
│   ├── pagedJsMiddleware.js   # 渲染队列：管理 Paged.js 的异步渲染任务
│   └── config.js              # 配置文件：滑杆范围、默认值、自动一页策略
├── AI_AGENT_PROMPT.md         # AI Agent 系统提示（削减策略）
├── setup_mcp.py               # MCP Server 安装脚本
└── setup_mcp.bat              # Windows 快捷安装脚本
```

## 2. 核心工作流

### A. 启动流程
1. 打开 `outer_resume_display.html`。
2. `controller.js` 初始化，加载 `config.js` 配置。
3. 创建 `ResumeStateManager` 实例。
4. 加载 `generated_resume.html` 到 iframe。
5. `viewer.js` 在 iframe 内启动，连接到父页面的状态管理器。
6. `dataLoader.js` 读取默认 Markdown 文件并触发 `SET_CONTENT`。

### B. 样式更新机制
1. 用户拖动滑杆 -> `sliderController.js` 捕获事件。
2. 调用 `startUpdate` -> 更新 State 中的 `styles`。
3. `pagedJsMiddleware` 拦截样式变更 -> 将渲染任务推入 `renderQueue`。
4. `viewer.js` 监听到队列变化 -> 调用 `Paged.js` 重新渲染 (`pagedPolyfill.preview()`)。

### C. 自动一页 (Auto One-Page) 原理
逻辑位置：`js/viewer.js` 类 `AutoOnePager`

当 Paged.js 渲染完成 (`onPagedRenderedOnce`) 且页数 > 1 时触发：
1. **快照**：记录当前所有滑杆的值。
2. **循环** (Max 10次)：
   - 检查当前页数。如果 <= 1，结束。
   - 按照 `config.js` 中的 `strategyOrder` 顺序寻找下一个可压缩属性。
   - **压缩**：将属性值减少一个 `step` (定义在 `config.js` 的 `bounds`)。
   - 应用新样式 -> 等待渲染完成。
3. **回退**：如果达到最小限制仍无法单页，触发 `requestContentAdjustment` (控制台输出 Log)。

## 3. MCP 集成架构 (新增)

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
    - 等待 simple_viewer.js 渲染完成信号
    - 检测页面高度（scrollHeight vs A4 高度）
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

### 关键技术点

1. **渲染完成信号**：
   - `simple_viewer.js` 在内容渲染完成后添加 `render-complete` CSS 类
   - Playwright 通过 `page.wait_for_selector('body.render-complete')` 等待

2. **溢出检测**：
   ```javascript
   const A4_HEIGHT_PX = 1120; // 297mm @ 96dpi
   const totalHeight = contentEl.scrollHeight;
   const pageCount = Math.ceil(totalHeight / A4_HEIGHT_PX);
   ```

3. **反馈精度**：
   - 返回具体的溢出像素（`overflow_px`）和百分比（`overflow_percentage`）
   - 提供针对性的削减建议（`hint`）

## 4. 开发指南

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
3. **添加 HTML**：在 `outer_resume_display.html` 中添加对应的 `<div id="newSpacingSlider">...</div>` 结构。

### 如何修改“自动一页”的策略？
编辑 `js/config.js` 中的 `autoFit` 对象：
- **修改顺序**：调整 `strategyOrder` 数组（例如优先压缩字体而不是边距）。
- **修改阈值**：调整 `bounds` 对象中各属性的 `min` (最小值) 和 `step` (步长)。

### 接入 AI 内容调整 (Future Hook)
在 `js/viewer.js` 的 `AutoOnePager.fitToOnePage` 方法底部，找到 `requestContentAdjustment` 日志处。
在此处添加代码：
1. 获取当前简历的 Markdown 内容。
2. 调用 AI Service (如 backend Python 服务)。
3. 获取精简后的 Markdown。
4. 调用 `renderer.render(newMarkdown)` 重新渲染。

## 4. 调试技巧
- **状态快照**：在控制台输入 `window.resumeController.stateManager.getState()` 查看全量状态。
- **AutoFit 日志**：控制台过滤 `[AutoOnePage]` 标签，可查看自动调整的每一步决策过程。


# TODO
列表间距的范围我希望改小一点，我现在设置为零，依然觉得有点宽

这里可能有两种原因，一种是现在列表间距的定义，在视觉上看起来不是直接反映列表这一段和上一段之间的间距的,中间还有别的元素，我们没有操作到,还有一种可能是列表间距，有可能是负的，先帮我调研 css 的结构，然后再做修改

强调段落间距也是同一个问题