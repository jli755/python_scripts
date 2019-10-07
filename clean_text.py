#!/bin/env python

"""
Go through text files
    - replace &amp;amp;# with &#
    - replace &amp;amp; with &amp;
"""

import os
import sys

def main():

    rootdir = "../xml_files"

    try:
        files = [f for f in os.listdir(rootdir) if os.path.isfile(os.path.join(rootdir, f))]
    except WindowsError:
        print("something is wrong")
        sys.exit(1)

    for filename in files:
        print(filename + ": pass 1 fixing '&amp;amp;#'")
        tmpfile = os.path.join(os.path.dirname(filename), os.path.basename(filename)+".temp")
        with open(filename, "r") as fin:
            with open(tmpfile, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&amp;amp;#", '&#'))

        print(filename + ": pass 2 fixing '&amp;amp;'")
        with open(tmpfile, "r") as fin:
            # overwrite
            with open(filename, "w") as fout:
                for line in fin:
                    fout.write(line.replace("&amp;amp;", '&amp;'))
        # remove tmp
        print(filename + ": deleting tmpfile")
        os.unlink(tmpfile)


if __name__ == '__main__':
    main()

