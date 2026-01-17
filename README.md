# AI Resume Auto-Fitting System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-1.40+-green.svg)](https://playwright.dev/)

> 🤖 AI 驱动的简历自动适配系统：智能生成、精确检测、分层削减，确保完美单页输出

## ✨ 核心特性

- **🎯 智能适配**：自动调整内容，确保简历完美适配一页 A4
- **🔍 精确检测**：基于 Playwright 的页面高度检测，精确到像素
- **📊 分层削减**：三级削减策略（格式优化 → 内容精简 → 深度削减）
- **🔄 反馈闭环**：AI Agent 根据溢出指标智能迭代优化
- **🚀 MCP 集成**：支持 Claude Desktop 等 AI 客户端直接调用

## 📸 工作流程

```
用户提供经历 → AI 生成 Markdown 简历
                      ↓
            MCP Server 渲染验证
                      ↓
          ┌───── 检测页面高度 ──────┐
          │                       │
        成功                     失败
     (单页内)                 (溢出 X%)
          │                       │
    生成 PDF               返回溢出指标 + 建议
          │                       ↓
          │              AI 应用削减策略
          │                (Level 1/2/3)
          │                       │
          └───────── 重新渲染 ←────┘
```

## 🚀 快速开始

### 1. 安装 MCP Server

**Windows 用户：**
```batch
# 双击运行
setup_mcp.bat
```

**或手动安装：**
```bash
# 1. 创建 MCP Server 结构
python setup_mcp.py

# 2. 安装依赖
cd mcp_server
pip install -r requirements.txt

# 3. 安装 Chromium 浏览器
playwright install chromium
```

### 2. 测试运行

```bash
# 测试渲染功能
python test_mcp_render.py
```

### 3. 配置 AI Agent

**Claude Desktop 配置示例：**

编辑 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "resume-autofit": {
      "command": "python",
      "args": ["D:/path/to/mcp_server/mcp_server.py"],
      "cwd": "D:/path/to/project"
    }
  }
}
```

详见 [QUICKSTART.md](QUICKSTART.md)

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [QUICKSTART.md](QUICKSTART.md) | 快速开始指南（安装、配置、使用） |
| [AI_AGENT_PROMPT.md](AI_AGENT_PROMPT.md) | AI Agent 系统提示完整版 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 技术架构与开发文档 |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | 实施总结与技术亮点 |
| [mcp_server/README.md](mcp_server/README.md) | MCP Server 详细文档 |

## 🎨 削减策略概览

| 级别 | 溢出范围 | 策略 | 信息损失 |
|------|---------|------|---------|
| **Level 1** | < 5% | 合并孤行、单行列表 | 低 |
| **Level 2** | 5-15% | 移除软技能、简化描述 | 中 |
| **Level 3** | > 15% | 删除不相关经历 | 高 |

详细策略见 [AI_AGENT_PROMPT.md](AI_AGENT_PROMPT.md)

## 🛠️ 技术栈

- **Frontend**: HTML5 + CSS3 + Vanilla JavaScript
- **Rendering**: Native CSS Printing + Markdown-it
- **Backend**: Python + Playwright (Headless Chrome)
- **Protocol**: MCP (Model Context Protocol)
- **AI Integration**: Claude Desktop / Custom Agents

## 📊 项目结构

```
myresumebuilder/
├── mcp_server/                # MCP Server - AI 自动化渲染
│   ├── mcp_server.py          # MCP 协议服务器入口
│   ├── resume_renderer.py     # Playwright 渲染引擎
│   └── requirements.txt       # Python 依赖
├── js/                        # 前端核心逻辑
│   ├── simple_viewer.js       # 简历渲染器（原生 CSS）
│   ├── config.js              # 配置文件
│   └── ...                    # 其他模块
├── generated_resume.html      # 简历渲染页面
├── outer_resume_display.html  # 控制台页面
├── AI_AGENT_PROMPT.md         # AI 系统提示
├── QUICKSTART.md              # 快速开始
└── README.md                  # 本文件
```

## 🔧 使用示例

### 方式一：通过 AI Agent（推荐）

```
User: 请根据我的经历生成适配单页的简历

AI Agent:
1. 📝 生成初始 Markdown
2. 🔍 调用 render_resume_pdf 验证
3. ⚠️ 检测到溢出 12%
4. 🔧 应用 Level 2 削减策略
5. ✅ 成功！PDF 已生成
```

### 方式二：Python 脚本

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
    ...
    """
    
    result = await renderer.render_resume_pdf(markdown, "output.pdf")
    
    if result['status'] == 'success':
        print(f"✅ PDF: {result['pdf_path']}")
    else:
        print(f"⚠️ 溢出: {result['overflow_amount']}%")
        print(f"建议: {result['hint']}")
    
    await renderer.stop()

asyncio.run(main())
```

## 🎯 核心价值

### 传统方式 vs AI 自动化

| 传统方式 | AI 自动化方式 |
|---------|-------------|
| 手动调整字号、边距 | AI 自动应用最优策略 |
| 反复预览-修改-预览 | 一次性生成完美版本 |
| 难以判断删除优先级 | 基于相关性智能削减 |
| 耗时 30+ 分钟 | 通常 < 2 分钟 |

### 适用场景

- ✅ 求职者快速生成简历
- ✅ HR 批量处理候选人信息
- ✅ 招聘平台自动格式化
- ✅ 教育机构简历指导

## 🐛 已知限制

1. **浏览器依赖**：需要 Chromium（首次约 150MB）
2. **内容长度**：极长简历（10+ 页）可能需要多轮削减
3. **特殊字符**：部分 emoji 可能影响排版

## 🔄 开发路线图

### v0.2.0 (计划中)
- [ ] Web 可视化界面
- [ ] 批量渲染支持
- [ ] 自定义模板

### v0.3.0 (规划中)
- [ ] 多语言简历
- [ ] ATS 关键词优化
- [ ] 简历评分系统

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
# 克隆仓库
git clone <repo-url>
cd myresumebuilder

# 创建虚拟环境
conda create -n agent_env python=3.10
conda activate agent_env

# 安装依赖
pip install -r mcp_server/requirements.txt
playwright install chromium
```

### 提交规范

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `test:` 测试相关

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [Playwright](https://playwright.dev/) - 强大的浏览器自动化
- [MCP](https://modelcontextprotocol.io/) - 统一的 AI 工具协议
- [Markdown-it](https://github.com/markdown-it/markdown-it) - 可靠的 Markdown 解析器

## 📧 联系方式

- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/your-repo/discussions)

---

**⭐ 如果这个项目对你有帮助，请给一个 Star！**
