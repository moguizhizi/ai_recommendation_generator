# app/clients/task_client.py

def fetch_task_info() -> dict:
    # 调外部接口，返回原始 taskinfo
    return {
        "tasks": [
            {"name": "小马过河", "ability": "perception", "level": 2},
            {"name": "幻色蝴蝶", "ability": "exec", "level": 3},
        ]
    }