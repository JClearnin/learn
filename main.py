import sys
from PyQt5.QtWidgets import QApplication
# from ui_app import UIApp
# from business_logic import BusinessLogic
from log_module import logger

# def main():
#     # 创建双向通信队列
#     ui_to_business_queue = queue.Queue()  # UI发送给业务逻辑的消息队列
#     business_to_ui_queue = queue.Queue()  # 业务逻辑发送给UI的消息队列
    
#     # 初始化业务逻辑，只传入通信队列
#     business = BusinessLogic(
#         input_queue=ui_to_business_queue,
#         output_queue=business_to_ui_queue
#     )
    
#     # 初始化UI，只传入通信队列
#     app = QApplication(sys.argv)
#     ui = UIApp(
#         input_queue=business_to_ui_queue,
#         output_queue=ui_to_business_queue
#     )
#     ui.show()
    
#     # 启动业务逻辑
#     business.start()
    
#     # 运行UI主循环
#     sys.exit(app.exec_())

if __name__ == "__main__":
    logger.info(f"Program begin.")
    # main()
    logger.info(f"program end.")