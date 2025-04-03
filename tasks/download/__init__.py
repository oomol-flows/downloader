#region generated meta
import typing
class Inputs(typing.TypedDict):
  url: str
  headers: dict | None
  cookies: dict | None
class Outputs(typing.TypedDict):
  output: str
#endregion

from oocana import Context
from shared import download

def main(params: Inputs, context: Context) -> Outputs:
  output_path = download(
    url=params["url"],
    buffer_path=context.tmp_pkg_dir,
    timeout=None,
    retry_times=5,
    retry_sleep=0.0,
    min_task_length=8192 * 1024,
    threads_count=1,
  )
  return { "output": output_path }
