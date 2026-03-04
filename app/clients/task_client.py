# app/clients/task_client.py


def fetch_task_info() -> dict:
    # 调外部接口，返回原始 taskinfo
    return {
        "tasks": [
            {
                "id": "task_101",
                "name": "数字记忆挑战",
                "level1_brain": "memory",
                "level2_brain": "working_memory,spatial_memory",
                "paradigm": "延迟匹配-标准",
                "difficulty": 1,
                "duration_min": 5,
                "life_desc": "工具宝箱能提高儿童对近期发生事情的记忆和回忆能力，帮儿童顺利想起需要做的事情，并减少因丢三落四而带来的烦恼。坚持一段时间的训练后，儿童可能会惊喜地发现忘事儿的情况得到了很好地缓解。",
            },
            {
                "id": "task_205",
                "name": "空间旋转训练",
                "level1_brain": "exec",
                "level2_brain": "conflict_inhibition,interference_control",
                "paradigm": "延迟匹配-标准",
                "difficulty": 1,
                "duration_min": 5,
                "life_desc": "工具宝箱能提高儿童对近期发生事情的记忆和回忆能力，帮儿童顺利想起需要做的事情，并减少因丢三落四而带来的烦恼。坚持一段时间的训练后，儿童可能会惊喜地发现忘事儿的情况得到了很好地缓解。",
            },
            {
                "id": "task_310",
                "name": "冲突抑制训练",
                "level1_brain": "attention",
                "level2_brain": "alerting,sustained",
                "paradigm": "延迟匹配-标准",
                "difficulty": 1,
                "duration_min": 5,
                "life_desc": "工具宝箱能提高儿童对近期发生事情的记忆和回忆能力，帮儿童顺利想起需要做的事情，并减少因丢三落四而带来的烦恼。坚持一段时间的训练后，儿童可能会惊喜地发现忘事儿的情况得到了很好地缓解。",
            },
            {
                "id": "task_360",
                "name": "冲突抑制训练",
                "level1_brain": "perception",
                "level2_brain": "spatial_perception",
                "paradigm": "延迟匹配-标准",
                "difficulty": 1,
                "duration_min": 5,
                "life_desc": "工具宝箱能提高儿童对近期发生事情的记忆和回忆能力，帮儿童顺利想起需要做的事情，并减少因丢三落四而带来的烦恼。坚持一段时间的训练后，儿童可能会惊喜地发现忘事儿的情况得到了很好地缓解。",
            },
        ],
    }
