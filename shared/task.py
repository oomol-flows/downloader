import io
import time
import requests

from typing import Any, Callable, Mapping, MutableMapping
from enum import auto, Enum
from threading import Lock, Event


Timeout = float | tuple[float, float] | tuple[float, None]

class TaskResult(Enum):
  SUCCESS=auto()
  STOPPED=auto()
  FAILURE=auto()

# thread safe class
class Task:
  def __init__(
      self,
      url: str,
      start: int,
      end: int,
      completed_bytes: int,
      on_finished: Callable[[int], Any],
      headers: Mapping[str, str | bytes | None] | None = None,
      cookies: MutableMapping[str, str] | None = None,
    ) -> None:

    self._url: str = url
    self._on_finished: Callable[[int], Any] = on_finished
    self._headers: Mapping[str, str | bytes | None] | None = headers
    self._cookies: MutableMapping[str, str] | None = cookies
    self._start: int = start
    self._end: int = end
    assert start >= 0
    assert end > start

    self._end_lock: Lock = Lock()
    self._stopped_event: Event = Event()
    self._offset: int = start + completed_bytes
    self._hold_offset: int = start - 1

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

  def stop(self):
    self._stopped_event.set()

  def update_end(self, end: int) -> int:
    updated_end = end
    with self._end_lock:
      updated_end = max(end, self._hold_offset)
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
      with requests.Session().get(
        stream=True,
        url=self._url,
        headers=self._headers,
        cookies=self._cookies,
        timeout=timeout,
      ) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_content(chunk_size=chunk_size):
          time.sleep(0.03)
          if self._stopped_event.is_set():
            result = TaskResult.STOPPED
            break

          # 在这个循环将下载偏移是 begin_offset ~- end_offset 之间的内容
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
      self._on_finished(written_count)
      return result

    except Exception as e:
      self._on_finished(written_count)
      raise e