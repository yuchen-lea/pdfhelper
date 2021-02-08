#!/usr/bin/env python3

import re
import argparse

import fitz

parser = argparse.ArgumentParser(description="Process PDF toc")
parser.add_argument("file", help="pdf file to deal with")
parser.add_argument("--import-toc", "-i", help="import toc", action="store_true")
parser.add_argument("--export-toc", "-e", help="export toc", action="store_true")
parser.add_argument("--toc-path", "-t", help="toc file path", default="toc.org")


args = parser.parse_args()


class PdfHelper(object):
    def __init__(self, path):
        self.path = path
        self.doc = fitz.open(self.path)

    def export_toc(self, toc_path):
        toc = self.doc.get_toc()
        contents = [f"{(x[0]-1)*2*' '}- {x[1].strip()}#{x[2]}" for x in toc]
        try:
            with open(toc_path, "w") as data:
                print("\n".join(contents), file=data)
        except IOError as ioerr:
            print("File Error: " + str(ioerr))

    def import_toc(self, toc_path):
        with open(toc_path, "r") as data:
            lines = data.readlines()
            toc = []
            for line in lines:
                match = re.match(r"( *)[-+] (.+)#(\d+)", line)
                if match:
                    current_indent = len(match.group(1))
                    if current_indent:
                        # NOTE No indentation in first row,
                        # ran into this part after lvl assigned
                        if current_indent > last_indent:
                            lvl += lvl
                        elif current_indent < last_indent:
                            lvl -= lvl
                    else:
                        lvl = 1
                    title = match.group(2)
                    page = int(match.group(3))
                    toc.append([lvl, title, page])
                    last_indent = current_indent
                else:
                    raise ("Unsuppoted Format!")
            self.doc.set_toc(toc)
            self.doc.saveIncr()


if __name__ == "__main__":
    path = args.file
    toc_path = args.toc_path
    pdf = PdfHelper(path)
    if args.export_toc:
        pdf.export_toc(toc_path)
    if args.import_toc:
        pdf.import_toc(toc_path)
