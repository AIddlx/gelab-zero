import sys
import os
import subprocess
import logging

from uuid import uuid4

if "." not in sys.path:
    sys.path.append(".")
# 添加 scrcpy-py-ddlx 路径
# 支持两种目录结构：
# 1. scrcpy-py-ddlx 与 gelab-zero 平级（GitHub 独立仓库）
# 2. scrcpy-py-ddlx 在 gelab-zero 内部（开发环境）
_current_file = os.path.abspath(__file__)
_gelab_root = os.path.dirname(os.path.dirname(_current_file))

# 尝试平级目录（GitHub 独立仓库模式）
_scrcpy_path = os.path.join(os.path.dirname(_gelab_root), 'scrcpy-py-ddlx')

# 如果平级目录不存在，尝试内部目录（开发环境）
if not os.path.exists(_scrcpy_path):
    _scrcpy_path = os.path.join(_gelab_root, 'scrcpy-py-ddlx')

# 如果找到路径且不在 sys.path 中，则添加
if os.path.exists(_scrcpy_path) and os.path.basename(_scrcpy_path) not in sys.path:
    sys.path.insert(0, _scrcpy_path)
from copilot_front_end.package_map import find_package_name

import time
from tqdm import tqdm

from megfile import smart_copy

logger = logging.getLogger(__name__)

def _get_adb_command(device_id=None):
    """
    Get the ADB command for the specified device ID.
    """
    if device_id is None:
        adb_command = "adb "
    else:
        assert device_id in list_devices(), f"Device {device_id} not found in connected devices."
        adb_command = f"adb -s {device_id} "
    return adb_command

def get_adb_command(device_id=None):
    """
    Get the ADB command for the specified device ID.
    """
    adb_command = _get_adb_command(device_id)
    return adb_command

def local_str_grep(input_str, pattern):
    """
    A simple local grep function that searches for a pattern in a string.
    :param input_str: The input string to search within.
    :param
    pattern: The pattern to search for.
    :return: True if the pattern is found, False otherwise.
    """
    return_lines = []
    for line in input_str.splitlines():
        if pattern in line:
            return_lines.append(line)
    
    return "\n".join(return_lines) if return_lines else None


def close_app_on_device(device_id, app_name, print_command = False):
    """
    Close the specified app on the device.
    """
    adb_command = _get_adb_command(device_id)
    
    package_name = find_package_name(app_name)
    if package_name is None:
        raise ValueError(f"App {app_name} not found in package map.")
    
    command = f"{adb_command} shell am force-stop {package_name}"
    if print_command:
        print(f"Executing command: {command}")
    
    subprocess.run(command, shell=True, capture_output=True, text=True)

def press_home_key(device_id, print_command=False, show_window=False):
    """
    Press the home key on the device (using scrcpy-py-ddlx).
    """
    from .scrcpy_connection_manager import get_scrcpy_manager
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=show_window)
    if client:
        client.home()

def init_device(device_id, print_command = False):
    """
    Initialize the device by checking if yadb is installed.
    """
    adb_command = _get_adb_command(device_id)
    
    # adb -s DEVICE_ID shell ls /data/local/tmp 
    # except yadb 
    command = f"{adb_command} shell md5sum /data/local/tmp/yadb"
    if print_command:
        print(f"Executing command: {command}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if "29a0cd3b3adea92350dd5a25594593df" not in result.stdout:
        # to push yadb into the device
        command = f"{adb_command} push yadb /data/local/tmp"
        logger.info(f"YADB not installed, installing on device {device_id}...")

        if print_command:
            print(f"Executing command: {command}")

        subprocess.run(command, shell=True, capture_output=True, text=True)
    else:
        logger.debug(f"YADB already installed on device {device_id}")

    # press_home_key(device_id, print_command=print_command)

def init_all_devices():
    """
    Initialize all devices by listing them and setting up the environment.
    """
    devices = list_devices()
    for device_id in tqdm(devices):
        init_device(device_id)
        logger.debug(f"Initialized device: {device_id}")

def dectect_screen_on(device_id, print_command = False):
    """
    Detect whether the screen is on for the specified device.
    """
    adb_command = _get_adb_command(device_id)
    
    # adb shell dumpsys display | grep mScreenState

    #duplicate the command, support win platform
    # command = f"{adb_command} shell dumpsys display | grep mScreenState"
    # if print_command:
    #     print(f"Executing command: {command}")
    
    # result = subprocess.run(command, shell=True, capture_output=True, text=True)
    # screen_state = result.stdout.strip()


    if sys.platform == "win32":
        # On Windows, we need to decode the output
        command = f"{adb_command} shell dumpsys display"
        if print_command:
            print(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        result.stdout = result.stdout.encode('utf-8').decode('utf-8')
        screen_state = local_str_grep(result.stdout, "mScreenState").strip()
    else:
        command = f"{adb_command} shell dumpsys display | grep mScreenState"
        if print_command:
            print(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        screen_state = result.stdout.strip()
    
    if "ON" in screen_state:
        return True
    else:
        return False

def press_power_key(device_id, print_command=False, show_window=False):
    """
    Press the power key on the specified device (using scrcpy-py-ddlx).
    Toggles screen on/off.
    """
    from .scrcpy_connection_manager import get_scrcpy_manager
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=show_window)
    if client:
        # 切换电源状态（开/关）
        client.set_display_power(False)  # 先关
        time.sleep(0.1)
        client.set_display_power(True)   # 再开

def swipe_up_to_unlock(device_id, wm_size=(1000,2000), print_command=False, show_window=False):
    """
    Swipe up on the specified device to unlock the screen (using scrcpy-py-ddlx).
    """
    from .scrcpy_connection_manager import get_scrcpy_manager
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=show_window)
    if client:
        x = wm_size[0] // 2
        y_start = int(wm_size[1] * 0.9)
        y_end = int(wm_size[1] * 0.2)
        client.swipe(x, y_start, x, y_end, 300)

def get_manufacturer(device_id):
    """
    Get the manufacturer of the specified device.
    """
    adb_command = _get_adb_command(device_id)
    command = f"{adb_command} shell getprop ro.product.manufacturer"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    manufacturer = result.stdout.strip().lower()
    return manufacturer

def _open_screen(device_id, print_command=False, show_window=False):
    """
    Open the screen of the specified device (using scrcpy-py-ddlx).
    """
    is_screen_on = dectect_screen_on(device_id, print_command=print_command)
    if is_screen_on:
        if print_command:
            print(f"Screen is already on for device {device_id}.")
        return

    from .scrcpy_connection_manager import get_scrcpy_manager
    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=show_window)
    if client:
        # 打开屏幕
        client.turn_screen_on()
        time.sleep(0.2)
        manufacturer = get_manufacturer(device_id)
        if "vivo" in manufacturer:
            # vivo 设备需要上滑解锁
            size = get_device_wm_size(device_id)
            x = size[0] // 2
            y_start = int(size[1] * 0.9)
            y_end = int(size[1] * 0.2)
            client.swipe(x, y_start, x, y_end, 300)
            time.sleep(0.2)

        

def open_screen(device_id, print_command=False, show_window=False):
    """
    Open the screen of the specified device.
    """
    _open_screen(device_id, print_command=print_command, show_window=show_window)


def list_devices():
    """
    List all connected mobile devices (using scrcpy-py-ddlx).
    """
    from scrcpy_py_ddlx.core.adb import ADBManager
    adb = ADBManager()
    devices = adb.list_devices()
    return [d.serial for d in devices]

def capture_screenshot(device_id, tmp_file_dir="tmp_screenshot", image_name=None, print_command=False, show_window=False):
    """
    Capture a screenshot of the specified device and save it to the specified directory (using scrcpy-py-ddlx).
    """
    from .scrcpy_connection_manager import get_scrcpy_manager
    import time
    import numpy as np
    from PIL import Image

    # 确保使用绝对路径
    tmp_file_dir = os.path.abspath(tmp_file_dir)
    if not os.path.exists(tmp_file_dir):
        os.makedirs(tmp_file_dir)

    if image_name is None:
        image_name = f"uuid_{uuid4()}.png"

    screen_shot_pic_path = os.path.join(tmp_file_dir, image_name)

    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=show_window)
    if client is None:
        raise RuntimeError(f"无法连接到设备 {device_id}")

    # 非懒加载模式：需要等待视频流稳定
    time.sleep(1.0)

    # 使用 scrcpy-py-ddlx 截图
    # 不使用 filename 参数（异步保存），而是获取 numpy 数组手动保存
    max_retries = 10
    for attempt in range(max_retries):
        frame = client.screenshot()  # 返回 numpy 数组或 None
        if frame is not None:
            # 手动保存为 PNG（同步）
            img = Image.fromarray(frame)
            img.save(screen_shot_pic_path)
            if os.path.exists(screen_shot_pic_path):
                return screen_shot_pic_path

        if attempt < max_retries - 1:
            time.sleep(0.5)

    raise RuntimeError(f"截图失败: 设备 {device_id}")    

def get_device_wm_size(device_id, show_window=True):
    """
    Get the screen size of the specified device (using scrcpy-py-ddlx).

    Args:
        device_id: Device ID
        show_window: Whether to show real-time preview window (default: True)
    """
    from .scrcpy_connection_manager import get_scrcpy_manager
    manager = get_scrcpy_manager()
    size = manager.get_device_size(device_id, show_window=show_window)
    if size is None:
        raise RuntimeError(f"无法获取设备 {device_id} 的屏幕尺寸")
    return size

# convert model action from api to a front-end action
def model_act2front_act(act, wm_size):
    """
    Convert model action to front-end action.
    """
    # to parse the action and convert it to front-end action
    model_action_type_list = ['CLICK', "TYPE", "COMPLETE", "WAIT", "AWAKE", "INFO", "ABORT", "SWIPE", "LONGPRESS"]

    action_type_map = {
        "CLICK": "Click",
        "TYPE": "Type",
        "COMPLETE": "Complete",
        "INFO": "Pop",
        "WAIT": "Wait",
        "AWAKE": "Awake",
        "ABORT": "Abort",
        "SWIPE": "Scroll",
        "LONGPRESS": "LongPress",
    }

    if "action" in act:
        act['action_type'] = act['action']

    assert act['action_type'] in model_action_type_list, f"Invalid action type: {act['action_type']}"

    # action unrelated parameters
    status = act.get('status', None)
    payload_dict = act.get('payload', {})
    plan, summary = payload_dict.get('plan', None), payload_dict.get('summary', None)

    explain = act['explain']


    down_stream_action = {
        "action_type": action_type_map[act['action_type']],
        "args": {
            "status": status,
            "plan": plan,
            "summary": summary,

            "explain": explain,
        }
    }

    if act['action_type'] == 'CLICK':
        # <STATUS>xxx<ACTION>explain:xxx\taction:CLICK\tpoint:x,y\tsearch_type:app|keyboard|none<PAYLOAD>plan:xxx\tsummary:xxx\t
        assert "point" in act, f"Point not found in CLICK action: {act}"

        search_type = act.get('search_type', "none")

        point = act['point']

        zero_one_point = ((float(point[0])) / 1000, (float(point[1])) / 1000)
        real_coordinate = (int(zero_one_point[0] * wm_size[0]), int(zero_one_point[1] * wm_size[1]))

        # click point for several versions
        down_stream_action['args']['coordinate'] = real_coordinate + real_coordinate
        down_stream_action['args']['point'] = real_coordinate
        down_stream_action['args']['normalized_point'] = zero_one_point

        down_stream_action['args']['search_type'] = search_type

    elif act['action_type'] == 'TYPE':
        # <STATUS>xxx<ACTION>explain:xxx\taction:TYPE\tvalue:xxxx\tpoint:x,y\tkeyboard:true|alse<PAYLOAD>plan:xxx\tsummary:xxx\t
        assert "value" in act, f"Value not found in TYPE action: {act}"

        value = act['value'].replace(" ", "_")
        # point = act['point']
        # point can be optional
        point = act.get('point', None)

        # to set the keyboard exists default to True, for point is None
        keyboard_exists = act.get('keyboard', True)

        if point is not None:        
            zero_one_point = ((float(point[0])) / 1000, (float(point[1])) / 1000)
            real_coordinate = (int(zero_one_point[0] * wm_size[0]), int(zero_one_point[1] * wm_size[1]))
        else:
            zero_one_point = None
            real_coordinate = [None]

        # click point for several versions
        down_stream_action['args']['coordinate'] = real_coordinate + real_coordinate
        down_stream_action['args']['point'] = real_coordinate
        down_stream_action['args']['normalized_point'] = zero_one_point

        down_stream_action['args']['text'] = value

        down_stream_action['args']['keyboard_exists'] = keyboard_exists

    elif act['action_type'] == "INFO": 
        # <STATUS>xxx<ACTION>explain:xxx\taction:INFO\tvalue:xxxx\t<PAYLOAD>plan:xxx\tsummary:xxx\t
        assert "value" in act, f"Value not found in INFO action: {act}"

        value = act['value']
        down_stream_action['args']['text'] = value


    elif act['action_type'] == "WAIT":
        #<STATUS>xxx<ACTION>explain:xxx\taction:WAIT\tvalue:5\tis_auto_close:true|false\tr1:xxx\tp1:x1,y1\tr2:xxx\tp2:x2,y2\t<PAYLOAD>plan:xxx\tsummary:xxx\t

        assert "value" in act, f"Value not found in WAIT action: {act}"
        value = act['value']
        is_auto_close = act.get('is_auto_close', False)

        clickable_regions = []
        close_reasons = act.get('close_reasons', [])
        for click_area in close_reasons:

            point, reason = click_area['point'], click_area['reason']
            bbox = click_area.get('bbox', None)

            zero_one_point = ((float(point[0])) / 1000, (float(point[1])) / 1000)
            real_coordinate = (int(zero_one_point[0] * wm_size[0]), int(zero_one_point[1] * wm_size[1]))
            
            if bbox is not None:
                zero_one_bbox = ((float(bbox[0])) / 1000, (float(bbox[1])) / 1000, 
                                 (float(bbox[2])) / 1000, (float(bbox[3])) / 1000)
                real_bbox = (int(zero_one_bbox[0] * wm_size[0]), int(zero_one_bbox[1] * wm_size[1]),
                              int(zero_one_bbox[2] * wm_size[0]), int(zero_one_bbox[3] * wm_size[1]))
                
            else:
                zero_one_bbox = (zero_one_point[0], zero_one_point[1], zero_one_point[0], zero_one_point[1])
                real_bbox = (real_coordinate[0], real_coordinate[1], real_coordinate[0], real_coordinate[1])
            
                
            clickable_regions.append({
                "reason": reason,

                "point": real_coordinate,
                "region": real_bbox,

                "normalized_point": zero_one_point,
                "normalized_region": zero_one_bbox,
            })

        # for reason, point in act['']

        down_stream_action['args']['duration'] = value
        down_stream_action['args']['closability'] = {
            "auto_closable": is_auto_close,
            "type": explain,
            "regions": clickable_regions,
        }

    elif act['action_type'] == "AWAKE":
        # <STATUS>xxx<ACTION>explain:xxx\taction:AWAKE\tvalue:xxxx\t<PAYLOAD>plan:xxx\tsummary:xxx\t
        assert "value" in act, f"Value not found in AWAKE action: {act}"

        value = act['value']
        down_stream_action['args']['text'] = value

    elif act['action_type'] == "ABORT":
        # <STATUS>xxx<ACTION>explain:xxx\taction:ABORT\t<PAYLOAD>plan:xxx\tsummary:xxx\t

        down_stream_action['args']['abort_reason'] = explain
    
    elif act['action_type'] == "COMPLETE":
        # <STATUS>xxx<ACTION>explain:xxx\taction:COMPLETE\t<PAYLOAD>plan:xxx\tsummary:xxx\t

        # nothing to add
        pass

    elif act['action_type'] == "SWIPE":
        # <STATUS>xxx<ACTION>explain:xxx\taction:SWIPE\tpoint1:x,y\tpoint2:x,y\t<PAYLOAD>plan:xxx\tsummary:xxx\t  

        point1 = act['point1']
        zero_one_point1 = ((float(point1[0])) / 1000, (float(point1[1])) / 1000)
        real_coordinate1 = (int(zero_one_point1[0] * wm_size[0]), int(zero_one_point1[1] * wm_size[1]))

        point2 = act['point2']
        zero_one_point2 = ((float(point2[0])) / 1000, (float(point2[1])) / 1000)
        real_coordinate2 = (int(zero_one_point2[0] * wm_size[0]), int(zero_one_point2[1] * wm_size[1]))

        path = [(real_coordinate1[0], real_coordinate1[1]), (real_coordinate2[0], real_coordinate2[1])]
        normalized_path = [(zero_one_point1[0], zero_one_point1[1]), (zero_one_point2[0], zero_one_point2[1])]

        down_stream_action['args']['path'] = path
        down_stream_action['args']['normalized_path'] = normalized_path

    elif act['action_type'] == "LONGPRESS":
        # <STATUS>xxx<ACTION>explain:xxx\taction:LONGPRESS\tpoint:x,y\t<PAYLOAD>plan:xxx\tsummary:xxx\t

        point = act['point']
        zero_one_point = ((float(point[0])) / 1000, (float(point[1])) / 1000)
        real_coordinate = (int(zero_one_point[0] * wm_size[0]), int(zero_one_point[1] * wm_size[1]))

        # click point for several versions
        down_stream_action['args']['coordinate'] = real_coordinate + real_coordinate
        down_stream_action['args']['point'] = real_coordinate
        down_stream_action['args']['normalized_point'] = zero_one_point

    else:
        raise ValueError(f"Invalid action type: {act['action_type']}")
    
    return down_stream_action

def normlize_point(point, wm_size):
    """
    Normalize a point based on the window manager size.
    """
    real_world_point = ((float(point[0])) / wm_size[0], (float(point[1])) / wm_size[1])
    return real_world_point


def act_on_device(device_id, action, print_command=False, refush_app=True, device_wm_size=None):
    """
    Perform an action on a specific device (using scrcpy-py-ddlx).
    """
    from .scrcpy_connection_manager import get_scrcpy_manager

    manager = get_scrcpy_manager()
    client = manager.get_client(device_id, show_window=show_window)
    if client is None:
        raise RuntimeError(f"无法连接到设备 {device_id}")

    action_type = action['action_type']

    if action_type == "Click":
        if device_wm_size is None:
            real_point = action['args']['point']
        else:
            normalized_point = action['args']['normalized_point']
            real_point = (int(normalized_point[0] * device_wm_size[0]), int(normalized_point[1] * device_wm_size[1]))
        client.tap(real_point[0], real_point[1])

    elif action_type == "Awake":
        app_name = action['args']['text']
        package_name = find_package_name(app_name)
        if package_name is None:
            raise ValueError(f"App {app_name} not found in package map.")

        # scrcpy-py-ddlx 启动应用
        client.start_app(package_name)
        time.sleep(2)

    elif action_type == "Type":
        text = action['args']['text']

        # 如果需要点击输入框
        if "keyboard_exists" in action['args'] and not action['args']['keyboard_exists']:
            if device_wm_size is None:
                point = action['args']['point']
            else:
                normalized_point = action['args']['normalized_point']
                point = (int(normalized_point[0] * device_wm_size[0]), int(normalized_point[1] * device_wm_size[1]))
            client.tap(point[0], point[1])
            time.sleep(0.3)

        # scrcpy-py-ddlx 输入文本（支持中文）
        client.inject_text(text)

    elif action_type == "Pop":
        client.back()

    elif action_type == "Wait":
        wait_time = action['args']['duration']
        time.sleep(float(wait_time))
        return

    elif action_type == "Scroll":
        path = action['args']['path']
        if device_wm_size is not None:
            normalized_path = action['args']['normalized_path']
            path = [(int(normalized_path[0][0] * device_wm_size[0]), int(normalized_path[0][1] * device_wm_size[1])),
                    (int(normalized_path[1][0] * device_wm_size[0]), int(normalized_path[1][1] * device_wm_size[1]))]
        client.swipe(path[0][0], path[0][1], path[1][0], path[1][1], 1000)

    elif action_type == "LongPress":
        if device_wm_size is None:
            point = action['args']['point']
        else:
            normalized_point = action['args']['normalized_point']
            point = (int(normalized_point[0] * device_wm_size[0]), int(normalized_point[1] * device_wm_size[1]))
        client.long_press(point[0], point[1], 2000)

    elif action_type == "Abort":
        pass

    elif action_type == "Complete":
        pass

    else:
        raise ValueError(f"Invalid action type: {action_type}")


def default_reply_method(task, envs, actions, question):
    """
    Default reply method for the evaluation.
    :param task: The task to evaluate.
    :param envs: The environments to evaluate the task on.
    :param actions: The actions taken during the evaluation.
    :param question: The question to ask the model.
    :return: The model's reply.
    """
    

    return "Choose the second one."

class BaseMoboleActionHelper:
    def __init__(self, device_id = None):
        self.device_id = device_id
        self.wm_size = get_device_wm_size(self.device_id)
        if self.device_id is not None:
            init_device(self.device_id, print_command=True)
            # _open_screen(self.device_id, print_command=True)

        pass

    def set_device_id(self, device_id):
        """
        Set the device ID for the mobile action helper.
        """
        self.device_id = device_id
        self.wm_size = get_device_wm_size(self.device_id)
    
    def get_device_id(self):
        """
        Get the device ID for the mobile action helper.
        """
        return self.device_id
    
    def step_interaction(self, action, capture_duration = 0.5, image_full_path = None, user_comment = None):
        """
        Perform a step interaction on the device, and get the observation.
        """

        # to make sure the screen is on
        _open_screen(self.device_id)
        
        user_comment = ""
        if action is not None and action['action_type'] not in ['INFO', 'COMPLETE', 'ABORT']:
            # to convert vthe action to front-end action
            front_end_action = model_act2front_act(action, self.wm_size)

            # to perform the action
            act_on_device(self.device_id, front_end_action) 

        elif action is not None and action['action_type'] == "INFO":
            # to convert the action to front-end action
            front_end_action = model_act2front_act(action, self.wm_size)

            value = front_end_action['args']['text']
            
            # to ask the user to input the value
            if user_comment is None:
                user_comment = input(f"Please answer the model's question: {value}: ")

        
        elif action is not None and action['action_type'] in ["COMPLETE", "ABORT"]:
            
            return None

        # to wait for the action to be completed
        time.sleep(capture_duration)

        is_screenshot = False

        # to get the observation
        for i in range(3):
            try:
                screen_shot_pic_path = capture_screenshot(self.device_id, tmp_file_dir="tmp_screenshot")
                is_screenshot = True
                break
            except Exception as e:
                logger.warning(f"Screenshot attempt {i+1}/3 failed: {e}")
                time.sleep(0.5)


        if not is_screenshot:
            raise ValueError(f"Error capturing screenshot: {e}")
        # to check if the screenshot is valid

        if image_full_path is not None:
            # to copy the image to the full path
            smart_copy(screen_shot_pic_path, image_full_path)
            screen_shot_pic_path = image_full_path
            

        observation = {
            "image": screen_shot_pic_path,
            "user_comment": user_comment,
        }

        return observation
        





    


# ============================================================
# 模块导出
# ============================================================

__all__ = [
    # 设备管理
    "list_devices",
    "get_device_wm_size",
    "get_manufacturer",
    # 屏幕控制
    "open_screen",
    "dectect_screen_on",
    # 动作执行
    "act_on_device",
    "press_home_key",
    "press_power_key",
    "swipe_up_to_unlock",
    # 应用管理
    "close_app_on_device",
    # 截图
    "capture_screenshot",
    # 辅助函数
    "model_act2front_act",
    "normlize_point",
    # 类
    "BaseMoboleActionHelper",
]


if __name__ == "__main__":
    pass