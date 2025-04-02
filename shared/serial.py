from shared.task import Task


import os
import time
import requests

from typing import Generator, Mapping, MutableMapping
from threading import Lock
from dataclasses import dataclass
from .task import Task, TaskResult, Timeout


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
    content_length, etag = self._fetch_meta()
    if content_length is None:
      raise ValueError(f"Content-Length is null: {url}")

    self._files: list[_File] = []
    self._etag: str | None = etag
    self._content_length: int = content_length

  @property
  def etag(self) -> str | None:
    return self._etag

  @property
  def content_length(self) -> int:
    return self._content_length

  @property
  def file_offsets(self) -> list[int]:
    return [f.offset for f in self._files]

  def to_chunk_file(self, offset: int) -> str:
    return f"{self._name}.{offset}.{_DOWNALODING}{self._ext_name}"

  def load_buffer(self):
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
    for file in self._files:
      task: Task
      with file.task_lock:
        if file.task is None:
          continue
        task = file.task
      task.stop()

  def get_task(self) -> Task | None:
    new_file: _File | None = None
    for file in self._files:
      with file.task_lock:
        complated_length: int = file.complated_length
        if file.task is not None:
          complated_length = file.task.complated_length

        remain_length: int = file.target_length - complated_length
        if remain_length < 2 * self._min_task_length:
          continue

        splitted_offset: int = file.offset + complated_length + self._min_task_length - 1
        if file.task is not None:
          splitted_offset = file.task.update_end(splitted_offset)

      new_offset = splitted_offset + 1
      new_end = file.offset + file.target_length
      if new_offset == new_end:
        continue

      file.target_length = splitted_offset - file.offset
      new_file = _File(
        offset=new_offset,
        complated_length=0,
        target_length=new_end - new_offset,
        task=None,
        task_lock=Lock(),
      )
      break

    if new_file is None:
      return None

    self._files.append(new_file)
    self._files.sort(key=lambda e: e.offset)
    new_file.task = Task(
      url=self._url,
      start=new_file.offset,
      end=new_file.offset + new_file.target_length,
      headers=self._headers,
      cookies=self._cookies,
      on_finished=lambda result: self._on_task_finished(new_file, result),
    )
    return new_file.task

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
        if content_length is not None:
          content_length = int(content_length)
        return content_length, etag

      elif resp.status_code in (408, 429, 502, 503, 504):
        if self._retry_sleep > 0.0 and i < self._retry_times: # not last times
          time.sleep(self._retry_sleep)
      else:
        break

    assert resp is not None
    raise Exception(f"Failed to fetch meta data: {resp.status_code} {resp.reason}")

  def _create_first_file(self) -> _File:
    return _File(
      offset=0,
      complated_length=0,
      target_length=self._content_length,
      task=None,
      task_lock=Lock(),
    )

  def _on_task_finished(self, file: _File, _: TaskResult):
    with file.task_lock:
      task = file.task
      if task is None:
        return
      file.task = None
      chunk_name = self.to_chunk_file(file.offset)
      chunk_path = os.path.join(self._base_path, chunk_name)
      file.complated_length = os.path.getsize(chunk_path)

  def _search_chunks(self) -> Generator[int, None, None]:
    for file in os.listdir(self._base_path):
      file_name, ext = os.path.splitext(file)
      if self._ext_name != ext:
        continue
      cells = file_name.split(".")
      if len(cells) != 3:
        continue
      name, offset_text, mark = cells
      if self._name != name:
        continue
      if mark != _DOWNALODING:
        continue
      offset: int = 0
      try:
        offset = int(offset_text)
      except Exception as _:
        continue
      yield offset
