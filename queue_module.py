import threading
import time
import random
from queue import Queue

def thread_task(queue, stop_event):
    """线程任务：生成int值并放入队列"""
    while not stop_event.is_set():
        current_value = random.randint(1, 100)  # 模拟实时数据
        queue.put(current_value)  # 将值放入队列
        time.sleep(0.5)  # 模拟耗时操作

if __name__ == "__main__":
    # 创建队列（用于线程间传递数据）
    data_queue = Queue()
    # 用于控制线程停止的事件
    stop_event = threading.Event()
    
    # 创建并启动线程
    feedback_thread = threading.Thread(
        target=thread_task,
        args=(data_queue, stop_event)
    )
    feedback_thread.start()
    
    try:
        # 主线程从队列取数据
        for _ in range(10):
            # 阻塞等待队列中的数据（超时1秒）
            value = data_queue.get(timeout=1)
            print(f"主线程收到：{value}")
            data_queue.task_done()  # 标记任务完成
    except Exception as e:
        print(f"读取数据出错：{e}")
    finally:
        # 停止线程并清理
        stop_event.set()
        feedback_thread.join()
        print("程序结束")
