from PyQt5.QtWidgets import (QMainWindow, QPushButton, QLabel, QTextEdit, 
                            QVBoxLayout, QHBoxLayout, QFrame, QGroupBox, QWidget)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

# 定义UI发送给业务逻辑的命令（UI只需要知道这些命令）
class UICommand:
    START = "start"
    STOP = "stop"

class UIApp(QMainWindow):
    """PyQt UI应用类，只通过队列与外部通信"""
    def __init__(self, input_queue, output_queue):
        super().__init__()
        self.input_queue = input_queue  # 接收外部消息的队列（业务逻辑→UI）
        self.output_queue = output_queue  # 发送消息的队列（UI→业务逻辑）
        
        # 设置窗口属性
        self.setWindowTitle("纯队列通信示例")
        self.setGeometry(100, 100, 600, 500)
        
        # 初始化UI
        self._init_ui()
        
        # 设置定时器处理输入队列
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._process_input_queue)
        self.timer.start(100)  # 每100ms检查一次队列
    
    def _init_ui(self):
        """初始化UI组件"""
        main_layout = QVBoxLayout()
        
        # 控制按钮区域
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        
        self.start_btn = QPushButton("启动业务程序")
        self.start_btn.clicked.connect(self._send_start_command)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("停止业务程序")
        self.stop_btn.clicked.connect(self._send_stop_command)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        main_layout.addWidget(control_frame)
        
        # 状态显示
        self.status_label = QLabel("请启动业务程序")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
        # 数据显示
        data_group = QGroupBox("最新数据")
        data_layout = QVBoxLayout(data_group)
        self.data_label = QLabel("等待数据...")
        self.data_label.setFont(QFont("Arial", 24))
        self.data_label.setAlignment(Qt.AlignCenter)
        data_layout.addWidget(self.data_label)
        main_layout.addWidget(data_group)
        
        # 日志显示
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group, 1)
        
        # 设置中心部件
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
    def _send_start_command(self):
        """向业务逻辑发送启动命令"""
        self.output_queue.put({"command": UICommand.START})
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._add_log("已发送启动命令")
    
    def _send_stop_command(self):
        """向业务逻辑发送停止命令"""
        self.output_queue.put({"command": UICommand.STOP})
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._add_log("已发送停止命令")
    
    def _add_log(self, message):
        """添加日志信息"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.moveCursor(self.log_text.textCursor().End)
    
    def _process_input_queue(self):
        """处理从业务逻辑接收的消息"""
        while not self.input_queue.empty():
            try:
                message = self.input_queue.get_nowait()
                
                # 根据消息类型更新UI
                if message["type"] == "status_update":
                    self.status_label.setText(message["data"])
                    self._add_log(message["data"])
                elif message["type"] == "data_update":
                    self.data_label.setText(f"{message['value']}")
                    self._add_log(f"收到数据: {message['value']} ({message['timestamp']})")
                elif message["type"] == "error":
                    self._add_log(f"错误: {message['data']}")
                
            except Exception as e:
                self._add_log(f"处理消息出错: {str(e)}")
                break
    