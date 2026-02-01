@echo off
REM Gelab MCP Server - HTTP 模式启动脚本
REM 用于测试和调试，支持 SSE 流式传输

echo [启动] Gelab MCP Server (HTTP 模式)...

REM 设置 HTTP 模式
set GELAB_MCP_TRANSPORT=http

REM 启动服务器
python mcp_server\detailed_gelab_mcp_server.py
