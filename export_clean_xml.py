#!/bin/env python

"""
Python 3
    Web scraping using selenium to get .xml
        - from https://archivist.closer.ac.uk/admin/export  Download latest

    Clean xml 

    grep -rnw 'archivist' -e '&amp;amp;'
    archivist/alspac_91_pq.xml:16376:          <r:Content xml:lang="en-GB">City &amp;amp; Guilds intermediate technical</r:Content>
    archivist/alspac_91_pq.xml:16385:          <r:Content xml:lang="en-GB">City &amp;amp; Guilds final technical</r:Content>
    archivist/alspac_91_pq.xml:16394:          <r:Content xml:lang="en-GB">City &amp;amp; Guilds full technical</r:Content>
    archivist/alspac_91_pq.xml:16412:          <r:Content xml:lang="en-GB">Yes &amp;amp; affected me a lot</r:Content>

"""

from selenium import webdriver
from lxml import etree
import pandas as pd
import time
import sys
import os
import re


# Download geckodriver-v0.25.0-linux64.tar.gz from https://github.com/mozilla/geckodriver/releases
# unpack the tar.gz: has single binary inside
driver = webdriver.Firefox(executable_path="/home/jenny/Documents/python_scripts.git/geckodriver")


def archivist_login(url):
    """
    Log in to archivist
    """
    driver.get(url)
    driver.find_element_by_id("login-email").send_keys("YOUR ACCOUNT")
    driver.find_element_by_id("login-password").send_keys("YOUR PASSWORD")
    driver.find_element_by_class_name("btn-default").click()
    time.sleep(10)


def get_names(df):
    """
    Return a dictionary of files 
    """

    df["url"] = df.apply(lambda row: "https://archivist.closer.ac.uk/admin/export/" if row["Archivist"] == "Main"
                                else "https://closer-archivist-alspac.herokuapp.com/admin/export" if row["Archivist"] == "ALSPAC"
                                else "https://closer-archivist-us.herokuapp.com/admin/export" if row["Archivist"] == "US"
                                else None, axis=1)
    names_dict = pd.Series(df.url.values, index=df.Prefix).to_dict()
    return names_dict


def archivist_download_xml(export_names, output_dir):
    """
    Loop over export_names dictionary, downloading xml
    """

    # Log in to all
    unique_instance = set([os.path.dirname(l) for l in list(export_names.values())])
    print(unique_instance)
    for i in unique_instance: 
        archivist_login(i)
 
    k = 0
    for prefix, url in export_names.items():

        if url is not None:
            driver.get(url)
            time.sleep(10)
 
            print(k)
            # find the input box
            inputElement = driver.find_element_by_xpath("//input[@placeholder='Search for...']")
            
            inputElement.send_keys(prefix)   

            # locate id and link
            trs = driver.find_elements_by_xpath("html/body/div/div/div/div/div/div/table/tbody/tr")
            # print("This page has {} rows".format(len(trs)))

            for i in range(1, len(trs)):
                # row 0 is header: tr has "th" instead of "td"
                tr = trs[i]

                # column 2 is "Prefix"
                xml_prefix = tr.find_elements_by_xpath("td")[1].text

                # column 5 is "Export date"           
                xml_date = tr.find_elements_by_xpath("td")[4].text

                # column 6 is "Actions", need to have both "download latest and export"
                xml_location = tr.find_elements_by_xpath("td")[5].find_elements_by_xpath("a")[0].get_attribute("href")

                if (xml_prefix == prefix and xml_location is not None):
                    print("Getting xml for " + prefix) 
            
                    driver.get(xml_location)

                    time.sleep(10)
                    print("  Downloading xml for " + prefix)
                    out_f = os.path.join(output_dir, prefix + ".xml")

                    with open(out_f, "wb") as f:
                        try:
                            f.write(driver.page_source.encode("utf-8"))
                        except UnicodeEncodeError:
                            print("Could not download Unicode: ", prefix)
                            continue
                        except IOError:
                            print("Could not download IO : ", prefix)
                            continue
                    time.sleep(5)
                else:
                    print("No download link for " + prefix)
                    xml_location = "No download link"

                k = k + 1
                with open(os.path.join(os.path.dirname(output_dir), "download_list.csv"), "a") as f:
                    f.write( ",".join([str(k), prefix, xml_date, xml_location]) + "\n")
    driver.quit()

 
def get_xml(df, output_dir):
    """
    Export xml to output dir
    """

    export_names = get_names(df)
    print("Got {} xml names".format(len(export_names)))

    archivist_download_xml(export_names, output_dir)
           

def clean_text(rootdir):
    """
    Go through text files
        - replace &amp;amp;# with &#
        - replace &amp;amp; with &amp;
        - replace &amp;# with &#    
        - replace &#160: with &#160; 
    """

    try:
        files = [f for f in os.listdir(rootdir) if os.path.isfile(os.path.join(rootdir, f))]
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


def clean_newline(rootdir):
    """
    Overwrite the original xml file with a middle of context line break replaced by a space.
    Also expand the escaped characters, for example: &#163; becomes £
    Line breaks in text are generally represented as:
        \r\n - on a windows computer
        \r   - on an Apple computer
        \n   - on Linux
    """

    try:
        files = [f for f in os.listdir(rootdir) if os.path.isfile(os.path.join(rootdir, f))]
    except WindowsError:
        print("something is wrong")
        sys.exit(1)

    for filename in files:
        filename = os.path.join(rootdir, filename)
        print(filename)
        p = etree.XMLParser(resolve_entities=True)
        with open(filename, "rt") as f:
            tree = etree.parse(f, p)

        for node in tree.iter():
            if node.text is not None:
                if re.search("\n|\r|\r\n", node.text.rstrip()):
                    node.text = node.text.replace("\r\n", " ")
                    node.text = node.text.replace("\r", " ")
                    node.text = node.text.replace("\n", " ")

        # because encoding="UTF-8" in below options, the output can contain non-ascii characters, e.g. £
        tree.write(filename, encoding="UTF-8", xml_declaration=True)


def main():
    main_dir = "../Jenny_ucl/export_xml"
    output_dir = os.path.join(main_dir, "archivist")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Hayley's txt as dataframe
    df = pd.read_csv(os.path.join(main_dir, "Prefixes_to_export.txt"), sep="\t")

    get_xml(df, output_dir)
    clean_text(output_dir)
    clean_newline(output_dir)


if __name__ == "__main__":
    main()

