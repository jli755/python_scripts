#!/bin/env python

"""
Go through each tab of excel sheet, create database input files
"""

import os
import pandas as pd
import numpy as np
from datetime import date

def isNaN(num):
    return num != num


def find_parent(start, stop, df_mapping, source, section_label):
    """
        Find the parent label and parent source
    """
    if isNaN(stop):
        df = df_mapping.loc[(df_mapping.Order < start) & (df_mapping.End > start), :]
    else:
        df = df_mapping.loc[(df_mapping.Order < start) & (df_mapping.End > stop), :]

    if source == 'Sequences':
        return section_label
    elif not df.empty:
        df['dist'] = start - df['Order']
        df_r = df.loc[df['dist'].idxmin()]
        return df_r['Label']
    else:
        return section_label


def main():
    input_dir = '../NCDS_2004'
    fn = os.path.join(input_dir, 'NCDS_2004_tables_version5.xlsx') 
    # creating pandas.io.excel.ExcelFile object
    xl = pd.ExcelFile(fn)
    #  generate a dictionary of DataFrames
    dfs = {sh:xl.parse(sh) for sh in xl.sheet_names}

    for sheet_name in dfs.keys():
        print(sheet_name)

    fn_end = os.path.join(input_dir, 'NCDS_2004_tables_version8_jenny.xlsx') 
    # creating pandas.io.excel.ExcelFile object
    xl_end = pd.ExcelFile(fn_end)
    #  generate a dictionary of DataFrames
    dfs_end = {sh:xl_end.parse(sh) for sh in xl_end.sheet_names}

    for sheet_name in dfs_end.keys():
        print(sheet_name)
    """
    1. Codes
    """
    df_codes = dfs['Codes']
    df_codes['source'] = 'Codes'
    # add order
    df_codes['codes_order'] = df_codes.sort_values(by='Number').groupby('Label').cumcount() + 1

    df_codes['new_label'] = df_codes['Label'].str.replace(r'\(.*\)', '_', regex=True)
    # sort by column "Number"
    df_codes = df_codes.sort_values(['Label', 'Value'])
    # find possible duplicated Label
    df_codes_dup = pd.concat(g for _, g in df_codes.groupby(['new_label', 'Value', 'Category']) if len(g) > 1)

    # all modified labels are stored in a dictionary
    modify_lable_dict = dict([(x, y) for x, y in zip(df_codes_dup['Label'], df_codes_dup['new_label'])])

    # keep the first dup, remove the rest
    first_element_lists = df_codes_dup.groupby(['new_label', 'Value', 'Category']).first()['Number'].values.tolist()
    all_elements_list = df_codes_dup['Number'].values.tolist()
    df_codes['keep'] = df_codes['Number'].apply(lambda x: 0 if x in [item for item in all_elements_list if item not in first_element_lists]  else 1)

    df_codes_sub = df_codes.loc[(df_codes.keep == 1)]
    df_codes_sub.drop(['Label', 'keep'], axis=1, inplace=True)
    df_codes_sub.rename(columns={'new_label': 'Label'}, inplace=True)

    """
    2. Sequences
    """
    df_sequences = dfs['Sequences']
    df_sequences['source'] = 'Sequences'
    # add sequence id
    df_sequences['section_id'] = df_sequences.index + 1

    """
    3. Questions_Instructions_Response
    """
    df_questions = dfs['Questions_Instructions_Response']
    df_questions['source'] = 'Questions'
    # sort by column "Number"
    df_questions = df_questions.sort_values('Number')
    # rename column
    df_questions.rename(columns={'Number': 'Order'}, inplace=True)
    # replace 'qi' with 'qc' in Label column
    df_questions['Label'] = df_questions['Label'].str.replace('qi_', 'qc_')
    # replace '&' with '_' in Label column
    df_questions['Label'] = df_questions['Label'].str.replace('&', '_')
    # replace 'qc_qc_' with 'qc_'
    df_questions['Label'] = df_questions['Label'].str.replace('qc_qc_', 'qc_')

    # replace label with new_label from codes dataframe
    df_questions["Response domain"].replace(modify_lable_dict, inplace=True) 

    """
    4. Response Domain
    """
    df_response = dfs['Response Domain']
    df_response['source'] = 'Response'
    # convert to integer
    df_response['Min'] = df_response['Min'].apply(lambda x: None if pd.isnull(x) else '{0:.0f}'.format(pd.to_numeric(x)))
    df_response['Max'] = df_response['Max'].apply(lambda x: None if pd.isnull(x) else '{0:.0f}'.format(pd.to_numeric(x)))

    """
    5. Conditions
    """
    df_conditions = dfs_end['Conditions']
    df_conditions.rename(columns={'Start point of the condition': 'Order', 'End point of the condition': 'End'}, inplace=True)
    df_conditions['source'] = 'Conditions'
    # replace '&' with '_' in Label column
    df_conditions['Label'] = df_conditions['Label'].str.replace('&', '_')

    """
    5. Loops
    """
    df_loops = dfs_end['Loops']
    df_loops.rename(columns={'Start point of the loop': 'Order', 'End point of the loop': 'End'}, inplace=True)
    df_loops['source'] = 'Loops'
    # replace '&' with '_' in Label column
    df_loops['Label'] = df_loops['Label'].str.replace('&', '_')


    """
    position of question/condition/loop
        - Need to have a end position for condition/loop
        - from current excel file, assume
	    - every condition/loop will follow by one question
    """

    keep_columns = ['Order', 'End', 'Label', 'source', 'section_id',]
    df_all = pd.concat([df_sequences.loc[:, keep_columns], df_questions.loc[:, keep_columns], df_conditions.loc[:, keep_columns], df_loops.loc[:, keep_columns]])
    df_all = df_all.sort_values('Order').reset_index()

    # sections region
    df_sequences_m = df_sequences[['Label', 'section_id']]
    df_sequences_m.rename(columns={'Label': 'section_label'}, inplace=True)
    df_all_new = pd.merge(df_all, df_sequences_m, how='left', on=['section_id'])
    df_all_new['section_id'] = df_all_new['section_id'].fillna(method='ffill')
    df_all_new['section_label'] = df_all_new['section_label'].fillna(method='ffill')

    df_mapping = df_all_new.loc[ df_all.End > 0, ['Label', 'source', 'Order', 'End']]

    # find above label
    for index,row in df_all_new.iterrows():
        df_all_new.at[index, 'above_label'] = find_parent(row['Order'], row['End'], df_mapping, row['source'], row['section_label'])

    # calculate position
    df_all_new['Position'] = df_all_new.groupby('above_label').cumcount() + 1

    df_all_new['parent_type'] = df_all_new['above_label'].apply(lambda x: 'CcCondition' if x[0:1] == 'c'  else 'CcLoop' if x[0:1] == 'l' else 'CcSequence')

    df_all_new['branch'] = 0
    cols = ['section_id', 'branch', 'Position']
    df_all_new[cols] = df_all_new[cols].astype(int)

    df_all_new.to_csv(os.path.join(input_dir, 'ALL_ORDER.csv'), encoding='utf-8', index=False)



    # csv
    df_questions_new = pd.merge(df_questions, df_all_new, how='left', on=['Order', 'Label'])
    questions_keep = ['Label', 'Literal', 'Instructions', 'Response domain', 'above_label', 'parent_type', 'branch', 'Position']
    df_questions_new[questions_keep].to_csv(os.path.join(input_dir, 'questions.csv'), encoding='utf-8', index=False)

    df_conditions_new = pd.merge(df_conditions, df_all_new, how='left', on=['Order', 'Label'])
    conditions_keep = ['Label', 'Literal', 'Logic', 'above_label', 'parent_type', 'branch', 'Position']
    df_conditions_new[conditions_keep].to_csv(os.path.join(input_dir, 'conditions.csv'), encoding='utf-8', index=False)

    df_loops_new = pd.merge(df_loops, df_all_new, how='left', on=['Order', 'Label'])
    loops_keep = ['Label', 'Variable', 'Start Value', 'End Value', 'Loop While', 'Logic', 'above_label', 'parent_type', 'branch', 'Position']
    df_loops_new[loops_keep].to_csv(os.path.join(input_dir, 'loops.csv'), encoding='utf-8', index=False)

    df_sequences.drop('source', 1).to_csv(os.path.join(input_dir, 'sequences.csv'), encoding='utf-8', index=False)
    df_response.drop('source', 1).to_csv(os.path.join(input_dir, 'response.csv'), encoding='utf-8', index=False)
    df_codes_sub.drop('source', 1).to_csv(os.path.join(input_dir, 'codes.csv'), encoding='utf-8', index=False)


if __name__ == '__main__':
    main()
