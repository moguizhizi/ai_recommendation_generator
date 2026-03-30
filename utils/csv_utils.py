"""
utils/csv_utils.py

CSV 文件相关工具：
- CSV 转 Parquet
"""

from pathlib import Path
from typing import Any, Dict
import pandas as pd

from utils.logger import get_logger


logger = get_logger(__name__)


def csv_to_parquet(
    csv_path: str,
    parquet_path: str | None = None,
    encoding: str = "utf-8",
    sep: str = ",",
    chunksize: int | None = None,
    config: Dict[str, Any] = None,
) -> str:
    """
    将 CSV 文件转换为 Parquet 文件，并在转换后检查行数一致性
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if parquet_path is None:
        parquet_path = csv_path.with_suffix(".parquet")
    else:
        parquet_path = Path(parquet_path)

    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    # =========================
    # 从 config 读取字段
    # =========================
    columns = None
    max_rows = None
    csv_name = csv_path.stem
    if config is not None:
        columns = config.get("columns", {}).get(csv_name)
        max_rows = config.get("debug", {}).get("dataset_row_limits", {}).get(csv_name)

    read_csv_kwargs = dict(
        encoding=encoding,
        sep=sep,
        dtype=str,
    )

    if max_rows is not None:
        logger.info(f"Applying debug row limit for {csv_name}: {max_rows}")

    if columns:
        read_csv_kwargs["header"] = None
        read_csv_kwargs["names"] = columns

    total_csv_rows = 0  # 用于统计 CSV 行数

    # =========================
    # 小文件直接读取
    # =========================
    if chunksize is None:
        df = pd.read_csv(csv_path, nrows=max_rows, **read_csv_kwargs)
        df.to_parquet(parquet_path, index=False)
        total_csv_rows = len(df)

    # =========================
    # 大文件分块读取
    # =========================
    else:
        writer_initialized = False
        for chunk in pd.read_csv(csv_path, chunksize=chunksize, **read_csv_kwargs):
            if max_rows is not None:
                remaining_rows = max_rows - total_csv_rows
                if remaining_rows <= 0:
                    break
                chunk = chunk.iloc[:remaining_rows]

            total_csv_rows += len(chunk)
            if not writer_initialized:
                chunk.to_parquet(parquet_path, index=False)
                writer_initialized = True
            else:
                chunk.to_parquet(parquet_path, index=False, append=True)

            if max_rows is not None and total_csv_rows >= max_rows:
                break

    # =========================
    # 检查 Parquet 行数
    # =========================
    df_parquet = pd.read_parquet(parquet_path)
    total_parquet_rows = len(df_parquet)

    if total_csv_rows != total_parquet_rows:
        logger.warning(
            f"[CSV->Parquet] 行数不一致: CSV={total_csv_rows}, Parquet={total_parquet_rows}"
        )

    return str(parquet_path)
