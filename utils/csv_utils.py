"""
utils/csv_utils.py

CSV 文件相关工具：
- CSV 转 Parquet
"""

from pathlib import Path
import pandas as pd


def csv_to_parquet(
    csv_path: str,
    parquet_path: str | None = None,
    encoding: str = "utf-8",
    sep: str = ",",
    chunksize: int | None = None,
) -> str:
    """
    将 CSV 文件转换为 Parquet 文件

    Parameters
    ----------
    csv_path : str
        CSV 文件路径
    parquet_path : str | None
        输出 parquet 文件路径
        如果为空，则自动生成与 csv 同名的 parquet
    encoding : str
        CSV 编码格式
    sep : str
        CSV 分隔符
    chunksize : int | None
        分块读取大小（用于大文件）

    Returns
    -------
    str
        生成的 parquet 文件路径
    """

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # 自动生成 parquet 路径
    if parquet_path is None:
        parquet_path = csv_path.with_suffix(".parquet")
    else:
        parquet_path = Path(parquet_path)

    # 创建目录
    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    # 小文件直接读
    if chunksize is None:
        df = pd.read_csv(csv_path, encoding=encoding, sep=sep)
        df.to_parquet(parquet_path, index=False)

    # 大文件分块
    else:
        writer = None

        for chunk in pd.read_csv(
            csv_path,
            encoding=encoding,
            sep=sep,
            chunksize=chunksize,
        ):
            if writer is None:
                chunk.to_parquet(parquet_path, index=False)
                writer = True
            else:
                chunk.to_parquet(parquet_path, index=False, append=True)

    return str(parquet_path)
