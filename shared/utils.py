import os
import hashlib

from urllib.parse import urlparse


def str2sha256(input: str) -> str:
  sha256_hash = hashlib.sha256()
  sha256_hash.update(input.encode("utf-8"))
  return sha256_hash.hexdigest()

def ext_from_url(url: str):
  parsed_url = urlparse(url)
  path = parsed_url.path
  _, ext = os.path.splitext(path)
  return ext