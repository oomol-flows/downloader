from hashlib import sha512
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse, unquote


def file_path_with_url(
      url: str,
      base_path: Path,
      hash_name: Callable[[], str],
      file_head: str | None = None,
    ) -> Path:

  path = urlparse(url).path
  path = unquote(path).strip()
  parts = [p for p in path.split("/") if p]
  if not parts:
    return base_path / hash_name()

  file_name = parts[-1]
  file_path = base_path / file_name

  if not file_path.exists():
    return file_path

  file_ext = file_name.split(".")[-1]
  file_hash = hash_name()
  index_tail: int = 0

  while True:
    file_name = file_hash
    if index_tail > 0:
      file_name += f"_{index_tail}"
    if file_ext:
      file_name += f".{file_ext}"
    if file_head:
      file_name = file_head + file_name
    file_path = base_path / file_name
    if not file_path.exists():
      return file_path
    index_tail += 1