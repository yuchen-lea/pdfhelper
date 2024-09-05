#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import os
from operator import itemgetter
from typing import List
import xml.etree.ElementTree as ET

import fitz
from mako.template import Template

from picture_handler import Picture
from toc_handler import TocHandler
from format_annots_template import (
    toc_item_default_format,
    annot_item_default_format,
)

TEXT = 0
LINE = 3
SQUARE = 4
HIGHLIGHT = 8
UNDERLINE = 9
SQUIGGLY = 10
STRIKEOUT = 11
INK = 15

PYMUPDF_ANNOT_TYPE_MAPPING = {
    TEXT: "Text",
    LINE: "Line",
    SQUARE: "Square",
    HIGHLIGHT: "Highlight",
    UNDERLINE: "Underline",
    SQUIGGLY: "Squiggly",
    STRIKEOUT: "StrikeOut",
    INK: "Ink",
}

PYMUPDF_LINE_ENDING_STYLE_MAPPING = {
    1: "Square",
    2: "Circle",
    3: "Diamond",
    4: "OpenArrow",
    5: "ClosedArrow",
    6: "Butt",
    7: "ROpenArrow",
    8: "RClosedArrow",
    9: "Slash",
}

PYMUPDF_LINE_ENDING_STYLE_REVERSE_MAPPING = {
    v: k for k, v in PYMUPDF_LINE_ENDING_STYLE_MAPPING.items()
}


def parse_date(date_str):
    if date_str.startswith("D:"):
        # PDF timestamp: "D:20231023135429+08'00'" or 'D:20240101152246Z'
        try:
            return datetime.strptime(date_str[2:16], "%Y%m%d%H%M%S")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"Invalid date format: {date_str}")


def is_annot_type_name_in_list(annot_type_name: str, annot_type_list: list[int]):
    annot_type_name_list = [
        PYMUPDF_ANNOT_TYPE_MAPPING[x].lower() for x in annot_type_list
    ]
    return annot_type_name.lower() in annot_type_name_list


class PdfHelper(object):
    pymupdf_to_xfdf_mappings = [
        ("modDate", "date"),
        ("id", "name"),
        ("creationDate", "creationdate"),
    ]

    def __init__(self, path):
        self.path = path
        self.doc = fitz.open(path)
        self.file_name = os.path.splitext(os.path.split(path)[1])[0]
        self.file_dir = os.path.split(path)[0]

    def export_toc(self, toc_path: str = ""):
        toc = self.doc.get_toc()
        toc_path = self._get_target_file_path(target=toc_path, file_type="txt")
        TocHandler().save_pymupdf_toc_to_file(pymupdf_toc=toc, toc_path=toc_path)

    def import_toc_from_url(self, url: str, target_pdf: str = ""):
        toc_list = TocHandler().get_toc_list_from_chinapub(url=url)
        toc = TocHandler().convert_toc_list_to_pymupdf_toc(toc_list=toc_list)
        self.save_toc(toc=toc, target_pdf=target_pdf)

    def import_toc_from_file(self, toc_path: str, target_pdf: str = ""):
        with open(toc_path, "r") as data:
            lines = data.readlines()
            toc = TocHandler().convert_toc_list_to_pymupdf_toc(toc_list=lines)
            self.save_toc(toc=toc, target_pdf=target_pdf)

    def save_toc(self, toc: list, target_pdf: str = ""):
        self.doc.set_toc(toc)
        self.save_doc(target=target_pdf)

    def save_doc(self, target: str = ""):
        target_path = self._get_target_file_path(target=target, file_type="pdf")
        temp_file_path = target_path + "2"
        self.doc.save(temp_file_path, garbage=2)
        os.replace(temp_file_path, target_path)
        return target_path

    def _get_target_file_path(self, target, file_type):
        """If target is a folder, return {target}/{self.file_name}.{file_type};
        If target is empty, return {self.file_dir}/{self.file_name}.{file_type};
        else return {target}
        """
        if target and not os.path.splitext(target)[-1]:  # target is a folder
            if not os.path.exists(target):
                os.mkdir(target)
            target = os.path.join(target, f"{self.file_name}.{file_type}")
        return target or os.path.join(self.file_dir, f"{self.file_name}.{file_type}")

    def _get_annots(
        self,
        annot_image_dir: str = "",
        ocr_service: str = "",
        ocr_language: str = "",
        zoom: int = 4,  # image zoom factor
        creation_start_date: str = "",
        creation_end_date: str = "",
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
            word_list = page.get_text("words")  # list of words on page
            word_list.sort(key=lambda w: (w[3], w[0]))  # ascending y, then x
            for annot in page.annots():
                annot_date = parse_date(annot.info.get("creationDate"))
                if creation_start_date and annot_date < parse_date(creation_start_date):
                    continue
                if creation_end_date and annot_date > parse_date(creation_end_date):
                    continue
                annot_handler = AnnotationHandler(annot)
                page_num = page.number + 1
                annot_number = f"annot-{page_num}-{annot_num}"
                picture_path = os.path.join(
                    annot_image_dir,
                    f'{self.file_name.replace(" ", "-")}-{annot_number}.png',
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
                        "type": annot_handler.type_name,
                        "author": annot.info.get("title"),
                        "creation_date": annot_date.strftime("%Y-%m-%d"),
                        "creation_timestamp": annot_date,
                        "page": page_num,
                        "comment": annot_handler.content.strip(),
                        "text": text,
                        "annot_number": annot_number,
                        "annot_id": annot.info.get("id"),
                        "height": annot_handler.height,
                        "color": annot_handler.stroke_color,
                        "pic_path": os.path.abspath(picture_path)
                        if picture_path
                        else "",
                    }
                )
                annot_num += 1
                annot_count += 1
        return annot_list

    def delete_annots(self, target_path: str = ""):
        if not self.doc.has_annots():
            return
        for page in self.doc.pages():
            for annot in page.annots():
                page.delete_annot(annot)
        self.save_doc(target=target_path)

    def format_annots(
        self,
        annot_image_dir: str = "",
        ocr_service: str = "",
        ocr_language: str = "",
        output_file: str = "",
        zoom: int = 4,
        with_toc: bool = True,
        creation_start_date: str = "",
        creation_end_date: str = "",
        toc_list_item_format: str = toc_item_default_format,
        annot_list_item_format: str = annot_item_default_format,
        bib_file_list: List = [],
        run_test: bool = False,
    ):
        results_items = []
        results_strs = []
        level = 0
        pdf_path = os.path.abspath(self.path)
        bib_key = (
            find_unique_bib_key(bib_path_list=bib_file_list, val=pdf_path)
            if bib_file_list
            else ""
        )
        if with_toc:
            results_items.extend(
                self.toc_dict
            )  # extend toc before annot to ensure that annot item is after toc item after sorting by page
        annots = self._get_annots(
            annot_image_dir=annot_image_dir,
            ocr_service=ocr_service,
            ocr_language=ocr_language,
            zoom=zoom,
            creation_start_date=creation_start_date,
            creation_end_date=creation_end_date,
            run_test=run_test,
        )
        results_items.extend(annots)
        results_items = sorted(results_items, key=itemgetter("page"))
        for item in results_items:
            context = item
            context["pdf_path"] = pdf_path
            context["bib_key"] = bib_key
            if item.get("type") == "toc":
                level = item.get("level")
                toc_item_template = Template(toc_list_item_format)
                string = toc_item_template.render(**context)
            else:  # note
                annot_item_template = Template(annot_list_item_format)
                context["level"] = level
                string = annot_item_template.render(**context)
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
        self.save_toc(toc)

    @property
    def toc_dict(self):
        toc = self.doc.get_toc()
        return [
            {"type": "toc", "level": x[0], "content": x[1].strip(), "page": x[2]}
            for x in toc
        ]

    def export_info(self, info_file: str = ""):
        root = ET.Element("root")
        ET.SubElement(root, "f", href=self.path)
        filtered_metadata = {
            k: v for k, v in self.doc.metadata.items() if v not in [None, ""]
        }
        ET.SubElement(root, "metadata", **filtered_metadata)
        toc_tag = ET.SubElement(root, "toc")
        for item in self.doc.get_toc():
            item_attrs = {"lvl": str(item[0]), "title": item[1], "page": str(item[2])}
            ET.SubElement(toc_tag, "item", **item_attrs)
        page_label_tag = ET.SubElement(root, "labels")
        for item in self.doc.get_page_labels():
            ET.SubElement(
                page_label_tag, "item", **{k: str(v) for k, v in item.items()}
            )
        info_file = self._get_target_file_path(target=info_file, file_type="xml")
        tree = ET.ElementTree(root)
        tree.write(info_file, encoding="utf-8", xml_declaration=True)
        print(info_file)

    def export_xfdf_annots(self, annot_file: str = ""):
        """
        Export annotations in XFDF format.

        Args:
            annot_file (str): Path to the output XFDF file.
        """
        if not self.doc.has_annots():
            return

        root = ET.Element(
            "xfdf", xmlns="http://ns.adobe.com/xfdf/", attrib={"xml:space": "preserve"}
        )
        annots = ET.SubElement(root, "annots")

        for page in self.doc.pages():
            for annot in page.annots():
                annot_h = AnnotationHandler(annot)
                annot_tag = ET.SubElement(annots, annot_h.type_name.lower())

                # Set common attributes
                annot_attrs = annot.info
                for old_key, new_key in self.pymupdf_to_xfdf_mappings:
                    if old_key in annot_attrs:
                        annot_attrs[new_key] = annot_attrs[old_key]
                        del annot_attrs[old_key]
                annot_attrs["page"] = str(annot_h.page.number)
                annot_attrs["rect"] = annot_h.xfdf_rect_string()
                annot_attrs["color"] = annot_h.stroke_color
                if annot_h.fill_color:
                    annot_attrs["interior-color"] = annot_h.fill_color
                # TODO annot_attrs["flags"] = str(annot.flags)
                annot_attrs["flags"] = "print"

                # Set border attributes
                border_width = annot.border.get("width")
                if border_width and border_width != -1:
                    annot_attrs["width"] = str(border_width)
                if annot.border.get("dashes"):
                    annot_attrs["style"] = "dash"
                    annot_attrs["dashes"] = ",".join(
                        [str(x) for x in annot.border.get("dashes")]
                    )
                elif annot.border.get("clouds") and annot.border.get("clouds") > 0:
                    annot_attrs["style"] = "cloudy"
                    annot_attrs["intensity"] = str(annot.border.get("clouds"))
                    # TODO if fringe not set，imported by xchange will be invisible. Haven't found correspoing pymupdf atrributes.
                    annot_attrs["fringe"] = "9,9,9,9"

                # Add child nodes
                if annot_h.content:
                    content_tag = ET.SubElement(annot_tag, "contents")
                    content_tag.text = annot_h.content

                if annot.has_popup:
                    popup_tag = ET.SubElement(annot_tag, "popup")
                    popup_attrs = {
                        "open": "yes" if annot.is_open else "no",
                        "page": str(annot_h.page.number),
                        "rect": annot_h.xfdf_rect_string(type="popup"),
                    }
                    popup_tag.attrib = popup_attrs

                # Set type-specific attributes
                if annot_h.type_name_in_list([TEXT]):
                    annot_attrs["icon"] = annot.info.get("name") or "Note"
                elif annot_h.type_name_in_list([LINE]):
                    annot_attrs["start"], annot_attrs["end"] = annot_h.line_end_points()
                    line_head_type = annot.line_ends[0]
                    line_tail_type = annot.line_ends[1]
                    if line_head_type:
                        annot_attrs["head"] = PYMUPDF_LINE_ENDING_STYLE_MAPPING[
                            line_head_type
                        ]
                    if line_tail_type:
                        annot_attrs["tail"] = PYMUPDF_LINE_ENDING_STYLE_MAPPING[
                            line_tail_type
                        ]
                elif annot_h.type_name_in_list([INK]):
                    inklist = ET.SubElement(annot_tag, "inklist")
                    gesture_string_list = annot_h.xfdf_ink_gesture_string_list()
                    for gesture_string in gesture_string_list:
                        gesture = ET.SubElement(inklist, "gesture")
                        gesture.text = gesture_string
                elif annot_h.type_name_in_list(
                    [HIGHLIGHT, UNDERLINE, STRIKEOUT, SQUIGGLY]
                ):
                    annot_attrs["coords"] = annot_h.xfdf_coords_string()
                annot_tag.attrib = annot_attrs

        annot_file = self._get_target_file_path(target=annot_file, file_type="xfdf")
        tree = ET.ElementTree(root)
        tree.write(annot_file, encoding="utf-8", xml_declaration=True)

    def import_info(
        self, info_file: str = "", target_pdf: str = "", save_pdf: bool = False
    ):
        if os.path.isdir(info_file):
            info_file = os.path.join(info_file, f"{self.file_name}.xml")
        if not os.path.exists(info_file):
            raise Exception("No info file Found!")
        tree = ET.parse(info_file)
        root = tree.getroot()
        metadata_tag = root.find("metadata")
        if metadata_tag is not None:
            metadata_dict = metadata_tag.attrib
            self.doc.set_metadata(metadata_dict)

        toc = []
        toc_tag = root.find("toc")
        if toc_tag is not None:
            for item in toc_tag.findall("item"):
                toc.append(
                    [
                        int(item.attrib.get("lvl", 0)),
                        item.attrib.get("title", ""),
                        int(item.attrib.get("page", 0)),
                    ]
                )
            self.doc.set_toc(toc)

        labels = []
        labels_tag = root.find("labels")
        if labels_tag is not None:
            for item in labels_tag.findall("item"):
                item_dict = item.attrib
                item_dict.update(
                    {
                        k: int(v)
                        for k, v in item_dict.items()
                        if k in ["firstpagenum", "startpage"]
                    }
                )
                labels.append(item_dict)
            self.doc.set_page_labels(labels)
        if save_pdf:
            pdf_path = self.save_doc(target=target_pdf)
            print(pdf_path)

    def import_xfdf_annots(
        self, annot_file: str = "", target_pdf: str = "", save_pdf: bool = False
    ):
        if os.path.isdir(annot_file):
            annot_file = os.path.join(annot_file, f"{self.file_name}.xfdf")
        if not os.path.exists(annot_file):
            raise Exception("No XFDF Annot Found!")
        tree = ET.parse(annot_file)
        root = tree.getroot()
        namespace = "{http://ns.adobe.com/xfdf/}"
        annots = root.find(f"{namespace}annots")
        if not annots:
            raise Exception("Wrong Format")
        for annot_tag in annots:
            annot_tag_h = AnnotTagHandler(
                annot_tag=annot_tag, namespace=namespace, pdf_handler=self
            )
            page = annot_tag_h.page
            annot_tag_name = annot_tag_h.name

            if is_annot_type_name_in_list(annot_tag_name, [HIGHLIGHT]):
                annot = page.add_highlight_annot(quads=annot_tag_h.coords)
            elif is_annot_type_name_in_list(annot_tag_name, [UNDERLINE]):
                annot = page.add_underline_annot(quads=annot_tag_h.coords)
            elif is_annot_type_name_in_list(annot_tag_name, [STRIKEOUT]):
                annot = page.add_strikeout_annot(quads=annot_tag_h.coords)
            elif is_annot_type_name_in_list(annot_tag_name, [SQUIGGLY]):
                annot = page.add_squiggly_annot(quads=annot_tag_h.coords)
            elif is_annot_type_name_in_list(annot_tag_name, [SQUARE]):
                annot = page.add_rect_annot(annot_tag_h.rect())
            elif is_annot_type_name_in_list(annot_tag_name, [TEXT]):
                annot = page.add_text_annot(
                    point=annot_tag_h.rect().tl,
                    text=annot_tag_h.contents_text,
                    icon=annot_tag.attrib.get("icon"),
                )
            elif is_annot_type_name_in_list(annot_tag_name, [INK]):
                annot = page.add_ink_annot(annot_tag_h.ink_list)
            elif is_annot_type_name_in_list(annot_tag_name, [LINE]):
                annot = page.add_line_annot(
                    annot_tag_h.get_line_ends_point(type="start"),
                    annot_tag_h.get_line_ends_point(type="end"),
                )
                annot.set_line_ends(
                    annot_tag_h.get_line_ends_type(type="head"),
                    annot_tag_h.get_line_ends_type(type="tail"),
                )
            else:
                raise Exception("Unsupported")

            if not is_annot_type_name_in_list(
                annot_tag_name, [HIGHLIGHT, STRIKEOUT, UNDERLINE, SQUIGGLY, TEXT]
            ):
                annot.set_border(border=annot_tag_h.border_dict)
            annot.set_colors(colors=annot_tag_h.color_dict)
            annot.set_info(info=annot_tag_h.attrs)
            if annot_tag_h.has_popup():
                annot.set_popup(annot_tag_h.rect(type="popup"))
                annot.set_open(annot_tag_h.popup_open)
            annot.update()

        if save_pdf:
            pdf_path = self.save_doc(target=target_pdf)
            print(pdf_path)

    def get_page_number(self, label):
        page_numbers = self.doc.get_page_numbers(label=label)
        if len(page_numbers):
            page_number = page_numbers[0] + 1
        else:
            page_number = label
        print(page_number)
        return page_number

    def get_page_label(self, number):
        page_index = int(number) - 1
        page_label = self.doc.load_page(page_index).get_label() or str(number)
        print(page_label)
        return page_label


class AnnotTagHandler(object):
    def __init__(self, annot_tag, namespace, pdf_handler):
        self.annot_tag = annot_tag
        self.namespace = namespace
        self.attrib = self.annot_tag.attrib
        self.page = pdf_handler.doc.load_page(int(self.attrib.get("page")))
        self.pymupdf_to_xfdf_mappings = pdf_handler.pymupdf_to_xfdf_mappings
        self.page_height = self.page.rect.height

    @property
    def name(self):
        return self.annot_tag.tag.replace(self.namespace, "")

    @property
    def attrs(self):
        attrs = self.attrib
        if self.contents_text:
            attrs["content"] = self.contents_text
        for new_key, old_key in self.pymupdf_to_xfdf_mappings:
            if old_key in attrs:
                attrs[new_key] = attrs[old_key]
                del attrs[old_key]
        return attrs

    def rect(self, type: str = "default"):
        rect_string = (
            self.popup.attrib.get("rect")
            if type == "popup"
            else self.attrib.get("rect")
        )
        if rect_string:
            rect = rect_string.split(",")
            r = fitz.Rect(
                (
                    float(rect[0]),
                    self.page_height - float(rect[3]),
                    float(rect[2]),
                    self.page_height - float(rect[1]),
                )
            )
            return r
        return None

    @property
    def coords(self):
        coords_str = self.attrib.get("coords")
        if coords_str:
            coords_list = list(map(float, coords_str.split(",")))
            vertices = []
            for i in range(0, len(coords_list), 2):
                x = coords_list[i]
                y = self.page_height - coords_list[i + 1]
                vertices.append((x, y))

            quad_count = int(len(vertices) / 4)
            return [
                fitz.Quad(vertices[i * 4 : i * 4 + 4]).rect for i in range(quad_count)
            ]
        return None

    @property
    def contents_text(self):
        if self.attrib.get("content"):
            return self.attrib.get("content")
        contents = self.annot_tag.find(f"{self.namespace}contents")
        if isinstance(contents, ET.Element):
            return contents.text
        contents_richtext = self.annot_tag.find(f"{self.namespace}contents-richtext")
        if isinstance(contents_richtext, ET.Element):
            text_parts = [
                part for part in contents_richtext.itertext() if part.strip() != ""
            ]
            return "\n".join(text_parts).strip()
        return ""

    @property
    def ink_list(self):
        gestures = self.annot_tag.find(f"{self.namespace}inklist").findall(
            f"{self.namespace}gesture"
        )
        ink_list = []
        for gesture in gestures:
            points = gesture.text.split(";")
            coords = [
                (float(p.split(",")[0]), self.page_height - float(p.split(",")[1]))
                for p in points
            ]
            ink_list.append(coords)
        return ink_list

    def get_line_ends_point(self, type):
        x, y = self.attrib.get(type).split(",")
        return fitz.Point((x, self.page_height - float(y)))

    def get_line_ends_type(self, type):
        return PYMUPDF_LINE_ENDING_STYLE_REVERSE_MAPPING.get(
            self.attrib.get(type, ""), 0
        )

    @property
    def border_dict(self):
        border = {}
        width = self.attrib.get("width")
        if width:
            border["width"] = float(width)
        style = self.attrib.get("style")
        if style == "dash":
            dashes = self.attrib.get("dashes")
            if dashes:
                border["dashes"] = [int(x) for x in dashes.split(",")]
        elif style == "cloudy":
            intensity = self.attrib.get("intensity")
            if intensity:
                border["clouds"] = int(intensity)
        return border

    @property
    def color_dict(self):
        color = {}
        stroke = self.attrib.get("color")
        if stroke:
            color["stroke"] = RGB(stroke).to_float()
        fill = self.attrib.get("interior-color")
        if fill:
            color["fill"] = RGB(fill).to_float()
        return color

    def has_popup(self):
        return isinstance(self.popup, ET.Element)

    @property
    def popup(self):
        return self.annot_tag.find(f"{self.namespace}popup")

    @property
    def popup_open(self):
        open = self.popup.attrib.get("open")
        if open:
            return True if open == "yes" else False
        return False


class AnnotationHandler(object):
    def __init__(self, annot):
        self.annot = annot
        self.page = annot.parent
        self.pdf_path = self.page.parent.name
        self.page_height = self.page.rect.height

    @property
    def stroke_color(self):
        return RGB(self.annot.colors.get("stroke")).to_hex()

    @property
    def fill_color(self):
        fill_color = self.annot.colors.get("fill")
        if fill_color:
            return RGB(fill_color).to_hex()
        else:
            return ""

    @property
    def height(self):
        return round(self.annot.rect.y0 / self.page_height, 2)

    @property
    def type_id(self):
        return self.annot.type[0]

    @property
    def type_name(self):
        return self.annot.type[1]

    def type_name_in_list(self, annot_type_list: list[int]):
        return is_annot_type_name_in_list(self.type_name, annot_type_list)

    @property
    def content(self):
        return self.annot.info.get("content", "")

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

    def xfdf_rect_string(self, type: str = "default"):
        rect = self.annot.popup_rect if type == "popup" else self.annot.rect
        return (
            f"{rect.x0},{self.page_height-rect.y1},{rect.x1},{self.page_height-rect.y0}"
        )

    def xfdf_coords_string(self):
        result = []
        vertices = self.annot.vertices
        for x, y in vertices:
            result.append(x)
            result.append(self.page_height - y)
        return ",".join(map(str, result))

    def line_end_points(self):
        result = []
        vertices = self.annot.vertices
        for x, y in vertices:
            result.append((x, self.page_height - y))
        return [f"{x},{y}" for x, y in result]

    def xfdf_ink_gesture_string_list(self) -> list[str]:
        result = []
        vertices = self.annot.vertices
        for sublist in vertices:
            gesture_points = []
            for x, y in sublist:
                gesture_points.append(f"{x},{self.page_height - y}")
            gesture_text = ";".join(gesture_points)
            result.append(gesture_text)
        return result

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
            pix.save(picture_path)
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
            text = self._extract_rectangle_list_text(wordlist)
        if text:
            return text
        elif picture_path and ocr_service:
            return Picture(picture_path).get_ocr_result(
                ocr_service=ocr_service, language=ocr_language
            )
        return ""

    def _extract_rectangle_list_text(self, wordlist):
        sentences = []
        for rect in self.rect_list:
            words = [w for w in wordlist if fitz.Rect(w[:4]).intersects(rect)]
            sentence = " ".join(w[4] for w in words).strip()
            sentences.append(sentence)
        return " ".join(sentences)


class RGB(object):
    def __init__(self, value):
        self.value = value

    def to_hex(self):
        if len(self.value) == 3 and type(self.value[0]) == float:
            return "#" + "".join([self._float2hex(x) for x in self.value])

    def to_float(self):
        if type(self.value) == str:
            value = self.value.replace("#", "")
            rgb = (value[:2], value[2:4], value[-2:])
            return [int(f"0x{x}", 16) / 255 for x in rgb]

    def _float2hex(self, x: float):
        return self._int2hex(int(255 * x))

    def _int2hex(self, x: int):
        return hex(x).replace("x", "0")[-2:]


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


def find_unique_bib_key(bib_path_list, val):
    keys = []
    for bib_path in bib_path_list:
        with open(bib_path, "r", encoding="utf-8") as bib_file:
            bib_content = bib_file.read()

        for entry in bib_content.split("\n\n"):
            if val in entry:
                key = entry.split("{")[1].split(",")[0].strip()
                keys.append(key)
        if len(keys) == 1:
            return keys[0]
    return ""


def images_to_open(file_names: list):
    return sorted([x for x in file_names if "png" in x or "jpg" in x])


if __name__ == "__main__":
    path = ""
    ocr_api = "http://198.18.0.153:8865/predict/chinese_ocr_db_crnn_mobile"
    PdfHelper(path).import_toc_from_url("http://product.china-pub.com/8081279")
