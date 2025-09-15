import queue
import threading

class PubSubWithQueue:
    def __init__(self):
        self.topics = {}  # { "news": {sub_id: 队列}, ... }
        self.next_sub_id = 1

    def subscribe(self, topic, consumer_callback):
        """订阅者提供消费回调，系统自动创建队列和消费者线程"""
        if topic not in self.topics:
            self.topics[topic] = {}
        
        # 为订阅者创建专属队列
        q = queue.Queue()
        sub_id = self.next_sub_id
        self.topics[topic][sub_id] = q
        self.next_sub_id += 1

        # 启动消费者线程：从队列取消息并调用回调
        def consumer():
            while True:
                msg = q.get()  # 阻塞等待消息
                if msg is None:  # 用None作为退出信号
                    break
                consumer_callback(msg)
                q.task_done()

        threading.Thread(target=consumer, daemon=True).start()
        return (sub_id, q)  # 返回ID和队列（用于发送退出信号）

    def unsubscribe(self, topic, sub_id, q):
        """取消订阅时，发送退出信号并清理"""
        if topic in self.topics and sub_id in self.topics[topic]:
            q.put(None)  # 发送退出信号
            del self.topics[topic][sub_id]
            if not self.topics[topic]:
                del self.topics[topic]

    def publish(self, topic, message):
        if topic in self.topics:
            for q in list(self.topics[topic].values()):
                q.put(message)  # 只放队列，不等待处理


# 使用示例
def consumer1(msg):
    print(f"消费者1处理: {msg}")

def consumer2(msg):
    print(f"消费者2处理: {msg}")

pubsub = PubSubWithQueue()
sub_id1, q1 = pubsub.subscribe("news", consumer1)
sub_id2, q2 = pubsub.subscribe("news", consumer2)

pubsub.publish("news", "异步消息1")  # 立即返回，不等待处理
pubsub.publish("news", "异步消息2")
pubsub.unsubscribe("news", sub_id1, q1)  # 安全停止消费者1