# app/services/plan_rule_engine.py

def calc_user_type(profile: dict) -> str:
    """
    根据用户训练数据，判定用户类型：
    - 优势倾向型
    - 潜能倾向型
    - 专项优势型
    - 蓄力成长型
    """

    perception = profile.get("perception_score", 0)
    exec_score = profile.get("exec_score", 0)
    attention = profile.get("attention", 0)
    memory = profile.get("memory", 0)

    scores = {
        "perception": perception,
        "exec": exec_score,
        "attention": attention,
        "memory": memory
    }

    valid_scores = {k: v for k, v in scores.items() if v > 0}
    if not valid_scores:
        return "蓄力成长型"

    max_ability = max(valid_scores, key=valid_scores.get)
    max_score = valid_scores[max_ability]
    min_score = min(valid_scores.values())
    avg_score = sum(valid_scores.values()) / len(valid_scores)

    # 🔥 1️⃣ 专项优势型（单项明显高）
    # 规则：最高项 ≥ 110，且比均值高 20 分以上
    if max_score >= 110 and (max_score - avg_score) >= 20:
        return "专项优势型"

    # 🔥 2️⃣ 优势倾向型（双高或多项较高）
    # 规则：至少 2 项 ≥ 150
    high_count = sum(1 for s in valid_scores.values() if s >= 150)
    if high_count >= 2:
        return "优势倾向型"

    # 🔥 3️⃣ 潜能倾向型（整体偏低，但有潜力）
    # 规则：至少 2 项介于 80~110
    mid_count = sum(1 for s in valid_scores.values() if 80 <= s < 110)
    if mid_count >= 2 and avg_score < 120:
        return "潜能倾向型"

    # 🔥 4️⃣ 蓄力成长型（整体偏低或波动明显）
    # 规则：均值 < 80 或 最低项 < 60
    if avg_score < 80 or min_score < 60:
        return "蓄力成长型"

    # 🧠 默认兜底
    return "潜能倾向型"

# app/services/template_service.py

def get_fixed_templates(user_type: str) -> dict:
    templates = {
        "优势倾向型": {
            "overview": (
                "为了让训练更高效、更贴合孩子的成长节奏，我们结合本阶段的认知训练数据与优势倾向，"
                "为孩子生成了专属的 AI 训练方案。这份方案精准匹配宝贝的能力发展节奏，能更有针对性地助力孩子提升认知能力。"
                "建议您仔细阅读，和我们一起助力孩子认知成长。"
            ),
            "training_plan_intro": (
                "训练任务将围绕孩子优势倾向展开，以下是 AI 生成的一周专属训练计划，"
                "通过强化优势、带动均衡，精准匹配孩子当前的能力水平与发展需求。"
            ),
            "home_advice": [
                "生活功能场景：听新闻后复述4-5个信息点，锻炼孩子记忆联结能力。",
                "家庭延伸训练：每日可增加10分钟“家庭寻宝游戏”（锻炼感知觉）或“时间管理小任务”（锻炼执行控制），强化能力迁移。",
                "正向反馈技巧：当孩子完成跨场景任务时，具体表扬其能力表现（如“你刚才在整理玩具时，按颜色和形状分类，执行控制能力用得真好！”），强化优势能力的应用意识。"
            ],
            "tracking_and_adjustment": [
                "数据监测：系统会每日记录任务完成率并推送日报；每周生成能力变化曲线，对比感知觉、执行控制、注意力、记忆力的稳定性与训练效果；每3个月生成阶段报告，评估阶段训练效果及孩子生活行为改善情况。",
                "迭代规则：每天更新任务，同一个训练任务连续出现不超过3天。"
            ]
        },

        "潜能倾向型": {
            "overview": (
                "为保障认知训练的高效性与适配性，贴合孩子的个性化成长节奏，我们依托本阶段训练数据，"
                "结合孩子的认知潜能倾向，为其定制专属 AI 训练方案。方案精准匹配宝贝的认知发展节奏，"
                "可针对性助力认知能力提升，建议您详细阅读。"
            ),
            "training_plan_intro": (
                "为了让训练效果最大化，我们将训练计划拆解为两大模块：认知潜能拓展聚焦强化孩子的潜能，"
                "能力均衡训练则巩固基础、补齐短板。以下为 AI 推荐的一周训练安排。"
            ),
            "home_advice": [
                "生活功能场景：玩“听记数字”游戏（家长报数字串，孩子复述，逐步增加长度），锻炼孩子信息加工速度。",
                "家庭延伸训练：玩“干扰游戏”（家长制造轻微噪音，孩子专注拼图）。",
                "正向反馈技巧：和孩子一起讨论“分心时如何拉回注意力”（如捏耳垂、默念“专注”），陪孩子一起想办法做到。"
            ],
            "tracking_and_adjustment": [
                "数据监测：系统会每日记录任务完成率并推送日报；每周生成能力变化曲线；每3个月生成阶段报告。",
                "迭代规则：每天更新任务，同一个训练任务连续出现不超过3天。"
            ]
        },

        "专项优势型": {
            "overview": (
                "本方案结合孩子本阶段训练数据与专项优势特征制定。通过优势能力深化、巩固基础能力，"
                "将实验室得分转化为临床功能改善，最终提升孩子的生活能力表现。建议您详细阅读。"
            ),
            "training_plan_intro": (
                "基于孩子的专项优势能力，我们以核心能力强化 + 关联能力联动提升为原则，"
                "为孩子制定了周度训练任务方案。"
            ),
            "home_advice": [
                "生活功能场景：分心时在本子上记录“刚才想了什么”，事后一起分析干扰源。",
                "家庭环境打造：为孩子创建低干扰学习环境，减少视觉与听觉分心源，背景噪音控制在 40-50 分贝。"
            ],
            "tracking_and_adjustment": [
                "数据监测：系统会每日记录任务完成率并推送日报；每周生成能力变化曲线；每3个月生成阶段报告。",
                "迭代规则：每天更新任务，同一个训练任务连续出现不超过3天。"
            ]
        },

        "蓄力成长型": {
            "overview": (
                "为了帮助孩子扭转能力波动下降的趋势，我们结合本阶段训练数据与能力现状，为孩子生成了专属的 AI 训练方案。"
                "方案以稳定能力、巩固基础、逐步提升为核心，帮助孩子重拾训练信心，稳步提升认知能力。"
                "建议您仔细阅读，陪伴孩子走出波动期。"
            ),
            "training_plan_intro": (
                "本阶段训练以“低压力、高成功体验”为原则，通过基础稳控 + 阶梯式提升，逐步改善能力表现。"
            ),
            "home_advice": [
                "生活功能场景：听新闻后复述4-5个信息点，锻炼孩子记忆联结能力。",
                "家庭延伸训练：每日增加10分钟“家庭寻宝游戏”或“时间管理小任务”，强化能力迁移。",
                "正向反馈技巧：具体表扬孩子的努力过程，而不仅是结果，增强信心。"
            ],
            "tracking_and_adjustment": [
                "数据监测：系统会每日记录任务完成率并推送日报；每周生成能力变化曲线；每3个月生成阶段报告。",
                "迭代规则：每天更新任务，同一个训练任务连续出现不超过3天。"
            ]
        }
    }

    return templates.get(user_type, templates["潜能倾向型"])