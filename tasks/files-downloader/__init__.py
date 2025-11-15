from typing import cast, Callable
from threading import Lock
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import requests
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
  success_paths: typing.NotRequired[list[str]]
  failed_urls: typing.NotRequired[list[str]]
  on_task_completed: typing.NotRequired[dict]
  on_task_failed: typing.NotRequired[dict]
  on_task_failed_with_retry_error: typing.NotRequired[dict]
#endregion


def _is_signed_url(url: str) -> bool:
  """
  Detect if a URL is a pre-signed URL (AWS S3, Aliyun OSS, etc.)
  These URLs should not have custom headers added as it breaks signature validation.
  """
  try:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Check for AWS S3 signature parameters
    aws_sig_params = ['X-Amz-Signature', 'X-Amz-Algorithm', 'X-Amz-Credential', 'Signature']
    if any(param in query_params for param in aws_sig_params):
      return True

    # Check for Aliyun OSS signature parameters
    oss_sig_params = ['OSSAccessKeyId', 'Expires', 'Signature']
    if any(param in query_params for param in oss_sig_params):
      return True

    return False
  except Exception:
    return False


def _download_signed_url(url: str, file_path: str, timeout: float) -> None:
  """
  Download a file from a presigned URL using a minimal HTTP request.
  Presigned URLs include authentication in the URL itself, so we must avoid
  sending any additional headers that weren't included in the signature.

  This uses a custom requests session that prevents default headers from being added.
  """
  from requests.structures import CaseInsensitiveDict

  # Create a custom session that doesn't add default headers
  session = requests.Session()

  # Override the session's prepare_request to prevent default headers
  original_prepare = session.prepare_request

  def minimal_prepare(request):
    prepared = original_prepare(request)
    # Keep only the Host header which is required for HTTP/1.1
    # Remove all other default headers that requests adds
    new_headers = CaseInsensitiveDict()
    if 'Host' in prepared.headers:
      new_headers['Host'] = prepared.headers['Host']
    prepared.headers = new_headers
    return prepared

  session.prepare_request = minimal_prepare

  try:
    # Download with minimal headers
    response = session.get(url, timeout=timeout, stream=True)
    response.raise_for_status()

    # Write to file
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'wb') as f:
      for chunk in response.iter_content(chunk_size=16384):
        if chunk:
          f.write(chunk)
  finally:
    session.close()


def main(params: Inputs, context: Context) -> Outputs:
  all_tasks = params["tasks"]
  found_existing = params["found_existing"]
  download_fail = params["download_fail"]

  override_existing_files: bool
  if found_existing == "ignore":
    override_existing_files = False
  elif found_existing == "override":
    override_existing_files = True
  else:
    raise ValueError(f"Invalid value for found_existing: {found_existing}")

  # Separate signed URLs from regular URLs
  signed_url_tasks: list[dict] = []
  regular_tasks: list[Task] = []

  for task in all_tasks:
    if _is_signed_url(task["url"]):
      signed_url_tasks.append(task)
    else:
      regular_tasks.append(_decode_task(task))

  lock = Lock()
  success_paths: list[str] = []
  failed_urls: list[str] = []
  total_tasks = len(all_tasks)

  # Handle signed URLs with custom download function
  for task_dict in signed_url_tasks:
    url = task_dict["url"]
    file_path = task_dict["saved_path"]

    try:
      # Check if file exists
      path_obj = Path(file_path)
      if path_obj.exists() and not override_existing_files:
        with lock:
          success_paths.append(file_path)
          context.output("on_task_completed", task_dict)
          progress = float(len(success_paths) + len(failed_urls)) / total_tasks
          context.report_progress(100.0 * progress)
        continue

      # Download using custom function for signed URLs
      _download_signed_url(url, file_path, params["timeout"])

      with lock:
        success_paths.append(file_path)
        context.output("on_task_completed", task_dict)
        progress = float(len(success_paths) + len(failed_urls)) / total_tasks
        context.report_progress(100.0 * progress)

    except Exception as error:
      with lock:
        failed_urls.append(url)
        error_task = {**task_dict, "error": f"{type(error).__name__}: {error}"}
        context.output("on_task_failed", error_task)
        progress = float(len(success_paths) + len(failed_urls)) / total_tasks
        context.report_progress(100.0 * progress)

      if download_fail == "error":
        raise

  # Handle regular URLs with downloaderx
  if regular_tasks:
    def on_task_completed(task: Task):
      with lock:
        success_paths.append(str(task.file))
        task_json = _encode_task(task)
        progress = float(len(success_paths) + len(failed_urls)) / total_tasks
        context.output("on_task_completed", task_json)
        context.report_progress(100.0 * progress)

    def _on_task_failed(error: TaskError):
      with lock:
        failed_urls.append(error.task.get_url())
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
        tasks_iter=iter(regular_tasks),
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
  """
  Convert task dictionary to downloaderx Task object.
  Note: Signed URLs are handled separately and should not use this function.
  """
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
