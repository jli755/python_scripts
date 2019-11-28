#!/bin/env python
# -*- coding: utf-8 -*-

"""
    Parse xml file
"""

import re
import pandas as pd
import xmltodict
from io import open

def xml_to_dict(xmlFile):
    """
        Input: xml file
        Output: dictionary
    """
    with open(xmlFile, encoding="utf-8") as fobj:
        xml = fobj.read()

    namespaces = {'r': None, 'ddi':None}
    root = xmltodict.parse(xml, namespaces=namespaces)
    return root

def flatten_dict(list_of_dict):
    """
        Input: list of dictionary
	Output: pandas dataframe of all
    """
    df_list = []
    for i in range(0, len(list_of_dict)):

        df_all = pd.io.json.json_normalize(list_of_dict[i], sep='_')

        for k in list_of_dict[i].keys():

            if isinstance(list_of_dict[i][k], list):
                #df_k = pd.io.json.json_normalize(list_of_dict[i], record_path=[k], record_prefix=k, sep='_')
                df_k = pd.io.json.json_normalize(list_of_dict[i][k], sep='_')
                df_k.columns = [ k + '_' + str(col) for col in df_k.columns]
                df_all.drop(k, axis=1, inplace=True)
            elif isinstance(list_of_dict[i][k], dict):
                for ke in list_of_dict[i][k].keys():
                    if isinstance(list_of_dict[i][k][ke], list):
                        df_k = pd.io.json.json_normalize(list_of_dict[i][k][ke], sep='_')
                        df_k.columns = [ k + '_' + ke + '_' + str(col) for col in df_k.columns]
                        df_all.drop(k + '_' + ke, axis=1, inplace=True)
            else:
                df_k = pd.DataFrame()

        df_list.append(pd.concat([df_all, df_k], axis=1))
    return pd.concat(df_list, sort=False, ignore_index=True).ffill()


def main():
    xmlFile = '../LSYPE1/wave8-xml/NS8MAINV014.xml'
    r = xml_to_dict(xmlFile)

    # how many differenct sections
    A = r['FragmentInstance']['Fragment']
    section_names = set(a.keys()[1] for a in A)

    for section_name in section_names:
        print("****** {} ******".format(section_name))
        L = [a[section_name] for a in A if section_name in a.keys()]
        df = flatten_dict(L)

        # delete some columns
        patternDel = '(@versionDate$|@xmlns$|URN$|Agency$|@isUniversallyUnique$|Version$)'
        df = df[df.columns.drop(list(df.filter(regex=patternDel)))]

        non_null_columns = [col for col in df.columns if df.loc[:, col].notna().any()]
        df[non_null_columns].to_csv('../LSYPE1/wave8-xml/' + section_name + '.csv', encoding='utf-8', index=False)

if __name__ == "__main__":
    main()
