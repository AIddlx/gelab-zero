"""
scrcpy-py-ddlx 连接管理器

提供全局单例的 scrcpy-py-ddlx 连接管理，支持：
- 多设备连接池
- 自动连接和断开管理
- 自动重连机制
- 健康检查
- 线程安全
"""

import sys
import os
import logging
import threading
import time
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

# 添加 scrcpy-py-ddlx 路径（与 gelab-zero 平级）
_current_file = os.path.abspath(__file__)
_gelab_root = os.path.dirname(os.path.dirname(_current_file))
_scrcpy_path = os.path.join(os.path.dirname(_gelab_root), 'scrcpy-py-ddlx')

if os.path.exists(_scrcpy_path) and _scrcpy_path not in sys.path:
    sys.path.insert(0, _scrcpy_path)

# 导入 scrcpy-py-ddlx
from scrcpy_py_ddlx import ScrcpyClient, ClientConfig

logger = logging.getLogger(__name__)


@dataclass
class ScrcpyConnection:
    """scrcpy-py-ddlx 连接封装"""
    device_id: str
    client: ScrcpyClient
    last_used: float
    health_check_failures: int = 0
    connection_info: dict = None  # 连接信息（连接方式、stay_awake 等）

    def __post_init__(self):
        if self.connection_info is None:
            self.connection_info = {}

    def is_alive(self) -> bool:
        """检查连接是否存活"""
        try:
            return self.client.is_connected and self.client.is_running
        except Exception:
            return False


class ScrcpyConnectionManager:
    """
    scrcpy-py-ddlx 连接管理器（全局单例）

    功能：
    - 管理多个设备的连接
    - 自动连接和断开
    - 自动重连
    - 健康检查
    - 线程安全
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def _enable_tcpip_mode(self, device_id: str) -> Optional[str]:
        """自动启用设备的 TCP/IP 无线连接模式（仅限真机）

        Args:
            device_id: 设备序列号（USB 连接）

        Returns:
            无线连接地址 (ip:port)，如果启用失败返回 None
        """
        try:
            import subprocess
            import re

            logger.info(f"正在为真机设备 {device_id} 启用 TCP/IP 模式...")

            # 1. 启用 TCP/IP 模式 (端口 5555)
            result = subprocess.run(
                [self._adb_path, "-s", device_id, "tcpip", "5555"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.error(f"启用 TCP/IP 模式失败: {result.stderr}")
                return None

            logger.info(f"设备 {device_id} TCP/IP 模式已启用 (端口 5555)")

            # 2. 获取设备的 WiFi IP 地址（仅从 wlan0 接口）
            # 只使用 ip addr show wlan0，确保获取真实 WiFi IP
            result = subprocess.run(
                [self._adb_path, "-s", device_id, "shell", "ip", "addr", "show", "wlan0"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.error(f"无法获取 wlan0 接口信息: {result.stderr}")
                return None

            # 查找 wlan0 的 inet 地址（跳过 inet6）
            device_ip = None
            for line in result.stdout.split('\n'):
                if 'inet ' in line and 'inet6' not in line:
                    # 格式: inet 192.168.1.100/24 brd ...
                    match = re.search(r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                    if match:
                        device_ip = match.group(1)
                        break

            if not device_ip:
                logger.error(f"无法从 wlan0 获取设备 IP 地址")
                logger.debug(f"wlan0 输出: {result.stdout}")
                return None

            # 3. 验证是真机 IP（过滤模拟器 IP 和特殊网络）
            # 模拟器 IP: 10.0.2.x, 10.10.10.x, 192.168.5x.x 等
            # 真机通常是: 192.168.x.x, 10.x.x.x (正常局域网)
            if device_ip.startswith('10.0.2.') or device_ip.startswith('10.10.10.'):
                logger.error(f"检测到模拟器 IP 地址 {device_ip}，跳过连接（仅支持真机）")
                return None

            logger.info(f"检测到真机 WiFi IP: {device_ip}")

            # 4. 连接到无线地址
            wireless_addr = f"{device_ip}:5555"
            logger.info(f"正在连接到 {wireless_addr}...")

            result = subprocess.run(
                [self._adb_path, "connect", wireless_addr],
                capture_output=True,
                text=True,
                timeout=10
            )

            if "connected" in result.stdout.lower():
                logger.info(f"✅ 成功启用双链路模式: USB ({device_id}) + 无线 ({wireless_addr})")
                return wireless_addr
            else:
                logger.warning(f"TCP/IP 已启用但连接失败: {result.stderr}")
                return device_ip  # 返回 IP 地址，scrcpy-py-ddlx 可能可以处理

        except Exception as e:
            logger.error(f"启用 TCP/IP 模式时出错: {e}")
            return None

    def _check_tcpip_available(self, device_id: str) -> bool:
        """检查设备是否支持 TCP/IP 无线连接

        Args:
            device_id: 设备序列号

        Returns:
            True 如果设备已启用 TCP/IP 模式，否则 False
        """
        try:
            import subprocess
            import re

            # 检查设备是否有 IP 地址（表示已启用 TCP/IP）
            result = subprocess.run(
                [self._adb_path, "-s", device_id, "shell", "ip addr show"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # 查找 wlan0 或类似接口的 IP 地址
                ip_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
                ips = re.findall(ip_pattern, result.stdout)
                # 过滤掉本地回环地址
                ips = [ip for ip in ips if not ip.startswith('127.')]
                return len(ips) > 0

            return False
        except Exception as e:
            logger.debug(f"检查 TCP/IP 可用性失败: {e}")
            return False

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._connections: Dict[str, ScrcpyConnection] = {}
        self._lock = threading.RLock()  # 可重入锁
        self._initialized = True

        # 配置
        self._max_health_failures = 3
        self._connection_timeout = 10.0
        self._health_check_interval = 30.0

        # ADB 路径
        import shutil
        self._adb_path = shutil.which("adb")

        logger.info("ScrcpyConnectionManager 初始化完成")

    def get_client(self, device_id: str, show_window: bool = True) -> Optional[ScrcpyClient]:
        """
        获取设备的 scrcpy-py-ddlx 客户端

        Args:
            device_id: 设备序列号
            show_window: 是否显示实时预览窗口（仅在首次创建连接时生效）

        Returns:
            ScrcpyClient 实例，如果获取失败返回 None

        Note:
            如果已有连接存在，将直接返回现有连接（忽略 show_window 参数），
            以避免因 show_window 参数不同而导致的重新连接和白屏问题。
        """
        with self._lock:
            # 检查现有连接
            if device_id in self._connections:
                conn = self._connections[device_id]
                if conn.is_alive():
                    conn.last_used = time.time()
                    # 复用现有连接，忽略 show_window 参数差异
                    current_show_window = conn.connection_info.get('show_window', False)
                    if current_show_window != show_window:
                        logger.debug(f"show_window 参数不同（请求={show_window}, 现有={current_show_window}），复用现有连接")
                    return conn.client
                else:
                    # 连接已断开，清理
                    logger.warning(f"设备 {device_id} 连接已断开，将重新连接")
                    self._cleanup_connection(device_id)

            # 创建新连接（使用请求的 show_window 参数）
            return self._create_connection(device_id, show_window)

    def _create_connection(self, device_id: str, show_window: bool = True) -> Optional[ScrcpyClient]:
        """
        创建新的 scrcpy-py-ddlx 连接

        Args:
            device_id: 设备序列号
            show_window: 是否显示实时预览窗口

        Returns:
            ScrcpyClient 实例，如果连接失败返回 None
        """
        logger.info(f"正在为设备 {device_id} 创建 scrcpy-py-ddlx 连接...")

        try:
            # 配置客户端
            import os
            # 使用模块级别定义的 _scrcpy_path
            scrcpy_server_path = os.path.join(_scrcpy_path, "scrcpy-server")

            # 检测设备类型并确定是否启用 TCP/IP
            tcpip_available = self._check_tcpip_available(device_id)

            # 只有在设备已经有无线连接时才启用 TCP/IP
            # 纯 USB 设备不尝试启用（避免干扰设备状态）
            if ':' in device_id:
                # 无线设备，已经支持 TCP/IP
                tcpip_available = True
                logger.info(f"检测到无线设备 {device_id}")
            else:
                # 纯 USB 设备
                if tcpip_available:
                    # 这不应该发生，但以防万一
                    logger.warning(f"纯 USB 设备 {device_id} 检测到 TCP/IP 可用，但为安全起见使用纯 USB 模式")
                    tcpip_available = False
                else:
                    logger.info(f"使用纯 USB 模式连接设备 {device_id}")
                    tcpip_available = False

            config = ClientConfig(
                device_serial=device_id,
                show_window=show_window,
                lazy_decode=False,  # 禁用懒加载，持续解码（解决解码问题）
                max_fps=60,  # 60帧流畅
                bitrate=8000000,  # 8兆码率
                connection_timeout=self._connection_timeout,
                server_jar=scrcpy_server_path,
                stay_awake=True,  # 服务端保活，防止设备休眠导致断开
                tcpip=tcpip_available,  # 只对已有无线连接的设备启用
                tcpip_auto_disconnect=False,  # 不断开连接，保持连接供下次使用
            )

            client = ScrcpyClient(config)

            # 连接设备
            if not client.connect():
                logger.error(f"设备 {device_id} 连接失败")
                return None

            # 获取连接信息
            connection_info = self._get_connection_info(client, show_window)

            # 输出连接信息到控制台
            self._print_connection_info(device_id, connection_info)

            # 存储连接
            conn = ScrcpyConnection(
                device_id=device_id,
                client=client,
                last_used=time.time(),
                connection_info=connection_info
            )
            self._connections[device_id] = conn

            logger.info(f"设备 {device_id} 连接成功 (尺寸: {client.device_size})")
            return client

        except Exception as e:
            logger.error(f"创建设备 {device_id} 连接时出错: {e}")
            return None

    def _get_connection_info(self, client: ScrcpyClient, show_window: bool) -> dict:
        """获取连接信息"""
        info = {
            "device_serial": getattr(client.state, 'device_serial', 'Unknown'),
            "show_window": show_window,
            "stay_awake": True,
            "tcpip": True,
            "tcpip_auto_disconnect": False,
            "connection_type": "USB",
            "tcpip_ip": None,
            "tcpip_port": None,
        }

        # 检查是否使用 TCP/IP 连接
        if hasattr(client.state, 'tcpip_connected') and client.state.tcpip_connected:
            info["connection_type"] = "TCP/IP (Wireless)"
            info["tcpip_ip"] = getattr(client.state, 'tcpip_ip', None)
            info["tcpip_port"] = getattr(client.state, 'tcpip_port', None)

        # 检查是否是双连接（USB + TCP/IP）
        if hasattr(client.state, 'tcpip_connected') and client.state.tcpip_connected:
            # 如果 serial 包含 :，说明使用的是 TCP/IP
            if info["device_serial"] and ":" in info["device_serial"]:
                info["connection_type"] = "TCP/IP (Wireless) - USB can be unplugged"
            else:
                info["connection_type"] = "USB + TCP/IP Dual-link (Seamless)"

        return info

    def _print_connection_info(self, device_id: str, info: dict):
        """打印连接信息到控制台"""
        print(f"\n{'='*60}")
        print(f"[设备] 设备连接信息: {device_id}")
        print(f"{'='*60}")
        print(f"连接方式: {info['connection_type']}")
        print(f"实时预览: {'[启用]' if info['show_window'] else '[禁用]'}")
        print(f"Stay Awake (服务端保活): {'[启用]' if info['stay_awake'] else '[禁用]'}")
        print(f"TCP/IP 无线模式: {'[启用]' if info['tcpip'] else '[禁用]'}")

        if info['tcpip_ip']:
            print(f"TCP/IP 地址: {info['tcpip_ip']}:{info['tcpip_port']}")
            print(f"[双链路] USB 可随时拔除，自动切换到无线连接")

        print(f"{'='*60}\n")

    def _cleanup_connection(self, device_id: str):
        """清理指定设备的连接"""
        if device_id in self._connections:
            conn = self._connections[device_id]
            try:
                if conn.client.is_connected:
                    conn.client.disconnect()
            except Exception as e:
                logger.warning(f"断开设备 {device_id} 时出错: {e}")
            del self._connections[device_id]

    def disconnect(self, device_id: str):
        """断开指定设备的连接"""
        with self._lock:
            self._cleanup_connection(device_id)

    def disconnect_all(self):
        """断开所有设备的连接"""
        with self._lock:
            device_ids = list(self._connections.keys())
            for device_id in device_ids:
                self._cleanup_connection(device_id)
        logger.info("所有设备连接已断开")

    def health_check(self, device_id: str) -> bool:
        """
        检查设备连接健康状态

        Args:
            device_id: 设备序列号

        Returns:
            True 表示健康，False 表示不健康
        """
        with self._lock:
            if device_id not in self._connections:
                return False

            conn = self._connections[device_id]
            if not conn.is_alive():
                conn.health_check_failures += 1
                logger.warning(f"设备 {device_id} 健康检查失败 ({conn.health_check_failures}/{self._max_health_failures})")

                # 失败次数过多，清理连接
                if conn.health_check_failures >= self._max_health_failures:
                    logger.error(f"设备 {device_id} 健康检查失败次数过多，清理连接")
                    self._cleanup_connection(device_id)
                return False

            # 重置失败计数
            conn.health_check_failures = 0
            return True

    def get_device_size(self, device_id: str, show_window: bool = True) -> Optional[Tuple[int, int]]:
        """
        获取设备屏幕尺寸

        Args:
            device_id: 设备序列号
            show_window: 是否显示实时预览窗口

        Returns:
            (width, height) 或 None
        """
        client = self.get_client(device_id, show_window=show_window)
        if client and client.is_connected:
            return client.device_size
        return None

    def is_connected(self, device_id: str) -> bool:
        """检查设备是否已连接"""
        with self._lock:
            return device_id in self._connections and self._connections[device_id].is_alive()

    def list_connected_devices(self) -> list:
        """列出所有已连接的设备ID"""
        with self._lock:
            return [device_id for device_id, conn in self._connections.items() if conn.is_alive()]

    def get_connection_info(self, device_id: str) -> Optional[dict]:
        """
        获取设备连接信息

        Args:
            device_id: 设备序列号

        Returns:
            连接信息字典，如果设备未连接返回 None
        """
        with self._lock:
            if device_id in self._connections:
                conn = self._connections[device_id]
                return conn.connection_info
            return None

    def __del__(self):
        """析构函数，清理所有连接"""
        try:
            self.disconnect_all()
        except Exception:
            pass


# 全局实例
_connection_manager = None


def get_scrcpy_manager() -> ScrcpyConnectionManager:
    """获取全局 scrcpy-py-ddlx 连接管理器实例"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ScrcpyConnectionManager()
    return _connection_manager


__all__ = [
    "ScrcpyConnectionManager",
    "get_scrcpy_manager",
]
