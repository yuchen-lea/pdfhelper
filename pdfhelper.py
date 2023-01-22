#!/usr/bin/env python3

"""
Some useful functions to process a PDF file.
"""
import argparse
import sys


from pdf_handler import PdfHelper
from picture_handler import help_text_for_ocr_language, help_text_for_ocr_service


def create_argparser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "file",
        metavar="INFILE",
        help="PDF file to process",
        type=argparse.FileType("rb"),
    )
    p.add_argument(
        "--target",
        help="TARGET could be a folder or a PDF file. If TARGET is ommited, update INFILE.",
    )
    p.add_argument("--version", "-v", action="version", version="1.4.0")

    group_toc = p.add_argument_group("Process TOC", "PDF TOC <-> Human readable List")
    group_toc.add_argument(
        "--import-toc",
        "-ti",
        help="load TOC_PATH into INFILE and update the pdf file.",
        action="store_true",
    )

    group_toc.add_argument(
        "--import-toc-url",
        "-til",
        help="load TOC form url into INFILE and update the pdf file.",
    )

    group_toc.add_argument(
        "--export-toc",
        "-te",
        help="export the toc of INFILE to TOC_PATH. If TOC_PATH is not set, just print to stdout",
        action="store_true",
    )
    group_toc.add_argument(
        "--toc-path",
        help="toc file path",
    )

    group_pdf = p.add_argument_group("Process PDF")
    group_pdf.add_argument(
        "--delete-annot",
        help="delete annotations of INPUT and update the pdf file. If TARGET is set, save to TARGET.",
        action="store_true",
    )

    group_annot = p.add_argument_group("Export Annots")
    group_annot.add_argument(
        "--export-annot", "-ae", help="export annotations of INPUT", action="store_true"
    )
    group_annot.add_argument(
        "--annot-image-dir",
        help="dir to save extracted pictures. when omitted, save to current working dir",
        default="",
    )
    group_annot.add_argument(
        "--ocr-service",
        help=help_text_for_ocr_service,
    )
    group_annot.add_argument(
        "--ocr-language",
        help=help_text_for_ocr_language,
    )
    group_annot.add_argument(
        "--annot-path",
        help="file to save the exported annotations. when omitted, just print to stdout",
    )
    group_annot.add_argument(
        "--image-zoom",
        help="image zoom factor",
        default=4,
    )
    group_annot.add_argument(
        "--with-toc",
        help="when set, the annotations are placed under corresponding outline items",
        action="store_true",
    )
    group_annot.add_argument(
        "--toc-list-item-format",
        help="customize the format of toc item when WITH_TOC, default is '{checkbox} {link}'. available fields: checkbox, link, title ",
        default="{checkbox} {link}",
    )
    group_annot.add_argument(
        "--annot-list-item-format",
        help="customize the format of annot item, default is '{checkbox} {color} {link} {content}'. available fields: checkbox, color, annot_id, link, content",
        default="{checkbox} {color} {link} {content}",
    )
    group_annot.add_argument(
        "--run-test",
        help="run a test instead of extracting full annotations. useful for checking output format and image quality",
        action="store_true",
    )
    return p


def main(args):
    path = args.file.name
    toc_path = args.toc_path
    target = args.target
    pdf = PdfHelper(path)
    if args.export_toc:
        pdf.export_toc(toc_path)
    if args.import_toc:
        pdf.import_toc_from_file(toc_path)
    if args.import_toc_url:
        pdf.import_toc_from_url(args.import_toc_url)
    if args.delete_annot:
        pdf.delete_annots(target_path=target)
    if args.export_annot:
        pdf.format_annots(
            annot_image_dir=args.annot_image_dir,
            ocr_service=args.ocr_service,
            ocr_language=args.ocr_language,
            output_file=args.annot_path,
            zoom=args.image_zoom,
            with_toc=args.with_toc,
            toc_list_item_format=args.toc_list_item_format,
            annot_list_item_format=args.annot_list_item_format,
            run_test=args.run_test,
        )


if __name__ == "__main__":
    parser = create_argparser()
    # args = parser.parse_args(
    #     [
    #         "/Users/yuchen/Books/Wei Zhi/MyMathG2 (12506)/MyMathG2 - Wei Zhi.pdf",
    #         "-ti",
    #         "--toc-path",
    #         "/var/folders/1_/xvxlsyn97mz30w_mlf08q7n00000gp/T/toc.org",
    #     ]
    # )
    args = parser.parse_args()
    main(args)
