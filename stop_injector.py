import threading
from typing import Callable, List, Any, TypeVar, ParamSpec
import inspect
from log_module import logger

# 类型变量，用于装饰器类型注解
P = ParamSpec('P')
R = TypeVar('R')

def auto_stop_check(interval: float = 0.1):
    """
    装饰器：自动为业务函数添加停止检查，业务代码无需感知stop_event
    :param interval: 检查停止信号的时间间隔（秒），适用于阻塞型任务
    """
    def decorator(func: Callable[P, R]) -> Callable[P + (threading.Event,), R]:
        # 检查函数是否有循环结构（简化判断，实际可更复杂）
        # 这里采用通用方案：在函数执行过程中定期检查
        def wrapper(*args: P.args, stop_event: threading.Event, **kwargs: P.kwargs) -> R:
            # 如果是迭代器/生成器类型的任务，在每次迭代中检查
            if inspect.isgeneratorfunction(func):
                gen = func(*args, **kwargs)
                while True:
                    if stop_event.is_set():
                        logger.info("任务已收到停止信号，退出")
                        return None
                    try:
                        yield next(gen)
                    except StopIteration as e:
                        return e.value
            else:
                # 普通函数：启动一个监控线程，定期检查停止信号
                # 同时执行原函数，通过线程间通信实现强制退出（安全方式）
                result = [None]
                error = [None]
                is_done = threading.Event()

                # 实际执行任务的子线程
                def task_runner():
                    try:
                        result[0] = func(*args, **kwargs)
                    except Exception as e:
                        error[0] = e
                    finally:
                        is_done.set()

                runner_thread = threading.Thread(target=task_runner)
                runner_thread.start()

                # 监控线程：定期检查停止信号
                while not is_done.is_set() and not stop_event.is_set():
                    stop_event.wait(interval)  # 等待指定间隔或停止信号

                if stop_event.is_set() and runner_thread.is_alive():
                    logger.info("任务已收到停止信号，正在终止")
                    # 这里不强制杀死线程，而是通过业务函数自然退出
                    # 若需强制退出，可使用更复杂的信号机制（如ctypes），但不推荐

                # 等待任务线程真正结束
                runner_thread.join()

                if error[0]:
                    raise error[0]
                return result[0]
        return wrapper
    return decorator

class TaskThread(threading.Thread):
    def __init__(self) -> None:
        super().__init__()
        self._stop_event = threading.Event()
        self._target_func: Callable = None
        self._args: List[Any] = []
        self._callback_func: Callable = None
        self.daemon = True

    def setup_task(self, target_func: Callable, args: List[Any], callback_func: Callable) -> None:
        self._target_func = target_func
        self._args = args
        self._callback_func = callback_func

    def run(self) -> None:
        if not self._target_func:
            logger.warning("未设置任务函数，请先调用setup_task()")
            return

        try:
            while not self._stop_event.is_set():
                # 自动传入stop_event，但业务函数无需感知
                result = self._target_func(*self._args, stop_event=self._stop_event)
                
                if self._callback_func and not self._stop_event.is_set():
                    self._callback_func(result)

        except Exception as e:
            logger.error(f"线程执行出错: {str(e)}", exc_info=True)
        finally:
            logger.info("线程已退出")

    def stop(self) -> None:
        if not self._stop_event.is_set():
            self._stop_event.set()
            logger.info("已发送停止信号")

# ------------------------------
# 使用示例：业务代码完全无感知
# ------------------------------
if __name__ == "__main__":
    # 1. 业务函数：完全不涉及stop_event，纯净的业务逻辑
    @auto_stop_check(interval=0.1)  # 装饰器自动添加停止检查
    def example_task(counter: List[int]) -> int:
        """业务函数：只关注核心逻辑，完全不知道stop_event的存在"""
        import time
        # 模拟一个长时间运行的任务（例如循环处理数据）
        for _ in range(10):
            time.sleep(0.5)  # 模拟耗时操作
            counter[0] += 1
            print(f"处理进度: {counter[0]}")
        return counter[0]

    # 2. 回调函数
    def handle_result(result: int) -> None:
        logger.info(f"任务完成，结果: {result}")

    # 3. 线程使用：和普通函数一样传入参数
    counter = [0]
    thread = TaskThread()
    thread.setup_task(
        target_func=example_task,
        args=[counter],  # 只传业务参数，无需关心stop_event
        callback_func=handle_result
    )
    thread.start()

    # 4. 运行2秒后停止（此时任务还在执行中）
    import time
    time.sleep(2)
    logger.info("准备停止任务")
    thread.stop()

    thread.join()
    logger.info("主线程结束")
