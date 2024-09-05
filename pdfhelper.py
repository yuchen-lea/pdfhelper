#!/usr/bin/env python3

"""
Some useful functions to process a PDF file.
"""
import argparse


from pdf_handler import PdfHelper
from picture_handler import help_text_for_ocr_language, help_text_for_ocr_service
from format_annots_template import (
    toc_item_default_format,
    annot_item_default_format,
)


def create_argparser():
    p = argparse.ArgumentParser(description=__doc__)
    subparsers = p.add_subparsers(dest="command", required=True)

    p.add_argument(
        "INFILE",
        help="PDF file to process",
        type=argparse.FileType("rb"),
    )
    p.add_argument("--version", "-v", action="version", version="2.5.0")

    # export-toc
    parser_export_toc = subparsers.add_parser(
        "export-toc", help="Export the TOC of the PDF."
    )
    parser_export_toc.add_argument(
        "TOC_PATH",
        nargs="?",
        default="",
        help="Path to save the TOC. Defaults to the folder where INFILE is located.",
    )

    # import-toc
    parser_import_toc = subparsers.add_parser(
        "import-toc", help="Import TOC from a file into the PDF."
    )
    parser_import_toc.add_argument(
        "TOC_PATH", nargs="?", default="", help="file or url to load the TOC from."
    )
    parser_import_toc.add_argument(
        "--target", help="Target PDF file or folder. Defaults to updating INFILE."
    )

    # delete-annot
    parser_delete_annot = subparsers.add_parser(
        "delete-annot", help="Delete annotations from the PDF."
    )
    parser_delete_annot.add_argument(
        "--target", help="Target PDF file or folder. Defaults to updating INFILE."
    )

    # export-xfdf-annot
    parser_export_xfdf_annot = subparsers.add_parser(
        "export-xfdf-annot", help="Export XFDF annotations of the PDF."
    )
    parser_export_xfdf_annot.add_argument(
        "XFDF_ANNOT_PATH",
        nargs="?",
        default="",
        help="Path to save the XFDF annotations.",
    )

    # import-xfdf-annot
    parser_import_xfdf_annot = subparsers.add_parser(
        "import-xfdf-annot", help="Import XFDF annotations of the PDF."
    )
    parser_import_xfdf_annot.add_argument(
        "XFDF_ANNOT_PATH",
        nargs="?",
        default="",
        help="Path to save the XFDF annotations.",
    )
    parser_import_xfdf_annot.add_argument(
        "--target", help="Target PDF file or folder. Defaults to updating INFILE."
    )

    # export-annot
    parser_export_annot = subparsers.add_parser(
        "export-annot", help="Export formatted text annotations of the PDF."
    )
    parser_export_annot.add_argument(
        "ANNOT_PATH",
        nargs="?",
        default="",
        help="File to save the exported annotations. When omitted, just print to stdout",
    )
    parser_export_annot.add_argument(
        "--annot-image-dir",
        help="Dir to save extracted pictures. When omitted, save to current working dir",
        default="",
    )
    parser_export_annot.add_argument("--ocr-service", help=help_text_for_ocr_service)
    parser_export_annot.add_argument("--ocr-language", help=help_text_for_ocr_language)
    parser_export_annot.add_argument(
        "--image-zoom", help="Image zoom factor", default=4
    )
    parser_export_annot.add_argument(
        "--with-toc",
        help="When set, the annotations are placed under corresponding outline items",
        action="store_true",
    )
    parser_export_annot.add_argument(
        "--toc-list-item-format",
        help="Customize the format of the table of contents (TOC) item using the mako template syntax. The default template is defined in `format_annots_template.toc_item_default_format`. The template supports the following variables: level, page, content, and pdf_path. For detailed usage, please refer to the Readme.",
        default=toc_item_default_format,
    )
    parser_export_annot.add_argument(
        "--annot-list-item-format",
        help="Customize the format of the annotation item using the mako template syntax. The default template is defined in `format_annots_template.annot_item_default_format`. The template supports the following variables: type, page, comment, text, annot_number, annot_id, height, color, pic_path, bib_key, and pdf_path. For detailed usage, please refer to the Readme.",
        default=annot_item_default_format,
    )
    parser_export_annot.add_argument(
        "--bib-path",
        nargs="+",
        help="List of bib path(s). When defined, try to find the key of INFILE within bib-path and store it in the bib_key variable.",
    )
    parser_export_annot.add_argument(
        "--creation-start",
        help="Specify the start of creation date range for exporting annotations in the format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.",
        default="",
    )

    parser_export_annot.add_argument(
        "--creation-end",
        help="Specify the end of creation date range for exporting annotations in the format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.",
        default="",
    )
    parser_export_annot.add_argument(
        "--run-test",
        help="Run a test instead of extracting full annotations. Useful for checking output format and image quality",
        action="store_true",
    )

    # export-info
    parser_export_info = subparsers.add_parser(
        "export-info", help="Export information of the PDF."
    )
    parser_export_info.add_argument(
        "INFO_PATH",
        nargs="?",
        default="",
        help="Path to save the PDF information.",
    )

    # import-info
    parser_import_info = subparsers.add_parser(
        "import-info", help="Import information of the PDF."
    )
    parser_import_info.add_argument(
        "INFO_PATH",
        nargs="?",
        default="",
        help="Path to load the PDF information from.",
    )
    parser_import_info.add_argument(
        "--target", help="Target PDF file or folder. Defaults to updating INFILE."
    )

    # page-label-to-number
    parser_page_label_to_number = subparsers.add_parser(
        "page-label-to-number", help="Convert page label to page number."
    )
    parser_page_label_to_number.add_argument(
        "PAGE_LABEL", help="Page label to convert."
    )

    # page-number-to-label
    parser_page_number_to_label = subparsers.add_parser(
        "page-number-to-label", help="Convert page number to page label."
    )
    parser_page_number_to_label.add_argument(
        "PAGE_NUMBER", help="Page number to convert."
    )

    return p


def main(args):
    path = args.INFILE.name
    pdf = PdfHelper(path)

    if args.command == "export-toc":
        pdf.export_toc(args.TOC_PATH)
    elif args.command == "import-toc":
        toc = args.TOC_PATH
        target = args.target
        if toc.startswith("http"):
            pdf.import_toc_from_url(url=toc, target_pdf=target)
        else:
            pdf.import_toc_from_file(toc_path=toc, target_pdf=target)
    elif args.command == "delete-annot":
        pdf.delete_annots(target_path=args.target)
    elif args.command == "export-xfdf-annot":
        pdf.export_xfdf_annots(annot_file=args.XFDF_ANNOT_PATH)
    elif args.command == "import-xfdf-annot":
        pdf.import_xfdf_annots(
            annot_file=args.XFDF_ANNOT_PATH, target_pdf=args.target, save_pdf=True
        )
    elif args.command == "export-annot":
        pdf.format_annots(
            output_file=args.ANNOT_PATH,
            annot_image_dir=args.annot_image_dir,
            ocr_service=args.ocr_service,
            ocr_language=args.ocr_language,
            zoom=args.image_zoom,
            with_toc=args.with_toc,
            toc_list_item_format=args.toc_list_item_format,
            annot_list_item_format=args.annot_list_item_format,
            bib_file_list=args.bib_path,
            creation_start_date=args.creation_start,
            creation_end_date=args.creation_end,
            run_test=args.run_test,
        )
    elif args.command == "export-info":
        pdf.export_info(info_file=args.INFO_PATH)
    elif args.command == "import-info":
        pdf.import_info(info_file=args.INFO_PATH, target_pdf=args.target, save_pdf=True)
    elif args.command == "page-label-to-number":
        pdf.get_page_number(label=args.PAGE_LABEL)
    elif args.command == "page-number-to-label":
        pdf.get_page_label(number=args.PAGE_NUMBER)


if __name__ == "__main__":
    parser = create_argparser()
    args = parser.parse_args()
    main(args)
