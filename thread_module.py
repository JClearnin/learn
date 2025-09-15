import threading
from typing import Callable, List, Any

class TaskThread(threading.Thread):  # 1. 修正：继承自threading.Thread而非threading
    def __init__(self, stop_event: threading.Event) -> None:
        super().__init__()  # 初始化父类
        self._stop_event = stop_event  # 用于线程间停止信号传递
        self._target_func: Callable = None  # 要执行的任务函数
        self._args: List[Any] = []  # 任务函数参数
        self._callback_func: Callable = None  # 任务完成后的回调函数
        self.daemon = True  # 设为守护线程，主程序退出时自动结束

    def setup_task(self, target_func: Callable, args: List[Any], callback_func: Callable) -> None:
        """设置任务参数（分离初始化和任务设置，更灵活）"""
        self._target_func = target_func
        self._args = args
        self._callback_func = callback_func

    def run(self) -> None:  # 2. 修正：重写run()方法而非start()
        """线程启动后自动执行的方法（核心逻辑）"""
        if not self._target_func:
            raise ValueError("未设置任务函数，请先调用setup_task()")

        try:
            # 3. 循环执行任务，直到收到停止信号
            while not self._stop_event.is_set():
                # 执行目标任务并获取结果
                result = self._target_func(*self._args)  # 4. 修正：参数解包传递
                
                # 执行回调函数（如果设置）
                if self._callback_func:
                    self._callback_func(result)

                # 可根据需要添加任务间隔
                # self._stop_event.wait(0.1)  # 等待0.1秒或直到收到停止信号

                # 如果是一次性任务，执行完可跳出循环
                # break

        except Exception as e:
            print(f"线程执行出错: {e}")
        finally:
            print("线程已退出")

    def stop(self) -> None:  # 5. 修正：添加self参数
        """发送停止信号，请求线程退出"""
        self._stop_event.set()
        print("已发送停止信号")

# ------------------------------
# 使用示例
# ------------------------------
if __name__ == "__main__":
    # 创建停止信号
    stop_event = threading.Event()

    # 定义任务函数（示例：累加计数）
    def count_task(start: int, step: int) -> int:
        current = start
        current += step
        return current

    # 定义回调函数（处理任务结果）
    def handle_result(result: int) -> None:
        print(f"任务结果: {result}")

    # 创建并配置线程
    task_thread = TaskThread(stop_event)
    task_thread.setup_task(
        target_func=count_task,
        args=[0, 1],  # 初始值0，步长1
        callback_func=handle_result
    )

    # 启动线程
    task_thread.start()  # 调用父类的start()，会自动触发run()

    # 运行3秒后停止线程
    import time
    time.sleep(3)
    task_thread.stop()

    # 等待线程完全退出
    task_thread.join()
    print("主线程结束")
