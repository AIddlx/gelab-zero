@echo off
REM Gelab MCP Server - STDIO 模式启动脚本
REM 用于 MCP 客户端软件连接

echo [启动] Gelab MCP Server (STDIO 模式)...

REM 设置 stdio 模式
set GELAB_MCP_TRANSPORT=stdio

REM 启动服务器
python mcp_server\detailed_gelab_mcp_server.py
