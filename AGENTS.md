# Agent 使用指引

## 基本编码与语言要求
- 始终以 UTF-8 读写文件，遇到中文或特殊字符时主动检查避免乱码，必要时举例说明处理方式。
- 和用户的对话文档、注释、日志、解释均优先使用中文；如出现生僻英文术语，请补充括号说明含义和使用场景。
- 涉及多步骤任务时，按阶段同步进度，每一步做之前先说明你要做什么,遇到不确定点先提问或确认，再继续实施，做完之后说明下一步要做什么
- 如果用户没有直接给出修改的详细方案，那么动手前先说明你的方案，理由和计划并请求确认

### PowerShell (Windows 5.1) 全局执行规则

1. **所有命令必须通过**
	```powershell
	powershell.exe -NoLogo -NoProfile -Command <命令>
	```
	来执行。

2. **强制设置控制台为 UTF-8 编码（每次执行前都需设置）：**
	```powershell
	[Console]::InputEncoding = [Text.Encoding]::UTF8;
	[Console]::OutputEncoding = [Text.Encoding]::UTF8;
	chcp 65001 > $null;
	```

3. **读取文本文件统一写法：**
	```powershell
	Get-Content -Raw -Encoding UTF8 "<路径>"
	```

4. **写入文本文件统一写法：**
	```powershell
	Set-Content -Encoding UTF8 <路径> <内容>
	Add-Content -Encoding UTF8 <路径> <内容>
	Out-File -Encoding UTF8 <路径>
	```

5. **如环境中存在 PowerShell 7 (`pwsh`)，优先使用 `pwsh` 替代 `powershell.exe`。**




## 设计与实现准则
- 优先采用最佳实践与 MVP 原则，实现最核心价值后再扩展功能。
- 代码结构要清晰，合理分层与模块化；尽量复用已有模块或工具，避免重复造轮子。
- 关键逻辑、易混淆的流程写上适量注释，并提供日志或 console 输出示例帮助定位问题。

## 测试与质量保障
- 当修改影响测试或类型检查时，务必修复所有失败项，确保整套测试全绿。
- 如新增功能，请补充相应的单元测试或集成测试示例，并说明如何运行验证。

## 文档维护
- 关联代码有变动时，更新 `readme.md`：说明当前代码结构、各文件职责、调用关系以及新增/修改的使用方式。
- 若新增配置或脚本，也请记录在 README 或相关文档，保证他人可以按步骤复现。

## 环境与工具
- 默认使用 Anaconda 环境，先执行 `conda activate agent_env` 再运行 Python 相关命令。
- 需要使用 Node、npm、前端打包工具等其他技术栈时，请在文档中标明环境要求与启动指令。
- 注意当前系统为 Windows，涉及路径、分隔符、自动化脚本时遵循 Windows 习惯。

## 反馈与交付
- 提交结果时，简要概述修改点、测试方式和执行结果，并给出可选的后续建议。
- 若遇到阻塞或外部依赖问题，及时说明已有尝试和卡点，等待进一步指示。



npx @agentdeskai/browser-tools-server@1.2.0
