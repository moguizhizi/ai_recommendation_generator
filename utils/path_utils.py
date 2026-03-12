import re


def safe_filename(name: str) -> str:
    """
    将任意sheet名转换为安全文件名

    Result 1      -> result_1
    游戏结果(最终) -> 游戏结果_最终
    A/B Test     -> a_b_test
    """

    name = name.strip().lower()

    # 把所有非 字母/数字/中文 替换成 _
    name = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name)

    # 去掉多余 _
    name = re.sub(r"_+", "_", name).strip("_")

    return name
