import queue
import threading
import time
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional, List, Type
import json

# ------------------------------
# 消息协议定义（核心，确保通信双方遵循）
# ------------------------------
@dataclass(frozen=True)
class Message:
    """标准化消息结构"""
    type: str  # 消息类型（如"status_update", "data_update"）
    payload: Dict[str, Any]  # 消息内容
    timestamp: float = None  # 时间戳（自动生成）
    message_id: str = None  # 消息唯一标识（自动生成）

    def __post_init__(self):
        """自动生成时间戳和消息ID"""
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', time.time())
        if self.message_id is None:
            object.__setattr__(self, 'message_id', f"{self.timestamp:.6f}_{threading.get_ident()}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化"""
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息对象"""
        return cls(
            type=data['type'],
            payload=data['payload'],
            timestamp=data['timestamp'],
            message_id=data['message_id']
        )


# ------------------------------
# 增强型队列实现
# ------------------------------
class CommunicationQueue:
    """增强型通信队列，支持消息验证、类型过滤和流量控制"""
    
    def __init__(self, 
                 maxsize: int = 1000,  # 队列最大容量（防止内存溢出）
                 name: str = "comm_queue",  # 队列名称（用于日志和调试）
                 message_types: Optional[List[str]] = None  # 允许的消息类型（None表示全部允许）
                ):
        self._inner_queue = queue.Queue(maxsize=maxsize)
        self._name = name
        self._message_types = set(message_types) if message_types else None
        self._dropped_count = 0  # 被丢弃的消息计数
        self._lock = threading.Lock()  # 用于线程安全的计数操作
        
        # 消息处理钩子（可注册回调函数）
        self._hooks: Dict[str, List[Callable[[Message], None]]] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def qsize(self) -> int:
        """当前队列大小"""
        return self._inner_queue.qsize()

    @property
    def dropped_count(self) -> int:
        """获取被丢弃的消息总数"""
        with self._lock:
            return self._dropped_count

    def register_hook(self, message_type: str, callback: Callable[[Message], None]) -> None:
        """注册消息处理钩子（如日志、监控）"""
        if message_type not in self._hooks:
            self._hooks[message_type] = []
        self._hooks[message_type].append(callback)

    def put(self, message: Message, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        放入消息（带类型验证和流量控制）
        
        Args:
            message: 要放入的消息对象
            block: 是否阻塞等待队列空间
            timeout: 阻塞超时时间
            
        Returns:
            消息是否成功放入队列
        """
        # 1. 验证消息类型
        if self._message_types and message.type not in self._message_types:
            raise ValueError(f"队列 {self.name} 不支持消息类型: {message.type}，允许的类型: {self._message_types}")

        try:
            # 2. 放入内部队列
            self._inner_queue.put(message, block=block, timeout=timeout)
            
            # 3. 触发钩子函数（如日志记录）
            if message.type in self._hooks:
                for hook in self._hooks[message.type]:
                    try:
                        hook(message)
                    except Exception as e:
                        print(f"队列 {self.name} 的钩子函数执行失败: {str(e)}")
            
            return True
            
        except queue.Full:
            # 处理队列满的情况（记录并计数）
            with self._lock:
                self._dropped_count += 1
            print(f"队列 {self.name} 已满，丢弃消息 {message.message_id} (类型: {message.type})")
            return False

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Message]:
        """获取消息"""
        try:
            return self._inner_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def get_by_type(self, message_type: str, block: bool = True, timeout: Optional[float] = None) -> Optional[Message]:
        """按类型获取消息（跳过其他类型）"""
        start_time = time.time()
        while True:
            # 检查超时
            if timeout is not None and (time.time() - start_time) > timeout:
                return None
                
            msg = self.get(block=block, timeout=0.1 if block else 0)
            if msg:
                if msg.type == message_type:
                    return msg
                # 非目标类型，放回队列（注意：会改变消息顺序，谨慎使用）
                self.put(msg, block=False)
            elif not block:
                return None

    def clear(self) -> None:
        """清空队列"""
        while not self._inner_queue.empty():
            try:
                self._inner_queue.get_nowait()
            except queue.Empty:
                break

    def __iter__(self):
        """迭代器接口，用于循环获取消息"""
        while True:
            msg = self.get(block=True)
            if msg:
                yield msg


# ------------------------------
# 序列化工具（支持消息持久化/跨进程通信）
# ------------------------------
class MessageSerializer:
    """消息序列化工具，支持JSON格式转换"""
    
    @staticmethod
    def serialize(message: Message) -> str:
        """将消息序列化为JSON字符串"""
        return json.dumps(message.to_dict())
    
    @staticmethod
    def deserialize(data: str) -> Message:
        """将JSON字符串反序列化为消息对象"""
        return Message.from_dict(json.loads(data))
