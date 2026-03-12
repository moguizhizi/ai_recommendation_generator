"""
utils/csv_utils.py

CSV 文件相关工具：
- CSV 转 Parquet
"""

from pathlib import Path
from typing import Any, Dict
import pandas as pd


from pathlib import Path
from typing import Dict, Any
import pandas as pd


def csv_to_parquet(
    csv_path: str,
    parquet_path: str | None = None,
    encoding: str = "utf-8",
    sep: str = ",",
    chunksize: int | None = None,
    config: Dict[str, Any] = None,
) -> str:
    """
    将 CSV 文件转换为 Parquet 文件
    """

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # 自动生成 parquet 路径
    if parquet_path is None:
        parquet_path = csv_path.with_suffix(".parquet")
    else:
        parquet_path = Path(parquet_path)

    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    # =========================
    # 从 config 读取字段
    # =========================
    columns = None

    if config is not None:
        csv_name = csv_path.stem

        columns = config.get("columns", {}).get(csv_name)

    read_csv_kwargs = dict(
        encoding=encoding,
        sep=sep,
        dtype=str,
    )

    if columns:
        read_csv_kwargs["header"] = None
        read_csv_kwargs["names"] = columns

    # =========================
    # 小文件直接读取
    # =========================
    if chunksize is None:

        df = pd.read_csv(csv_path, **read_csv_kwargs)

        df.to_parquet(parquet_path, index=False)

    # =========================
    # 大文件分块读取
    # =========================
    else:

        writer_initialized = False

        for chunk in pd.read_csv(
            csv_path,
            chunksize=chunksize,
            **read_csv_kwargs,
        ):

            if not writer_initialized:

                chunk.to_parquet(parquet_path, index=False)

                writer_initialized = True

            else:

                chunk.to_parquet(
                    parquet_path,
                    index=False,
                    append=True,
                )

    return str(parquet_path)
