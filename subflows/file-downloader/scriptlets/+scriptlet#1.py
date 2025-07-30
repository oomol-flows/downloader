from pathlib import Path
from urllib.parse import urlparse, unquote
from oocana import Context

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
    path = unquote(urlparse(url).path).strip()

    if not path:
      saved_path = base_path / context.job_id
    else:
      saved_path = base_path / path
      if saved_path.exists():
        saved_ext = path.split(".")[-1]
        saved_file_name = context.job_id
        if saved_ext:
          saved_file_name += f".{saved_ext}"
        saved_path = base_path / saved_file_name

  return {
    "tasks": [{
      "saved_path": str(saved_path),
      "url": url,
      "headers": params["headers"],
      "cookies": params["cookies"],
    }],
  }
