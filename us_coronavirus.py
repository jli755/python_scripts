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
    input_dir = '../Jenny_ucl/us_coronavirus'
    fn = os.path.join(input_dir, 'US_covid19_Jenny_version2.xlsx') 
    # creating pandas.io.excel.ExcelFile object
    xl = pd.ExcelFile(fn)
    #  generate a dictionary of DataFrames
    dfs = {sh:xl.parse(sh) for sh in xl.sheet_names}

    for sheet_name in dfs.keys():
        print(sheet_name)


    """
    1. Codes
    """
    df_codes = dfs['Code_list']
    df_codes['source'] = 'Codes'

    df_codes.rename(columns={'code': 'Code_Value', 'category': 'Category', 'Codelist_label': 'Label'}, inplace=True)

    df_codes['Label'] = df_codes['Label'].str.rstrip()
    df_codes['Label'] = df_codes['Label'].str.replace('cs_q', 'cs_')
    # add order
    df_codes['Code_Order'] = df_codes.groupby('Label').cumcount() + 1

    df_codes = df_codes.sort_values(['Label', 'Code_Order'])

    codes_cols = ['Label', 'Code_Order', 'Code_Value', 'Category', 'source']
    df_codes = df_codes[codes_cols]

    """
    2. Sequences
    """
    df_sequences = dfs['Sequences']
    df_sequences['source'] = 'Sequences'
    # add sequence id
    df_sequences['section_id'] = df_sequences.index + 1
    df_sequences.rename(columns={'Sequence': 'Label', 'end': 'end_position', 'start': 'start_position'}, inplace=True)

    """
    3. Statements
    """
    df_statements = dfs['Statement']

    # Replacing Header with Top Row
    df_statements.columns = df_statements.iloc[0]
    df_statements = df_statements[1:]

    df_statements['source'] = 'StatementsUnnamed'
    df_statements.rename(columns={'label': 'Label', 'statement': 'Literal'}, inplace=True)

    """
    4. Questions
    """
    df_questions = dfs['Questions']
    # Replacing Header with Top Row
    df_questions.columns = df_questions.iloc[0]
    df_questions = df_questions[1:]

    df_questions['source'] = 'Questions'

    # sort by column "Number"
    df_questions = df_questions.sort_values('Order')

    df_questions.rename(columns={'Question_label': 'Label', 'Response Domain': 'Response_domain', 'Question_literal': 'Literal'}, inplace=True)

    df_questions['Response_domain'] = df_questions['Response_domain'].str.rstrip()


    """
    5. Response Domain
    """
    df_response = dfs['Response domain']
    df_response['source'] = 'Response'
    # convert to integer
    df_response['Min'] = df_response['Min'].apply(lambda x: None if pd.isnull(x) else '{0:.0f}'.format(pd.to_numeric(x)))
    df_response['Max'] = df_response['Max'].apply(lambda x: None if pd.isnull(x) else '{0:.0f}'.format(pd.to_numeric(x)))


    """
    Find parent and position
    """
    df_sequences_p = df_sequences

    df_questions_p = df_questions.loc[:, ['Order', 'Label', 'source']]
    df_questions_p.rename(columns={'Order': 'start_position'}, inplace=True)

    df_statements_p = df_statements.loc[:, ['Order', 'Label', 'source']]
    df_statements_p.rename(columns={'Order': 'start_position'}, inplace=True)

    df_all = pd.concat([df_sequences_p, df_questions_p, df_statements_p])

    df_all = df_all.sort_values('start_position').reset_index()

    df_all['above_label'] = df_all.apply(lambda row: row['Label'] if row['source'] == 'Sequences' else None, axis=1)
    df_all.loc[:, 'above_label'] = df_all.loc[:, 'above_label'].ffill()
    df_all['parent_type'] = 'CcSequence'
    df_all['Position'] = df_all.groupby('above_label').cumcount()

    df_all.to_csv(os.path.join(input_dir, 'ALL_ORDER.csv'), encoding='utf-8', index=False)
 
    # csv
    df_questions_new = pd.merge(df_questions, df_all, how='left', left_on = ['Order', 'Label'], right_on=['start_position', 'Label'])
    questions_keep = ['Label', 'Literal', 'Instructions', 'Response_domain', 'above_label', 'parent_type', 'Position']
    df_questions_new[questions_keep].to_csv(os.path.join(input_dir, 'questions.csv'), encoding='utf-8', index=False, sep=';')
    print(df_statements.columns)
    df_statements_new = pd.merge(df_statements, df_all, how='left', left_on = ['Order', 'Label'], right_on=['start_position', 'Label'])
    statements_keep = ['Label', 'Literal', 'above_label', 'parent_type', 'Position']
    df_statements_new[statements_keep].to_csv(os.path.join(input_dir, 'statements.csv'), encoding='utf-8', index=False, sep=';')

    df_sequences.drop(['source', 'start_position', 'end_position'], 1).to_csv(os.path.join(input_dir, 'sequences.csv'), encoding='utf-8', index=False, sep=';')
    df_response.drop('source', 1).to_csv(os.path.join(input_dir, 'response.csv'), encoding='utf-8', index=False, sep=';')
    df_codes.drop('source', 1).to_csv(os.path.join(input_dir, 'codes.csv'), encoding='utf-8', index=False, sep=';')


if __name__ == '__main__':
    main()
