#!/usr/bin/env python3

import requests
import json
import base64


class Picture(object):
    def __init__(self, path):
        self.path = path

    def get_ocr_result(self, ocr_api):
        data = {"images": [self._to_base64()]}
        headers = {"Content-type": "application/json"}
        res = requests.post(url=ocr_api, headers=headers, data=json.dumps(data))
        text = [x["text"] for x in res.json()["results"][0]["data"]]
        return "\n".join(text)

    def _to_base64(self):
        with open(self.path, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode("utf8")


if __name__ == "__main__":
    ocr_api = "http://198.18.0.153:8865/predict/chinese_ocr_db_crnn_mobile"
    pic_path = "/Users/yuchen/Notes/imgs/Shao Nian Kai Ge - Chen Kai Ge-annot-44-0.png"
    Picture(pic_path).get_ocr_result(ocr_api)
