#!/usr/bin/env python3

import re
import os
import sys
from operator import itemgetter

import fitz

from picture_handler import Picture

TEXT = 0
LINE = 3
SQUARE = 4
HIGHLIGHT = 8
UNDERLINE = 9
SQUIGGLY = 10
STRIKEOUT = 11
INK = 15


class PdfHelper(object):
    def __init__(self, path):
        self.path = path
        self.doc = fitz.open(path)
        self.file_name = os.path.splitext(os.path.split(path)[1])[0]

    def export_toc(self, toc_path: str = ""):
        toc = self.doc.get_toc()
        toc_text = self.toc_text(toc)
        if not toc_path:
            print(toc_text)
            return
        try:
            with open(toc_path, "w") as data:
                print(toc_text, file=data)
        except IOError as ioerr:
            print("File Error: " + str(ioerr))

    def toc_text(self, toc: list):
        contents = [f"{(x[0] - 1) * 2 * ' '}- {x[1].strip()}#{x[2]}" for x in toc]
        return "\n".join(contents)

    def import_toc_from_file(self, toc_path):
        with open(toc_path, "r") as data:
            lines = data.readlines()
            toc = []
            page_gap = 0
            for line in lines:
                page_match = re.match(r"( *)[-+] (.+)#(\d+)", line)
                gap_match = re.match(r"# *\+(\d+)", line)
                first_page_match = re.match(r"#.+= *(\d+)", line)
                indent_step = 2
                if page_match:
                    current_indent = len(page_match.group(1))
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
                    title = page_match.group(2)
                    page = int(page_match.group(3)) + page_gap
                    toc.append([lvl, title, page])
                    last_indent = current_indent
                elif first_page_match:
                    page_gap += int(first_page_match.group(1)) - 1
                elif gap_match:
                    page_gap -= int(gap_match.group(1))
                else:
                    if line.strip():
                        raise ("Unsuppoted Format!")
            self.save_toc(toc)

    def save_toc(self, toc: list):
        self.doc.set_toc(toc)
        temp_file_path = self.path + "2"
        self.doc.save(temp_file_path, garbage=2)
        os.replace(temp_file_path, self.path)

    def _get_annots(
        self,
        annot_image_dir: str = "",
        ocr_api: str = "",
        zoom: int = 4,  # image zoom factor
        run_test: bool = False,  # get 3 annot and 3 pic at most
    ):
        if not self.doc.has_annots():
            return
        annot_list = []
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
                text = annot_handler.get_text(word_list, picture_path, ocr_api)
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
                zoom=zoom,
                run_test=run_test,
            )
        )
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
            toc_item = [line for line in text.split("\n") if is_toc_item(line)]
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
    def rect(self) -> fitz.Rect:
        if self.type_id == SQUARE:
            return self.annot.rect
        elif self.type_id in [INK, LINE]:
            page_width = self.page.mediabox.x1
            return fitz.Rect(0, self.annot.rect.y0, page_width, self.annot.rect.y1)
        elif self.type_id in [HIGHLIGHT, UNDERLINE, SQUIGGLY, STRIKEOUT]:
            points = self.annot.vertices  # TODO
            return fitz.Quad(points).rect
        else:
            return fitz.Rect()

    def save_pic(self, picture_path, zoom):
        if self.type_id in [SQUARE, INK, LINE]:
            export_picture_with_annot = (
                False if self.type_id == SQUARE else True
            )  # TODO maybe let user customize this?
            pix = self.page.get_pixmap(
                annots=export_picture_with_annot,
                clip=self.rect,
                matrix=fitz.Matrix(zoom, zoom),  # zoom image
            )
            pix.writePNG(picture_path)
            return 1
        return 0

    def get_text(self, wordlist, picture_path, ocr_api):
        text = ""
        if self.type_id in [SQUARE, INK, LINE, HIGHLIGHT, UNDERLINE, SQUIGGLY, STRIKEOUT]:
            text = extract_rectangle_text(self.rect, wordlist)
        if text:
            return text
        elif picture_path and ocr_api:
            return Picture(picture_path).get_ocr_result(ocr_api)
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


def extract_rectangle_text(rect: fitz.Rect, wordlist):
    words = [w for w in wordlist if fitz.Rect(w[:4]).intersects(rect)]
    sentence = " ".join(w[4] for w in words)
    return sentence.strip()


def is_toc_item(text: str):
    if re.match(r"^第 \d+ 章.+", text):
        return True
    return False

def pic2pdf(image_dir: str, pdf_path: str):
    doc = fitz.open()
    toc = []
    level = 0
    page = 0
    for root, subdirs, files in os.walk(image_dir):
        level += 1
        folder_toc_added = False
        for filepath in images_to_open(files):
            page += 1
            if not folder_toc_added:
                toc.append([level-1, root.replace(image_dir, "").replace("/", ""), page])
                folder_toc_added = True
            imgdoc = fitz.open(os.path.join(root, filepath))         # 打开图片
            pdfbytes = imgdoc.convertToPDF()    # 使用图片创建单页的 PDF
            imgpdf = fitz.open("pdf", pdfbytes)
            doc.insertPDF(imgpdf) # 将当前页插入文档
            file_name = os.path.splitext(filepath)[0]
            toc.append([level, file_name, page])
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    doc.set_toc(toc)
    doc.save(pdf_path, garbage=2)
    doc.close()

def images_to_open(file_names: list):
    return sorted([x for x in file_names if "png" in x or "jpg" in x])

if __name__ == "__main__":
    path = "/Users/yuchen/Books/Louis Rosenfeld/Xin Xi Jia Gou (10469)/Xin Xi Jia Gou - Louis Rosenfeld.pdf"
    ocr_api = "http://198.18.0.153:8865/predict/chinese_ocr_db_crnn_mobile"
    PdfHelper(path).format_annots(
        annot_image_dir="",
        ocr_api="http://198.18.0.153:8865/predict/chinese_ocr_db_crnn_mobile",
    )
