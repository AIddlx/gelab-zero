"""
GELab-Zero MCP Server - stdio 模式包装器

为 Claude Desktop 等 MCP 客户端提供稳定的 stdio 模式接口。
"""

import sys
import json
import os

# 添加项目路径（自动检测，从脚本位置推导）
# 无论脚本从哪里运行，都能正确找到项目根目录
_current_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(_current_file))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if "." not in sys.path:
    sys.path.append(".")

# 导入主 MCP 服务器
from mcp_server.detailed_gelab_mcp_server import mcp

# 运行 stdio 模式
if __name__ == "__main__":
    # 使用 stdio 传输模式（最兼容）
    mcp.run(transport="stdio")
