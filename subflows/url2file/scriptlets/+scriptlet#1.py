from oocana import Context
from pathlib import Path
from shared.utils import file_path_with_url

#region generated meta
import typing
class Inputs(typing.TypedDict):
  url: str
  saved_folder: str | None
  ensure_folder: bool
  file_head: str | None
class Outputs(typing.TypedDict):
  name: typing.NotRequired[str]
  saved_path: typing.NotRequired[str]
  saved_folder: typing.NotRequired[str]
#endregion

def main(params: Inputs, context: Context) -> Outputs:
  url = params["url"]
  saved_folder = params["saved_folder"]

  if saved_folder is None:
    saved_folder = Path(context.session_dir) / "downloader"
    saved_folder.mkdir(parents=True, exist_ok=True)
  else:
    saved_folder = Path(saved_folder)
    if not saved_folder.exists():
      if not params["ensure_folder"]:
        raise ValueError("Folder does not exist")
      saved_folder.mkdir(parents=True)
    elif not saved_folder.is_dir():
      raise ValueError("Folder is not a directory")

  file_path = file_path_with_url(
    url=url,
    base_path=saved_folder,
    hash_name=lambda: context.job_id,
    file_head=params["file_head"],
  )
  return {
    "name": file_path.name,
    "saved_path": str(file_path),
    "saved_folder": str(file_path),
  }
