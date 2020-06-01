#!/bin/env python

"""
Python 3
    quick fix for LSYPE studys
        used to be 1-1 relationship between code and question
        now change to same code can be used more than one time
"""

import pandas as pd
import os
import re


def get_new_label(df):
    """
    Go though codes table, find re-used codes
    """
    label_dict = {}
    codes_dict = {}

    for old_label in df['Label'].unique():
        # print(old_label)
        df_codes = df.loc[(df.Label == old_label), ['codes_order', 'value', 'Category']].reset_index(drop=True)

        # two values and each value is one word only
        if (df_codes.shape[0] == 2) and ( all([ not pd.isnull(s) and len(s.split()) == 1 for s in df_codes['Category'].tolist()])):
            #print("TWO")
            new_label = 'cs_' + ('_').join(df_codes['Category'].tolist()) 

        elif not bool(codes_dict):
            #print("empty dict")
            new_label = old_label

        # already in codes value, no need to add again 
        else:
            new_label = old_label
            for dict_label, dict_df in codes_dict.items():
                if df_codes.equals(dict_df):
                    new_label =  dict_label

        label_dict[old_label] = new_label

        if not new_label in codes_dict.keys():
            codes_dict[new_label] = df_codes

    return label_dict, codes_dict


def main():
    input_dir = '../LSYPE1/wave4-html'
    output_dir = os.path.join(input_dir, 'clean_code_input')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    df_codes = pd.read_csv(os.path.join(input_dir, 'codes.csv'), sep=';')

    df_codes = df_codes.drop('Number', 1)


    label_dict, codes_dict = get_new_label(df_codes)

    df_codes_dict = pd.concat(codes_dict, axis=0).reset_index().drop('level_1', 1)
    df_codes_dict.rename(columns={'level_0': 'Label'}, inplace=True)
    df_codes_dict.to_csv(os.path.join(output_dir, 'codes.csv'), encoding='utf-8', sep=';', index=False)

    df_qg = pd.read_csv(os.path.join(input_dir, 'question_grids.csv'), sep=';')
    df_qg['horizontal_code_list_name'] = df_qg['horizontal_code_list_name'].map(label_dict)
    df_qg['vertical_code_list_name'] = df_qg['vertical_code_list_name'].map(label_dict)
    df_qg.to_csv(os.path.join(output_dir, 'question_grids.csv'), encoding='utf-8', sep=';', index=False)

    df_qi = pd.read_csv(os.path.join(input_dir, 'question_items.csv'), sep=';')
    df_qi['Response'] = df_qi['Response'].map(label_dict)
    df_qi.to_csv(os.path.join(output_dir, 'question_items.csv'), encoding='utf-8', sep=';', index=False)

    df_loops = pd.read_csv(os.path.join(input_dir, 'loops.csv'), sep=';')
    df_loops.to_csv(os.path.join(output_dir, 'loops.csv'), encoding='utf-8', sep=';', index=False)

    df_conditions = pd.read_csv(os.path.join(input_dir, 'conditions.csv'), sep=';')
    df_conditions.to_csv(os.path.join(output_dir, 'conditions.csv'), encoding='utf-8', sep=';', index=False)

    df_response = pd.read_csv(os.path.join(input_dir, 'response.csv'), sep=';')
    df_response.to_csv(os.path.join(output_dir, 'response.csv'), encoding='utf-8', sep=';', index=False)

    df_sequences = pd.read_csv(os.path.join(input_dir, 'sequences.csv'), sep=';')
    df_sequences.to_csv(os.path.join(output_dir, 'sequences.csv'), encoding='utf-8', sep=';', index=False)

    df_statements = pd.read_csv(os.path.join(input_dir, 'statements.csv'), sep=';')
    df_statements.to_csv(os.path.join(output_dir, 'statements.csv'), encoding='utf-8', sep=';', index=False)


if __name__ == '__main__':
    main()
