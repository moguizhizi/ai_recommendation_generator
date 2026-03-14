import asyncio

# CSV 初始化完成信号
csv_ready_event = asyncio.Event()

# CSV 初始化计数
csv_ready_counter = 0

# CSV 任务总数
total_csv_jobs = 0
