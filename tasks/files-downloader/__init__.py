from typing import cast, Callable
from threading import Lock
from downloaderx import download, Task, TaskError, RetryError
from oocana import Context

#region generated meta
import typing
class Inputs(typing.TypedDict):
  tasks: list[dict]
  found_existing: typing.Literal["ignore", "override"]
  download_fail: typing.Literal["continue", "error"]
  threads_count: int
  window_width: int
  failure_ladder: list[int]
  min_segment_length: int
  once_fetch_size: int
  timeout: float
  retry_times: int
  retry_sleep: float
class Outputs(typing.TypedDict):
  success_paths: list[str]
  failed_urls: list[str]
  on_task_completed: dict
  on_task_failed: dict
  on_task_failed_with_retry_error: dict
#endregion


def main(params: Inputs, context: Context) -> Outputs:
  tasks = [_decode_task(t) for t in params["tasks"]]
  found_existing = params["found_existing"]
  download_fail = params["download_fail"]

  override_existing_files: bool
  if found_existing == "ignore":
    override_existing_files = False
  elif found_existing == "override":
    override_existing_files = True
  else:
    raise ValueError(f"Invalid value for found_existing: {found_existing}")

  lock = Lock()
  success_paths: list[str] = []
  failed_urls: list[str] = []

  def on_task_completed(task: Task):
    with lock:
      success_paths.append(str(task.file))
      task_json = _encode_task(task)
      progress = float(len(success_paths)) / len(tasks)
      context.output("on_task_completed", task_json)
      context.report_progress(100.0 * progress)

  def _on_task_failed(error: TaskError):
    with lock:
      failed_urls.append(error.task.url)
      task_json = _encode_task(error.task)
      task_json["error"] = f"{type(error).__name__}: {error}"
      context.output("on_task_failed", task_json)

  def on_task_failed_with_retry_error(error: RetryError):
    with lock:
      task_json = _encode_task(error.task)
      task_json["error"] = f"{type(error).__name__}: {error}"
      context.output("on_task_failed_with_retry_error", task_json)

  on_task_failed: Callable[..., None] | None = _on_task_failed
  if download_fail == "error":
    on_task_failed = None

  try:
    download(
      tasks_iter=iter(tasks),
      window_width=params["window_width"],
      threads_count=params["threads_count"],
      failure_ladder=params["failure_ladder"],
      min_segment_length=params["min_segment_length"],
      once_fetch_size=params["once_fetch_size"],
      timeout=params["timeout"],
      retry_times=params["retry_times"],
      retry_sleep=params["retry_sleep"],
      override_existing_files=override_existing_files,
      on_task_completed=on_task_completed,
      on_task_failed=on_task_failed,
      on_task_failed_with_retry_error=on_task_failed_with_retry_error,
    )
  except TaskError as error:
    task_json = _encode_task(error.task)
    task_json["error"] = f"{type(error).__name__}: {error}"
    context.output("on_task_failed", task_json)
    raise error

  return cast(Outputs, {
    "success_paths": success_paths,
    "failed_urls": failed_urls,
  })

def _decode_task(task: dict) -> Task:
  return Task(
    file=task["saved_path"],
    url=task["url"],
    headers=task["headers"],
    cookies=task["cookies"],
  )

def _encode_task(task: Task) -> dict:
  return {
    "saved_path": str(task.file),
    "url": task.url,
    "headers": task.headers,
    "cookies": task.cookies,
  }
