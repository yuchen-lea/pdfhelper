#!/usr/bin/env python3

import requests
import json
import base64
import configparser
import os
import re
import argparse
import sys

help_text_for_ocr_service = "The OCR Sevice to use, now supported: paddle, ocrspace"
help_text_for_ocr_language = "The language to use for ocr: zh-Hans, zh-Hant, en, ja"


class Picture(object):
    def __init__(self, path):
        self.path = path

    def get_ocr_result(self, language, ocr_service="paddle"):
        ocr = OCRHandler(source_file=self, ocr_service=ocr_service)
        ocr_result = ocr.get_ocr_result(language)
        return ocr_result

    def _to_base64(self):
        with open(self.path, "rb") as f:
            data = f.read()
            return base64.b64encode(data).decode("utf8")

    @property
    def file_size(self):
        return os.path.getsize(self.path)


class OCRHandler(object):
    def __init__(self, source_file, ocr_service):
        self.source_file = source_file
        self.source_file_path = source_file.path
        self.ocr_config = configparser.ConfigParser()
        ocr_config_ini = os.path.join(
            os.path.split(os.path.realpath(__file__))[0], "ocr_config.ini"
        )
        self.ocr_config.read(ocr_config_ini)
        self.ocr_service_functions = {
            "paddle": self.get_ocr_result_by_paddle,
            "ocrspace": self.get_ocr_result_by_ocrspace,
        }
        if ocr_service in self.ocr_service_functions.keys():
            self.get_ocr_result = self.ocr_service_functions[ocr_service]
        else:
            raise Exception(f"{ocr_service} is not supported. ")

    def get_ocr_result_by_paddle(self, language):
        data = {"images": [self.source_file._to_base64()]}
        headers = {"Content-type": "application/json"}
        res = requests.post(
            url=self.ocr_config["paddle"]["url"], headers=headers, data=json.dumps(data)
        )
        text = [x["text"] for x in res.json()["results"][0]["data"]]
        return "\n".join(text)

    def get_ocr_result_by_ocrspace(self, language):
        if not self.does_file_exceed_size_limit("ocrspace"):
            language_mapping = {
                Language.Chinese_Simplified: "chs",
                Language.Chinese_Traditional: "cht",
                Language.English: "eng",
                Language.Japanese: "jpn",
            }
            if language_mapping.get(language):
                data = {
                    "isOverlayRequired": True,
                    "apikey": self.ocr_config["ocrspace"]["key"],
                    "language": language_mapping.get(language),
                }
                with (open(self.source_file_path, "rb")) as f:
                    res = requests.post(
                        url=self.ocr_config["ocrspace"]["url"],
                        files={"filename": f},
                        data=data,
                    )
                raw = res.json()
                if type(raw) == str:
                    raise Exception(raw)
                if raw["IsErroredOnProcessing"]:
                    raise Exception(raw["ErrorMessage"][0])
                return raw["ParsedResults"][0]["ParsedText"]
            else:
                raise Exception(f"Lanugage not suppoted.")
        else:
            raise Exception(f"Exceeds size limit.")

    def does_file_exceed_size_limit(self, ocr_service):
        try:
            size_limit = self.ocr_config[ocr_service]["size_limit"]
            size_limit_pattern = re.compile(r"([\d\.]+) *(MB|mb|kb|KB)")
            size_limit_number = float(size_limit_pattern.match(size_limit).group(1))
            if "MB" or "mb" in size_limit:
                size_limit_in_bytes = size_limit_number * 1024 * 1024
            return True if size_limit_in_bytes < self.source_file.file_size else False
        except KeyError:
            return False


class Language:
    Chinese_Simplified = "zh-Hans"
    Chinese_Traditional = "zh-Hant"
    English = "en"
    Japanese = "ja"


def create_argparser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "file",
        metavar="INFILE",
        help="Picture to ocr",
        type=argparse.FileType("rb"),
    )
    p.add_argument(
        "--ocr-service",
        help=help_text_for_ocr_service,
    )
    p.add_argument(
        "--language",
        help=help_text_for_ocr_language,
    )

    return p


def main(args):
    path = args.file.name
    ocr_service = args.ocr_service
    language = args.language
    ocr_result = Picture(path).get_ocr_result(
        language=language, ocr_service=ocr_service
    )
    print(ocr_result)


if __name__ == "__main__":
    parser = create_argparser()
    # args = parser.parse_args(
    #     [
    #         "/Users/yuchen/Notes/imgs/2021-12-11_10-51-25_screenshot.png",
    #         "--ocr-service",
    #         "ocrspace",
    #         "--language",
    #         Language.Chinese_Traditional,
    #     ]
    # )
    args = parser.parse_args()
    main(args)
