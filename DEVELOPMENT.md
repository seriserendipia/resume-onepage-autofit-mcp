# VirtualJobSeeker Resume Builder 开发文档

## 1. 项目结构与职责

```text
myresumebuilder/
├── outer_resume_display.html  # [入口]控制台页面，宿主环境
├── generated_resume.html      # [入口] 简历渲染页面，被嵌入的iframe
├── resumes/                   # 数据源文件夹 (Markdown)
└── js/                        # 核心逻辑
    ├── controller.js          # 外层主控：初始化UI、监听消息、控制流程
    ├── viewer.js              # 内层主控：负责Markdown渲染、Paged.js调用、AutoOnePage逻辑
    ├── resumeStateManager.js  # 状态管理：Redux-like 状态容器
    ├── styleController.js     # 样式逻辑：CSS变量计算与应用
    ├── sliderController.js    # UI组件：滑杆事件绑定与数值映射
    ├── renderer.js            # 内容转换：Markdown -> HTML
    ├── pagedJsMiddleware.js   # 渲染队列：管理 Paged.js 的异步渲染任务
    └── config.js              # 配置文件：滑杆范围、默认值、自动一页策略
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

## 3. 开发指南

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
