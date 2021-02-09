#!/usr/bin/env python3

"""
Some useful functions to process a PDF file.
"""

import re
import argparse
import os
from operator import itemgetter


import fitz

ANNOT_TYPES = [0, 4, 8, 9, 10, 11]

PYMUPDF_ANNOT_MAPPING = {
    0: "Text",
    4: "Square",
    8: "Highlight",
    9: "Underline",
    10: "Squiggly",
    11: "StrikeOut",
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "file",
        metavar="INFILE",
        help="PDF file to process",
        type=argparse.FileType("rb"),
    )

    g = p.add_argument_group("Process TOC")
    g.add_argument("--import-toc", "-i", help="import toc", action="store_true")
    g.add_argument(
        "--export-toc",
        "-e",
        help="export toc of INPUT to TOC_PATH",
        action="store_true",
    )
    g.add_argument("--toc-path", "-t", help="toc file path", default="toc.org")

    return p.parse_args()


class PdfHelper(object):
    def __init__(self, path):
        self.path = path
        self.doc = fitz.open(path)
        self.title = self.doc.metadata.get("title")
        self.file_name = os.path.splitext(os.path.split(path)[1])[0]

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
                        # run into this part after lvl assigned
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
                else:  # TODO support set the first page and gap
                    raise ("Unsuppoted Format!")
            self.doc.set_toc(toc)
            self.doc.saveIncr()

    def get_annots(self, annot_image_dir):
        if not self.doc.has_annots():
            return
        annot_list = []
        for page in self.doc.pages():
            annot_num = 0
            wordlist = page.getText("words")  # list of words on page
            wordlist.sort(key=lambda w: (w[3], w[0]))  # ascending y, then x
            for annot in page.annots():
                annot_type = annot.type[0]
                if annot_type not in ANNOT_TYPES:
                    continue
                page_num = page.number + 1
                annot_id = f"annot-{page_num}-{annot_num}"
                color = RGB(annot.colors.get("stroke")).to_hex()
                height = annot.rect[1] / page.rect[3]
                if annot.type[0] == 4:  # rectangle
                    pix = page.get_pixmap(
                        annots=False, clip=annot.rect, matrix=fitz.Matrix(4, 4)
                    )
                    base_name = self.title if self.title else self.file_name
                    base_name = base_name.replace(" ", "-")
                    picture_path = os.path.join(
                        annot_image_dir, f"{base_name}-{annot_id}.png"
                    )
                    pix.writePNG(picture_path)
                    content = [picture_path]
                else:
                    content = [annot.info.get("content")]
                    if annot.type[0] in [8, 9, 10, 11]:
                        text = self._parse_highlight(annot, wordlist)
                        content.append(text)
                annot_list.append(
                    {
                        "type": annot.type[1],
                        "page": page_num,
                        "content": content,
                        "id": annot_id,
                        "height": height,
                        "color": color,
                    }
                )
                annot_num += 1
        return annot_list

    def format_annots(
        self,
        annot_image_dir,
        checkbox_on_toc: bool = True,
        checkbox_on_annot: bool = False,
    ):
        results_items = []
        results_strs = []
        level = 0
        results_items.extend(self.toc_dict)
        results_items.extend(self.get_annots(annot_image_dir))
        results_items = sorted(results_items, key=itemgetter("page"))
        for item in results_items:
            page = item.get("page")
            content = item.get("content")
            if item.get("type") == "toc":
                level = item.get("depth")
                string = "{indent}- {checkbox}{link}".format(
                    indent=(level - 1) * 2 * " ",
                    checkbox="[ ] " if checkbox_on_toc else "",
                    link="[[{}:{}::{}][{}]]".format(
                        "pdf",
                        self.path,
                        page,
                        content[0].strip(),
                    ),
                )
                pass
            else:  # note
                annot_type = item.get("type")
                string = "{indent}- {checkbox}{color}{link} {content}".format(
                    indent=(level) * 2 * " ",
                    checkbox="[ ] " if checkbox_on_annot else "",
                    color=f"{item.get('color')} ",
                    link="[[{}:{}::{}++{:.2f}][{}]]".format(
                        "pdf",
                        self.path,
                        page,
                        item.get("height"),
                        item.get("id"),
                    ),
                    content=f"[[file:{content[0]}]]"
                    if annot_type == "Square"
                    else content[0],
                )
                if len(content) > 1 and content[1]:  # add multiline text in quote block
                    string += "\n" + (level + 1) * 2 * " " + "#+begin_quote\n"
                    string += content[1]
                    string += "\n" + (level + 1) * 2 * " " + "#+end_quote"
            results_strs.append(string)
        return "\n".join(results_strs)

    def _parse_highlight(self, annot, wordlist):
        points = annot.vertices
        quad_count = int(len(points) / 4)
        sentences = ["" for i in range(quad_count)]
        for i in range(quad_count):
            r = fitz.Quad(points[i * 4 : i * 4 + 4]).rect
            words = [w for w in wordlist if fitz.Rect(w[:4]).intersects(r)]
            sentences[i] = " ".join(w[4] for w in words)
        sentence = " ".join(sentences)
        return sentence

    @property
    def toc_dict(self):
        toc = self.doc.get_toc()
        return [
            {"type": "toc", "depth": x[0], "content": [x[1]], "page": x[2]} for x in toc
        ]


class RGB(object):
    def __init__(self, value):
        self.value = value

    def to_hex(self):
        if len(self.value) == 3 and type(self.value[0]) == float:
            return "#" + "".join([self._float2hex(x) for x in self.value])

    def _float2hex(self, x: float):
        return self._int2hex(int(255 * x))

    def _int2hex(self, x: int):
        return hex(x).replace("x", "0")[-2:]


def main():
    args = parse_args()
    path = args.file
    toc_path = args.toc_path
    pdf = PdfHelper(path)
    if args.export_toc:
        pdf.export_toc(toc_path)
    if args.import_toc:
        pdf.import_toc(toc_path)

if __name__ == "__main__":
    main()
