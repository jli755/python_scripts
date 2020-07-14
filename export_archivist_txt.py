#!/bin/env python

"""
Python 3: Web scraping using selenium
    - Download tq.txt and qv.txt files from Archivist Instruments, rename: prefix.tqlinking.txt, prefix.qvmapping.txt
    - Download tv.txt and dv.txt files from Archivist Datasets, rename: prefix.tvlinking.txt, prefix.dv.txt
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


def get_base_url(df):
    """
    Return a dataframe of files that need to be downloaded
    """

    df["base_url"] = df.apply(lambda row: "https://archivist.closer.ac.uk/" if row["Archivist"] == "Main"
                                     else "https://closer-archivist-alspac.herokuapp.com/" if row["Archivist"] == "ALSPAC"
                                     else "https://closer-archivist-us.herokuapp.com/" if row["Archivist"] == "US"
                                     else None, axis=1)

    return df


def archivist_download_txt(df_base_urls, output_prefix_dir, output_type_dir):
    """
    Loop over prefix, downloading txt files
    """

    # Log in to all
    unique_instance = df_base_urls["base_url"].unique()
    for i in unique_instance: 
        archivist_login(i)

    for index, row in df_base_urls.iterrows():

        output_dir = os.path.join(output_prefix_dir, row["Prefix"])
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_tq_dir = os.path.join(output_type_dir, "tqlinking",)
        if not os.path.exists(output_tq_dir):
            os.makedirs(output_tq_dir)

        output_qv_dir = os.path.join(output_type_dir, "qvmapping",)
        if not os.path.exists(output_qv_dir):
            os.makedirs(output_qv_dir)

        output_tv_dir = os.path.join(output_type_dir, "tvlinking",)
        if not os.path.exists(output_tv_dir):
            os.makedirs(output_tv_dir)

        output_dv_dir = os.path.join(output_type_dir, "dv",)
        if not os.path.exists(output_tv_dir):
            os.makedirs(output_tv_dir)

        print("Getting " + row["Prefix"] + "/tq.txt")
        tq_url = os.path.join(row["base_url"], "instruments", row["Prefix"] + "/tq.txt")
        driver.get(tq_url)

        time.sleep(1)
        print("  Downloading " + row["Prefix"] + "/tq.txt")
        try:
            tq_content = driver.find_elements_by_xpath("html/body/pre")[0].text
        except IndexError:
            print("skipping {}".format(row["Prefix"]))
            tq_content = None

        if tq_content:
            with open(os.path.join(output_dir, row["Prefix"] + ".tqlinking.txt"), "w") as f:
                try:
                    f.write(tq_content.replace(" ", "\t"))
                except :
                    print("Could not download tq : ", row["Prefix"])
                    continue
            with open(os.path.join(output_tq_dir, row["Prefix"] + ".tqlinking.txt"), "w") as f:
                try:
                    f.write(tq_content.replace(" ", "\t"))
                except :
                    print("Could not download tq : ", row["Prefix"])
                    continue
            time.sleep(3)

        print("Getting " + row["Prefix"] + "/qv.txt")
        try:
            qv_url = os.path.join(row["base_url"], "instruments", row["Prefix"] + "/qv.txt")
        except:
            print("qv for: ", qv_url, " not found")
        driver.get(qv_url)

        time.sleep(1)
        print("  Downloading " + row["Prefix"] + "/qv.txt")
        try:
            qv_content = driver.find_elements_by_xpath("html/body/pre")[0].text
        except IndexError:
            print("could not find qv", qv_url)
            continue

        if qv_content:
            with open(os.path.join(output_dir, row["Prefix"] + ".qvmapping.txt"), "w") as f:
                f.write(qv_content.replace(" ", "\t"))
            with open(os.path.join(output_qv_dir, row["Prefix"] + ".qvmapping.txt"), "w") as f:
                f.write(qv_content.replace(" ", "\t"))
            time.sleep(3)

        # dataset: from prefix find id
        datasets_url = os.path.join(row["base_url"], "datasets")

        if datasets_url is not None:

            driver.get(datasets_url)
            time.sleep(10)

            # find the input box
            inputElement = driver.find_element_by_xpath("//input[@placeholder='Search for...']")
            print(row["Prefix"])
            print(inputElement)
            inputElement.send_keys(row["Prefix"])   
            time.sleep(1)

            # locate id and link
            trs = driver.find_elements_by_xpath("html/body/div/div/div/div/table/tbody/tr")
            print("This page has {} rows".format(len(trs)))

            for i in range(1, len(trs)):
                # row 0 is header: tr has "th" instead of "td"
                tr = trs[i]

                # column 0 (first column) is "ID"
                study_id = tr.find_elements_by_xpath("td")[0].text
                print("Getting " + study_id + "/tv.txt")
                try:
                    tv_url = os.path.join(datasets_url, study_id + "/tv.txt")
                except:
                    "Cound not find: ", tv_url
                    continue
                driver.get(tv_url)
                time.sleep(10)
                print("  Downloading " + study_id + "/tv.txt")
                tv_content = driver.find_elements_by_xpath("html/body/pre")[0].text

                if tv_content:
                    with open(os.path.join(output_dir, row["Prefix"] + ".tvlinking.txt"), "w") as f:
                        f.write(tv_content.replace(" ", "\t"))
                    with open(os.path.join(output_tv_dir, row["Prefix"] + ".tvlinking.txt"), "w") as f:
                        f.write(tv_content.replace(" ", "\t"))

                time.sleep(3)

                print("Getting " + study_id + "/dv.txt")
                dv_url = os.path.join(datasets_url, study_id + "/dv.txt")
                driver.get(dv_url)
                time.sleep(10)
                print("  Downloading " + study_id + "/dv.txt")
                dv_content = driver.find_elements_by_xpath("html/body/pre")[0].text

                if dv_content:
                    with open(os.path.join(output_dir, row["Prefix"] + ".dv.txt"), "w") as f:
                        f.write(dv_content.replace(" ", "\t"))
                    with open(os.path.join(output_dv_dir, row["Prefix"] + ".dv.txt"), "w") as f:
                        f.write(dv_content.replace(" ", "\t"))
                time.sleep(3)

    #driver.quit()

 
def get_txt(df, output_prefix_dir, output_type_dir):
    """
    Export txt files to output dir
    """

    df_base_urls = get_base_url(df)

    archivist_download_txt(df_base_urls, output_prefix_dir, output_type_dir)
           

def main():
    main_dir = "../Jenny_ucl/archivist_export"
    output_prefix_dir = os.path.join(main_dir, "by_prefix")
    if not os.path.exists(output_prefix_dir):
        os.makedirs(output_prefix_dir)
    output_type_dir = os.path.join(main_dir, "by_type")
    if not os.path.exists(output_type_dir):
        os.makedirs(output_type_dir)

    # Hayley's txt as dataframe
    df = pd.read_csv(os.path.join(main_dir, "Prefixes_to_export.txt"), sep="\t")

    get_txt(df, output_prefix_dir, output_type_dir)


if __name__ == "__main__":
    main()

