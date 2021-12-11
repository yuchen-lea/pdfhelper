#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import re
import os
from operator import itemgetter
from typing import List

import fitz

from picture_handler import Picture
from toc_handler import TocHandler

TEXT = 0
LINE = 3
SQUARE = 4
HIGHLIGHT = 8
UNDERLINE = 9
SQUIGGLY = 10
STRIKEOUT = 11
INK = 15

PYMUPDF_ANNOT_MAPPING = {
    0: "Text",
    4: "Square",
    6: "Polygon",
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

    def export_toc(self, toc_path: str = ""):
        toc = self.doc.get_toc()
        TocHandler().save_pymupdf_toc_to_file(pymupdf_toc=toc, toc_path=toc_path)

    def import_toc_from_url(self, url: str):
        toc_list = TocHandler().get_toc_list_from_chinapub(url=url)
        toc = TocHandler().convert_toc_list_to_pymupdf_toc(toc_list=toc_list)
        self.save_toc(toc)

    def import_toc_from_file(self, toc_path):
        with open(toc_path, "r") as data:
            lines = data.readlines()
            toc = TocHandler().convert_toc_list_to_pymupdf_toc(toc_list=lines)
            self.save_toc(toc)

    def save_toc(self, toc: list):
        self.doc.set_toc(toc)
        temp_file_path = self.path + "2"
        self.doc.save(temp_file_path, garbage=2)
        os.replace(temp_file_path, self.path)

    def _get_annots(
        self,
        annot_image_dir: str = "",
        ocr_service: str = "",
        ocr_language: str = "",
        zoom: int = 4,  # image zoom factor
        run_test: bool = False,  # get 3 annot and 3 pic at most
    ):
        annot_list = []
        if not self.doc.has_annots():
            return annot_list
        annot_count = 0
        extracted_pic_count = 0
        for page in self.doc.pages():
            if run_test and annot_count > 2 and extracted_pic_count > 2:
                break
            annot_num = 0
            word_list = page.getText("words")  # list of words on page
            word_list.sort(key=lambda w: (w[3], w[0]))  # ascending y, then x
            for annot in page.annots():
                annot_handler = AnnotationHandler(annot)
                page_num = page.number + 1
                annot_id = f"annot-{page_num}-{annot_num}"
                picture_path = os.path.join(
                    annot_image_dir,
                    f'{self.file_name.replace(" ", "-")}-{annot_id}.png',
                )
                if annot_handler.save_pic(picture_path, zoom):
                    extracted_pic_count += 1
                else:
                    picture_path = ""
                text = annot_handler.get_text(
                    wordlist=word_list,
                    picture_path=picture_path,
                    ocr_service=ocr_service,
                    ocr_language=ocr_language,
                )
                annot_list.append(
                    {
                        "type": annot_handler.type_id,
                        "page": page_num,
                        "content": annot_handler.content,
                        "text": text,
                        "id": annot_id,
                        "height": annot_handler.height,
                        "color": annot_handler.color,
                        "pic": picture_path,
                    }
                )
                annot_num += 1
                annot_count += 1
        return annot_list

    def format_annots(
        self,
        annot_image_dir: str = "",
        ocr_service: str = "",
        ocr_language: str = "",
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
        annots = self._get_annots(
            annot_image_dir=annot_image_dir,
            ocr_service=ocr_service,
            ocr_language=ocr_language,
            zoom=zoom,
            run_test=run_test,
        )
        if annots:
            results_items.extend(annots)
        results_items = sorted(results_items, key=itemgetter("page"))
        for item in results_items:
            page = item.get("page")
            content = item.get("content").strip()
            item_type = item.get("type")
            if item_type == "toc":
                level = item.get("depth")
                string = ("{indent}- " + toc_list_item_format).format(
                    indent=(level - 1) * 2 * " ",
                    checkbox="[ ]",
                    title=content,
                    link="[[{}:{}::{}][{}]]".format(
                        "pdf",
                        self.path,
                        page,
                        content,
                    ),
                )
            else:  # note
                pic_path = item.get("pic")
                annot_id = item.get("id")
                text = item.get("text")
                string = ("{indent}- " + annot_list_item_format).format(
                    indent=(level) * 2 * " ",
                    checkbox="[ ]",
                    color=item.get("color"),
                    annot_id=annot_id,
                    link="[[{}:{}::{}++{:.2f}][{}]]".format(
                        "pdf",
                        self.path,
                        page,
                        item.get("height"),
                        annot_id,
                    ),
                    content=f"[[file:{pic_path}]]" if pic_path else content,
                )
                if text:  # add multiline text in quote block
                    string += "\n" + (level + 1) * 2 * " " + "#+begin_quote\n"
                    string += text
                    string += "\n" + (level + 1) * 2 * " " + "#+end_quote"
            results_strs.append(string)
        if not output_file:
            print("\n".join(results_strs))
            return
        with open(output_file, "w") as data:
            print("\n".join(results_strs), file=data)

    def extract_toc_from_text(self):
        toc = []
        for num in range(self.doc.page_count):
            page = self.doc.load_page(num)
            text = page.get_text()
            toc_item = [
                line for line in text.split("\n") if TocHandler().is_toc_item(line)
            ]
            if len(toc_item) < 5:
                toc.extend([[1, x, num + 1] for x in toc_item])
        print(self.toc_text(toc))
        self.save_toc(toc)

    @property
    def toc_dict(self):
        toc = self.doc.get_toc()
        return [
            {"type": "toc", "depth": x[0], "content": x[1], "page": x[2]} for x in toc
        ]


class AnnotationHandler(object):
    def __init__(self, annot):
        self.annot = annot
        self.page = annot.parent
        self.pdf_path = self.page.parent.name

    @property
    def color(self):
        return RGB(self.annot.colors.get("stroke")).to_hex()

    @property
    def height(self):
        return self.annot.rect.y0 / self.page.rect.y1

    @property
    def type_id(self):
        return self.annot.type[0]

    @property
    def type_name(self):
        return self.annot.type[1]

    @property
    def content(self):
        return self.annot.info.get("content")

    @property
    def rect_list(self) -> List[fitz.Rect]:
        if self.type_id == SQUARE:
            return [self.annot.rect]
        elif self.type_id in [INK, LINE]:
            page_width = self.page.mediabox.x1
            return [fitz.Rect(0, self.annot.rect.y0, page_width, self.annot.rect.y1)]
        elif self.type_id in [HIGHLIGHT, UNDERLINE, SQUIGGLY, STRIKEOUT]:
            points = self.annot.vertices
            quad_count = int(len(points) / 4)
            return [
                fitz.Quad(points[i * 4 : i * 4 + 4]).rect for i in range(quad_count)
            ]
        else:
            return [fitz.Rect()]

    def save_pic(self, picture_path, zoom):
        if self.type_id in [SQUARE, INK, LINE]:
            export_picture_with_annot = (
                False if self.type_id == SQUARE else True
            )  # TODO maybe let user customize this?
            pix = self.page.get_pixmap(
                annots=export_picture_with_annot,
                clip=self.rect_list[0],
                matrix=fitz.Matrix(zoom, zoom),  # zoom image
            )
            pix.writePNG(picture_path)
            return 1
        return 0

    def get_text(self, wordlist, picture_path, ocr_service, ocr_language):
        text = ""
        if self.type_id in [
            SQUARE,
            INK,
            LINE,
            HIGHLIGHT,
            UNDERLINE,
            SQUIGGLY,
            STRIKEOUT,
        ]:
            text = extract_rectangle_list_text(self.rect_list, wordlist)
        if text:
            return text
        elif picture_path and ocr_service:
            return Picture(picture_path).get_ocr_result(
                ocr_service=ocr_service, language=ocr_language
            )
        return ""


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


def extract_rectangle_list_text(rect_list: List[fitz.Rect], wordlist):
    sentences = []
    for rect in rect_list:
        sentence = extract_rectangle_text(rect, wordlist)
        sentences.append(sentence)
    return " ".join(sentences)


def extract_rectangle_text(rect: fitz.Rect, wordlist):
    words = [w for w in wordlist if fitz.Rect(w[:4]).intersects(rect)]
    sentence = " ".join(w[4] for w in words)
    return sentence.strip()


def pic2pdf(image_dir: str, pdf_path: str):
    doc = fitz.open()
    toc = []
    page = 0
    initial_depth = image_dir.count(os.sep)
    for root, sub_dirs, files in os.walk(image_dir):
        sub_dirs.sort()
        folder_toc_added = False
        depth = root.count(os.sep) - initial_depth
        for file in images_to_open(files):
            page += 1
            if not folder_toc_added:
                toc.append([depth, os.path.split(root)[1], page])
                folder_toc_added = True
            img_doc = fitz.open(os.path.join(root, file))
            img_pdf = fitz.open("pdf", img_doc.convertToPDF())
            doc.insertPDF(img_pdf)
            file_name = os.path.splitext(file)[0]
            toc.append([depth + 1, file_name, page])
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    doc.set_toc(toc)
    doc.save(pdf_path, garbage=2)
    doc.close()


def images_to_open(file_names: list):
    return sorted([x for x in file_names if "png" in x or "jpg" in x])


if __name__ == "__main__":
    path = ""
    ocr_api = "http://198.18.0.153:8865/predict/chinese_ocr_db_crnn_mobile"
    PdfHelper(path).import_toc_url("http://product.china-pub.com/8081279")
