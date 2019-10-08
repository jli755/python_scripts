## October 2019

### Week 1 (Oct 1 - Oct 4)

1. [x] File manipulations
    1. [x] Change all .txt files from 2 to 3/4 columns
        1. [modify_columns.py](https://github.com/jli755/python_scripts/blob/master/modify_columns.py)
            - If the column number if 2 then this script will fix it and over write the file
            - Output a `notes.txt` to show what was done to each file
            - Neet to modify the hard coded directory path before running
    2. [x] Remove all carriage returns and correct ascii characters from .xml files
        1. [clean_text.py](https://github.com/jli755/python_scripts/blob/master/clean_text.py) 
            - Clean the text field in `.xml`
        2. [clean_xml_and_newline.py](https://github.com/jli755/python_scripts/blob/master/clean_xml_and_newline.py)
            - Remove carriage returns
            - Expand the escaped characters, for example: \&#163; becomes £
2. [x] Scrape [Archivist](https://archivist.closer.ac.uk)
    1. [x] Download all the `.xml` from [Instrument](https://archivist.closer.ac.uk/instruments)
        1. [scrape_archivist_selenium.py](https://github.com/jli755/python_scripts/blob/master/scrape_archivist_selenium.py)
            - Use selenium to download all `.xml` files
            - Need to modify the user log in and password

### Week 2 (Oct 7 - Oct 11)

- [x] Scrape [Archivist](https://archivist.closer.ac.uk) continuous
   - [x] Download all the `.txt` from [Datasets](https://archivist.closer.ac.uk/datasets)
