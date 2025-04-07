import io
import requests

from typing import Any, Callable, Mapping, MutableMapping
from enum import auto, Enum
from threading import Lock, Event
from .retry import Retry


Timeout = float | tuple[float, float] | tuple[float, None]

class TaskResult(Enum):
  SUCCESS=auto()
  STOPPED=auto()
  FAILURE=auto()

class AssertEnableRangeError(AssertionError):
  def __init__(self, url: str) -> None:
    super().__init__(f"Server does not support range requests: GET {url}")
    self.url: str = url

# thread safe class
class Task:
  def __init__(
      self,
      url: str,
      retry: Retry,
      start: int,
      end: int,
      completed_bytes: int,
      total_bytes: int,
      assert_can_use_range: bool,
      on_finished: Callable[[int], Any],
      headers: Mapping[str, str | bytes | None] | None = None,
      cookies: MutableMapping[str, str] | None = None,
    ) -> None:

    self._url: str = url
    self._retry: Retry = retry
    self._start: int = start
    self._end: int = end
    self._total_bytes: int = total_bytes
    self._on_finished: Callable[[int], Any] = on_finished
    self._headers: Mapping[str, str | bytes | None] | None = headers
    self._cookies: MutableMapping[str, str] | None = cookies
    assert start >= 0
    assert start <= end < total_bytes

    self._end_lock: Lock = Lock()
    self._disable_update_end: bool = False
    self._stopped_event: Event = Event()
    self._offset: int = start + completed_bytes
    self._hold_offset: int = start - 1
    self._must_use_range = (start + completed_bytes > 0 or end < total_bytes - 1)
    self._can_use_range: bool = False
    self._know_can_use_range_event: Event = Event()

    if assert_can_use_range:
      self._can_use_range = True
      self._know_can_use_range_event.set()

  @property
  def start(self) -> int:
    return self._start

  @property
  def end(self) -> int:
    with self._end_lock:
      return self._end

  @property
  def complated_length(self) -> int:
    return self._offset - self._start

  @property
  def know_can_use_range(self) -> bool:
    return self._know_can_use_range_event.is_set()

  # will pendding by self.do()
  def check_can_use_range(self) -> bool:
    self._know_can_use_range_event.wait()
    return self._can_use_range

  def stop(self):
    self._stopped_event.set()

  # a full task means downloading from 0 to the end of file
  def promoise_is_full_task(self) -> bool:
    if not self._must_use_range:
      return False
    with self._end_lock:
      if self._end < self._total_bytes - 1:
        return False
      self._disable_update_end = True
      return True

  def update_end(self, end: int) -> int:
    with self._end_lock:
      if self._disable_update_end:
        return self._end
      updated_end: int = max(end, self._hold_offset)
      self._end = updated_end
      return updated_end

  def do(
      self,
      file: io.IOBase,
      chunk_size: int,
      timeout: Timeout | None = None,
    ) -> TaskResult:

    written_count = 0
    headers: Mapping[str, str | bytes | None] = {**self._headers} if self._headers else {}

    with self._end_lock:
      headers["Range"] = f"{self._offset}-{self._end}"

    try:
      result: TaskResult = TaskResult.SUCCESS

      with self._retry.request(
        request=lambda: requests.Session().get(
          stream=True,
          url=self._url,
          headers=self._headers,
          cookies=self._cookies,
          timeout=timeout,
        ),
      ) as resp:
        enable_use_range = self._check_enable_range(resp)
        if self._must_use_range and not enable_use_range:
          raise AssertEnableRangeError(self._url)

        if enable_use_range:
          self._can_use_range = True
        self._know_can_use_range_event.set()

        for chunk in resp.iter_content(chunk_size=chunk_size):
          if self._stopped_event.is_set():
            result = TaskResult.STOPPED
            break

          # 在这个循环将下载偏移是 begin_offset ~ end_offset 之间的内容
          begin_offset = self._offset
          end_offset = self._offset + len(chunk) - 1

          with self._end_lock:
            end_offset = min(self._end, end_offset)
            self._hold_offset = end_offset
            is_last_chunk: bool = (end_offset >= self._end)

          written_size: int = end_offset - begin_offset + 1
          if written_size <= 0:
            break

          if written_size < len(chunk):
            file.write(chunk[:written_size])
          else:
            file.write(chunk)

          written_count += written_size
          self._offset = end_offset + 1
          if is_last_chunk:
            break

      file.flush()
      return result

    finally:
      self._know_can_use_range_event.set()
      self._on_finished(written_count)

  def _check_enable_range(self, resp: requests.Response) -> bool:
    content_range = resp.headers.get("Content-Range")
    content_length = resp.headers.get("Content-Length")
    if content_range != f"bytes {self._offset}-{self._end}/{self._total_bytes}":
      return False
    if content_length != f"{self._total_bytes}":
      return False
    return True