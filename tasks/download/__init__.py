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

def main(params: Inputs, context: Context) -> Outputs:

  # your code

  return { "output": "output_value" }
