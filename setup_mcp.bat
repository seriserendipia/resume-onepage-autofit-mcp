@echo off
chcp 65001 >nul
echo 正在创建 MCP Server 结构...

python setup_mcp.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 创建成功！
    echo.
    echo 下一步：
    echo 1. cd mcp_server
    echo 2. pip install -r requirements.txt
    echo 3. playwright install chromium
    pause
) else (
    echo.
    echo ❌ 创建失败，请检查 Python 是否已安装
    pause
)
