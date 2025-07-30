from pathlib import Path
from oocana import Context

#region generated meta
import typing
class Inputs(typing.TypedDict):
  files: list[dict]
  saved_folder: str | None
  headers: dict
  cookies: dict
class Outputs(typing.TypedDict):
  tasks: list[dict]
  saved_folder: str
#endregion


def main(params: Inputs, context: Context) -> Outputs:
  saved_folder = params["saved_folder"]
  task_jsons: list[dict] = []

  if saved_folder is None:
    saved_folder = Path(context.session_dir) / "downloader"
  else:
    saved_folder = Path(saved_folder)

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
