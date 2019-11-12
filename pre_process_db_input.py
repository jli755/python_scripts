#!/bin/env python

"""
Go through each tab of excel sheet, create database input files
"""

import os
import pandas as pd
from datetime import date
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def func(row):
    if (row['pre_source'] == 'Conditions' and row['source'] == 'Questions'):
        return 'CcCondition'
    elif (row['pre_source'] == 'Loops' and row['source'] in ('Questions', 'Conditions')):
        return 'CcLoop'
    else:
        return 'CcSequence'

def main():
    input_dir = '../NCDS_2004'
    fn = os.path.join(input_dir, 'NCDS_2004_tables_version5.xlsx') 
    # creating pandas.io.excel.ExcelFile object
    xl = pd.ExcelFile(fn)
    #  generate a dictionary of DataFrames
    dfs = {sh:xl.parse(sh) for sh in xl.sheet_names}

    for sheet_name in dfs.keys():
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
    df_conditions = dfs['Conditions']
    df_conditions['source'] = 'Conditions'

    """
    5. Loops
    """
    df_loops = dfs['Loops']
    df_loops['source'] = 'Loops'


    """
    position of question/condition/loop
	- Need to have a end position for condition/loop, this probably should be done at parsing questionnaire stage and manually reviewed 
	- from current excel file, assume
		- every condition/loop will follow by one question, unless all questions have similar name
    """

    keep_columns = ['Order', 'Label', 'source', 'section_id']
    df_all = pd.concat([df_sequences.loc[:, keep_columns], df_questions.loc[:, keep_columns], df_conditions.loc[:, keep_columns], df_loops.loc[:, keep_columns]])
    df_all = df_all.sort_values('Order').reset_index()

    # condition/question
    df_all['pre_source'] = df_all['source'].shift(1)
    df_all['pre_label'] = df_all['Label'].shift(1)

    df_all['parent_type'] = df_all.apply(func, axis=1)

    df_all['condition_position'] = df_all['parent_type'].apply(lambda x: 1 if x in ('CcCondition', 'CcLoop') else 0)
    df_all['branch'] = 0

    # similar names
    df_all['similar_label'] = df_all.apply(lambda x: 0 if (x['pre_label'] != x['pre_label']) else ( 1 if similar(x['Label'], x['pre_label']) > 0.8 else 0), axis=1)
    for i in range(1, len(df_all)):
        if df_all.loc[i, 'source'] == 'Questions' and df_all.loc[i, 'similar_label'] == 1:
            df_all.loc[i, 'condition_position'] = 1 + df_all.loc[i-1, 'condition_position'] 

    # order within section
    # only order part of data
    mask = ~((df_all['section_id'] >= 1) | (df_all['condition_position'] >= 1))

    df_all.loc[:, 'section_id'] = df_all.loc[:, 'section_id'].ffill()
    df_all['section_position'] = df_all[mask].groupby('section_id').cumcount() + 1 

    df_all['Position'] = df_all.apply(lambda x: max(x['section_id'], x['condition_position'], x['section_position']) if x['condition_position'] != 1 else 1, axis=1)
    cols = ['section_id', 'branch', 'Position']
    df_all[cols] = df_all[cols].astype(int)

    # find pre-section label and pre-condition label
    df_sequences_m = df_sequences[['Label', 'section_id']]
    df_sequences_m.rename(columns={'Label': 'section_label'}, inplace=True)
    df_all_new = pd.merge(df_all, df_sequences_m, how='left', on=['section_id'])
    df_all_new['above_label'] = df_all_new.apply(lambda x: x['pre_label'] if x['parent_type'] in ('CcCondition', 'CcLoop') else x['section_label'], axis=1)

    for i in range(1, len(df_all_new)):
        if df_all_new.loc[i, 'condition_position'] > 1:
            df_all_new.loc[i, 'above_label'] = df_all_new.loc[i-1, 'above_label'] 
            df_all_new.loc[i, 'parent_type'] = df_all_new.loc[i-1, 'parent_type']

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
