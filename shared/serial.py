from shared.task import Task


import os
import time
import requests

from typing import Generator, Mapping, MutableMapping
from threading import Lock
from dataclasses import dataclass
from .task import Task, Timeout


_DOWNALODING = "downloading"

@dataclass
class _File:
  offset: int
  complated_length: int
  target_length: int
  task: Task | None
  task_lock: Lock

# not thread safe
class Serial:
  def __init__(
      self,
      url: str,
      name: str,
      ext_name: str,
      base_path: str,
      timeout: Timeout | None,
      retry_times: int,
      retry_sleep: float,
      min_task_length: int,
      headers: Mapping[str, str | bytes | None] | None = None,
      cookies: MutableMapping[str, str] | None = None,
    ) -> None:

    self._url: str = url
    self._name: str = name
    self._base_path: str = base_path
    self._ext_name: str = ext_name # includes dot prefix
    self._timeout: Timeout | None = timeout
    self._retry_times: int = retry_times
    self._retry_sleep: float = retry_sleep
    self._min_task_length: int = min_task_length
    self._headers: Mapping[str, str | bytes | None] | None = headers
    self._cookies: MutableMapping[str, str] | None = cookies

    assert min_task_length > 1
    content_length, etag, range_uesable = self._fetch_meta()
    if content_length is None:
      raise ValueError(f"Content-Length is null: {url}")

    self._files: list[_File] = []
    self._files_lock: Lock = Lock()
    self._etag: str | None = etag
    self._content_length: int = content_length
    self._enable_range: bool = range_uesable

  @property
  def etag(self) -> str | None:
    return self._etag

  @property
  def content_length(self) -> int:
    return self._content_length

  @property
  def file_offsets(self) -> list[int]:
    with self._files_lock:
      return [f.offset for f in self._files]

  def to_chunk_file(self, offset: int) -> str:
    return f"{self._name}.{offset}{self._ext_name}.{_DOWNALODING}"

  def load_buffer(self):
    if self._enable_range:
      for offset in self._search_chunks():
        chunk_name = self.to_chunk_file(offset)
        chunk_path = os.path.join(self._base_path, chunk_name)
        chunk_length = os.path.getsize(chunk_path)
        self._files.append(_File(
          offset=offset,
          complated_length=chunk_length,
          target_length=0,
          task=None,
          task_lock=Lock(),
        ))
      self._files.sort(key=lambda e: e.offset)

      for i, file in enumerate(self._files):
        if i < len(self._files) - 1:
          next_file = self._files[i + 1]
          file.target_length = next_file.offset - file.offset
        else:
          file.target_length = self._content_length - file.offset
    else:
      for offset in self._search_chunks():
        chunk_name = self.to_chunk_file(offset)
        chunk_path = os.path.join(self._base_path, chunk_name)
        os.remove(chunk_path)

    if len(self._files) == 0:
      self._files.append(self._create_first_file())

  def rename_and_clean_buffer(self, name: str):
    if self._name != name:
      for offset in sorted(list(self._search_chunks())):
        chunk_path = os.path.join(self._base_path, self.to_chunk_file(offset))
        os.remove(chunk_path)

    if len(self._files) == 0:
      self._files.append(self._create_first_file())

  def stop_tasks(self):
    with self._files_lock:
      for file in self._files:
        task: Task
        with file.task_lock:
          if file.task is None:
            continue
          task = file.task
        task.stop()

  def get_task(self) -> Task | None:
    with self._files_lock:
      file: _File | None
      if self._enable_range:
        file = self._select_or_split_next_file()
      else:
        file = self._no_range_file()

      if file is None:
        return None

      file.task = Task(
        url=self._url,
        start=file.offset,
        end=file.offset + file.target_length - 1,
        completed_bytes=file.complated_length,
        headers=self._headers,
        cookies=self._cookies,
        on_finished=lambda bytes_count: self._on_task_finished(file, bytes_count),
      )
      return file.task

  def _fetch_meta(self):
    resp: requests.Response | None = None
    for i in range(self._retry_times + 1):
      resp = requests.head(
        url=self._url,
        headers=self._headers,
        cookies=self._cookies,
        timeout=self._timeout,
      )
      if resp.status_code == 200:
        content_length = resp.headers.get("Content-Length")
        etag = resp.headers.get("ETag")
        range_uesable = resp.headers.get("Accept-Ranges") == "bytes"

        if content_length is not None:
          content_length = int(content_length)
        return content_length, etag, range_uesable

      elif resp.status_code in (408, 429, 502, 503, 504):
        if self._retry_sleep > 0.0 and i < self._retry_times: # not last times
          time.sleep(self._retry_sleep)
      else:
        break

    assert resp is not None
    raise Exception(f"Failed to fetch meta data: {resp.status_code} {resp.reason}")

  def _no_range_file(self) -> _File | None:
    file = self._files[0]
    if file.task is not None:
      return None # disable multi-threading downloading
    if file.complated_length >= file.target_length:
      return None
    return file

  def _select_or_split_next_file(self) -> _File | None:
    def is_file_useable_thread_safe(file: _File):
      with file.task_lock:
        return self._is_file_useable(file)

    useable_files = [f for f in self._files if is_file_useable_thread_safe(f)]
    useable_files.sort(key=lambda f: (
      0 if f.task is None else 1,
      - (f.target_length - f.complated_length),
    ))

    for file in useable_files:
      with file.task_lock:
        if not self._is_file_useable(file):
          # 两次上锁之间，状态可能发生变化
          continue
        if file.task is None:
          return file
        splitted_file = self._split_file(file)
        if splitted_file is not None:
          return splitted_file

    return None

  def _is_file_useable(self, file: _File):
    if file.complated_length >= file.target_length:
      return False

    if file.task is None:
      return True

    remain_length: int = file.target_length - file.task.complated_length
    if remain_length < 2 * self._min_task_length:
      return False

    return True

  def _split_file(self, file: _File):
    task = file.task
    assert task is not None
    splitted_offset: int = task.update_end(
      file.offset + task.complated_length + self._min_task_length - 1,
    )
    new_offset = splitted_offset + 1
    new_end = file.offset + file.target_length
    if new_offset > new_end:
      return None

    file.target_length = splitted_offset - file.offset
    splitted_file = _File(
      offset=new_offset,
      complated_length=0,
      target_length=new_end - new_offset,
      task=None,
      task_lock=Lock(),
    )
    self._files.append(splitted_file)
    self._files.sort(key=lambda e: e.offset)
    return splitted_file

  def _create_first_file(self) -> _File:
    return _File(
      offset=0,
      complated_length=0,
      target_length=self._content_length,
      task=None,
      task_lock=Lock(),
    )

  def _on_task_finished(self, file: _File, bytes_count: int):
    with file.task_lock:
      file.task = None
      file.complated_length += bytes_count

  def _search_chunks(self) -> Generator[int, None, None]:
    for file in os.listdir(self._base_path):
      cells = file.split(".")
      if len(cells) != 4:
        continue
      name, offset_text, ext, mark = cells
      if self._name != name:
        continue
      if self._ext_name != f".{ext}":
        continue
      if mark != _DOWNALODING:
        continue
      offset: int = 0
      try:
        offset = int(offset_text)
      except Exception as _:
        continue
      yield offset
