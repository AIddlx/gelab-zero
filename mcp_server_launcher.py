"""
MCP Server Launcher - 独立可执行文件
"""
import sys
import os

# 自动检测项目路径（支持任意目录结构）
project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# 切换到项目目录
os.chdir(project_path)

# 启动 MCP 服务器
if __name__ == "__main__":
    # 使用 simple HTTP MCP 服务器
    os.environ["PYTHONPATH"] = project_path
    from mcp_server import simple_http_mcp_server
