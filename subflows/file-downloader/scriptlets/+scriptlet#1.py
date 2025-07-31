from pathlib import Path
from oocana import Context
from shared.utils import file_path_with_url

#region generated meta
import typing
class Inputs(typing.TypedDict):
  url: str
  saved_path: str | None
  headers: dict
  cookies: dict
class Outputs(typing.TypedDict):
  tasks: list[dict]
#endregion


def main(params: Inputs, context: Context) -> Outputs:
  url = params["url"]
  saved_path = params["saved_path"]

  if saved_path is None:
    base_path = Path(context.session_dir) / "downloader"
    base_path.mkdir(parents=True, exist_ok=True)
    saved_path = file_path_with_url(
      url, base_path,
      hash_name=lambda: context.job_id,
    )

  return {
    "tasks": [{
      "saved_path": str(saved_path),
      "url": url,
      "headers": params["headers"],
      "cookies": params["cookies"],
    }],
  }
