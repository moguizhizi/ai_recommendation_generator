import json
import duckdb
import pandas as pd
import os
from typing import Iterator, List, Literal, Optional
from typing import Iterable

def write_facts_jsonl(
    path: str,
    facts: Iterable,
    mode: Literal["append", "overwrite"] = "append",
) -> None:
    file_mode = "a" if mode == "append" else "w"

    with open(path, file_mode, encoding="utf-8") as f:
        for fact in facts:
            # tuple → list，JSON 友好
            f.write(json.dumps(list(fact), ensure_ascii=False))
            f.write("\n")


def iter_duckdb_query_df(
    query: str,
    columns: Optional[List[str]] = None,
    batch_size: int = 100_000,
    database: str = ":memory:",
) -> Iterator[pd.DataFrame]:
    """
    流式执行 DuckDB SQL 查询，按批返回 DataFrame

    参数:
        query: DuckDB SQL 查询语句
        columns: DataFrame 列名（None 则自动从 cursor.description 推断）
        batch_size: 每批 DataFrame 行数
        database: DuckDB 数据库（:memory: 或磁盘路径）

    返回:
        Iterator[pd.DataFrame]
    """

    # 如果是磁盘数据库且存在，则删除
    if database != ":memory:" and os.path.exists(database):
        os.remove(database)

    con = duckdb.connect(database=database)
    cursor = con.execute(query)

    try:
        if columns is None:
            columns = [desc[0] for desc in cursor.description]

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield pd.DataFrame(rows, columns=columns)
    finally:
        con.close()
