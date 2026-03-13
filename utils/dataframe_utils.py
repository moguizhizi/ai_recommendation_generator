# utils/dataframe_utils.py

from typing import Dict, List, Optional

import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)


class ColumnAccessor:
    """
    DataFrame column accessor based on Enum + column mapping
    """

    def __init__(self, mapping, enum_cls):
        self._cols = {e.name.lower(): mapping[e.value] for e in enum_cls}

    def __getattr__(self, item):
        if item not in self._cols:
            raise AttributeError(f"Column '{item}' not defined")
        return self._cols[item]


def normalize_multilabel_series(series: pd.Series) -> pd.Series:
    """
    规范化多标签字段（多标签使用 "_" 分隔）。

    该函数用于统一多标签字符串的格式，使语义相同但格式不同的标签组合
    具有一致的表示形式，便于后续特征工程、统计分析或模型训练。

    处理步骤：
    1. 使用 "_" 将字符串拆分为多个标签
    2. 去除每个标签前后的空格
    3. 过滤空标签（如 "" 或仅包含空格）
    4. 对标签进行去重
    5. 按字母顺序排序，保证标签顺序一致
    6. 使用 "_" 重新拼接为字符串

    示例
    -------
    输入：
        "B_A"
        "A_A_B"
        " A _ B _ "
        "C_B_A"

    输出：
        "A_B"
        "A_B"
        "A_B"
        "A_B_C"

    作用：
    - 保证逻辑相同的标签集合有一致的字符串表示
    - 避免 "A_B" 与 "B_A" 被当成不同类别
    - 便于 groupby、统计、特征编码等操作
    """

    return series.str.split("_").apply(
        lambda parts: "_".join(sorted({p.strip() for p in parts if p and p.strip()}))
    )


def clean_dataframe(
    df: pd.DataFrame, multi_label_keywords: list | None = None
) -> pd.DataFrame:
    """
    高性能清洗函数

    当 multi_label_keywords=None 时：
        -> 不执行多标签规范化
    """

    df.columns = (
        df.columns.str.replace(
            r"[\u200b\u200c\u200d\ufeff]", "", regex=True
        )  # 去隐形字符
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    df = (
        df.fillna("")
        .astype(str)
        .apply(lambda col: col.str.strip())
        .replace(r"\s*_\s*", "_", regex=True)
        .replace(r"\s+", " ", regex=True)
        .replace(r"[\u200b\u200c\u200d\ufeff]", "", regex=True)
    )

    # 关键改动
    if not multi_label_keywords:
        return df

    # 防止有人传字符串，例如 "颜色"
    if isinstance(multi_label_keywords, str):
        multi_label_keywords = [multi_label_keywords]

    target_cols = [
        col for col in df.columns if any(k == col for k in multi_label_keywords)
    ]

    for col in target_cols:
        try:
            df[col] = normalize_multilabel_series(df[col])
        except Exception:
            pass

    return df


def parse_date_fields(
    df: pd.DataFrame,
    date_fields: List[str],
    date_format: Optional[str] = None,
) -> pd.DataFrame:
    """
    将日期字段统一转为 ISO 格式字符串
    """
    df = df.copy()

    for field in date_fields:
        if field not in df.columns:
            logger.warning(f"Date field not found, skip: {field}")
            continue

        logger.info(f"Parsing date field: {field}")
        df[field] = pd.to_datetime(
            df[field],
            format=date_format,
            errors="coerce",
        ).dt.strftime("%Y-%m-%d")

    return df


def validate_schema(df: pd.DataFrame, required_fields: List[str]) -> None:
    """
    校验必需字段是否存在
    """
    logger.info(f"Validating required fields: {required_fields}")

    missing = [f for f in required_fields if f not in df.columns]
    if missing:
        logger.error(f"Missing required fields: {missing}")
        raise ValueError(f"Missing required fields: {missing}")

    logger.info("Schema validation passed")


def drop_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    删除全为空的行
    """
    before = len(df)
    df = df.dropna(how="all")
    after = len(df)

    if before != after:
        logger.info(f"Dropped {before - after} empty rows")

    return df


def normalize_columns(
    df: pd.DataFrame,
    column_mapping: Optional[Dict[str, str]] = None,
    strip_whitespace: bool = True,
) -> pd.DataFrame:
    """
    统一字段名（别名 / 空格 / 全角问题）
    """
    df = df.copy()

    if strip_whitespace:
        old_cols = list(df.columns)
        df.columns = [str(c).strip() for c in df.columns]
        if old_cols != list(df.columns):
            logger.info("Stripped whitespace from column names")

    if column_mapping:
        missing_cols = set(column_mapping) - set(df.columns)
        if missing_cols:
            logger.warning(f"Columns not found in DataFrame: {missing_cols}")

        df = df.rename(columns=column_mapping)

    logger.debug(f"Final columns: {list(df.columns)}")
    return df


def parse_multivalue_columns(
    df: pd.DataFrame,
    fields: List[str],
    sep: str = ",",
) -> pd.DataFrame:
    """
    将 DataFrame 中指定的多值字段从字符串格式解析为列表(list)。

    该函数用于处理形如 "A,B,C" 的多值字段，将其拆分为
    ["A", "B", "C"] 的列表形式，方便后续特征工程或统计分析。

    注意：
    - 仅进行 **字符串 → list 的转换**
    - 不进行行展开（不会使用 explode）
    - 原 DataFrame 会被复制，避免修改原始数据

    处理规则：
    1. 如果字段不存在，则记录 warning 并跳过
    2. NaN 值转换为 []
    3. 字符串按 sep 分隔并去除空格
    4. 过滤空字符串
    5. 非字符串值包装为单元素 list

    示例
    -------
    输入：
        疾病 = "A,B,C"

    输出：
        疾病 = ["A", "B", "C"]

    参数
    -------
    df : pd.DataFrame
        输入数据表

    fields : List[str]
        需要拆分的多值字段列表

    sep : str
        多值分隔符，默认 ","
    """
    df = df.copy()

    for field in fields:
        if field not in df.columns:
            logger.warning(f"Multi-value field not found, skip: {field}")
            continue

        logger.info(f"Splitting multi-value field: {field}")

        def _split(val):
            if pd.isna(val):
                return []
            if isinstance(val, str):
                return [v.strip() for v in val.split(sep) if v.strip()]
            return [val]

        df[field] = df[field].apply(_split)

    return df


def fill_na_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    保持 DataFrame 内部为 NaN，
    在导出 records 时再统一转换为 None。
    """

    na_count = df.isna().sum().sum()

    logger.info(f"Keeping NA values as NaN | total_na_cells={na_count}")

    return df
