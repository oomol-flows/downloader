import os
import unittest
import shutil

from shared import download


class TextFramework(unittest.TestCase):
  def test_download_single(self):
    url = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/GOODSMILE_Racing_Komatti-Mirai_EV_TT_Zero.jpg/2880px-GOODSMILE_Racing_Komatti-Mirai_EV_TT_Zero.jpg"
    buffer_path: str = os.path.join(__file__, "..", "..", "tmp")
    buffer_path = os.path.abspath(buffer_path)

    if os.path.exists(buffer_path):
      shutil.rmtree(buffer_path)
    os.makedirs(buffer_path)

    output_path = download(
      url=url,
      buffer_path=buffer_path,
      timeout=None,
      retry_times=5,
      retry_sleep=0.0,
      min_task_length=8192 * 1024,
      threads_count=1,
    )
    print(output_path)