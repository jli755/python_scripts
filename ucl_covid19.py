#!/bin/env python

"""
    Python 3
    Go through each tab of Nimal's excel sheet, create database input files
"""

import os
import pandas as pd
import numpy as np
from datetime import date

def main():
    input_dir = '../Jenny_ucl/ucl_covid19'
    fn = os.path.join(input_dir, 'Covid-19_version4_Hayley.xls') 
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
    # print(df_codes['cat'].unique())
    df_codes['cat_new'] = df_codes['cat'].astype(str).str.replace('(', '').astype(int)
    df_codes['label'] = df_codes['label'].str.rstrip()
    # add order
    df_codes['codes_order'] = df_codes.groupby('label').cumcount() + 1

    df_codes = df_codes.sort_values(['label', 'codes_order'])

    df_codes.drop(['cat'], axis=1, inplace=True)
    df_codes.rename(columns={'cat_new': 'Value', 'val': 'Category', 'label': 'Label'}, inplace=True)

    """
    2. Sequences
    """
    df_sequences = dfs['Sequence_start_end']
    df_sequences['source'] = 'Sequences'
    # add sequence id
    df_sequences['section_id'] = df_sequences.index + 1
    df_sequences.rename(columns={'Block name': 'label', 'End_position': 'end_position'}, inplace=True)

    """
    3. Statements
    """
    df_statements = dfs['Statements']
    df_statements['source'] = 'Statements'

    """
    4. Questions
    """
    df_questions = dfs['Questions']
    df_questions['source'] = 'Questions'
    # sort by column "Number"
    df_questions = df_questions.sort_values('Order')
    # replace 'qc' with 'qi' in Label column
    df_questions['label'] = df_questions['label'].str.replace('qc_', 'qi_')

    # deal with same label name
    df_questions['label'] = df_questions['label'] + '_' + df_questions.groupby('label').cumcount().astype(str)
    df_questions['label'] = df_questions['label'].str.replace('_0', '')

    df_questions['Response_domain'] = df_questions['Response_domain'].str.rstrip()

    """
    5. Response Domain
    """
    df_response = dfs['Response_'].loc[:, ['Label', 'Type', 'Numeric_Type/Datetime_type', 'Min', 'Max']]
    df_response['source'] = 'Response'
    # convert to integer
    df_response['Min'] = df_response['Min'].apply(lambda x: None if pd.isnull(x) else '{0:.0f}'.format(pd.to_numeric(x)))
    df_response['Max'] = df_response['Max'].apply(lambda x: None if pd.isnull(x) else '{0:.0f}'.format(pd.to_numeric(x)))


    """
    Find parent and position
    """
    df_questions_p = df_questions.loc[:, ['Order', 'label', 'source']]
    df_questions_p.rename(columns={'Order': 'start_position'}, inplace=True)
    df_statements_p = df_statements.loc[:, ['Order', 'Label', 'source']]
    df_statements_p.rename(columns={'Order': 'start_position', 'Label': 'label'}, inplace=True)

    df_all = pd.concat([df_sequences.loc[:, ['start_position', 'end_position', 'label', 'source']], df_questions_p, df_statements_p])
    df_all = df_all.sort_values('start_position').reset_index()

    df_all['above_label'] = df_all.apply(lambda row: row['label'] if row['source'] == 'Sequences' else None, axis=1)
    df_all.loc[:, 'above_label'] = df_all.loc[:, 'above_label'].ffill()
    df_all['parent_type'] = 'CcSequence'
    df_all['Position'] = df_all.groupby('above_label').cumcount()

    df_all.to_csv(os.path.join(input_dir, 'ALL_ORDER.csv'), encoding='utf-8', index=False)
 
    # csv
    df_questions_new = pd.merge(df_questions, df_all, how='left', left_on = ['Order', 'label'], right_on=['start_position', 'label'])
    questions_keep = ['label', 'Literal', 'Instructions', 'Response_domain', 'above_label', 'parent_type', 'Position']
    df_questions_new[questions_keep].to_csv(os.path.join(input_dir, 'questions.csv'), encoding='utf-8', index=False, sep=';')

    df_statements_new = pd.merge(df_statements, df_all, how='left', left_on = ['Order', 'Label'], right_on=['start_position', 'label'])
    statements_keep = ['Label', 'Literal', 'above_label', 'parent_type', 'Position']
    df_statements_new[statements_keep].to_csv(os.path.join(input_dir, 'statements.csv'), encoding='utf-8', index=False, sep=';')

    df_sequences.drop(['source', 'start_position', 'end_position'], 1).to_csv(os.path.join(input_dir, 'sequences.csv'), encoding='utf-8', index=False, sep=';')
    df_response.drop('source', 1).to_csv(os.path.join(input_dir, 'response.csv'), encoding='utf-8', index=False, sep=';')
    df_codes.drop('source', 1).to_csv(os.path.join(input_dir, 'codes.csv'), encoding='utf-8', index=False, sep=';')


if __name__ == '__main__':
    main()
