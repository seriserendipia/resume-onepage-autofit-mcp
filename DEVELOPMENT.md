# Resume One-Page Autofit MCP 开发文档

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


# TODO
列表间距的范围我希望改小一点，我现在设置为零，依然觉得有点宽

这里可能有两种原因，一种是现在列表间距的定义，在视觉上看起来不是直接反映列表这一段和上一段之间的间距的,中间还有别的元素，我们没有操作到,还有一种可能是列表间距，有可能是负的，先帮我调研 css 的结构，然后再做修改

强调段落间距也是同一个问题