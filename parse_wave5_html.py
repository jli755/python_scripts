#!/bin/env python
# -*- coding: utf-8 -*-

"""
    Parse wave 5 html file:
"""

from collections import OrderedDict
from lxml import etree
import pandas as pd
import numpy as np
import os
import re


def html_to_tree(htmlFile):
    """
        Input: html file
        Output: dictionary
		# questions are in r['html']['body']['div'][1]['div'][2]['div']['html']['body'].keys()
    """
    parser = etree.HTMLParser()
    with open(htmlFile, "rt") as f:
        tree = etree.parse(f, parser)
    return tree


def get_class(tree, search_string, t='*'):
    """
    get line numbers and text from html elements of type t (default to *) with class name = search_string
    """
    dicts = []
    for elem in tree.xpath("//{}[contains(@class, '{}')]".format(t, search_string)):
        L = list(elem.itertext())
        s = "".join(L).strip()

        # hack to rescure some
        if ' ©' in s and search_string == 'Standard':
            search_string = 'SectionNumber'
        else:
            search_string = 'Standard'

        strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        s = strip_unicode.sub('', s)

        if s:
            dicts.append({"source": search_string, 
                          "sourceline": elem.sourceline, 
                          "title": s})
    return pd.DataFrame(dicts)


def get_SequenceNumber(tree):
    """
    get line numbers and text from html elements of type 'h1' (SequenceNumber)
    """
    dicts = []
    for elem in tree.xpath("//h1"):
        L = list(elem.itertext())
        s = "".join(L).strip()        
        strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        s = strip_unicode.sub('', s)
        if s:
            dicts.append({"source": 'SequenceNumber', 
                          "sourceline": elem.sourceline, 
                          "title": s})
    return pd.DataFrame(dicts)


def get_SectionNumber(tree):
    """
    get line numbers and text from html elements of type 'h2' (SectionNumber)
    """
    dicts = []
    for elem in tree.xpath("//h2"):
        L = list(elem.itertext())
        s = "".join(L).strip()        
        strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        s = strip_unicode.sub('', s)

        if s:
            if s == '{If studying for at least one Edexcel, BTEC or LQL qualification (EdExNo > 0)}':
                dicts.append({"source": 'Condition', 
                              "sourceline": elem.sourceline, 
                              "title": s})
            elif s == 'TO BE ASKED OF EVERY JOB OR PERIOD OF ACTIVITY SINCE WAVE 4 INTERVIEW MONTH (IF COMPLETED WAVE 4 INTERVIEW) OR SINCE SEPTEMBER 2006 (IF NOT INTERVIEWED IN WAVE 4)':
                dicts.append({"source": 'Standard', 
                              "sourceline": elem.sourceline, 
                              "title": s})
            else:
                dicts.append({"source": 'SectionNumber', 
                              "sourceline": elem.sourceline, 
                              "title": s})
    return pd.DataFrame(dicts)

	
def get_questionnaire(tree):
    """
    combine individual parts, return questionnaire dataframe
    'Heading1Char' has duplicated sequence information
    """
    df_SequenceNumber = get_SequenceNumber(tree)
    df_SectionNumber = get_SectionNumber(tree)
    df_Heading1Char = get_class(tree,'Heading1Char')
    df_PlainText = get_class(tree, 'PlainText')
    df_QuestionText = get_class(tree, 'QuestionText')
    df_Standard = get_class(tree, 'Standard')
    df_AnswerText = get_class(tree, 'AnswerText')
    df_Filter = get_class(tree, 'Filter')
    # listlevel with different number
    df_listlevel1WW8Num = get_class(tree, 'listlevel1WW8Num')
    # split string into multiple rows
    df_listlevel = df_listlevel1WW8Num.assign(title=df_listlevel1WW8Num['title'].str.split('\n')).explode('title')
    df_listlevel['seq'] = df_listlevel.groupby(['source', 'sourceline']).cumcount() + 1
    df_listlevel['source'] = 'listlevel1WW8Num'
    
    # df_Footnote = get_class(tree, 'Footnote')   
    # df_FootnoteSymbol = get_class(tree, 'FootnoteSymbol')

    df = pd.concat([df_SequenceNumber,
                    df_SectionNumber,
                    df_Heading1Char,
                    df_PlainText,
                    df_QuestionText,
                    df_Standard,
                    df_AnswerText,
                    df_Filter,
                    df_listlevel
                 ])
    df['seq'].fillna('0', inplace=True)
    
    df.sort_values(by=['sourceline', 'seq'], inplace=True)

    df = df.apply(lambda x: x.replace('U+00A9',''))

    df['source_new'] = df.apply(lambda row: 'codelist' if (row['title'][0].isdigit() == True and row['source'] in ['Standard', 'PlainText'])
                                                       else row['source'], axis=1)
    df['seq_new'] = df.apply(lambda row: row['title'].split('.')[0] if (row['source_new'] == 'codelist' and '.' in row['title']) 
                                         else row['title'].split(' ')[0] if (row['source_new'] == 'codelist' and '.' not in row['title']) 
                                         else row['seq'] , axis=1) 
    
    df.drop(['source', 'seq'], axis=1, inplace=True)
    df['source'] = df.apply(lambda row: row['source_new'] if row['source_new'] != 'listlevel1WW8Num' else 'codelist' , axis=1) 
    df['seq'] = df['seq_new']
    df.drop(['source_new', 'seq_new'], axis=1, inplace=True)

    df = df[pd.notnull(df['title'])]

    df['title'] = df['title'].replace('\s+', ' ', regex=True)
    df['title'] = df['title'].str.lstrip()
    df.drop_duplicates(keep = 'first', inplace = True)

    # remove {Ask all}, Refused, Dont know, Dont Know
    new_df_1 = df[~df['title'].str.lower().str.contains('ask all')]
    new_df = new_df_1.loc[(new_df_1['title'] != 'Refused') & (new_df_1['title'] != 'Dont know') & (new_df_1['title'] != 'Dont Know'), :]
    # special case:
    new_df['condition_source'] = new_df.apply(lambda row: 'Condition' if any(re.findall(r'{Ask if|{If|{\(If|\(If|{ If|If claiming sickness', row['title'], re.IGNORECASE)) else row['source'], axis=1)
    new_df['new_source'] = new_df.apply(lambda row: 'Instruction' if ((row['title'].isupper() == True or 'INTERVIEWER' in row['title']) and row['source'] not in ['SequenceNumber', 'SectionNumber']) else row['condition_source'], axis=1)

    question_list = ['YOUNG PERSON BENEFITS', 'Benfts', 'BenftsO', 'Chiben', 'UnEmBen', 'JSATyp', 'IncSup', 'SkDsBn', 
                     'Family', 'HSING', 'CCTC', 'FinCour', 'Mainmeth2', 'MainMeth2O', 'CintroO']
    new_df['question_source'] = new_df.apply(lambda row: 'SectionNumber' if row['title'] in question_list else row['new_source'], axis=1)

    new_df['response_source'] = new_df.apply(lambda row: 'Response' if any(re.findall(r'Numeric|Open answer|OPEN ENDED', row['title'], re.IGNORECASE)) else row['question_source'], axis=1)

    new_df.drop(['source', 'condition_source', 'new_source', 'question_source'], axis=1, inplace=True)

    new_df.rename(columns={'response_source': 'source'}, inplace=True)
    return new_df

 
def f(string, match):
    """
    Find a word containts '/' in a string
    """
    string_list = [s for s in string.split(' ') if '/' in s]
    match_list = []
    for word in string_list:
        if match in word:
            match_list.append(word)
    return match_list[0]


def get_question_grids(df_questionnaire):
    """
    Build questions table 
        - sourceline
        - Label
        - Literal
        - Instructions
        - horizontal_code_list_name
        - vertical_code_list_name
        - source
    """
   
    df_question_grid_name = df_questionnaire.loc[(df_questionnaire['title'].str.contains('LOOPED')), :]
    df_question_grid_name['vertical_codes'] = df_question_grid_name['title'].apply(lambda x: f(x, '/'))
    df_question_grid_name['vertical_code_list_name'] = 'cs_' + df_question_grid_name['vertical_codes'].str.replace('/', '')
    df_question_grid_name['horizontal_code_list_name'] = 'cs_' + df_question_grid_name['questions']

    df_question_grid = df_questionnaire.loc[df_questionnaire['questions'].isin(df_question_grid_name['questions']), :]

    df_question_grid_literal = df_question_grid.loc[df_question_grid['source'] == 'Standard', ['questions', 'title']]
    df_question_grid_literal_combine = df_question_grid_literal.groupby('questions')['title'].apply('\n'.join).reset_index()

    df_1 = df_question_grid_name[['questions', 'sourceline', 'vertical_code_list_name', 'horizontal_code_list_name']].merge(df_question_grid_literal_combine[['questions', 'title']], on='questions', how='left')

    df_1.rename(columns={'title': 'Literal'}, inplace=True)

    df_question_instruction = df_question_grid.loc[df_question_grid['source'] == 'Instruction', ['questions', 'title']]
    df_question_instruction_combine = df_question_instruction.groupby('questions')['title'].apply('\n'.join).reset_index()

    df_question_grids = df_1.merge(df_question_instruction_combine[['questions', 'title']], on='questions', how='left')
    df_question_grids.rename(columns={'title': 'Instructions'}, inplace=True)
    df_question_grids['Label'] = 'qg_' + df_question_grids['questions']
    df_question_grids.drop(['questions'], axis=1, inplace=True)

   
    # vertical code 
    df_qg_codes = df_question_grid_name.loc[:, ['vertical_code_list_name', 'vertical_codes']]
    df_qg_codes = df_qg_codes.drop_duplicates()

    df_qg_codes = (df_qg_codes.set_index(['vertical_code_list_name']).apply(lambda x: x.str.split('/').explode()).reset_index()) 

    df_qg_codes.rename(columns={'vertical_code_list_name': 'Label', 'vertical_codes': 'Category'}, inplace=True)
    df_qg_codes['codes_order'] = df_qg_codes.groupby(['Label']).cumcount() + 1
    df_qg_codes['value'] = ''
    df_qg_codes['Number'] = ''

    return df_question_grids, df_qg_codes


def get_question_items(df):
    """
    Build questions table 
        - Label
        - Literal
        - Instructions
        - Response domain
        - above_label
        - parent_type
        - branch
        - Position
    """

    # find each question
    df_question_name = df.loc[(df.source == 'SectionNumber'), ['sourceline', 'questions']]
    
    df_question_literal = df.loc[df['source'] == 'Standard', ['questions', 'title']]
    df_question_literal_combine = df_question_literal.groupby('questions')['title'].apply('\n'.join).reset_index()

    df_1 = df_question_name.merge(df_question_literal_combine[['questions', 'title']], on='questions', how='left')
    df_1.rename(columns={'title': 'Literal'}, inplace=True)

    df_question_instruction = df.loc[df['source'] == 'Instruction', ['questions', 'title']]
    df_question_instruction_combine = df_question_instruction.groupby('questions')['title'].apply('\n'.join).reset_index()

    df_question = pd.merge(df_1, df_question_instruction_combine, how='left', on=['questions'])
    df_question.rename(columns={'title': 'Instructions'}, inplace=True)

    # ignore footnote for now, it could be 'instruction'

    # responds
    # 1. codelist
    df_question_code = df.loc[df['source'] == 'codelist', ['questions']].drop_duplicates()
    df_question_code['Response'] = 'cs_' + df_question_code['questions']

    # 2. Response
    df_question_response = df.loc[df['source'] == 'Response', ['questions', 'title']].drop_duplicates()
    df_question_response.rename(columns={'title': 'Response'}, inplace=True)

    df_response = pd.concat([df_question_code, df_question_response])

    df_question_all = pd.merge(df_question, df_response, how='left', on=['questions'])


    # all questions
    df_question_all.sort_values(by=['sourceline'], inplace=True)
    
    df_question_all['source'] = 'question'
    #df_question_all['Label'] = 'qi_' + df_question['questions']
    df_question_all['Label'] = df_question_all.groupby('questions').questions.apply(lambda n: 'qi_' + n.str.strip() + '_' + (np.arange(len(n))).astype(str))
    df_question_all['Label'] = df_question_all['Label'].str.strip('_0')
    
    return df_question_all
 

def int_to_roman(num):

    roman = OrderedDict()
    roman[1000] = "m"
    roman[900] = "cm"
    roman[500] = "d"
    roman[400] = "cd"
    roman[100] = "c"
    roman[90] = "xc"
    roman[50] = "l"
    roman[40] = "xl"
    roman[10] = "x"
    roman[9] = "ix"
    roman[5] = "v"
    roman[4] = "iv"
    roman[1] = "i"

    def roman_num(num):
        for r in roman.keys():
            x, y = divmod(num, r)
            yield roman[r] * x
            num -= (r * x)
            if num <= 0:
                break
    if num == 0:
        return "0"
    else:
        return "".join([a for a in roman_num(num)])
   

def get_conditions(df):
    """
    Build conditions table 
    """
    df_conditions = df.loc[(df.source == 'Condition'), ['sourceline', 'questions', 'title']]

    df_conditions['Logic_name'] = df_conditions['title'].apply(lambda x: re.findall(r"(\w+) *(=|>|<)", x) ) 
    df_conditions['Logic_name1'] = df_conditions['Logic_name'].apply(lambda x: '' if len(x) ==0 else x[0][0])
    df_conditions['Logic_name2'] = df_conditions.apply(lambda row: row['questions'].strip() if (row['Logic_name1'].isdigit() or row['Logic_name1'] == '') else row['Logic_name1'].strip(), axis = 1)
    df_conditions['tmp'] = df_conditions.groupby('Logic_name2')['Logic_name2'].transform('count')
    df_conditions['tmp2'] = df_conditions.groupby('Logic_name2').cumcount()
    
    df_conditions['Logic_name_new'] = df_conditions['Logic_name2'].str.cat(df_conditions['tmp2'].astype(str), sep="_")

    df_conditions['Logic_c'] = df_conditions['title'].apply(lambda x: re.findall('(?<=\().*(?=\))', x))
    df_conditions['Logic_c1'] = df_conditions['Logic_c'].apply(lambda x: '' if len(x) ==0 else x[0])
    
    df_conditions['Logic_r'] = df_conditions['Logic_c1'].str.replace('=', ' == ').str.replace('<>', ' != ').str.replace(' OR ', ' || ').str.replace(' AND ', ' && ').str.replace(' or ', ' || ').str.replace(' and ', ' && ')

  #  df_conditions.drop(['Logic_name', 'Logic_name1', 'tmp', 'tmp2', 'Logic_c', 'Logic_c1'], axis=1, inplace=True)

    df_conditions['Logic_name_roman'] = df_conditions['Logic_name_new'].apply(lambda x: '_'.join([x.split('_')[0], int_to_roman(int(x.split('_')[1]))]))
    df_conditions['Logic_name_roman'] = df_conditions['Logic_name_roman'].str.strip('_0')
  
    df_conditions['Label'] = 'c_q' + df_conditions['Logic_name_roman']

    # rename inside 'logic', add qc_
    df_conditions['Logic'] = df_conditions.apply(lambda row: row['Logic_r'].replace(row['Logic_name2'], 'qc_' + row['Logic_name2']) if (row['Logic_name2'] in row['Logic_r']) else row['Logic_r'], axis = 1)

    df_conditions.rename(columns={'title': 'Literal'}, inplace=True)
    df_conditions = df_conditions.drop(['Logic_c', 'Logic_c1', 'Logic_r', 'Logic_name', 'Logic_name1', 'tmp', 'tmp2', 'Logic_name2', 'Logic_name_new', 'Logic_name_roman'], 1)


    return df_conditions
 
     
def main():
    input_dir = '../LSYPE1/wave5-html'
    htmlFile = os.path.join(input_dir, 'YP-W5-S2_FINAL_F2F - Questionnaire.htm')
    tree = html_to_tree(htmlFile)

    title = tree.xpath('//title')[0].text
    print(title)

    df = get_questionnaire(tree)
    	
    # find each question
    df['questions'] = df.apply(lambda row: row['title'] if row['source'] in ['SectionNumber'] else None, axis=1)
    df['questions'] = df['questions'].ffill()
    # actual questionnaire
    df = df.loc[(df.sourceline >= 105) & (df.sourceline < 6110), :]
    df.to_csv('../LSYPE1/wave5-html/YP-W5-final_attempt.csv', sep= ';', encoding = 'utf-8', index=False)

    # 1. Codes
    df_codes = df.loc[(df.source == 'codelist') , ['questions', 'sourceline', 'seq', 'title']]
    # label
    df_codes['Label'] = 'cs_' + df_codes['questions']
    df_codes.rename(columns={'sourceline': 'Number', 'seq': 'codes_order'}, inplace=True)
    df_codes['value'] = df_codes['codes_order']

    # strip number. out from title
    df_codes['Category'] = df_codes['title'].apply(lambda x: x.split('.')[1].lstrip() if '.' in x else x)
    df_codes_out = df_codes.drop(['questions', 'title'], 1)

    # need to add codes from question grid before write out
    #df_codes_out.to_csv('../LSYPE1/wave5-html/codes.csv', encoding = 'utf-8', index=False)	

    # 2. Response: numeric, text, datetime	
    df_response = df.loc[(df.source == 'Response') , ['questions', 'sourceline', 'seq', 'title']]

    df_response['Type'] = df_response['title'].apply(lambda x: 'Numeric' if any (c in x for c in ['Numeric', 'RANGE']) else 'Text')
    df_response['Numeric_Type/Datetime_type'] = df_response['title'].apply(lambda x: 'Integer' if any (c in x for c in ['Numeric', 'RANGE']) else '')
    df_response['Min'] = df_response['title'].apply(lambda x: re.findall(r'\d+', x)[0] if len(re.findall(r'\d+', x)) == 2
                                                              else None)
    df_response['Max'] = df_response['title'].apply(lambda x: re.findall(r'\d+', x)[-1] if len(re.findall(r'\d+', x)) >= 1 else None)
    df_response.loc[df_response['questions'] == 'Wrkch5', ['Numeric_Type/Datetime_type']] = 'float'
    df_response.loc[df_response['questions'] == 'Wrkch5', ['Min']] = '0.01'
    df_response.loc[df_response['questions'] == 'Wrkch5', ['Max']] = '999999.99'

    df_response.rename(columns={'title': 'Label'}, inplace=True)

    # de-dup
    response_keep = ['Label', 'Type', 'Numeric_Type/Datetime_type', 'Min', 'Max']
    df_response_sub = df_response.loc[:, response_keep]
    df_response_sub.drop_duplicates().to_csv('../LSYPE1/wave5-html/response.csv', sep= ';', encoding = 'utf-8', index=False)

    	
    # 3. Question grids
    df_question_grids, df_qg_codes = get_question_grids(df)
    df_question_grids.to_csv('../LSYPE1/wave5-html/df_qg.csv', sep = ';', encoding = 'utf-8', index=False)

    df_codes_out['codes_order'] = df_codes_out['codes_order'].astype(int)
    df_codes_out['value'] = df_codes_out['value'].astype(int)
    df_codes_final = df_codes_out.append(df_qg_codes, ignore_index=True)
    df_codes_final.to_csv('../LSYPE1/wave5-html/codes.csv', sep = ';', encoding = 'utf-8', index=False)
    # add one more line here for question grids
    with open('../LSYPE1/wave5-html/codes.csv', 'a') as file:
        file.write('-;-;;1;1\n')


    # 4. Question items
    # minus question grids
    df_all_questions = df[~df['questions'].isin(df_question_grids['Label'].str.replace('qg_', ''))]

    df_question_items = get_question_items(df_all_questions)
    #df_question_items.to_csv('../LSYPE1/wave5-html/df_qi.csv', sep = ';', encoding = 'utf-8', index=False)


    # 5. Sequences
    df_sequences = df.loc[(df.source == 'SequenceNumber'), :]
    df_sequences.rename(columns={'title': 'Label'}, inplace=True)
    df_sequences['section_id'] = df_sequences.index + 1
    df_sequences.loc[:, ['sourceline', 'Label', 'section_id']].to_csv('../LSYPE1/wave5-html/sequences.csv', sep = ';', encoding = 'utf-8', index=False)
	

    # 6. Conditions
    df_conditions = get_conditions(df)
    df_conditions.to_csv('../LSYPE1/wave5-html/df_conditions.csv', sep = ';', encoding = 'utf-8', index=False)

    
    # 7. Find parent label
    df_sequences_p = df_sequences.loc[:, ['sourceline', 'Label']]
    df_sequences_p['source'] = 'CcSequence'
    df_questions_items_p = df_question_items.loc[:, ['sourceline', 'Label']]
    df_questions_items_p['source'] = 'CcQuestions'
    df_questions_grids_p = df_question_grids.loc[:, ['sourceline', 'Label']]
    df_questions_grids_p['source'] = 'CcQuestions'
    df_conditions_p = df_conditions.loc[:, ['sourceline', 'Label']]
    df_conditions_p['source'] = 'CcCondition'
    
    df_sequences_p_1 = pd.DataFrame([[0, 'LSYPE_Wave_5', 'CcSequence']], columns=['sourceline', 'Label', 'source']) 	

    df_parent = pd.concat([df_sequences_p, df_questions_items_p, df_questions_grids_p, df_conditions_p, df_sequences_p_1]).reset_index()
    df_parent = df_parent.sort_values(by=['sourceline']).reset_index()

    # hack to get intro before the first sequence
#    l = df_parent.index[df_parent['source'] == 'CcSequence'].tolist()
#    df_sequence_position = df_parent.iloc[[x for x in range(l[0], l[1]+1)] + l[2:], :]
    df_sequence_position = df_parent
    df_sequence_position['Position'] = range(0, len(df_sequence_position))
    df_sequence_position.to_csv('../LSYPE1/wave5-html/df_sequence_position.csv', sep = ';', encoding = 'utf-8', index=False)
    
    df_sequences_out = df_sequence_position.loc[(df_sequence_position['source'] == 'CcSequence') & (df_sequence_position['Label'] != 'LSYPE_Wave_5'), :]
    df_sequences_out.rename(columns={'Position': 'section_id'}, inplace=True)
    df_sequences_out.loc[:, ['sourceline', 'Label', 'section_id']].to_csv('../LSYPE1/wave5-html/sequences.csv', sep = ';', encoding = 'utf-8', index=False)

    # assume one condition has one question
    df_parent['source_lagged'] = df_parent['source'].shift(1)
    df_parent['Label_lagged'] = df_parent['Label'].shift(1)
    df_parent['parent_c'] = df_parent.apply(lambda row: row['source_lagged'] if row['source_lagged'] == 'CcCondition' and row['source'] == 'CcQuestions' else None, axis=1)
    df_parent['above_c'] = df_parent.apply(lambda row: row['Label_lagged'] if row['source_lagged'] == 'CcCondition' and row['source'] == 'CcQuestions' else None, axis=1)
    df_parent['parent_s'] = df_parent.apply(lambda row: 'CcSequence' if row['source'] =='CcSequence' else None, axis=1)
    df_parent['above_s'] = df_parent.apply(lambda row: row['Label'] if row['source'] =='CcSequence' else None, axis=1)
    df_parent['parent_s'] = df_parent['parent_s'].ffill()
    df_parent['above_s'] = df_parent['above_s'].ffill() 
    df_parent['parent_type'] = df_parent.apply(lambda row: row['parent_c'] if row['parent_c'] is not None else row['parent_s'], axis=1)
    df_parent['above_label'] = df_parent.apply(lambda row: row['above_c'] if row['above_c'] is not None else row['above_s'], axis=1)

    df_parent['Position'] = df_parent['parent_c'].apply(lambda x: 1 if x is not None else None)

    # mask
    mask = df_parent['Position'].isnull()
    df_parent['Position'][mask] = df_parent[mask].groupby(['above_label']).cumcount() 
    df_parent['branch'] = 0
    df_parent['Position'] = df_parent['Position'].astype(int)
 
    df_parent.to_csv('../LSYPE1/wave5-html/df_parent.csv', sep = ';', encoding = 'utf-8', index=False)

    # output csv
    df_questions_new = pd.merge(df_question_items, df_parent, how='left', on=['sourceline', 'Label'])
    questions_keep = ['Label', 'Literal', 'Instructions', 'Response', 'above_label', 'parent_type', 'branch', 'Position']
    df_questions_new[questions_keep].to_csv(os.path.join(input_dir, 'question_items.csv'), encoding='utf-8', index=False, sep = ';')
 
    df_question_grids_new = pd.merge(df_question_grids, df_parent, how='left', on=['sourceline', 'Label'])
    question_grids_keep = ['Label', 'Literal', 'Instructions', 'horizontal_code_list_name', 'vertical_code_list_name', 'above_label', 'parent_type', 'branch', 'Position']
    df_question_grids_new[question_grids_keep].to_csv(os.path.join(input_dir, 'question_grids.csv'), sep = ';', encoding='utf-8', index=False)
 
    df_conditions_new = pd.merge(df_conditions, df_parent, how='left', on=['sourceline', 'Label'])

    conditions_keep = ['Label', 'Literal', 'Logic', 'above_label', 'parent_type', 'branch', 'Position']
    df_conditions_new[conditions_keep].to_csv(os.path.join(input_dir, 'conditions.csv'), sep = ';', encoding='utf-8', index=False)
	

if __name__ == "__main__":
    main()



