import shutil
from pathlib import Path


def copy_file(src: str | Path, dst: str | Path):
    """
    复制文件，并自动创建目标目录
    """

    src = Path(src)
    dst = Path(dst)

    dst.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, dst)
