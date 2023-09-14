#!/usr/bin/env python3
import argparse

import re

import requests
from bs4 import BeautifulSoup


class TocHandler:
    def save_pymupdf_toc_to_file(self, pymupdf_toc: list, toc_path: str = ""):
        toc_text = self.convert_pymupdf_toc_to_toc_list(pymupdf_toc=pymupdf_toc)
        self.save_toc_text_to_file(toc_text=toc_text, toc_path=toc_path)

    def convert_pymupdf_toc_to_toc_list(self, pymupdf_toc: list):
        contents = [
            f"{(x[0] - 1) * 2 * ' '}- {x[1].strip()}#{x[2]}" for x in pymupdf_toc
        ]
        toc_text = "\n".join(contents)
        return toc_text

    def save_toc_text_to_file(self, toc_text: str, toc_path: str):
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
            gap_match = re.match(r" *# *([\+\-]\d+)", line)
            first_page_match = re.match(r" *# *(\d+) *= *(-?\d+) *", line)
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
                page_gap += int(first_page_match.group(2)) - int(
                    first_page_match.group(1)
                )
            elif gap_match:
                page_gap += int(gap_match.group(1).replace(" ", ""))
            else:
                if line.strip():
                    raise ("Unsuppoted Format!")
        return toc

    def is_toc_item(self, text: str):
        if re.match(r"^第 \d+ 章.+", text):
            return True
        return False
