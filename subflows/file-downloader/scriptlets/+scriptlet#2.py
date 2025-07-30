from oocana import Context

#region generated meta
import typing
class Inputs(typing.TypedDict):
  success_paths: list[str]
class Outputs(typing.TypedDict):
  success_path: str
#endregion

def main(params: Inputs, context: Context) -> Outputs:
  return { "success_path": params["success_paths"][0] }
