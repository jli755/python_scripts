#!/bin/env python

"""
    Python 3
    Go through each tab of Nimal's excel sheet, create database input files
"""

from datetime import date
import pandas as pd
import numpy as np
import os


def isNaN(num):
    return num != num


def find_parent(start, stop, df_mapping, source, section_label):
    """
        Find the parent label and parent source
    """
    if isNaN(stop):
        df = df_mapping.loc[(df_mapping.start_position < start) & (df_mapping.end_position > start), :]
    else:
        df = df_mapping.loc[(df_mapping.start_position < start) & (df_mapping.end_position > stop), :]

    if source == 'Sequences':
        return section_label
    elif not df.empty:
        df['dist'] = start - df['start_position']
        df_r = df.loc[df['dist'].idxmin()]
        return df_r['Label']
    else:
        return section_label


def get_new_label(df):
    """
        Go though codes table, find re-used codes
    """
    label_dict = {}
    codes_dict = {}

    for old_label in df['Label'].unique():
        # print(old_label)
        df_codes = df.loc[(df.Label == old_label), ['Code_Order', 'Code_Value', 'Category']].reset_index(drop=True)

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


def update_codelist(df_codelist, df_qi):
    """
        Update codelist, one codelist can be used for multiple questions
    """

    label_dict, codes_dict = get_new_label(df_codelist)
    df_codes_dict = pd.concat(codes_dict, axis=0).reset_index().drop('level_1', 1)
    df_codes_dict.rename(columns={'level_0': 'Label'}, inplace=True)

    df_qi['Response_domain'].update(pd.Series(label_dict))

    return df_codes_dict, df_qi


def main():
    input_dir = '../Jenny_ucl/generations_scotland_covid19'

    output_dir = os.path.join(input_dir, "archivist_tables")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    fn = os.path.join(input_dir, 'Generation_Scotland (Tables - Ver2).xls') 
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

    df_codes.rename(columns={'Value': 'Code_Value'}, inplace=True)

    df_codes['Label'] = df_codes['Label'].str.rstrip()

    # add order
    df_codes['Code_Order'] = df_codes.groupby('Label').cumcount() + 1

    df_codes['Code_Value'] = df_codes['Code_Value'].apply(lambda x: x if pd.isnull(x) else int(x))

    df_codes = df_codes.sort_values(['Label', 'Code_Order'])

    codes_cols = ['Label', 'Code_Order', 'Code_Value', 'Category', 'source']
    df_codes = df_codes[codes_cols]

    """
    2. Sequences
    """
    df_sequences = dfs['Sequence']
    df_sequences['source'] = 'Sequences'
    # add sequence id
    df_sequences['section_id'] = df_sequences.index + 1
    df_sequences.rename(columns={'Lieral': 'Label', 'End': 'end_position', 'Start': 'start_position'}, inplace=True)

    sequences_cols = ['start_position', 'end_position', 'Label', 'source']
    df_sequences = df_sequences[sequences_cols]
    df_sequences = df_sequences.sort_values('start_position').reset_index()
    
    # add sequence id
    df_sequences['section_id'] = df_sequences.index + 1


    """
    3. Statements
    """
    df_statements = dfs['Statements']
    df_statements['source'] = 'Statements'
    df_statements['Literal'] = df_statements['Literal'].str.lstrip()                                                                                            
    df_statements.rename(columns={'Order': 'start_position'}, inplace=True)

    """
    4. Questions
    """
    df_questions = dfs['Questions']
    df_questions['source'] = 'Questions'
    df_questions['Label'] = df_questions['Label'].str.replace('qc_', 'qi_')

    # deal with same Label name
    df_questions['Label'] = df_questions['Label'] + '_' + df_questions.groupby('Label').cumcount().astype(str)
    df_questions['Label'] = df_questions['Label'].str.replace('_0', '')

    # sort by column "Number"
    df_questions = df_questions.sort_values('Order')
    df_questions['Response_domain'] = df_questions['Response_domain'].str.rstrip()

    # In the questions table you will find two new columns to note min and max of the cardinality. 
    df_questions.rename(columns={'Order': 'start_position', 'min': 'min_responses', 'max': 'max_responses'}, inplace=True)

    questions_cols = ['start_position', 'Literal', 'Label', 'Instructions', 'Response_domain', 'min_responses', 'max_responses', 'source']
    df_questions = df_questions[questions_cols]

    df_questions['min_responses'] = df_questions['min_responses'].fillna(1)
    df_questions['max_responses'] = df_questions['max_responses'].fillna(1)
    df_questions[['min_responses', 'max_responses']] = df_questions[['min_responses', 'max_responses']].astype(int)


    """
    5. Response Domain
    """
    df_response = dfs['Response Domain']
    df_response['source'] = 'Response'
    df_response['Type'] = df_response['Type'].fillna('Numeric')
    df_response['Numeric_Type/Datetime_type'] = df_response.apply(lambda row: 'Integer' if row['Label'].startswith('Range') else row['Numeric_Type/Datetime_type'], axis=1)
    df_response['Format'] = ''

    """
    6. Conditions
    """
    df_conditions = dfs['Conditions']
    df_conditions['source'] = 'Conditions'
    df_conditions.rename(columns={'End': 'end_position', 'Start': 'start_position', 'Branch': 'if_branch'}, inplace=True)

    # dict branch
    dict_if_branch = dict(zip(df_conditions['Label'], df_conditions['if_branch']))
    print(dict_if_branch)
    print(dict_if_branch['c_q323_i'])


    # clean code list
    df_codes, df_questions = update_codelist(df_codes, df_questions)


    """
    Find parent and position
    """
    df_sequences_p = df_sequences
    df_questions_p = df_questions.loc[:, ['start_position', 'Label', 'source']]
    df_statements_p = df_statements.loc[:, ['start_position', 'Label', 'source']]
    df_conditions_p = df_conditions.loc[:, ['start_position', 'end_position', 'Label', 'source']]

    df_all = pd.concat([df_sequences_p, df_questions_p, df_statements_p, df_conditions_p])
    df_all = df_all.sort_values('start_position').reset_index()

    # sections region
    df_sequences_m = df_sequences[['Label', 'section_id']]
    df_sequences_m.rename(columns={'Label': 'section_label'}, inplace=True)
    df_all_new = pd.merge(df_all, df_sequences_m, how='left', on=['section_id'])
    df_all_new['section_id'] = df_all_new['section_id'].fillna(method='ffill')
    df_all_new['section_label'] = df_all_new['section_label'].fillna(method='ffill')

    df_mapping = df_all_new.loc[ df_all['end_position'] > 0, ['Label', 'source', 'start_position', 'end_position']]

    # find above label
    for index,row in df_all_new.iterrows():
        df_all_new.at[index, 'parent_name'] = find_parent(row['start_position'], row['end_position'], df_mapping, row['source'], row['section_label'])

    # calculate position
    df_all_new['Position'] = df_all_new.groupby('parent_name').cumcount() + 1

    df_all_new['parent_type'] = df_all_new['parent_name'].apply(lambda x: 'CcCondition' if x[0:1] == 'c'  else 'CcLoop' if x[0:1] == 'l' else 'CcSequence')

    df_all_new['Branch'] = df_all_new.apply(lambda row: dict_if_branch[row['parent_name']] if row['parent_type'] == 'CcCondition' else 1, axis=1)

    cols = ['section_id', 'Branch', 'Position']
    df_all_new[cols] = df_all_new[cols].astype(int)
    df_all_new.to_csv(os.path.join(input_dir, 'ALL_ORDER.csv'), encoding='utf-8', index=False)
 
    # csv
    df_questions_new = pd.merge(df_questions, df_all_new, how='left', on=['start_position', 'Label'])
    questions_keep = ['Label', 'Literal', 'Instructions', 'Response_domain',  'min_responses', 'max_responses', 'parent_name', 'parent_type', 'Branch', 'Position']
    df_questions_new[questions_keep].to_csv(os.path.join(output_dir, 'question_item.csv'), encoding='utf-8', index=False, sep=';')

    df_statements_new = pd.merge(df_statements, df_all_new, how='left', on=['start_position', 'Label'])
    statements_keep = ['Label', 'Literal', 'parent_name', 'parent_type', 'Branch', 'Position']
    df_statements_new[statements_keep].to_csv(os.path.join(output_dir, 'statement.csv'), encoding='utf-8', index=False, sep=';')

    df_conditions_new = pd.merge(df_conditions, df_all_new, how='left', on=['start_position', 'Label'])
    conditions_keep = ['Label', 'Literal', 'Logic', 'parent_type', 'parent_name', 'Branch', 'Position']
    df_conditions_new[conditions_keep].to_csv(os.path.join(output_dir, 'condition.csv'), encoding='utf-8', index=False, sep=';')

    df_sequences = df_sequences.drop(['source', 'start_position', 'end_position', 'index'], 1)
    df_sequences.rename(columns={'section_id': 'Position'}, inplace=True)
    df_sequences['Branch'] = 1
    df_sequences.to_csv(os.path.join(output_dir, 'sequence.csv'), encoding='utf-8', index=False, sep=';')

    df_response.drop('source', 1).to_csv(os.path.join(output_dir, 'response.csv'), encoding='utf-8', index=False, sep=';')

    df_codes.to_csv(os.path.join(output_dir, 'codelist.csv'), encoding='utf-8', index=False, sep=';')


if __name__ == '__main__':
    main()
