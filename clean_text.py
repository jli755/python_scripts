#!/bin/env python

"""
Go through text files
    - replace &amp;amp;# with &#
    - replace &amp;amp; with &amp;
    - replace &amp;# with &#    (ncds_81_i)
    - replace &#160: with &#160;  (nshd_82_q)
"""

import re
import os
import sys

def main():

    rootdir = "../xml_files"

    try:
        files = [f for f in os.listdir(rootdir) if os.path.isfile(os.path.join(rootdir, f))]
        #print(files)
    except WindowsError:
        print("something is wrong")
        sys.exit(1)

    for filename in files:
        filename = os.path.join(rootdir, filename)
        print(filename + ": pass 1 fixing '&amp;amp;#'")
        tmpfile1 = filename + ".temp1"
        tmpfile2 = filename + ".temp2"
        tmpfile3 = filename + ".temp3"

        with open(filename, "r") as fin:
            with open(tmpfile1, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&amp;amp;#", '&#'))

        print(filename + ": pass 2 fixing '&amp;amp;'")
        with open(tmpfile1, "r") as fin:
            # overwrite
            with open(tmpfile2, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&amp;amp;", '&amp;'))

        print(filename + ": pass 3 fixing '&amp;#'")
        with open(tmpfile2, "r") as fin:
            # overwrite
            with open(tmpfile3, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&amp;#", '&#'))

        print(filename + ": pass 4 fixing '&#160: (note colon)'")
        with open(tmpfile3, "r") as fin:
            # overwrite
            with open(filename, "w") as fout:
                for line in fin:
                    fout.write(re.sub(r"(&#[0-9]+):", r"\1;", line))

        # remove tmp
        print(filename + ": deleting tmpfile")
        os.unlink(tmpfile1)
        os.unlink(tmpfile2)
        os.unlink(tmpfile3)


if __name__ == '__main__':
    main()

