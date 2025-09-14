import threading
import time
import random
from datetime import datetime

# 业务逻辑只需要知道这些命令（与UI定义的对应）
class UICommand:
    START = "start"
    STOP = "stop"

class BusinessLogic:
    """业务逻辑类，只通过队列与外部通信"""
    def __init__(self, input_queue, output_queue):
        self.input_queue = input_queue  # 接收外部命令的队列（UI→业务逻辑）
        self.output_queue = output_queue  # 发送消息的队列（业务逻辑→UI）
        self.running = False
        self.thread = None
        self.command_thread = None
    
    def start(self):
        """启动业务逻辑的命令监听线程"""
        self.command_thread = threading.Thread(target=self._command_listener, daemon=True)
        self.command_thread.start()
        self._send_message("status_update", "业务逻辑已初始化，等待启动命令")
    
    def _command_listener(self):
        """监听UI发送的命令"""
        while True:
            try:
                # 阻塞等待命令
                command = self.input_queue.get()
                
                # 处理命令
                if command["command"] == UICommand.START and not self.running:
                    self.running = True
                    self.thread = threading.Thread(target=self._work_loop, daemon=True)
                    self.thread.start()
                    self._send_message("status_update", "业务程序已启动")
                
                elif command["command"] == UICommand.STOP and self.running:
                    self.running = False
                    if self.thread:
                        self.thread.join()
                    self._send_message("status_update", "业务程序已停止")
            
            except Exception as e:
                self._send_message("error", f"命令处理错误: {str(e)}")
    
    def _work_loop(self):
        """业务逻辑主循环"""
        count = 0
        while self.running:
            # 生成随机数据
            value = random.randint(1, 100)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # 发送数据更新消息
            self._send_message(
                "data_update",
                value=value,
                timestamp=timestamp
            )
            
            count += 1
            # 每5次发送一次状态更新
            if count % 5 == 0:
                self._send_message("status_update", f"已处理 {count} 条数据")
            
            time.sleep(1)
        
        self._send_message("status_update", f"总计处理 {count} 条数据，已停止")
    
    def _send_message(self, message_type, data=None, **kwargs):
        """向输出队列发送消息"""
        message = {"type": message_type}
        if data is not None:
            message["data"] = data
        # 添加额外参数（如value、timestamp等）
        message.update(kwargs)
        self.output_queue.put(message)
    