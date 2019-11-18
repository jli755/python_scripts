#!/bin/env python

"""
Go through each tab of excel sheet, create database input files
"""

import os
import pandas as pd
import numpy as np
from datetime import date
from difflib import SequenceMatcher

def main():
    input_dir = '../NCDS_2004'
    fn = os.path.join(input_dir, 'NCDS_2004_tables_version5.xlsx') 
    # creating pandas.io.excel.ExcelFile object
    xl = pd.ExcelFile(fn)
    #  generate a dictionary of DataFrames
    dfs = {sh:xl.parse(sh) for sh in xl.sheet_names}

    for sheet_name in dfs.keys():
        print(sheet_name)

    fn_end = os.path.join(input_dir, 'NCDS_2004_tables_version8_1.xlsx') 
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

    """
    5. Loops
    """
    df_loops = dfs_end['Loops']
    df_loops.rename(columns={'Start point of the loop': 'Order', 'End point of the loop': 'End'}, inplace=True)
    df_loops['source'] = 'Loops'


    """
    position of question/condition/loop
	- Need to have a end position for condition/loop, this probably should be done at parsing questionnaire stage and manually reviewed 
	- from current excel file, assume
		- every condition/loop will follow by one question, unless all questions have similar name
    """

    keep_columns = ['Order', 'End', 'Label', 'source', 'section_id']
    df_all = pd.concat([df_sequences.loc[:, keep_columns], df_questions.loc[:, keep_columns], df_conditions.loc[:, keep_columns], df_loops.loc[:, keep_columns]])
    df_all = df_all.sort_values('Order').reset_index()

    # position within conditions	
    c_start = 0
    c_end = 0
    c_label = ''
    for index, row in df_all.iterrows():    
        if row['source'] == 'Conditions' and row['End'] > 0:
            c_start = row['Order']
            c_end = row['End']
            c_label = row['Label']
        
        c_start_curr = c_start
        c_end_curr = c_end
        c_label_curr = c_label

        if row['Order'] > c_start_curr and row['Order'] < c_end_curr:
            df_all.at[index, 'above_condition'] = c_label_curr
 
    # condition mask
    mask_conditions = df_all['above_condition'].notnull()
    df_all['c_position'] = df_all[mask_conditions].groupby('above_condition').cumcount() + 1

    # position within loops	
    l_start = 0
    l_end = 0
    l_label = '' 
    for index, row in df_all.iterrows():    
        if row['source'] == 'Loops' and row['End'] > 0:
            l_start = row['Order']
            l_end = row['End']
            l_label = row['Label']
        
        l_start_curr = l_start
        l_end_curr = l_end
        l_label_curr = l_label

        if row['Order'] > l_start_curr and row['Order'] < l_end_curr:
            df_all.at[index, 'above_loop'] = l_label_curr	

    # loop mask
    mask_loops = df_all['above_loop'].notnull()
    df_all['l_position'] = df_all[mask_loops].groupby(['above_loop', 'above_condition']).cumcount() + 1

    # order within section
    mask_section = ~((df_all['section_id'] >= 1) | (df_all['c_position'] >= 1) | (df_all['l_position'] >= 1))
    df_all.loc[:, 'section_id'] = df_all.loc[:, 'section_id'].ffill()
    df_all['section_position'] = df_all[mask_section].groupby('section_id').cumcount() + 1 

    df_sequences_m = df_sequences[['Label', 'section_id']]
    df_sequences_m.rename(columns={'Label': 'section_label'}, inplace=True)
    df_all_new = pd.merge(df_all, df_sequences_m, how='left', on=['section_id'])

    df_all_new['Position'] = df_all_new.apply(lambda x: max(x['section_id'], x['c_position'], x['section_position']) if x['l_position'] != 1 else 1, axis=1)
    df_all_new['above_condition'] = df_all_new['above_condition'].fillna("")
    df_all_new['above_loop'] = df_all_new['above_loop'].fillna("")
    df_all_new['above_label'] = df_all_new.apply(lambda x: x['above_condition'] if len(x['above_condition']) > 0 else x['above_loop'] if len(x['above_loop']) > 0 else x['section_label'], axis = 1)
    df_all_new['parent_type'] = df_all_new.apply(lambda x: 'CcCondition' if len(x['above_condition']) > 0 else 'CcLoop' if len(x['above_loop']) > 0 else 'CcSequence', axis = 1)

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
