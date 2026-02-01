# to define a standard front-end action space;
# to define some different format of parsers;
# to define executors to execute the front-end actions;

import subprocess
import time
import subprocess
import os
import logging

import sys
# add current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copilot_front_end.package_map import find_package_name

logger = logging.getLogger(__name__)


def parser0729_to_frontend_action(parser_action):
    pass


def uiTars_to_frontend_action(ui_action):
    # 初始化为 None 或默认值
    action_type = None

    if "action" in ui_action:
        action_type = ui_action["action"]
    elif "action_type" in ui_action:
        action_type = ui_action["action_type"]
    else:
        # 关键：兜底处理！
        raise ValueError(f"ui_action must contain 'action' or 'action_type'. Got keys: {list(ui_action.keys())}")

    # 现在 action_type 一定有值
    ui_action['action_type'] = action_type

    if action_type == "WAIT":
        if "value" in ui_action:
            seconds = float(ui_action["value"])
            ui_action["seconds"] = seconds
    elif action_type == "LONGPRESS":
        duration = ui_action.get("duration", ui_action.get("value", 1.5))
        ui_action["duration"] = float(duration)

    return ui_action

def _convert_normalized_point_to_fixed_point(point):
    x, y = point
    assert type(x) == float and type(y) == float, f"Point coordinates must be float, got {type(x)} and {type(y)}"
    assert 0.0 <= float(x) <= 1.0, f"x {x} out of range [0.0, 1.0]"
    assert 0.0 <= float(y) <= 1.0, f"y {y} out of range [0.0, 1.0]"

    fixed_x = int(float(x) * 1000)
    fixed_y = int(float(y) * 1000)
    return (fixed_x, fixed_y)

def step_api_to_frontend_action(step_api_action, default_duration=1.5):
    """
    Convert step API actions to frontend actions.
    """
    
    if "action" in step_api_action:
        action_type = step_api_action["action"]
    elif "action_type" in step_api_action:
        action_type = step_api_action["action_type"]
    else:
        raise ValueError("No action or action_type in step_api_action")
    
    action_type_map = {
        # "CLICK": "Click",
        "Click": "CLICK",
        # "TYPE": "Type",
        "Type": "TYPE",
        # "COMPLETE": "Complete",
        "Complete": "COMPLETE",
        # "INFO": "Pop",
        "Pop": "INFO",
        # "WAIT": "Wait",
        "Wait": "WAIT",
        # "AWAKE": "Awake",
        "Awake": "AWAKE",
        # "ABORT": "Abort",
        "Abort": "ABORT",
        # "SWIPE": "Scroll",
        "Scroll": "SLIDE",
        # "LONGPRESS": "LongPress",
        "LongPress": "LONGPRESS",
    }

    if action_type not in action_type_map:
        raise ValueError(f"Unsupported action type: {action_type}")

    frontend_action_type = action_type_map[action_type]

    action_type = action_type_map[action_type]

    frontend_action = {"action_type": frontend_action_type}
    
    if action_type == "CLICK":
        assert "args" in step_api_action, "Missing args in CLICK action"
        assert "normalized_point" in step_api_action["args"], "Missing normalized_point in CLICK action args"

        point = _convert_normalized_point_to_fixed_point(step_api_action["args"]["normalized_point"])
        frontend_action["point"] = point
        return frontend_action
    
    elif action_type == "TYPE":
        assert "args" in step_api_action, "Missing args in TYPE action"
        assert "text" in step_api_action["args"], "Missing text in TYPE action args"
        text = step_api_action["args"]["text"]
        frontend_action["value"] = text

        # keyboard_exists
        # normlized_point
        if "keyboard_exists" in step_api_action["args"]:
            frontend_action["keyboard_exists"] = step_api_action["args"]["keyboard_exists"]
        else:
            frontend_action["keyboard_exists"] = True

        if "normalized_point" in step_api_action["args"]:
            point = _convert_normalized_point_to_fixed_point(step_api_action["args"]["normalized_point"])
            frontend_action["point"] = point
    
        return frontend_action
    
    elif action_type == "COMPLETE":
        return frontend_action
    
    elif action_type == "INFO":
        return frontend_action
    
    elif action_type == "WAIT":
        assert "args" in step_api_action, "Missing args in WAIT action"
        assert "duration" in step_api_action["args"], "Missing seconds in WAIT action args"
        seconds = step_api_action["args"]["duration"]
        frontend_action["seconds"] = float(seconds)

        return frontend_action
    
    elif action_type == "AWAKE":
        assert "args" in step_api_action, "Missing args in AWAKE action"
        assert "text" in step_api_action["args"], "Missing text in AWAKE action args"
        text = step_api_action["args"]["text"]
        frontend_action["value"] = text

        return frontend_action
        
    elif action_type == "ABORT":
        return frontend_action

    elif action_type == "SLIDE":
        assert "args" in step_api_action, "Missing args in SLIDE action"
        assert "normalized_path" in step_api_action["args"], "Missing normalized_path in SLIDE action args"

        path = step_api_action["args"]["normalized_path"]
        start_point = _convert_normalized_point_to_fixed_point(path[0])
        end_point = _convert_normalized_point_to_fixed_point(path[-1])

        frontend_action["point1"] = start_point
        frontend_action["point2"] = end_point

        frontend_action["duration"] = default_duration

        return frontend_action
    
    elif action_type == "LONGPRESS":
        assert "args" in step_api_action, "Missing args in LONGPRESS action"
        assert "normalized_point" in step_api_action["args"], "Missing normalized_point in LONGPRESS action args"

        point = _convert_normalized_point_to_fixed_point(step_api_action["args"]["normalized_point"])
        frontend_action["point"] = point

        frontend_action["duration"] = default_duration

        return frontend_action
    
    else:
        raise ValueError(f"Unsupported action type: {action_type}")
    

def _convert_point_to_realworld_point(point, wm_size):
    x, y = point
    # scrcpy-py-ddlx requires integer coordinates
    real_x = int((float(x) / 1000) * wm_size[0])
    real_y = int((float(y) / 1000) * wm_size[1])
    return (real_x, real_y)

def _detect_screen_orientation(device_id):
    """
    Detect the screen orientation of the specified device.
    adb shell dumpsys input | grep -m 1 -o -E "orientation=[0-9]" | head -n 1 | grep -m 1 -o -E "[0-9]"
    """
    # adb_command = _get_adb_command(device_id)
    if device_id is None:
        adb_command = "adb"
    else:
        adb_command = f"adb -s {device_id}"
    if os.name == 'nt':
        # Windows
        command = f'{adb_command}' + ''' shell dumpsys input | Select-String 'orientation=\\d+' | Select -First 1 | % { $_.Matches.Value -replace 'orientation=', '' }'''
        
        # 使用 subprocess 运行 PowerShell 命令
        result = subprocess.run(
            ["powershell.exe", "-Command", command],  # 核心参数
            capture_output=True,  # 捕获 stdout/stderr（可选）
            encoding="utf-8",     # 编码（避免乱码）
            shell=False,          # 无需开启 shell（PowerShell 本身就是解释器）
            check=False           # 是否抛出非0退出码异常（可选）
        )

    else:
        # Unix/Linux/Mac
        command = f'''{adb_command} shell dumpsys input | grep -m 1 -o -E "orientation=[0-9]" | head -n 1 | grep -m 1 -o -E "[0-9]"'''

        result = subprocess.run(command, shell=True, capture_output=True, text=True)


    result_str = result.stdout.strip()

    result = int(result_str.strip())

    return result


def act_on_device(frontend_action, device_id, wm_size, print_command=False, reflush_app=True, show_window=False):
    """
    Execute the frontend action on the device.
    1. # CLICK(point=(x,y))
    2. # LONGPRESS(point=(x,y), duration=sec)
    3. # TYPE(value="string", point=None, keyboard_exists=True)  # point is the text input box; if not given, use the current focus box
    4. # SCROLL(point=(x,y), direction="up|down|left|right")  //UI-Tars only
    5. # AWAKE(value=app_name)
    6. # SLIDE(point1=(x1,y1), point2=(x2,y2), duration=sec)
    7. # BACK()   //UI-Tars only
    8. # HOME()   //UI-Tars only
    9. # COMPLETE()
    10. # ABORT()
    11. # INFO()
    12. # WAIT(seconds=sec)

    13. # HOT_KEY(key="volume_up|volume_down|power|...")  

    Standard frontend action space:
    {
        "action_type": "CLICK",
        "param_key": param_value,
        ...
    }

    """
    valid_actions = ["CLICK", "LONGPRESS", "TYPE", "SCROLL", "AWAKE", "SLIDE", "BACK", "HOME", "COMPLETE", "ABORT", "INFO", "WAIT", "HOT_KEY"]

    assert "action_type" in frontend_action, "Missing action_type in frontend_action"
    assert frontend_action["action_type"] in valid_actions, f"Invalid action type: {frontend_action['action_type']}"

    action_type = frontend_action["action_type"]

    if action_type == "CLICK":
        assert "point" in frontend_action, "Missing point in CLICK action"

        orientation = _detect_screen_orientation(device_id)

        if orientation in [1, 3]:
            wm_size = (wm_size[1], wm_size[0])

        x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)

        cmd = f"adb -s {device_id} shell input tap {x} {y}"
        if print_command:
            print(f"Executing command: {cmd}")
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result
    
    elif action_type == "LONGPRESS":
        assert "point" in frontend_action, "Missing point in LONGPRESS action"
        assert "duration" in frontend_action, "Missing duration in LONGPRESS action"
        x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)
        duration = frontend_action["duration"]
        cmd = f"adb -s {device_id} shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -touch {x} {y} {int(duration * 1000)}"

        if print_command:
            print(f"Executing command: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result

    # adb shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -keyboard "{text}"
    elif action_type == "TYPE":
        assert "value" in frontend_action, "Missing value in TYPE action"

        value = frontend_action["value"]
        keyboard_exists = frontend_action.get("keyboard_exists", True)
        if not keyboard_exists:
            if "point" in frontend_action:
                x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)
                cmd = f"adb -s {device_id} shell input tap {x} {y}"
                if print_command:
                    print(f"Executing command: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                time.sleep(1)
            else:
                print("Warning: keyboard does not exist and point is not given. Using current focus box.")

        def preprocess_text_for_adb(text):
            # Escape special characters for adb shell input
            text = text.replace("\n", " ").replace("\t", " ")
            text = text.replace(" ", "\\ ")
            return text


        cmd = f"adb -s {device_id} shell app_process -Djava.class.path=/data/local/tmp/yadb /data/local/tmp com.ysbing.yadb.Main -keyboard '{preprocess_text_for_adb(value)}'"
        if print_command:
            print(f"Executing command: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result
    
    elif action_type == "SCROLL":
        assert "point" in frontend_action, "Missing point in SCROLL action"
        assert "direction" in frontend_action, "Missing direction in SCROLL action"
        x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)

        deltax = int(0.3 * wm_size[0])
        deltay = int(0.3 * wm_size[1])

        direction = frontend_action["direction"]
        if direction == "down":
            x1, y1 = x, y
            x2, y2 = x, y - deltay
        elif direction == "up":
            x1, y1 = x, y
            x2, y2 = x, y + deltay
        elif direction == "left":
            x1, y1 = x, y
            x2, y2 = x - deltax, y
        elif direction == "right":
            x1, y1 = x, y
            x2, y2 = x + deltax, y
        else:
            raise ValueError(f"Invalid direction: {direction}")
        
        cmd = f"adb -s {device_id} shell input swipe {x1} {y1} {x2} {y2} 1200"
        if print_command:
            print(f"Executing command: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result
        
    elif action_type == "AWAKE":
        assert "value" in frontend_action, "Missing value in AWAKE action"
        app_name = frontend_action["value"]
        package_name = find_package_name(app_name)
        if package_name is None:
            raise ValueError(f"App name {app_name} not found in package map.")
        
        if reflush_app:
            cmd = f"adb -s {device_id} shell am force-stop {package_name}"
            if print_command:
                print(f"Executing command: {cmd}")

            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            time.sleep(1)

        cmd = f"adb -s {device_id} shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
        if print_command:
            print(f"Executing command: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result

    elif action_type == "SLIDE":
        assert "point1" in frontend_action, "Missing point1 in SLIDE action"
        assert "point2" in frontend_action, "Missing point2 in SLIDE action"
        x1, y1 = _convert_point_to_realworld_point(frontend_action["point1"], wm_size)
        x2, y2 = _convert_point_to_realworld_point(frontend_action["point2"], wm_size)
        
        duration = frontend_action.get("duration", 1.5)
        cmd = f"adb -s {device_id} shell input swipe {x1} {y1} {x2} {y2} {int(duration * 1000)}"
        if print_command:
            print(f"Executing command: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result
    
    elif action_type == "BACK":
        cmd = f"adb -s {device_id} shell input keyevent 4"
        if print_command:
            print(f"Executing command: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result
    
    elif action_type == "HOME":
        cmd = f"adb -s {device_id} shell input keyevent 3"
        if print_command:
            print(f"Executing command: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result
    
    elif action_type == "COMPLETE":
        if print_command:
            print("Task completed.")
        return None

    elif action_type == "ABORT":
        if print_command:
            print("Task aborted.")
        return None

    elif action_type == "INFO":
        if print_command:
            print("Info action executed.")
        return None

    elif action_type == "WAIT":
        assert "seconds" in frontend_action, "Missing seconds in WAIT action"
        seconds = frontend_action["seconds"]
        if print_command:
            print(f"Waiting for {seconds} seconds.")
        time.sleep(seconds)
        return None
    
    elif action_type == "HOT_KEY":
        assert "key" in frontend_action, "Missing key in HOT_KEY action"
        key = frontend_action["key"]
        key_event_map = {
            "volume_up": 24,
            "volume_down": 25,
            "power": 26,
            "home": 3,
            "back": 4,
            "menu": 82,
        }
        if key.lower() not in key_event_map:
            raise ValueError(f"Unsupported hot key: {key}")

        key_event = key_event_map[key.lower()]
        cmd = f"adb -s {device_id} shell input keyevent {key_event}"
        if print_command:
            print(f"Executing command: {cmd}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result

    else:
        raise ValueError(f"Unsupported action type: {action_type}")    
    
        


# ============================================================
# scrcpy-py-ddlx 动作执行（替代 ADB 实现）
# ============================================================

# 全局配置：使用 scrcpy 还是 ADB
USE_SCRCPY_FOR_ACTIONS = True  # 设为 False 可回退到 ADB


def act_on_device_scrcpy(frontend_action, device_id, wm_size, print_command=False, reflush_app=True, show_window=False):
    """
    使用 scrcpy-py-ddlx 执行设备动作（性能提升 5-10 倍）

    支持的动作类型：
    - CLICK: 点击
    - LONGPRESS: 长按
    - TYPE: 文本输入（原生 UTF-8，无需 yadb）
    - SLIDE: 滑动
    - SCROLL: 滚动
    - AWAKE: 应用启动（scrcpy-py-ddlx 原生实现）
    - BACK: 返回键
    - HOME: 主屏幕键
    - HOT_KEY: 热键（音量、电源等）
    - WAIT/COMPLETE/ABORT/INFO: 客户端逻辑

    Args:
        frontend_action: 动作字典
        device_id: 设备序列号
        wm_size: 设备屏幕尺寸 (width, height)
        print_command: 是否打印命令（兼容参数）
        reflush_app: 是否刷新应用（兼容参数）

    Returns:
        执行结果
    """
    from .scrcpy_connection_manager import get_scrcpy_manager

    valid_actions = ["CLICK", "LONGPRESS", "TYPE", "SCROLL", "AWAKE", "SLIDE",
                     "BACK", "HOME", "COMPLETE", "ABORT", "INFO", "WAIT", "HOT_KEY"]

    assert "action_type" in frontend_action, "Missing action_type in frontend_action"
    assert frontend_action["action_type"] in valid_actions, f"Invalid action type: {frontend_action['action_type']}"

    action_type = frontend_action["action_type"]
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=show_window)

    if client is None:
        raise RuntimeError(f"无法连接到设备 {device_id}")

    # 客户端逻辑动作，无需设备操作
    if action_type == "COMPLETE":
        logger.info("Task completed")
        return None
    elif action_type == "ABORT":
        logger.info("Task aborted")
        return None
    elif action_type == "INFO":
        value = frontend_action.get("value", "")
        logger.info(f"Info action: {value}")
        return None
    elif action_type == "WAIT":
        seconds = frontend_action.get("seconds", frontend_action.get("value", 0))
        time.sleep(float(seconds))
        return None

    # 使用 scrcpy-py-ddlx 执行设备动作
    if action_type == "CLICK":
        assert "point" in frontend_action, "Missing point in CLICK action"
        x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)
        client.tap(x, y)
        logger.debug(f"CLICK: ({x}, {y})")
        return None

    elif action_type == "LONGPRESS":
        assert "point" in frontend_action, "Missing point in LONGPRESS action"
        assert "duration" in frontend_action, "Missing duration in LONGPRESS action"
        x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)
        duration = frontend_action["duration"]
        client.long_press(x, y, int(duration * 1000))
        logger.debug(f"LONGPRESS: ({x}, {y}), {duration}s")
        return None

    elif action_type == "TYPE":
        assert "value" in frontend_action, "Missing value in TYPE action"
        value = frontend_action["value"]
        keyboard_exists = frontend_action.get("keyboard_exists", True)
        
        # 如果键盘不存在且有点坐标，先点击
        if not keyboard_exists and "point" in frontend_action:
            x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)
            client.tap(x, y)
            time.sleep(1)
        
        # scrcpy-py-ddlx 原生 UTF-8 支持，无需 yadb
        client.inject_text(value)
        logger.debug(f"TYPE: {value[:50]}...")
        return None

    elif action_type == "SLIDE":
        assert "point1" in frontend_action, "Missing point1 in SLIDE action"
        assert "point2" in frontend_action, "Missing point2 in SLIDE action"
        x1, y1 = _convert_point_to_realworld_point(frontend_action["point1"], wm_size)
        x2, y2 = _convert_point_to_realworld_point(frontend_action["point2"], wm_size)
        duration = frontend_action.get("duration", 1.5)
        client.swipe(x1, y1, x2, y2, int(duration * 1000))
        logger.debug(f"SLIDE: ({x1},{y1}) -> ({x2},{y2}), {duration}s")
        return None

    elif action_type == "SCROLL":
        assert "point" in frontend_action, "Missing point in SCROLL action"
        assert "direction" in frontend_action, "Missing direction in SCROLL action"
        x, y = _convert_point_to_realworld_point(frontend_action["point"], wm_size)
        
        deltax = int(0.3 * wm_size[0])
        deltay = int(0.3 * wm_size[1])
        
        direction = frontend_action["direction"]
        if direction == "down":
            x1, y1 = x, y
            x2, y2 = x, y - deltay
        elif direction == "up":
            x1, y1 = x, y
            x2, y2 = x, y + deltay
        elif direction == "left":
            x1, y1 = x, y
            x2, y2 = x - deltax, y
        elif direction == "right":
            x1, y1 = x, y
            x2, y2 = x + deltax, y
        else:
            raise ValueError(f"Invalid direction: {direction}")
        
        client.swipe(x1, y1, x2, y2, 1200)
        logger.debug(f"SCROLL: {direction}")
        return None

    elif action_type == "AWAKE":
        assert "value" in frontend_action, "Missing value in AWAKE action"
        app_name = frontend_action["value"]
        
        # scrcpy-py-ddlx 原生应用启动，无需 ADB monkey
        try:
            client.start_app(f"?{app_name}")
            logger.info(f"启动应用: {app_name} (模糊搜索)")
        except Exception:
            # 回退到精确包名
            from copilot_front_end.package_map import find_package_name
            package_name = find_package_name(app_name)
            if package_name is None:
                raise ValueError(f"应用 {app_name} 未找到")
            client.start_app(package_name)
            logger.info(f"启动应用: {app_name} (包名: {package_name})")
        
        time.sleep(1)
        return None

    elif action_type == "BACK":
        client.back()
        logger.debug("BACK key")
        return None

    elif action_type == "HOME":
        client.home()
        logger.debug("HOME key")
        return None

    elif action_type == "HOT_KEY":
        assert "key" in frontend_action, "Missing key in HOT_KEY action"
        key = frontend_action["key"].lower()
        
        key_actions = {
            "volume_up": client.volume_up,
            "volume_down": client.volume_down,
            "power": lambda: client.inject_keycode(26),  # POWER key
            "home": client.home,
            "back": client.back,
            "menu": client.menu,
        }
        
        if key not in key_actions:
            raise ValueError(f"Unsupported hot key: {key}")
        
        key_actions[key]()
        logger.debug(f"HOT_KEY: {key}")
        return None

    raise ValueError(f"Unsupported action type: {action_type}")


def act_on_device_auto(frontend_action, device_id, wm_size, print_command=False, reflush_app=True):
    """
    自动选择动作执行方式（优先 scrcpy-py-ddlx，失败回退 ADB）

    Args:
        frontend_action: 动作字典
        device_id: 设备序列号
        wm_size: 设备屏幕尺寸
        print_command: 是否打印命令
        reflush_app: 是否刷新应用

    Returns:
        执行结果
    """
    if USE_SCRCPY_FOR_ACTIONS:
        try:
            return act_on_device_scrcpy(frontend_action, device_id, wm_size, print_command, reflush_app, show_window)
        except Exception as e:
            logger.warning(f"scrcpy 执行动作失败，回退到 ADB: {e}")
    
    # 回退到 ADB
    return act_on_device(frontend_action, device_id, wm_size, print_command, reflush_app)
