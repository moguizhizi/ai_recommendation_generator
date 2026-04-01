# utils/metrics_utils.py

import numpy as np


# ===============================
# L2 分布 → 向量
# ===============================
def to_l2_vector(distribution, l2_size=19):
    """
    将 L2 分布转成固定长度向量
    """
    vec = np.zeros(l2_size)

    for item in distribution:
        idx = item.get("l2_index")
        if idx is not None:
            vec[idx] = item.get("ratio", 0.0)

    return vec


# ===============================
# L1 距离
# ===============================
def l1_distance(p, q):
    """
    计算 L1 距离
    """
    p = np.array(p, dtype=float)
    q = np.array(q, dtype=float)

    if p.sum() > 0:
        p = p / p.sum()
    if q.sum() > 0:
        q = q / q.sum()

    return float(np.sum(np.abs(p - q)))


# ===============================
# 分布 → L1
# ===============================
def compute_l1_from_distributions(history_dist, recommend_dist):
    """
    从 distribution 直接计算 L1
    """
    p_vec = to_l2_vector(history_dist)
    q_vec = to_l2_vector(recommend_dist)

    return l1_distance(p_vec, q_vec)


# ===============================
# 相似度（推荐一起给）
# ===============================
def l1_similarity(l1_value):
    """
    转换为相似度（0~1）
    """
    return 1.0 - l1_value / 2.0