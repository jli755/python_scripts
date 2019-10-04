#!/bin/env python
# -*- coding: utf-8 -*-

"""
Overwrite the original xml file with a middle of context line break replaced by a space.
Also expand the escaped characters, for example: &#163; becomes £

Line breaks in text are generally represented as:
\r\n - on a windows computer
\r - on an Apple computer
\n - on Linux
"""

import re
import os
import sys
from xml.etree import ElementTree


def main():

    rootdir = "../xml_files"

    try:
        files = [f for f in os.listdir(rootdir) if os.path.isfile(os.path.join(rootdir, f))]
    except WindowsError:
        print("something is wrong")
        sys.exit(1)

    for filename in files:
	filename = os.path.join(rootdir, filename)
        print(filename)
        with open(filename, 'rt') as f:
            tree = ElementTree.parse(f)

        for node in tree.iter():
            # TODO: any other elements?
            if not node.tag.lower() == "text":
                continue
            if re.search("\n|\r|\r\n", node.text):
                node.text = node.text.replace("\r\n", " ")
                node.text = node.text.replace("\r", " ")
                node.text = node.text.replace("\n", " ")

        # because encoding="UTF-8" in below options, the output can contain non-ascii characters, e.g. £
        tree.write(filename,encoding="UTF-8",xml_declaration=True)


if __name__ == '__main__':
    main()

