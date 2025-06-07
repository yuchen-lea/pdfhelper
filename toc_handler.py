#!/usr/bin/env python3
import argparse

import re


class TocHandler:
    def save_pymupdf_toc_to_file(
        self, pymupdf_toc: list, page_labels: list, toc_path: str = ""
    ):
        toc_text = self.convert_pymupdf_toc_to_toc_list(pymupdf_toc=pymupdf_toc)
        labels_text = self.convert_page_labels_to_text(page_labels=page_labels)
        full_text = f"{labels_text}\n{toc_text}"
        self.save_toc_text_to_file(toc_text=full_text, toc_path=toc_path)

    def convert_pymupdf_toc_to_toc_list(self, pymupdf_toc: list):
        contents = [
            f"{(x[0] - 1) * 2 * ' '}- {x[1].strip()}#{x[2]}" for x in pymupdf_toc
        ]
        toc_text = "\n".join(contents)
        return toc_text

    def convert_page_labels_to_text(self, page_labels: list):
        """
        Converts a list of page label dictionaries to formatted label strings.

        Each page label contains metadata about how the page numbering should be
        displayed. This function generates a corresponding string for each page label
        in a specific format.

        Args:
            page_labels (list): A list of dictionaries from PyMuPDF. where each dictionary contains
                                the following keys:
                                - "prefix" (str, optional): A prefix to append before the page number.
                                - "startpage" (int): the first page number (0-based) to apply the
                                                     label rule.
                                - "firstpagenum" (int): start numbering with this value..
                                - "style" (str): The style of numbering, which can be one of:
                                                 "A" (uppercase letters),
                                                 "a" (lowercase letters),
                                                 "R" (uppercase Roman numerals),
                                                 "r" (lowercase Roman numerals),
                                                 or other numeric styles.

        Returns:
            str: A string representing the formatted page labels, each on a new line.
        """
        labels_text = []
        for label in page_labels:
            prefix = label.get("prefix", "")
            startpage = label["startpage"] + 1
            firstpagenum = label["firstpagenum"]
            style = label.get("style", "None")
            if style in ["A", "a"]:
                rule_str = int_to_letter(firstpagenum)
                if style == "A":
                    rule_str = rule_str.upper()
            elif style in ["R", "r"]:
                rule_str = int_to_roman(firstpagenum)
                if style == "r":
                    rule_str = rule_str.lower()
            elif style == "None":
                rule_str = ""
            else:
                rule_str = str(firstpagenum)
            if prefix:
                label_str = f"@label {startpage}=[{prefix}]{rule_str}"
            else:
                label_str = f"@label {startpage}={rule_str}"
            labels_text.append(label_str)
        return "\n".join(labels_text)

    def save_toc_text_to_file(self, toc_text: str, toc_path: str):
        try:
            with open(toc_path, "w") as data:
                print(toc_text, file=data)
        except IOError as ioerr:
            print("File Error: " + str(ioerr))

    def convert_toc_list_to_pymupdf_toc(self, toc_list: list):
        toc = []
        page_labels = []
        roman_numeral_pattern = (
            r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
        )

        page_gap = 0
        for line in toc_list:
            page_match = re.match(r"( *)[-+] (.+)# *(\d+) *", line)
            toc_without_page_match = re.match(r"( *)[-+] ([^#]+) *", line)
            gap_match = re.match(r" *# *([\+\-]\d+)", line)
            first_page_match = re.match(r" *# *(\d+) *= *(-?\d+) *", line)
            label_match = re.match(
                r"@label *(\d+) *= *([\[【（\(](.*)[\]】）\)])? *([\w\-]+)", line
            )
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
                page_gap = int(first_page_match.group(2)) - int(
                    first_page_match.group(1)
                )
            elif gap_match:
                page_gap += int(gap_match.group(1))
            elif label_match:
                startpage = int(label_match.group(1)) - 1
                prefix = label_match.group(3) or ""
                rule = label_match.group(4)

                if re.match(roman_numeral_pattern, rule.upper()):
                    style = "R" if rule.isupper() else "r"
                    firstpagenum = roman_to_int(rule.upper())
                elif rule.isdigit():
                    style = "D"
                    firstpagenum = int(rule)
                elif re.match(r"^[a-zA-Z]+$", rule):
                    style = "A" if rule.isupper() else "a"
                    firstpagenum = letter_to_int(rule)
                else:
                    raise Exception("Unsupported label rule format!")

                page_labels.append(
                    {
                        "startpage": startpage,
                        "prefix": prefix,
                        "style": style,
                        "firstpagenum": firstpagenum,
                    }
                )
            else:
                if line.strip():
                    raise ("Unsuppoted Format!")
        return toc, page_labels

    def is_toc_item(self, text: str):
        if re.match(r"^第 \d+ 章.+", text):
            return True
        return False


def roman_to_int(s):
    """
    Converts a Roman numeral string to its integer representation.
    """
    roman_numerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    result = 0
    for i in range(len(s)):
        if i > 0 and roman_numerals[s[i]] > roman_numerals[s[i - 1]]:
            result += roman_numerals[s[i]] - 2 * roman_numerals[s[i - 1]]
        else:
            result += roman_numerals[s[i]]
    return result


def letter_to_int(rule):
    """
    Converts a letter sequence to its corresponding numeric value.
    """
    result = 0
    for char in rule.lower():
        result = result * 26 + (ord(char) - 96)
    return result


def int_to_letter(number):
    """
    Converts a number to its corresponding letter representation.

    For example:
      1 -> 'a'
      27 -> 'aa'
    """
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result.lower()


def int_to_roman(number):
    """
    Converts an integer to its Roman numeral representation.
    """
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    i = 0
    while number > 0:
        for _ in range(number // val[i]):
            roman_num += syb[i]
            number -= val[i]
        i += 1
    return roman_num
