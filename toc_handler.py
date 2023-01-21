#!/usr/bin/env python3
import argparse

import re

import requests
from bs4 import BeautifulSoup


class TocHandler:
    def save_toc_to_file_from_url(self, url: str, toc_path: str = ""):
        toc_list = self.get_toc_list_from_chinapub(url=url)
        toc_text = "\n".join(toc_list)
        self.save_toc_text_to_file(toc_text=toc_text, toc_path=toc_path)

    def save_pymupdf_toc_to_file(self, pymupdf_toc: list, toc_path: str = ""):
        contents = [
            f"{(x[0] - 1) * 2 * ' '}- {x[1].strip()}#{x[2]}" for x in pymupdf_toc
        ]
        toc_text = "\n".join(contents)
        self.save_toc_text_to_file(toc_text=toc_text, toc_path=toc_path)

    def save_toc_text_to_file(self, toc_text: str, toc_path: str = ""):
        if not toc_path:
            print(toc_text)
            return
        try:
            with open(toc_path, "w") as data:
                print(toc_text, file=data)
        except IOError as ioerr:
            print("File Error: " + str(ioerr))

    def get_toc_list_from_chinapub(self, url: str):
        res = requests.get(url)  # "http://product.china-pub.com/229169"
        content = res.content
        soup = BeautifulSoup(content, "lxml")
        ml = soup.select("#ml + div")[0]
        ml_txt = ml.text
        lines = []
        for ml in ml_txt.split("\n"):
            raw_line = ml.strip()
            line_with_page_match = re.match(r"(.+?)(\d+)?$", raw_line)
            if line_with_page_match:
                title = line_with_page_match.group(1)
                page = line_with_page_match.group(2)
                line = f"- {title}#{page}" if page else f"- {title}"
                line = re.sub("\s", " ", line)
                lines.append(line)
        return lines

    def convert_toc_list_to_pymupdf_toc(self, toc_list: list):
        toc = []
        page_gap = 0
        for line in toc_list:
            page_match = re.match(r"( *)[-+] (.+)# *(\d+) *", line)
            toc_without_page_match = re.match(r"( *)[-+] ([^#]+) *", line)
            gap_match = re.match(r"# *([\+\-]\d+)", line)
            first_page_match = re.match(r"#.+= *(\d+)", line)
            indent_step = 2

            if page_match or toc_without_page_match:
                current_indent = (
                    len(page_match.group(1))
                    if page_match
                    else len(toc_without_page_match.group(1))
                )
                if current_indent:
                    # NOTE No indentation in first row,
                    # run into this part after lvl assigned
                    if current_indent > last_indent:
                        lvl += 1
                        indent_step = current_indent - last_indent
                    elif current_indent < last_indent:
                        lvl -= int((last_indent - current_indent) / indent_step)
                else:
                    lvl = 1
                title = (
                    page_match.group(2)
                    if page_match
                    else toc_without_page_match.group(2)
                )
                page = int(page_match.group(3)) + page_gap if page_match else -1
                toc.append([lvl, title, page])
                last_indent = current_indent
            elif first_page_match:
                page_gap += int(first_page_match.group(1)) - 1
            elif gap_match:
                page_gap -= int(gap_match.group(1).replace(" ", ""))
            else:
                if line.strip():
                    raise ("Unsuppoted Format!")
        return toc

    def is_toc_item(self, text: str):
        if re.match(r"^第 \d+ 章.+", text):
            return True
        return False


def create_argparser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--book-url",
        help="Book url to get toc list",
    )
    p.add_argument(
        "--toc-path",
        help="toc file path",
    )

    return p


def main(args):
    url = args.book_url
    toc_path = args.toc_path
    TocHandler().save_toc_to_file_from_url(url=url, toc_path=toc_path)


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
