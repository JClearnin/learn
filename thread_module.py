import threading
import time
import sys
import os
import inspect
import logging

# 配置logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 全局控制变量
stoprc = threading.Event()

# 定义线程要执行的函数
def thread_function(name, delay):
    """线程执行的函数，打印消息并休眠指定时间"""
    logger = logging.getLogger(f"Thread-{name}")
    logger.info(f"=== 线程 {name} 开始执行 (线程ID: {threading.get_ident()}) ===")
    
    for i in range(10):
        if stoprc.is_set():
            logger.info(f"线程 {name} 收到停止信号，正在退出...")
            break
        logger.info(f"线程 {name}: 计数 {i}")
        time.sleep(delay)
    
    logger.info(f"=== 线程 {name} 执行完毕 ===")

def create_thread_a():
    """创建线程A"""
    thread = threading.Thread(target=thread_function, args=("Thread A", 1))
    thread.daemon = True
    return thread

def create_thread_b():
    """创建线程B"""
    thread = threading.Thread(target=thread_function, args=("Thread B", 2))
    thread.daemon = True
    return thread

def stop_all_threads():
    """停止所有线程"""
    stoprc.set()
    logging.info("停止信号已发送到所有线程")

def reset_stoprc():
    """重置停止信号"""
    stoprc.clear()
    logging.info("停止信号已重置")

if __name__ == "__main__":
    logging.info(f"主线程开始 (进程ID: {os.getpid()}, 线程ID: {threading.get_ident()})")
    
    # 创建线程
    thread1 = threading.Thread(target=thread_function, args=("Thread A", 1))
    thread2 = threading.Thread(target=thread_function, args=("Thread B", 2))
    
    # 启动线程
    thread1.start()
    thread2.start()
    
    logging.info("主线程即将退出...")
    # 短暂延迟，确保子线程已启动
    time.sleep(0.5)
    
    # 主线程退出
    sys.exit()
    # 下面这行代码永远不会执行
    logging.info("主线程结束")
