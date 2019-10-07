#!/bin/env python

"""
Download files from Archivist
"""

from selenium import webdriver 
import time

# Download geckodriver-v0.25.0-linux64.tar.gz from https://github.com/mozilla/geckodriver/releases
# unpack the tar.gz: has single binary inside
driver = webdriver.Firefox(executable_path='/home/jenny/Documents/python_scripts.git/geckodriver')


def archivist_login():
    url = "https://archivist.closer.ac.uk/instruments/"
    driver.get(url)
    driver.find_element_by_id("login-email").send_keys("YOUR LOGIN NAME")
    driver.find_element_by_id("login-password").send_keys("YOUR_PASSWORD")
    driver.find_element_by_class_name("btn-default").click()
    time.sleep(10)

def main():
    
    archivist_login()

    instrument_name = []
    while True:    
        # div are trial-and-error: could change if webpage changed at all
        trs = driver.find_elements_by_xpath("html/body/div/div/div/div/table/tbody/tr")
        print('This page has {} rows'.format(len(trs)))
    
        # From all the links find instrument name
        for i in range(1, len(trs)):
            # row 0 is header: tr has "th" instead of "td"
            tr = trs[i]
            # column 1 (2nd column) is "Prefix"
            prefix = tr.find_elements_by_xpath("td")[1].find_elements_by_xpath("a")[0].get_attribute('href').split("/")[-1]
            print('  ' + prefix)
            instrument_name.append(prefix)
        # next page
        loadMoreButton = driver.find_element_by_link_text("Next")
        if loadMoreButton.get_attribute('disabled') == 'true':
            break
        loadMoreButton.click()
        time.sleep(5)
        
    print("Got {} instrument names".format(len(instrument_name)))
    with open('filenames.txt', 'w') as f:
        f.write("\n".join(instrument_name))
    #print(instrument_name)

    # loop through individual instrument name, download xml files
    for x in instrument_name:
        print('Getting ' + x )
        url = 'https://archivist.closer.ac.uk/instruments/' + x + '.xml'
        driver.get(url)

        time.sleep(10)
        print('  Downloading ' + x )
        with open(x + '.xml', 'w') as f:
            f.write(driver.page_source)
        time.sleep(3)

    driver.quit()


if __name__ == '__main__':
    main()
