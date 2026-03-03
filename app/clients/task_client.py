# app/clients/task_client.py


def fetch_task_info() -> dict:
    # 调外部接口，返回原始 taskinfo
    return {
        "tasks": [
            {
                "id": 1,
                "name": "小马过河",
                "level1_brain": "记忆力",
                "level2_brain": "记忆力-工作记忆,记忆力-空间记忆",
                "paradigm": "延迟匹配-标准",
                "difficulty": 1,
                "duration_min": 5,
                "life_desc": "工具宝箱能提高儿童对近期发生事情的记忆和回忆能力，帮儿童顺利想起需要做的事情，并减少因丢三落四而带来的烦恼。坚持一段时间的训练后，儿童可能会惊喜地发现忘事儿的情况得到了很好地缓解。",
            },
            {
                "id": 2,
                "name": "小马过河",
                "level1_brain": "记忆力",
                "level2_brain": "记忆力-工作记忆,记忆力-空间记忆",
                "paradigm": "延迟匹配-标准",
                "difficulty": 1,
                "duration_min": 5,
                "life_desc": "工具宝箱能提高儿童对近期发生事情的记忆和回忆能力，帮儿童顺利想起需要做的事情，并减少因丢三落四而带来的烦恼。坚持一段时间的训练后，儿童可能会惊喜地发现忘事儿的情况得到了很好地缓解。",
            },
        ],
    }
