import io
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
      complated_bytes: int,
      on_finished: Callable[[TaskResult], Any],
      headers: Mapping[str, str | bytes | None] | None = None,
      cookies: MutableMapping[str, str] | None = None,
    ) -> None:

    self._url: str = url
    self._on_finished: Callable[[TaskResult], Any] = on_finished
    self._headers: Mapping[str, str | bytes | None] | None = headers
    self._cookies: MutableMapping[str, str] | None = cookies
    self._start: int = start
    self._end: int = end
    assert start >= 0
    assert end > start

    self._end_lock: Lock = Lock()
    self._stopped_event: Event = Event()
    self._offset: int = start + complated_bytes
    self._next_offset: int = start

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
      updated_end = max(end, self._next_offset)
      self._end = updated_end
    return updated_end

  def do(
      self,
      file: io.IOBase,
      chunk_size: int,
      timeout: Timeout | None = None,
    ) -> TaskResult:

    result: TaskResult = TaskResult.SUCCESS
    headers: Mapping[str, str | bytes | None] = {**self._headers} if self._headers else {}

    with self._end_lock:
      headers["Range"] = f"{self._offset}-{self._end}"

    try:
      with requests.Session().get(
        stream=True,
        url=self._url,
        headers=self._headers,
        cookies=self._cookies,
        timeout=timeout,
      ) as resp:
        resp.raise_for_status()
        for chunk in resp.iter_content(chunk_size=chunk_size):
          if self._stopped_event.is_set():
            result = TaskResult.STOPPED
            break

          offset = self._offset
          next_offset = offset + len(chunk)
          is_last_chunk = False

          with self._end_lock:
            next_offset = min(self._end, next_offset)
            self._next_offset = next_offset
            is_last_chunk = (next_offset >= self._end)

          if offset == next_offset:
            break
          elif offset + len(chunk) > next_offset:
            file.write(chunk[:next_offset - offset])
          else:
            file.write(chunk)

          self._offset = next_offset
          if is_last_chunk:
            break

      file.flush()
      self._on_finished(result)

      return result

    except Exception as e:
      result = TaskResult.FAILURE
      self._on_finished(TaskResult.FAILURE)
      raise e