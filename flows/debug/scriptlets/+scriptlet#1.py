from oocana import Context

#region generated meta
import typing
class Inputs(typing.TypedDict):
  urls: list[str]
class Outputs(typing.TypedDict):
  files: list[dict]
#endregion

def main(params: Inputs, context: Context) -> Outputs:
  files: list[dict] = []
  for i, url in enumerate(params["urls"]):
    files.append({
      "url": url,
      "name": f"{i+1}.png",
    })
  return { "files": files }
