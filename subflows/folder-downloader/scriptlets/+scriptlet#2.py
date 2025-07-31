from oocana import Context

#region generated meta
import typing
class Inputs(typing.TypedDict):
  saved_folder: str
  success_paths: list[str]
  failed_urls: list[str]
class Outputs(typing.TypedDict):
  saved_folder: str
  success_paths: list[str]
  failed_urls: list[str]
#endregion

def main(params: Inputs) -> Outputs:
  return params
