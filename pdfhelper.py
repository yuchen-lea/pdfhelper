#!/usr/bin/env python3

"""
Some useful functions to process a PDF file.
"""
import argparse

from pdf_handler import PdfHelper


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
