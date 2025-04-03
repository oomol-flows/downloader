import os
import unittest
import shutil

from shared import download


_PROXY_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
  "Accept-Language": "en-US,en;q=0.9",
  "Accept-Encoding": "gzip, deflate, br",
  "Referer": "https://www.wikipedia.org/",
  "Connection": "keep-alive",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
}

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
      threads_count=3,
      headers=_PROXY_HEADERS,
    )
    print(output_path)