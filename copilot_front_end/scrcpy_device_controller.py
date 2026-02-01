"""
scrcpy-py-ddlx 设备控制器

提供统一的设备控制接口，基于 scrcpy-py-ddlx 实现：
- 所有动作类型的执行
- 坐标转换
- 与现有 API 兼容
"""

import logging
import time
from typing import Optional, Tuple, Dict, Any, List

from .scrcpy_connection_manager import get_scrcpy_manager
from copilot_front_end.package_map import find_package_name

logger = logging.getLogger(__name__)


class ScrcpyDeviceController:
    """
    scrcpy-py-ddlx 设备控制器

    提供与原 ADB 实现兼容的 API，完全基于 scrcpy-py-ddlx 实现。
    """

    def __init__(self, device_id: str):
        """
        初始化设备控制器

        Args:
            device_id: 设备序列号
        """
        self.device_id = device_id
        self._manager = get_scrcpy_manager()
        self._wm_size = None

    def _get_client(self):
        """获取 scrcpy-py-ddlx 客户端"""
        client = self._manager.get_client(self.device_id)
        if client is None:
            raise RuntimeError(f"无法连接到设备 {self.device_id}")
        return client

    @property
    def wm_size(self) -> Tuple[int, int]:
        """获取设备屏幕尺寸"""
        if self._wm_size is None:
            self._wm_size = self._manager.get_device_size(self.device_id)
            if self._wm_size is None:
                self._wm_size = (1080, 2400)  # 默认尺寸
        return self._wm_size

    def tap(self, x: int, y: int):
        """
        点击屏幕

        Args:
            x: X 像素坐标
            y: Y 像素坐标
        """
        client = self._get_client()
        client.tap(x, y)
        logger.debug(f"tap: ({x}, {y})")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """
        滑动屏幕

        Args:
            x1, y1: 起始坐标（像素）
            x2, y2: 结束坐标（像素）
            duration_ms: 滑动持续时间（毫秒）
        """
        client = self._get_client()
        client.swipe(x1, y1, x2, y2, duration_ms)
        logger.debug(f"swipe: ({x1},{y1}) -> ({x2},{y2}), {duration_ms}ms")

    def long_press(self, x: int, y: int, duration_ms: int = 1500):
        """
        长按屏幕

        Args:
            x: X 像素坐标
            y: Y 像素坐标
            duration_ms: 长按持续时间（毫秒）
        """
        client = self._get_client()
        # scrcpy-py-ddlx 的 long_press 方法
        client.long_press(x, y, duration_ms)
        logger.debug(f"long_press: ({x}, {y}), {duration_ms}ms")

    def inject_text(self, text: str):
        """
        输入文本

        Args:
            text: 要输入的文本
        """
        client = self._get_client()
        # scrcpy-py-ddlx 原生 UTF-8 支持
        client.inject_text(text)
        logger.debug(f"inject_text: {text[:50]}...")

    def home(self):
        """按 Home 键"""
        client = self._get_client()
        client.home()
        logger.debug("home key")

    def back(self):
        """按 Back 键"""
        client = self._get_client()
        client.back()
        logger.debug("back key")

    def menu(self):
        """按 Menu 键"""
        client = self._get_client()
        client.menu()
        logger.debug("menu key")

    def enter(self):
        """按 Enter 键"""
        client = self._get_client()
        client.enter()
        logger.debug("enter key")

    def volume_up(self):
        """按音量+键"""
        client = self._get_client()
        client.volume_up()
        logger.debug("volume_up")

    def volume_down(self):
        """按音量-键"""
        client = self._get_client()
        client.volume_down()
        logger.debug("volume_down")

    def start_app(self, app_name: str):
        """
        启动应用（使用 scrcpy-py-ddlx 原生实现）

        Args:
            app_name: 应用名称（支持模糊搜索）
        """
        client = self._get_client()

        # 尝试直接用应用名启动（scrcpy-py-ddlx 支持模糊搜索）
        try:
            client.start_app(f"?{app_name}")
            logger.info(f"启动应用: {app_name} (模糊搜索)")
            time.sleep(1)  # 等待应用启动
            return
        except Exception as e:
            logger.warning(f"模糊搜索启动失败: {e}，尝试精确包名")

        # 回退到精确包名
        package_name = find_package_name(app_name)
        if package_name is None:
            raise ValueError(f"应用 {app_name} 未找到")

        client.start_app(package_name)
        logger.info(f"启动应用: {app_name} (包名: {package_name})")
        time.sleep(1)

    def screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        """
        截图（使用 scrcpy-py-ddlx 内存模式，超快速）

        Args:
            filename: 保存文件名（None 则不保存）

        Returns:
            如果指定 filename，返回保存路径；否则返回 numpy 数组
        """
        client = self._get_client()
        return client.screenshot(filename)

    def disconnect(self):
        """断开设备连接"""
        self._manager.disconnect(self.device_id)


def convert_point_to_pixel(point: Tuple[int, int], wm_size: Tuple[int, int]) -> Tuple[int, int]:
    """
    将固定点坐标 (0-1000) 转换为实际像素坐标

    Args:
        point: 固定点坐标 (x, y)，范围 0-1000
        wm_size: 设备屏幕尺寸 (width, height)

    Returns:
        实际像素坐标 (x, y)
    """
    x, y = point
    real_x = int((float(x) / 1000) * wm_size[0])
    real_y = int((float(y) / 1000) * wm_size[1])
    return (real_x, real_y)


def convert_normalized_to_pixel(point: Tuple[float, float], wm_size: Tuple[int, int]) -> Tuple[int, int]:
    """
    将归一化坐标 (0.0-1.0) 转换为实际像素坐标

    Args:
        point: 归一化坐标 (x, y)，范围 0.0-1.0
        wm_size: 设备屏幕尺寸 (width, height)

    Returns:
        实际像素坐标 (x, y)
    """
    x, y = point
    real_x = int(x * wm_size[0])
    real_y = int(y * wm_size[1])
    return (real_x, real_y)


__all__ = [
    "ScrcpyDeviceController",
    "convert_point_to_pixel",
    "convert_normalized_to_pixel",
]
