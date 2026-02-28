#app/services/plan_rule_engine.py

def calc_user_type(profile: dict) -> str:
    """
    判定顺序：
    1. 优势倾向型：任意一级脑能力 ≥ 100
    2. 潜能倾向型：任意一级脑能力 ∈ [90, 100)
    3. 专项优势型：任意二级脑能力 > 100
    4. 蓄力成长型：所有一级脑能力 < 90
    """

    level1_scores = profile.get("level1_scores", {})
    level2_scores = profile.get("level2_scores", {})

    level1_values = [v for v in level1_scores.values() if v > 0]

    # 1️⃣ 优势倾向型
    if any(v >= 100 for v in level1_values):
        return "优势倾向型"

    # 2️⃣ 潜能倾向型
    if any(90 <= v < 100 for v in level1_values):
        return "潜能倾向型"

    # 3️⃣ 专项优势型（二级能力存在明显优势）
    for ability, sub_scores in level2_scores.items():
        for v in sub_scores.values():
            if v > 100:
                return "专项优势型"

    # 4️⃣ 蓄力成长型
    if level1_values and all(v < 90 for v in level1_values):
        return "蓄力成长型"

    return "蓄力成长型"