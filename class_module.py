# 1. 修正类型导入：从 typing 导入 List（用于列表类型标注）
from typing import List
from dataclasses import dataclass
from enum import Enum, auto
import threading

# 任务状态枚举
class TaskStatus(Enum):
    PENDING = auto()    # 待执行
    RUNNING = auto()    # 执行中
    SUCCEEDED = auto()  # 成功
    FAILED = auto()     # 失败
    STOPPED = auto()    # 被停止

# 父类：基础任务信息
@dataclass
class Task:
    task_id: int               # 任务ID
    role_index: int            # 角色索引
    hwnd: int                  # 窗口句柄
    selected_tasks: list       # 选中的任务列表
    thread: threading.Thread = None  # 任务线程
    status: TaskStatus = TaskStatus.PENDING  # 任务状态
    progress: float = 0.0      # 任务进度
    error: str = None          # 错误信息

# 子类：扩展任务信息（新增time字段）
@dataclass
class TaskInfo(Task):
    time: float = 0.0  # 新增的时间字段（如任务耗时）

if __name__ == "__main__":
    # 2. 修正：创建TaskInfo对象时，参数之间加逗号
    new_task = TaskInfo(
        task_id=1,
        role_index=0,
        hwnd=123456,
        selected_tasks=[0, 2],
        progress=0.0,  # 注意：这里需要加逗号（之前缺少）
        time=0.0       # 新增的time字段
    )

    print(new_task)
    print(new_task.data)
    pass
    # 3. 修正：容器类型匹配（List对应[]，而非{}）
    tasks: List[TaskInfo] = []  # 列表初始化用[]，而非{}
    tasks.append(new_task)

    # 创建第二个任务（同样注意逗号）
    new_task1 = Task(
        task_id=2,
        role_index=1,  # 建议修改为不同角色索引，避免冲突
        hwnd=654321,   # 不同窗口句柄
        selected_tasks=[1, 3],
        progress=0.0
    )
    tasks.append(new_task1)
    
    print("任务列表：")
    for task in tasks:
        print(f"任务ID: {task.task_id}, 角色: {task.role_index}, 状态: {task.status}")