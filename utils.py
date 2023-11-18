import pandas as pd
import os
import os.path
import json

class Cache:
    cache_path = '.cache/'

    def create_cache_file(self, data, filename: str) -> None:
        path = r''.join((self.cache_path, filename, '.json'))
        pd.DataFrame(data).to_json(path)
        print(f"Created cache file in {path}")

    def check_if_cache_file_exist(self, filename: str) -> None:
        path = r''.join((self.cache_path, filename, '.json'))
        return os.path.exists(path)

    def get_cache_file(self, video_id: str) -> None:
        path = r''.join((self. cache_path, video_id, '.json'))
        return pd.read_json(path)

class ReadApiKeys:
    dev_path = '.dev/'

    def youtube_api_key(self) -> str:
        path = r''.join((self.dev_path, "keys.json"))
        with open(path, "r") as file:
            return json.load(file)["YOUTUBE_API_KEY"]