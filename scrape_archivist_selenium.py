#!/bin/env python

"""
Web scraping using selenium
    - Download tq.txt and qv.txt files from Archivist Instruments
    - Download tv.txt and dv.txt files from Archivist Datasets
"""

from selenium import webdriver
import time
import os

# Download geckodriver-v0.25.0-linux64.tar.gz from https://github.com/mozilla/geckodriver/releases
# unpack the tar.gz: has single binary inside
driver = webdriver.Firefox(executable_path="/home/jenny/Documents/python_scripts.git/geckodriver")

def archivist_login():
    url = "https://archivist.closer.ac.uk/"
    driver.get(url)
    driver.find_element_by_id("login-email").send_keys("YOUR LOGIN NAME")
    driver.find_element_by_id("login-password").send_keys("YOUR_PASSWORD")
    driver.find_element_by_class_name("btn-default").click()
    time.sleep(10)


def archivist_get_all_instrument_names():
    """Get a list of all instrument names"""

    url = "https://archivist.closer.ac.uk/instruments/"
    driver.get(url)
    time.sleep(10)

    instrument_name = []
    while True:
        # div are trial-and-error: could change if webpage changed at all
        trs = driver.find_elements_by_xpath("html/body/div/div/div/div/table/tbody/tr")
        print("This page has {} rows".format(len(trs)))

        # From all the links find instrument name
        for i in range(1, len(trs)):
            # row 0 is header: tr has "th" instead of "td"
            tr = trs[i]
            # column 1 (2nd column) is "Prefix"
            prefix = tr.find_elements_by_xpath("td")[1].find_elements_by_xpath("a")[0].get_attribute("href").split("/")[-1]
            print("  " + prefix)
            instrument_name.append(prefix)
        # next page
        loadMoreButton = driver.find_element_by_link_text("Next")
        if loadMoreButton.get_attribute("disabled") == "true":
            break
        loadMoreButton.click()
        time.sleep(5)
    return instrument_name


def archivist_download_instruments(names, output_dir):
    """loop over names, downloading xml and txt files"""
    for x in names:
        print("Getting " + x + ".xml")
        xml_url = "https://archivist.closer.ac.uk/instruments/" + x + ".xml"
        driver.get(xml_url)

        time.sleep(10)
        print("  Downloading " + x + ".xml")
        with open(os.path.join(output_dir, x + ".xml"), "w") as f:
            f.write(driver.page_source.encode("utf-8"))
        time.sleep(3)

        print("Getting " + x + "/tq.txt")
        tq_url = "https://archivist.closer.ac.uk/instruments/" + x + "/tq.txt"
        driver.get(tq_url)

        time.sleep(10)
        print("  Downloading " + x + "/tq.txt")
        tq_content = driver.find_elements_by_xpath("html/body/pre")[0].text

        if tq_content:
            with open(os.path.join(output_dir, x + ".tqlinking.txt"), "w") as f:
                f.write(tq_content.replace(" ", "\t"))
        time.sleep(3)

        print("Getting " + x + "/qv.txt")
        qv_url = "https://archivist.closer.ac.uk/instruments/" + x + "/qv.txt"
        driver.get(qv_url)

        time.sleep(10)
        print("  Downloading " + x + "/qv.txt")
        qv_content = driver.find_elements_by_xpath("html/body/pre")[0].text

        if qv_content:
            with open(os.path.join(output_dir, x + ".qvmapping.txt"), "w") as f:
                f.write(qv_content.replace(" ", "\t"))
        time.sleep(3)


def archivist_get_all_datasets():

    datasets_url = "https://archivist.closer.ac.uk/datasets/"
    driver.get(datasets_url)
    time.sleep(10)

    dataset_id_list = []
    while True:
        # div are trial-and-error: could change if webpage changed at all
        trs = driver.find_elements_by_xpath("html/body/div/div/div/div/table/tbody/tr")
        print("This page has {} rows".format(len(trs)))

        # From all the links find instrument name
        for i in range(1, len(trs)):
            # row 0 is header: tr has "th" instead of "td"
            tr = trs[i]

            # column 0 (1st column) is "ID"
            dataset_id = tr.find_elements_by_xpath("td")[0].text
            print('  ' + dataset_id)
            dataset_id_list.append(dataset_id)

        # next page
        loadNextButton = driver.find_element_by_link_text("Next")
        if loadNextButton.get_attribute("disabled") == "true":
            break
        loadNextButton.click()
        time.sleep(5)
    return dataset_id_list


def archivist_download_dataset(id_list, output_dir):
    """loop through individual dataset ids, download txt files, rename"""
    datasets_url = "https://archivist.closer.ac.uk/datasets/"

    for x in id_list:

        print("Getting " + x + "/tv.txt")
        tv_url = os.path.join(datasets_url, x + "/tv.txt")
        driver.get(tv_url)

        time.sleep(10)
        print("  Downloading " + x + "/tv.txt")
        content = driver.find_elements_by_xpath("html/body/pre")[0].text

        fname = "OOPSBUG"
        if content:
            fname = content.split()[0]
            tv = os.path.join(output_dir, fname + ".tvlinking.txt")
            with open(tv, "w") as f:
                f.write(content.replace(" ", "\t"))
        time.sleep(3)

        print("Getting " + x + "/dv.txt")
        dv_url = os.path.join(datasets_url, x + "/dv.txt")
        driver.get(dv_url)

        time.sleep(10)
        print("  Downloading " + x + "/dv.txt")
        dvcontent = driver.find_elements_by_xpath("html/body/pre")[0].text

        if dvcontent:
            dv = os.path.join(output_dir, fname + ".dv.txt")
            with open(dv, "w") as f:
                f.write(dvcontent.replace(" ", "\t"))
        time.sleep(3)


def main():
    output_dir = "../archivist"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    archivist_login()

    names = archivist_get_all_instrument_names()
    print("Got {} instrument names".format(len(names)))
    with open("filenames.txt", "w") as f:
        f.write("\n".join(names))
    #print(instrument_names)

    archivist_download_instruments(names, output_dir)

    dataset_id_list = archivist_get_all_datasets()
    print("Got {} dataset IDs".format(len(dataset_id_list)))
    with open("dataset_id.txt", "w") as f:
        f.write("\n".join(dataset_id_list))

    archivist_download_dataset(dataset_id_list, output_dir)

    driver.quit()


if __name__ == "__main__":
    main()

