#!/bin/env python

"""
Python 3
    Web scraping using selenium to click the "Export" button
        - from https://archivist.closer.ac.uk/admin/export 
"""

from selenium import webdriver
import pandas as pd
import time
import os


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


def click_export_button(df):
    """
    Loop over xml_name dictionary, click 'Export'
    """

    export_name = get_names(df)
    print("Got {} xml names".format(len(export_name)))

    # Log in to all
    unique_instance = set([os.path.dirname(l) for l in list(export_name.values())])
    print(unique_instance)
    for i in unique_instance: 
        archivist_login(i)
 
    k = 0
    for prefix, url in export_name.items():

        if url is not None:
            driver.get(url)
            time.sleep(10)
 
            print(k)
            # find the input box
            inputElement = driver.find_element_by_xpath('//input[@placeholder="Search for..."]')
            
            inputElement.send_keys(prefix)   

            # locate id and link
            trs = driver.find_elements_by_xpath("html/body/div/div/div/div/div/div/table/tbody/tr")

            for i in range(1, len(trs)):
                # row 0 is header: tr has "th" instead of "td"
                tr = trs[i]

                # column 2 is "Prefix"
                xml_prefix = tr.find_elements_by_xpath("td")[1].text

                # column 6 is "Actions", click on "export"
                exportButton = tr.find_elements_by_xpath("td")[5].find_elements_by_xpath("a")[1]

                if (xml_prefix == prefix):
                    print("Click export button for " + prefix) 
                    exportButton.click()
                    time.sleep(5)
                else:
                    print("Did not find " + prefix)
    driver.quit()


def main():
    main_dir = "../Jenny_ucl/export_xml"

    # Hayley's txt as dataframe
    df = pd.read_csv(os.path.join(main_dir, 'Prefixes_to_export.txt'), sep='\t')

    click_export_button(df)


if __name__ == "__main__":
    main()

