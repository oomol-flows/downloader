from shutil import rmtree
from pathlib import Path
from oocana import Context

#region generated meta
import typing
class Inputs(typing.TypedDict):
  files: list[dict]
  saved_folder: str | None
  clean_saved_folder: bool
  headers: dict
  cookies: dict
class Outputs(typing.TypedDict):
  tasks: typing.NotRequired[list[dict]]
  saved_folder: typing.NotRequired[str]
#endregion


def main(params: Inputs, context: Context) -> Outputs:
  saved_folder = params["saved_folder"]
  task_jsons: list[dict] = []

  if saved_folder is None:
    saved_folder = Path(context.session_dir) / "downloader"
  else:
    saved_folder = Path(saved_folder)
    if saved_folder.exists():
      if not saved_folder.is_dir():
        raise ValueError(f"'{saved_folder}' is not a directory")
      if params["clean_saved_folder"]:
        _clear_folder(saved_folder)

  saved_folder.mkdir(parents=True, exist_ok=True)

  for file in params["files"]:
    task_jsons.append({
      "url": file["url"],
      "saved_path": str(saved_folder / file["name"]),
      "headers": params["headers"],
      "cookies": params["cookies"]
    })
  return {
    "tasks": task_jsons,
    "saved_folder": str(saved_folder),
  }

def _clear_folder(folder_path: Path):
  for item in folder_path.iterdir():
    if item.is_file() or item.is_symlink():
      item.unlink()
    elif item.is_dir():
      rmtree(item)