# app/services/task_processor.py

def process_task_info(raw_task_info: dict) -> dict:
    tasks = raw_task_info.get("tasks", [])

    grouped = {
        "perception": [],
        "exec": [],
        "attention": [],
        "memory": []
    }

    for t in tasks:
        ability = t.get("ability")
        if ability in grouped:
            grouped[ability].append(t)

    return grouped