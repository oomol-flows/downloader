import os
import shutil

from dataclasses import dataclass
from _hashlib import HASH
from typing import Callable, Generator, Mapping, MutableMapping

from .serial import Serial
from .task import TaskResult, Timeout
from .executor import execute
from .utils import str2sha256, ext_from_url


_STEP_SIZE = 8192

@dataclass
class _Context:
  serial: Serial
  buffer_path: str
  timeout: Timeout | None

@dataclass
class _FailureEvent:
  error: Exception

def download(
    url: str,
    buffer_path: str,
    timeout: Timeout | None,
    retry_times: int,
    retry_sleep: float,
    min_task_length: int,
    threads_count: int,
    md5_hash: HASH | None = None,
    headers: Mapping[str, str | bytes | None] | None = None,
    cookies: MutableMapping[str, str] | None = None,
  ) -> str:
  hash = str2sha256(url)
  ext_name = ext_from_url(url)
  file_name = f"{hash}{ext_name}"
  file_path = os.path.join(buffer_path, file_name)

  if os.path.exists(file_path):
    return file_path

  serial = Serial(
    url=url,
    name=hash,
    ext_name=ext_name,
    base_path=buffer_path,
    timeout=timeout,
    retry_times=retry_times,
    retry_sleep=retry_sleep,
    min_task_length=min_task_length,
    headers=headers,
    cookies=cookies,
  )
  serial.load_buffer()
  ctx = _Context(
    serial=serial,
    buffer_path=buffer_path,
    timeout=timeout,
  )
  failure_error: BaseException | None = None
  did_clean_chunk_files: bool

  try:
    for event in execute(
      count=threads_count,
      handler=lambda _, send: _download_serial(ctx, send),
    ):
      if isinstance(event, _FailureEvent):
        if failure_error is None:
          serial.stop_tasks()
          failure_error = event.error

  except KeyboardInterrupt as e:
    serial.stop_tasks()
    failure_error = e

  if failure_error is not None:
    raise failure_error

  try:
    did_clean_chunk_files = _merge_file(
      serial=serial,
      buffer_path=buffer_path,
      target_file_path=file_path,
      md5_hash=md5_hash,
    )
  except Exception as e:
    if os.path.exists(file_path):
      os.remove(file_path)
    raise e

  if not did_clean_chunk_files:
    for chunk_path, _, _ in _list_chunk_infos(serial, buffer_path):
      if os.path.exists(chunk_path):
        os.remove(chunk_path)

  return file_path

def _download_serial(ctx: _Context, send: Callable[[_FailureEvent], None]):
  try:
    while True:
      task = ctx.serial.get_task()
      if task is None:
        break
      file_path = os.path.join(
        ctx.buffer_path,
        ctx.serial.to_chunk_file(task.start),
      )
      with open(file_path, "ab") as file:
        result = task.do(
          file,
          chunk_size=_STEP_SIZE,
          timeout=ctx.timeout,
        )
      if result == TaskResult.STOPPED:
        break

  except Exception as e:
    send(_FailureEvent(e))
    raise e

# @return did clean chunk files
def _merge_file(
    serial: Serial,
    buffer_path: str,
    target_file_path: str,
    md5_hash: HASH | None = None,
  ) -> bool:
  offsets = serial.file_offsets

  if len(offsets) == 1:
    chunk_path, _, _ = next(_list_chunk_infos(serial, buffer_path))
    shutil.move(chunk_path, target_file_path)
    if md5_hash is not None:
      with open(target_file_path, "rb") as file:
        while True:
          chunk = file.read(_STEP_SIZE)
          if not chunk:
            break
          md5_hash.update(chunk)

  else:
    assert len(offsets) > 0
    with open(target_file_path, "wb") as output:
      for chunk_path, offset, next_offset in _list_chunk_infos(serial, buffer_path):
        with open(chunk_path, "rb") as input:
          written_count: int = 0
          target_count: int = next_offset - offset
          while written_count < target_count:
            next_step_count = min(_STEP_SIZE, target_count - written_count)
            chunk = input.read(next_step_count)
            if len(chunk) != next_step_count:
              raise ValueError(f"Unexpected end of chunk: {chunk_path}")
            output.write(chunk)
            written_count += next_step_count
            if md5_hash is not None:
              md5_hash.update(chunk)
      output.flush()

  return len(offsets) == 1

def _list_chunk_infos(serial: Serial, buffer_path: str) -> Generator[tuple[str, int, int], None, None]:
  offsets = serial.file_offsets
  for i, offset in enumerate(offsets):
    chunk_file = serial.to_chunk_file(offset)
    chunk_path = os.path.join(buffer_path, chunk_file)
    if i < len(offsets) - 1:
      next_offset = offsets[i + 1]
    else:
      next_offset = serial.content_length
    yield chunk_path, offset, next_offset