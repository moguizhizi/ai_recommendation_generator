# app/data/preprocess.py

from typing import Any, Dict, List, Optional

import pandas as pd

from utils.dataframe_utils import (
    clean_dataframe,
    drop_empty_rows,
    fill_na_values,
    normalize_columns,
    parse_date_fields,
    parse_multivalue_columns,
    validate_schema,
)


def preprocess_dataframe(
    df: pd.DataFrame,
    column_mapping: Optional[Dict[str, str]] = None,
    date_fields: Optional[List[str]] = None,
    multi_value_fields: Optional[List[str]] = None,
    required_fields: Optional[List[str]] = None,
    numeric_fields: Optional[List[str]] = None,
    sep: Optional[str] = ",",
    value_replacements: Optional[Dict[str, Dict[Any, Any]]] = None,  
) -> pd.DataFrame:
    """
    DataFrame 数据预处理主流程

    包含：
    - 列名规范化
    - 删除空行
    - 缺失值填充
    - schema校验（可选）
    - 日期字段解析（可选）
    - 多值字段拆分（可选）
    - 数值字段转换（可选）
    - 按列值替换（可选）
    """

    df = clean_dataframe(df)

    df = normalize_columns(df, column_mapping=column_mapping)

    df = drop_empty_rows(df)

    df = fill_na_values(df)

    # ✅ 新增：按列值替换
    if value_replacements:
        for col, replace_map in value_replacements.items():
            if col in df.columns:
                df[col] = df[col].replace(replace_map)

    if required_fields:
        validate_schema(df, required_fields)

    if date_fields:
        df = parse_date_fields(df, date_fields)

    if multi_value_fields:
        df = parse_multivalue_columns(df, multi_value_fields, sep)

    if numeric_fields:
        df[numeric_fields] = df[numeric_fields].apply(pd.to_numeric, errors="coerce")

    return df
