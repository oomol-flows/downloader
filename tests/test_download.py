import os
import unittest
import shutil
import requests
import hashlib

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
    url = "https://plus.unsplash.com/premium_photo-1669018131211-5283d80e7104?q=80&w=3687&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
    buffer_path: str = os.path.join(__file__, "..", "..", "tmp")
    buffer_path = os.path.abspath(buffer_path)

    if os.path.exists(buffer_path):
      shutil.rmtree(buffer_path)
    os.makedirs(buffer_path)

    output_md5 = hashlib.md5()
    output_path = download(
      url=url,
      buffer_path=buffer_path,
      timeout=None,
      retry_times=5,
      retry_sleep=0.0,
      min_task_length=8192 * 1024,
      threads_count=3,
      md5_hash=output_md5,
      headers=_PROXY_HEADERS,
    )
    self.assertEqual(
      output_md5.hexdigest(),
      self.md5(url),
    )
    print(output_path)

  def md5(self, url: str) -> str:
    response = requests.get(url, headers=_PROXY_HEADERS)
    response.raise_for_status()
    md5_hash = hashlib.md5()
    md5_hash.update(response.content)
    return md5_hash.hexdigest()