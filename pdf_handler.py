#!/usr/bin/env python3

import re
import os
from operator import itemgetter

import fitz

from picture_handler import Picture

ANNOT_TYPES = [0, 4, 8, 9, 10, 11]

PYMUPDF_ANNOT_MAPPING = {
    0: "Text",
    4: "Square",
    8: "Highlight",
    9: "Underline",
    10: "Squiggly",
    11: "StrikeOut",
}


class PdfHelper(object):
    def __init__(self, path):
        self.path = path
        self.doc = fitz.open(path)
        self.file_name = os.path.splitext(os.path.split(path)[1])[0]

    def export_toc(self, toc_path):
        toc = self.doc.get_toc()
        contents = [f"{(x[0]-1)*2*' '}- {x[1].strip()}#{x[2]}" for x in toc]
        if not toc_path:
            print("\n".join(contents))
            return
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

    def _get_annots(
        self,
        annot_image_dir: str = "",
        ocr_api: str = "",
    ):
        if not self.doc.has_annots():
            return
        annot_list = []
        for page in self.doc.pages():
            annot_num = 0
            word_list = page.getText("words")  # list of words on page
            word_list.sort(key=lambda w: (w[3], w[0]))  # ascending y, then x
            for annot in page.annots():
                annot_type = annot.type[0]
                if annot_type not in ANNOT_TYPES:
                    continue
                page_num = page.number + 1
                annot_id = f"annot-{page_num}-{annot_num}"
                color = RGB(annot.colors.get("stroke")).to_hex()
                height = annot.rect[1] / page.rect[3]
                if annot_type == 4:  # rectangle
                    pix = page.get_pixmap(
                        annots=False, clip=annot.rect, matrix=fitz.Matrix(4, 4)
                    )
                    base_name = self.file_name.replace(" ", "-")
                    picture_path = os.path.join(
                        annot_image_dir, f"{base_name}-{annot_id}.png"
                    )
                    pix.writePNG(picture_path)
                    content = [picture_path]
                    if ocr_api:
                        ocr_result = Picture(picture_path).get_ocr_result(ocr_api)
                        content.append(ocr_result)
                else:
                    content = [annot.info.get("content")]
                    if annot_type in [8, 9, 10, 11]:
                        text = self._parse_highlight(annot, word_list)
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
        annot_image_dir: str = "",
        ocr_api: str = "",
        output_file: str = "",
        zoom: int = 4,
        with_toc: bool = True,
        toc_list_item_format: str = "{checkbox} {link}",
        annot_list_item_format: str = "{checkbox} {color} {link} {content}",
        run_test: bool = False,
    ):
        results_items = []
        results_strs = []
        level = 0
        if with_toc:
            results_items.extend(self.toc_dict)
        results_items.extend(
            self._get_annots(
                annot_image_dir=annot_image_dir,
                ocr_api=ocr_api,
            )
        )
        results_items = sorted(results_items, key=itemgetter("page"))
        for item in results_items:
            page = item.get("page")
            content = item.get("content")
            if item.get("type") == "toc":
                level = item.get("depth")
                string = ("{indent}- " + toc_list_item_format).format(
                    indent=(level - 1) * 2 * " ",
                    checkbox="[ ]",
                    title=content[0].strip(),
                    link="[[{}:{}::{}][{}]]".format(
                        "pdf",
                        self.path,
                        page,
                        content[0].strip(),
                    ),
                )
            else:  # note
                annot_type = item.get("type")
                string = ("{indent}- " + annot_list_item_format).format(
                    indent=(level) * 2 * " ",
                    checkbox="[ ]",
                    color=item.get("color"),
                    annot_id=item.get("id"),
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
        if not output_file:
            print("\n".join(results_strs))
            return
        with open(output_file, "w") as data:
            print("\n".join(results_strs), file=data)

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


if __name__ == "__main__":
    path = "/Users/yuchen/Books/Louis Rosenfeld/Xin Xi Jia Gou (10469)/Xin Xi Jia Gou - Louis Rosenfeld.pdf"
    ocr_api = "http://198.18.0.153:8865/predict/chinese_ocr_db_crnn_mobile"
    PdfHelper(path).format_annots(
        annot_image_dir="",
        ocr_api="http://198.18.0.153:8865/predict/chinese_ocr_db_crnn_mobile",
    )
