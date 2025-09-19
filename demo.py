import queue
import threading
import time
import inspect
from typing import Dict, Callable, Any
from dataclasses import dataclass
from enum import Enum, auto
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QTextBrowser)  # 新增GUI组件

# ------------------------------
# 1. 原依赖类（保持不变）
# ------------------------------
@dataclass
class PubSubMessage:
    sender: str  # 消息发送者（如"ui", "task"）
    data: dict   # 消息内容（业务数据）
    timestamp: float = 0.0  # 可选时间戳


class CommunicationTopic(Enum):
    UNKNOWN = auto()
    FROM_TASK = auto()       # 来自任务的消息
    FROM_UI = auto()         # 来自UI的消息
    SELECTED_TASK_START = auto()
    SELECTED_TASK_STOP = auto()
    AUTO_TASK_START = auto()
    ADVANCE_AUTO_TASK_START = auto()
    RESIZE_WINDOW = auto()
    CLOSE_WINDOW = auto()
    AUTO_LOGIN = auto()
    TASK_PROCESS_UPDATE = auto()
    WINDOW_STATUS = auto()


class PubSubWithQueue:
    def __init__(self):
        self.sub_list: Dict[CommunicationTopic, Dict[str, queue.Queue]] = {}

    def subscribe(self, name: str, topic: CommunicationTopic = CommunicationTopic.UNKNOWN) -> queue.Queue:
        if not name or topic == CommunicationTopic.UNKNOWN:
            return None
        if topic not in self.sub_list:
            self.sub_list[topic] = {}
        if name in self.sub_list[topic]:
            self.unsubscribe(name, topic)
        q = queue.Queue()
        self.sub_list[topic][name] = q
        return q

    def unsubscribe(self, name: str, topic: CommunicationTopic = CommunicationTopic.UNKNOWN):
        if topic in self.sub_list and name in self.sub_list[topic]:
            self.sub_list[topic][name].put(None)
            del self.sub_list[topic][name]
            if not self.sub_list[topic]:
                del self.sub_list[topic]

    def publish(self, topic: CommunicationTopic = CommunicationTopic.UNKNOWN, message: PubSubMessage = None):
        if topic in self.sub_list and message:
            for q in list(self.sub_list[topic].values()):
                q.put(message)


# 增强日志：同时输出到终端和GUI文本框
class GUILogger:
    _instance = None
    _text_browser = None  # 用于显示日志的GUI组件

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_text_browser(cls, text_browser: QTextBrowser):
        """关联GUI文本框，用于显示日志"""
        cls._text_browser = text_browser

    @staticmethod
    def _log(msg: str, level: str):
        """统一日志处理：终端+GUI"""
        log_msg = f"[{level}] {time.strftime('%H:%M:%S')} - {msg}"
        print(log_msg)  # 输出到终端
        if GUILogger._text_browser:
            # GUI中显示（线程安全，避免Qt报错）
            GUILogger._text_browser.append(log_msg)
            GUILogger._text_browser.verticalScrollBar().setValue(
                GUILogger._text_browser.verticalScrollBar().maximum()
            )

    @staticmethod
    def info(msg: str):
        GUILogger._log(msg, "INFO")

    @staticmethod
    def warning(msg: str):
        GUILogger._log(msg, "WARNING")

    @staticmethod
    def error(msg: str):
        GUILogger._log(msg, "ERROR")

# 全局日志实例（替换原MockLogger）
logger = GUILogger()


class WindowManager:
    def __init__(self):
        pass

    def cleanup(self):
        pass


class TaskManager:
    def __init__(self):
        pass

    def cleanup(self):
        pass


def singleton(cls):
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return wrapper


# ------------------------------
# 2. 原EventManager类（保持不变）
# ------------------------------
@singleton
class EventManager(QObject):
    def __init__(self):
        super().__init__()
        self.pubsub = PubSubWithQueue()
        self._window_manager = WindowManager()
        self._task_manager = TaskManager()

        self._ui_msg_handlers = {
            "start_selected_task": self.on_start_selected_task,
            "stop_selected_task": self.on_stop_selected_task,
            "start_auto_task": self.on_start_auto_task,
            "start_advanced_auto_task": self.on_start_advanced_auto_task,
            "resize_windows": self.on_resize_windows,
            "close_windows": self.on_close_windows,
            "auto_login": self.on_auto_login
        }

        self._task_msg_handlers = {
            "task_started": self.on_task_started,
            "task_finished": self.on_task_finished,
            "task_process": self.on_task_process,
            "window_status": self.on_window_status
        }

        self._topic_handlers: Dict[CommunicationTopic, Callable] = self.register_topic_handlers()
        self.subscribe_to_topics()

        self._is_running = True
        self._processing_thread = threading.Thread(
            target=self.process_messages,
            daemon=True,
            name="EventManagerProcessor"
        )
        self._processing_thread.start()

    def register_topic_handlers(self) -> Dict[CommunicationTopic, Callable]:
        return {
            CommunicationTopic.FROM_TASK: self.handle_task_messages,
            CommunicationTopic.FROM_UI: self.handle_ui_messages,
        }

    def subscribe_to_topics(self):
        self._subscribed_queues = {}
        for topic in self._topic_handlers.keys():
            sub_name = inspect.currentframe().f_code.co_name
            q = self.pubsub.subscribe(sub_name, topic=topic)
            if q:
                self._subscribed_queues[topic] = q

    def process_messages(self):
        while self._is_running:
            for topic, q in self._subscribed_queues.items():
                try:
                    msg = q.get(block=False)
                    if msg is None:
                        break
                    if not isinstance(msg, PubSubMessage):
                        logger.warning(f"收到非PubSubMessage类型消息: {type(msg)}")
                        continue

                    handler = self._topic_handlers.get(topic)
                    if handler:
                        threading.Thread(target=handler, args=(msg,), daemon=True).start()
                    q.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"消息处理错误: {str(e)}")
            time.sleep(0.01)

    def publish(self, topic: CommunicationTopic, message: PubSubMessage):
        if topic != CommunicationTopic.UNKNOWN and message:
            logger.info(f"发布消息到主题[{topic.name}]，发送者: {message.sender}")
            self.pubsub.publish(topic=topic, message=message)

    def handle_task_messages(self, msg: PubSubMessage) -> None:
        if not isinstance(msg, PubSubMessage):
            return
        msg_type = msg.data.get("type")
        logger.info(f"收到任务消息，类型: {msg_type}，数据: {msg.data}")
        handler = self._task_msg_handlers.get(msg_type)
        if handler:
            handler(msg.data)
        else:
            logger.warning(f"未知的任务消息类型: {msg_type}")

    def handle_ui_messages(self, msg: PubSubMessage) -> None:
        if not isinstance(msg, PubSubMessage):
            return
        msg_type = msg.data.get("type")
        logger.info(f"收到UI消息，类型: {msg_type}，数据: {msg.data}")
        handler = self._ui_msg_handlers.get(msg_type)
        if handler:
            handler(msg.data)
        else:
            logger.warning(f"未知的UI消息类型: {msg_type}")

    # ————————— UI的消息处理 —————————
    def on_start_selected_task(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.SELECTED_TASK_START,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_stop_selected_task(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.SELECTED_TASK_STOP,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_start_auto_task(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.AUTO_TASK_START,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_start_advanced_auto_task(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.ADVANCE_AUTO_TASK_START,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_resize_windows(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.RESIZE_WINDOW,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_close_windows(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.CLOSE_WINDOW,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_auto_login(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.AUTO_LOGIN,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    # ————————— TASK的消息处理 —————————
    def on_task_started(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.TASK_PROCESS_UPDATE,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_task_finished(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.TASK_PROCESS_UPDATE,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_task_process(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.TASK_PROCESS_UPDATE,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def on_window_status(self, msg: Any = None):
        self.pubsub.publish(
            topic=CommunicationTopic.WINDOW_STATUS,
            message=PubSubMessage(sender="EventManager", data=msg or {})
        )

    def cleanup(self):
        self._is_running = False
        if hasattr(self, "_processing_thread"):
            self._processing_thread.join(timeout=1.0)

        for topic, q in self._subscribed_queues.items():
            q.put(None)

        self._task_manager.cleanup()

        for topic in self._subscribed_queues.keys():
            self.pubsub.unsubscribe(name="event_manager", topic=topic)


# ------------------------------
# 3. 新增：测试订阅者（保持不变，用于验证消息）
# ------------------------------
class TestSubscriber:
    def __init__(self, pubsub: PubSubWithQueue, name: str):
        self.pubsub = pubsub
        self.name = name
        self.received_messages = {}

    def subscribe_topics(self, topics: list[CommunicationTopic]):
        for topic in topics:
            self.received_messages[topic] = []
            q = self.pubsub.subscribe(name=self.name, topic=topic)
            threading.Thread(
                target=self._listen_queue,
                args=(topic, q),
                daemon=True,
                name=f"TestSubscriber-{self.name}-{topic.name}"
            ).start()

    def _listen_queue(self, topic: CommunicationTopic, q: queue.Queue):
        while True:
            msg = q.get()
            if msg is None:
                break
            if isinstance(msg, PubSubMessage):
                self.received_messages[topic].append(msg)
                logger.info(f"【订阅者{self.name}】收到主题[{topic.name}]消息: {msg.data}")
            q.task_done()

    def get_received_count(self, topic: CommunicationTopic) -> int:
        return len(self.received_messages.get(topic, []))

    def has_message(self, topic: CommunicationTopic, check_data: dict = None) -> bool:
        if topic not in self.received_messages:
            return False
        if not check_data:
            return len(self.received_messages[topic]) > 0
        for msg in self.received_messages[topic]:
            if all(msg.data.get(k) == v for k, v in check_data.items()):
                return True
        return False


# ------------------------------
# 4. 新增：Qt GUI主窗口（核心新增部分）
# ------------------------------
class TestMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EventManager 测试工具")
        self.setGeometry(100, 100, 800, 600)  # 窗口位置(x,y)和大小(w,h)

        # 初始化EventManager和测试订阅者
        self.event_manager = EventManager()
        self.test_sub = TestSubscriber(pubsub=self.event_manager.pubsub, name="Test1")
        # 订阅所有需要验证的主题
        self.test_sub.subscribe_topics([
            CommunicationTopic.SELECTED_TASK_START,
            CommunicationTopic.SELECTED_TASK_STOP,
            CommunicationTopic.AUTO_TASK_START,
            CommunicationTopic.ADVANCE_AUTO_TASK_START,
            CommunicationTopic.RESIZE_WINDOW,
            CommunicationTopic.CLOSE_WINDOW,
            CommunicationTopic.AUTO_LOGIN,
            CommunicationTopic.TASK_PROCESS_UPDATE,
            CommunicationTopic.WINDOW_STATUS
        ])

        # 中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题标签
        title_label = QLabel("EventManager 功能测试按钮")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # ————————— 第一组：UI消息测试按钮 —————————
        ui_label = QLabel("1. UI消息测试（模拟UI发送指令）")
        ui_label.setStyleSheet("font-size: 14px; color: #2c3e50; margin-top: 10px;")
        layout.addWidget(ui_label)

        # 按钮1：启动选中任务
        btn_start_selected = QPushButton("启动选中任务（任务0/2，角色1/3）")
        btn_start_selected.clicked.connect(self.send_start_selected_task)
        layout.addWidget(btn_start_selected)

        # 按钮2：停止选中任务
        btn_stop_selected = QPushButton("停止选中任务（角色0/2）")
        btn_stop_selected.clicked.connect(self.send_stop_selected_task)
        layout.addWidget(btn_stop_selected)

        # 按钮3：启动自动任务
        btn_auto_task = QPushButton("启动自动任务（领队角色0）")
        btn_auto_task.clicked.connect(self.send_auto_task)
        layout.addWidget(btn_auto_task)

        # 按钮4：启动高级自动任务
        btn_adv_auto_task = QPushButton("启动高级自动任务（领队0，分组1/3）")
        btn_adv_auto_task.clicked.connect(self.send_adv_auto_task)
        layout.addWidget(btn_adv_auto_task)

        # 按钮5：自动登录
        btn_auto_login = QPushButton("自动登录（角色0/1/2）")
        btn_auto_login.clicked.connect(self.send_auto_login)
        layout.addWidget(btn_auto_login)

        # 按钮6：重新排布窗口
        btn_resize = QPushButton("重新排布窗口")
        btn_resize.clicked.connect(self.send_resize_window)
        layout.addWidget(btn_resize)

        # 按钮7：关闭窗口
        btn_close = QPushButton("关闭窗口（角色1/3）")
        btn_close.clicked.connect(self.send_close_window)
        layout.addWidget(btn_close)

        # ————————— 第二组：任务消息测试按钮 —————————
        task_label = QLabel("\n2. 任务消息测试（模拟任务发送状态）")
        task_label.setStyleSheet("font-size: 14px; color: #2c3e50; margin-top: 10px;")
        layout.addWidget(task_label)

        # 按钮8：模拟任务开始
        btn_task_start = QPushButton("模拟任务开始（角色1，任务0）")
        btn_task_start.clicked.connect(self.send_task_started)
        layout.addWidget(btn_task_start)

        # 按钮9：模拟任务进度更新
        btn_task_process = QPushButton("模拟任务进度（50%）")
        btn_task_process.clicked.connect(self.send_task_process)
        layout.addWidget(btn_task_process)

        # 按钮10：模拟任务完成
        btn_task_finish = QPushButton("模拟任务完成（角色1，任务0）")
        btn_task_finish.clicked.connect(self.send_task_finished)
        layout.addWidget(btn_task_finish)

        # 按钮11：模拟窗口状态更新
        btn_window_status = QPushButton("模拟窗口状态（角色0/2/4在线）")
        btn_window_status.clicked.connect(self.send_window_status)
        layout.addWidget(btn_window_status)

        # ————————— 日志显示区域 —————————
        log_label = QLabel("\n3. 消息日志")
        log_label.setStyleSheet("font-size: 14px; color: #2c3e50; margin-top: 10px;")
        layout.addWidget(log_label)

        self.log_text = QTextBrowser()
        self.log_text.setStyleSheet("font-size: 12px; background-color: #f8f9fa;")
        layout.addWidget(self.log_text, stretch=1)  # stretch=1 让日志区域自动填充剩余空间

        # 关联日志到GUI文本框
        GUILogger.set_text_browser(self.log_text)
        logger.info("初始化完成！点击按钮开始测试...")

    # ————————— 按钮点击事件（发送对应消息） —————————
    def send_start_selected_task(self):
        """发送“启动选中任务”消息（FROM_UI主题）"""
        msg = PubSubMessage(
            sender="TestGUI",
            data={
                "type": "start_selected_task",
                "selected_task_indice": [0, 2],
                "selected_role_btn_indice": [1, 3],
                "is_89_115": True
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_UI, message=msg)

    def send_stop_selected_task(self):
        """发送“停止选中任务”消息（FROM_UI主题）"""
        msg = PubSubMessage(
            sender="TestGUI",
            data={
                "type": "stop_selected_task",
                "selected_role_btn_indice": [0, 2]
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_UI, message=msg)

    def send_auto_task(self):
        """发送“启动自动任务”消息（FROM_UI主题）"""
        msg = PubSubMessage(
            sender="TestGUI",
            data={
                "type": "start_auto_task",
                "leader_role_btn_index": 0,
                "is_89_115": True
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_UI, message=msg)

    def send_adv_auto_task(self):
        """发送“启动高级自动任务”消息（FROM_UI主题）"""
        msg = PubSubMessage(
            sender="TestGUI",
            data={
                "type": "start_advanced_auto_task",
                "leader_role_btn_index": 0,
                "group_indices": [1, 3],
                "is_89_115": True
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_UI, message=msg)

    def send_auto_login(self):
        """发送“自动登录”消息（FROM_UI主题）"""
        msg = PubSubMessage(
            sender="TestGUI",
            data={
                "type": "auto_login",
                "role_indices": [0, 1, 2]
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_UI, message=msg)

    def send_resize_window(self):
        """发送“重新排布窗口”消息（FROM_UI主题）"""
        msg = PubSubMessage(
            sender="TestGUI",
            data={"type": "resize_windows"},
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_UI, message=msg)

    def send_close_window(self):
        """发送“关闭窗口”消息（FROM_UI主题）"""
        msg = PubSubMessage(
            sender="TestGUI",
            data={
                "type": "close_windows",
                "role_btn_indices": [1, 3]
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_UI, message=msg)

    def send_task_started(self):
        """发送“任务开始”消息（FROM_TASK主题）"""
        msg = PubSubMessage(
            sender="TestTask",
            data={
                "type": "task_started",
                "role_btn_index": 1,
                "is_doing_task": True,
                "task_process": 0.0,
                "task_index": 0
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_TASK, message=msg)

    def send_task_process(self):
        """发送“任务进度”消息（FROM_TASK主题）"""
        msg = PubSubMessage(
            sender="TestTask",
            data={
                "type": "task_process",
                "role_btn_index": 1,
                "is_doing_task": True,
                "task_process": 0.5,
                "task_index": 0
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_TASK, message=msg)

    def send_task_finished(self):
        """发送“任务完成”消息（FROM_TASK主题）"""
        msg = PubSubMessage(
            sender="TestTask",
            data={
                "type": "task_finished",
                "role_btn_index": 1,
                "is_doing_task": False,
                "task_process": 1.0,
                "task_index": 0
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_TASK, message=msg)

    def send_window_status(self):
        """发送“窗口状态”消息（FROM_TASK主题）"""
        msg = PubSubMessage(
            sender="TestTask",
            data={
                "type": "window_status",
                "role_btn_indices": [0, 2, 4]
            },
            timestamp=time.time()
        )
        self.event_manager.publish(topic=CommunicationTopic.FROM_TASK, message=msg)

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.event_manager.cleanup()
        event.accept()


# ------------------------------
# 5. 运行GUI程序
# ------------------------------
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = TestMainWindow()
    window.show()
    sys.exit(app.exec_())