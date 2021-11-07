#!/bin/env python
# -*- coding: utf-8 -*-

"""
    Parse wave 4 html file, updated from parse wave1
"""

from collections import OrderedDict
from unidecode import unidecode
from lxml import etree
import pandas as pd
import numpy as np
import os
import re


def remove_unmatched_parentheses(input_string):
    """
    Remove unmatched parentheses from a string
    """
    output = ''
    paren_depth = 0

    for char in input_string:
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1

        if paren_depth > 0:
            output = input_string.replace('(', '')
        elif paren_depth < 0:
            output = input_string.replace(')', '')
        else:
            output = input_string

    return output


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

        # strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        # s = strip_unicode.sub('', s)
        s = unidecode(s)

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
        # strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        # s = strip_unicode.sub('', s)
        s = unidecode(s)
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
        # strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        # s = strip_unicode.sub('', s)
        s = unidecode(s)

        if s:
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
    if df_listlevel1WW8Num.empty:
        df_listlevel = df_listlevel1WW8Num
    else:
        df_listlevel = df_listlevel1WW8Num.assign(title=df_listlevel1WW8Num['title'].str.split('\n')).explode('title')
        df_listlevel['seq'] = df_listlevel.groupby(['source', 'sourceline']).cumcount() + 1
        df_listlevel['source'] = 'listlevel1WW8Num'

    df_NormalWeb = get_class(tree, 'NormalWeb')

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
                    df_listlevel,
                    df_NormalWeb
                 ])

    if 'seq' in df.columns:
        df['seq'].fillna('0', inplace=True)
    else:
        df['seq'] = 0

    df.sort_values(by=['sourceline', 'seq'], inplace=True)

    df = df.apply(lambda x: x.replace('U+00A9',''))

    # -1 for don't know and -92 for refused
    df['title_m'] = df['title'].apply(lambda x: "-1. Don't know" if re.search(r"([0-9]*.*Don't know|don't know|Dont know|Dont Know|Don't Know|Don't know|DONT KNOW|DON'T KNOW).*", x) != None else '-92. Refused' if re.search(r'([0-9]*.*Refuse|refuse|REFUSE).*', x) != None else "99. Don't want to answer" if re.search(r"([0-9]*.*don't want to answer|Don't want to answer).*", x) != None else x)

    df.drop('title', axis=1, inplace=True)
    df.rename(columns={'title_m': 'title'}, inplace=True)

    df['source_new'] = df.apply(lambda row: 'codelist' if ((row['title'][0].isdigit() == True or row['title'].startswith('-1') or row['title'].startswith('-92') or  row['title'] == 'No') and row['source'] in ['Standard', 'PlainText'])
                                            else 'codelist' if row['source'] == 'listlevel1WW8Num'
                                            else 'Instruction' if row['title'].lower().startswith('show')
                                            else 'Instruction' if row['title'].lower().startswith('press')
                                            else 'Instruction' if row['title'].lower().startswith('enter')
                                            else 'Instruction' if row['title'].lower().startswith('- ')
                                            else 'Instruction' if row['title'].lower().startswith('multicoded')
                                            # All text which starts with upper case words should be added to instructions
                                            else 'Instruction' if (len(row['title'].split(' ')) > 1 and row['source'] in ['Standard', 'PlainText'] and row['title'].split(' ')[0].upper() == row['title'].split(' ')[0] and not row['title'].startswith('{') and not row['title'].startswith('(') and not row['title'].startswith('*') and not row['title'].startswith('...') and not row['title'].startswith('I ')) 
                                            # Open answer should be a response domain Generic text rather than used/added to question literal.
                                            # Open type: long verbatim answer is the response domain Long text
                                            else 'Response' if row['title'].lower().startswith('open')
                                            # Hours 0-XX is a response domain which should be labelled Range: 0-50
                                            else 'Response' if row['title'].lower().startswith('hours')
                                            else 'Standard' if 'ask all' in row['title']
                                            else row['source'], axis=1)

    # assign code list group
    df['code_group'] = df['source_new'].ne(df['source_new'].shift()).cumsum()
    df['sequence'] = df.groupby('code_group').cumcount() + 1

    df['seq_new_code'] = df.apply(lambda row: re.search(r'-\d+', row['title']).group() if (row['source_new'] == 'codelist' and row['title'][0] == '-') 
                                              else re.search(r'\d+', row['title']).group() if (row['source_new'] == 'codelist' and row['title'][0].isdigit() == True) else row['seq'], 
                                              axis=1)

    df['seq_new'] = df.apply(lambda row: row['seq_new_code'] if (row['source_new'] == 'codelist' and row['title'][0].isdigit() == True) else row['sequence'] if (row['source_new'] == 'codelist' and row['title'][0] == '-') else row['seq'], axis=1)

    df['seq_new'] = df['seq_new'].astype(int)

    df['seq_new_shift'] = df['seq_new'].shift(1).fillna(0).astype(int)
    df['seq_new_shift_2'] = df['seq_new'].shift(2).fillna(0).astype(int)

    df['seq_new_code_shift'] = df['seq_new_code'].shift(1).fillna(0).astype(int)

    df['seq_new_code'] = df['seq_new_code'].astype(int)
    #print(df.dtypes)

    df['seq_attemp'] = df.apply(lambda row: row['seq_new_shift'] + 1 if (row['seq_new_shift'] > row['seq_new'] and row['seq_new_code'] < 0 and row['seq_new_code_shift'] > 0) 
                                            else row['seq_new_shift_2'] + 2 if (row['seq_new_code'] < 0 and row['seq_new_code_shift'] < 0) 
                                            else row['seq_new'], axis=1)

    df.drop(['source', 'seq', 'code_group', 'sequence', 'seq_new_code', 'seq_new', 'seq_new_shift', 'seq_new_shift_2', 'seq_new_code_shift'], axis=1, inplace=True)
    df['source'] = df.apply(lambda row: row['source_new'] if row['source_new'] != 'listlevel1WW8Num' else 'codelist' , axis=1)
    df['seq'] = df['seq_attemp']
    df.drop(['source_new', 'seq_attemp'], axis=1, inplace=True)

    df = df[pd.notnull(df['title'])]

    df['title'] = df['title'].replace('\s+', ' ', regex=True)
    df['title'] = df['title'].str.strip()
    df.drop_duplicates(keep = 'first', inplace = True)

    # remove {ask all}, Refused, Dont know, Dont Know
###    new_df_1 = df[~(df['title'].str.lower().isin(['{ask all}', '{ask all)', '{ ask all )', '{ask all }', '{ask all)}', '{ask all)l}']))]

    # remove refused/dont know
###    new_df = new_df_1.loc[(new_df_1['title'] != 'Refused') & (new_df_1['title'] != 'Dont know') & (new_df_1['title'] != 'Dont Know'), :]

    new_df = df
    # special case:
    #new_df['condition_source'] = new_df.apply(lambda row: 'Condition' if any(re.findall(r'Ask if|{|{If|{\(If|{ If|If claiming sickness|\(If Repred|\(If Ben1|\(IF HEPOSS9 = 1-3\)|If wrk1a', row['title'], re.IGNORECASE)) 
#else 'Loop' if any(re.findall(r'loop repeats|loop ends|end loop|start loop|END OF AVCE LOOP', row['title'], re.IGNORECASE))
#else row['source'], axis=1)
    new_df['condition_source'] = new_df.apply(lambda row: 'Loop' if any(re.findall(r'loop repeats|loop ends|end loop|start loop|END OF AVCE LOOP|{Record for each|{Ask for each|{For each|{Ask for all', row['title'], re.IGNORECASE)) else 'Condition' if any(re.findall(r'Ask if|{|{If|{\(If|{ If|If claiming sickness|\(If Repred|\(If Ben1|\(IF HEPOSS9 = 1-3\)|If wrk1a', row['title'], re.IGNORECASE)) else row['source'], axis=1)
    new_df['new_source'] = new_df.apply(lambda row: 'Instruction' if (((row['title'].isupper() == True and row['title'] not in('NOT USING INTERPRETER, MAIN PARENT ANSWERING QUESTIONS', 'USING INTERPRETER')) or 'INTERVIEWER' in row['title'] or 'Interviewer' in row['title'] or ('look at this card' in row['title']) or ('NOTE' in row['title']) or ('[STATEMENT]' in row['title']) ) and row['condition_source'] not in ['SequenceNumber', 'SectionNumber', 'Loop']) and 'DATETYPE' not in row['title'] else row['condition_source'], axis=1) 

    question_list = ['Hdob']
    new_df['question_source'] = new_df.apply(lambda row: 'SectionNumber' if row['title'] in question_list else row['new_source'], axis=1)

    new_df['response_source'] = new_df.apply(lambda row: 'Response' if any(re.findall(r'Numeric|Open answer|Open type|OPEN ENDED|ENTER DATE|DATETYPE', row['title'], flags=re.IGNORECASE)) & ~(row['question_source'] in ('Instruction', 'Loop')) else row['question_source'], axis=1)

    new_df.drop(['source', 'condition_source', 'new_source', 'question_source'], axis=1, inplace=True)

    new_df.rename(columns={'response_source': 'source'}, inplace=True)

    # request 1: Change all text response domains to 'Generic text'
    new_df['Type_text'] = new_df.apply(lambda row: 2 if row['source'] == 'Response' and row['title'] =='ENTER DATE'
                                                   else 0, axis=1)

    for i in new_df.loc[(new_df['Type_text'] == 2), :]['sourceline'].tolist():
        new_df.loc[new_df['sourceline'] == i, ['source']] = 'Standard'
        new_df.loc[len(new_df)] = [i+0.5, 'DATETYPE', 0, 'Response', 0]

    new_df_sorted = new_df.sort_values(['sourceline'])
    new_df_sorted.drop(['Type_text'], axis=1, inplace=True)

    return new_df_sorted


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


def get_question_grids(df):
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
    df = df[df.title != '']

    df_name = df.loc[(df['source'] == 'SectionNumber'), ['title', 'questions', 'sourceline']]

    df_literal = df.loc[(df['source'] == 'Standard'), ['title', 'questions']]
    df_literal_com = df_literal.groupby('questions')['title'].apply('\n'.join).reset_index()
    df_literal_com.rename(columns={'title': 'Literal'}, inplace=True)

    df_instruction = df.loc[(df['source'] == 'Instruction'), ['title', 'questions']]
    df_instruction_com = df_instruction.groupby('questions')['title'].apply('\n'.join).reset_index()
    df_instruction_com.rename(columns={'title': 'Instructions'}, inplace=True)

    df_qg_1 = df_name.merge(df_literal_com, how = 'left', on = 'questions')
    df_question_grids = df_qg_1.merge(df_instruction_com, how = 'left', on = 'questions')
    df_question_grids['vertical_code_list_name'] = 'cs_vertical_' + df_question_grids['questions']
    df_question_grids['horizontal_code_list_name'] = 'cs_horizontal_' + df_question_grids['questions']
    df_question_grids['Label'] = 'qg_' + df_question_grids['questions']
    df_question_grids = df_question_grids[['Label', 'Literal', 'Instructions', 'horizontal_code_list_name', 'vertical_code_list_name', 'sourceline']]

    df_qg_codelist = df.loc[(df['source'] == 'codelist'), ['questions', 'sourceline', 'title', 'seq']]
    df_qg_codelist = df_qg_codelist.sort_values(['sourceline', 'seq'])
    df_qg_size = df.groupby(['sourceline']).size().reset_index(name='counts')
    df_qg_codelist_size = df_qg_codelist.merge(df_qg_size, how='left', on='sourceline')

    # vertical code
    df_qg_vertical = df_qg_codelist_size.loc[(df_qg_codelist_size['counts'] == 2), :]
    df_qg_vertical.loc[df_qg_vertical['seq'] == 3, ['seq']] = 2

    df_qg_vertical['vertical_code_list_name'] = 'cs_vertical_' + df_qg_vertical['questions']
    df_qg_vertical.drop(['questions', 'counts'], axis=1, inplace=True)
    df_qg_vertical.rename(columns={'title': 'Category', 'sourceline':'Number', 'seq': 'codes_order', 'vertical_code_list_name': 'Label'}, inplace=True)
    df_qg_vertical['value'] = df_qg_vertical['codes_order']
    df_qg_vertical = df_qg_vertical[['Number', 'codes_order', 'Label', 'value', 'Category']]

    # horizontal code
    df_qg_horizontal = df_qg_codelist_size.loc[(df_qg_codelist_size['counts'] != 2), :]

    df_qg_horizontal['horizontal_code_list_name'] = 'cs_horizontal_' + df_qg_horizontal['questions']
    df_qg_horizontal.drop(['questions', 'counts'], axis=1, inplace=True)
    df_qg_horizontal.rename(columns={'title': 'Category', 'sourceline':'Number', 'seq': 'codes_order', 'horizontal_code_list_name': 'Label'}, inplace=True)
    df_qg_horizontal['value'] = df_qg_horizontal['codes_order']
    df_qg_horizontal = df_qg_horizontal[['Number', 'codes_order', 'Label', 'value', 'Category']]

    df_qg_codes = df_qg_vertical.append(df_qg_horizontal, ignore_index=True)
    df_qg_codes['codes_order'] = df_qg_codes['codes_order'].astype(int)
    df_qg_codes['value'] = df_qg_codes['value'].astype(int)

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
    df_question_name = df.loc[(df.source == 'SectionNumber'), ['sourceline', 'questions', 'Interviewee']]

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
    df_question_code['Response'] = 'cs_q' + df_question_code['questions']

    # 2. Response
    df_question_response = df.loc[df['source'] == 'Response', ['questions', 'title']].drop_duplicates()
    df_question_response.rename(columns={'title': 'Response'}, inplace=True)

    df_response = pd.concat([df_question_code, df_question_response])

    df_question_all = pd.merge(df_question, df_response, how='left', on=['questions'])


    # all questions
    df_question_all.sort_values(by=['sourceline'], inplace=True)

    df_question_all['source'] = 'question'
    df_question_all['Label'] = 'qi_' + df_question_all['questions']
    # df_question_all['Label'] = df_question_all.groupby('questions').questions.apply(lambda n: 'qi_' + n.str.strip() + '_' + (np.arange(len(n))).astype(str))
    # df_question_all['Label'] = df_question_all['Label'].str.strip('_0')

    df_question_all = df_question_all.drop_duplicates(subset=['Label', 'Response'], keep='first')
    # rd_order: codelist last for mixed response
    df_question_all = df_question_all.sort_values(by=['Label', 'Response'], ascending=False)

    # add response order
    df_question_all['rd_order']=df_question_all.sort_values(('Response'), ascending=False).groupby('Label').cumcount() + 1
    #df_question_all.to_csv('tmp_qi.csv')
    # request 3: If there is no question literal, can we add the instruction text to the literal instead
    # remove it from instruction afterwards
    df_question_all.loc[df_question_all['Literal'].isnull(), 'Literal'] = df_question_all['Instructions']
    df_question_all.loc[df_question_all['Literal'] == df_question_all['Instructions'], 'Instructions'] = None

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

    # if can not parse (a=b), use the name of the NEXT question
    df['next_question'] = df['questions'].shift(-1)
    print(df)
    print(df.columns)
    df_conditions = df.loc[(df.source == 'Condition'), ['sourceline', 'questions', 'title', 'condition_end', 'next_question']]

    df_conditions['Logic_name'] = df_conditions['title'].apply(lambda x: re.findall(r"(\w+) *(=|>|<)", x) )
    df_conditions['Logic_name1'] = df_conditions['Logic_name'].apply(lambda x: '' if len(x) ==0 else x[0][0])


    df_conditions['Logic_name2'] = df_conditions.apply(lambda row: row['title'].split('=')[0].strip().split(' ')[-1].replace('(', '').replace(')', '') if (row['Logic_name1'] == '' and '=' in row['title']) else row['Logic_name1'] , axis = 1)

    df_conditions['Logic_name3'] = df_conditions.apply(lambda row: row['next_question'].strip() if (row['Logic_name1'].isdigit() or row['Logic_name2'] == '') else row['Logic_name2'].strip(), axis = 1)

    df_conditions['tmp'] = df_conditions.groupby('Logic_name3')['Logic_name3'].transform('count')
    df_conditions['tmp2'] = df_conditions.groupby('Logic_name3').cumcount() + 1

    df_conditions['Logic_name_new'] = df_conditions['Logic_name3'].str.cat(df_conditions['tmp2'].astype(str), sep="_")

    df_conditions['Logic_c'] = df_conditions['title'].apply(lambda x: re.findall('\((?<=\().*(?=\))\)', x))

    df_conditions['Logic_c1'] = df_conditions['Logic_c'].apply(lambda x: '' if len(x) ==0 else x[0])

    # special case: "if a=b" without ()
    df_conditions['Logic_c2'] = df_conditions.apply(lambda row: row['Logic_c1'] if len(row['Logic_c1']) > 0
        else (row['Logic_name1'] + re.search(r"(?:{})(.*)".format(row['Logic_name1']), row['title']).group(1)).rstrip('}').rstrip(' ') if len(row['Logic_name1']) > 0
        else '', axis=1)

    # remove some string, only keep () or () and ()
    # df_conditions['Logic_c3'] = df_conditions['Logic_c1'].apply(lambda x: ''.join(re.findall('\(.*?\)| or | and | OR | AND ', x)))

    df_conditions['Logic_r'] = df_conditions['Logic_c2'].str.replace('=', ' == ').str.replace('<>', ' != ').str.replace(' OR ', ' || ').str.replace(' AND ', ' && ').str.replace(' or ', ' || ').str.replace(' and ', ' && ')

    # Remove unmatched parentheses from a string, replace {}
    df_conditions['Logic_r1'] = df_conditions['Logic_r'].str.replace('{', '').str.replace('}', '')
    df_conditions['Logic_r2'] = df_conditions['Logic_r1'].apply(lambda x: remove_unmatched_parentheses(x))

    # reform logic: qc_EthGrp == 3, 7, 11, 14 || 16 will be qc_EthGrp == 3 || qc_EthGrp == 7 || qc_EthGrp == 14 || qc_EthGrp == 16
    df_conditions['Logic_reform_num'] = df_conditions['Logic_r2'].apply(lambda x: re.findall(r"(\d+)", x) )
    df_conditions['Logic_reform_equal'] = df_conditions['Logic_r2'].apply(lambda x: re.findall(r"(&&|\|\|)", x) )
    df_conditions['Logic_reform_begin'] = df_conditions['Logic_r2'].apply(lambda x: re.findall(r"(\w+) *(==|!=)", x) )

    df_conditions['Logic_reform'] = df_conditions.apply(lambda row: (' '+ row['Logic_reform_equal'][0] + ' ').join([' '.join(row['Logic_reform_begin'][0]) + ' ' + s for s in row['Logic_reform_num']])
                                                                     if len(row['Logic_reform_equal']) != 0 and len(row['Logic_reform_num']) != 0 and len(row['Logic_reform_begin']) != 0
                                                                     else row['Logic_r2'], axis = 1)
    df_conditions['Logic_name_roman_1'] = df_conditions['Logic_name_new'].apply(lambda x: '_'.join([x.split('_')[0], int_to_roman(int(x.split('_')[1]))]))

    df_conditions['Logic_name_roman'] = df_conditions.apply(lambda row: row['Logic_name_roman_1'].strip('_i') if row['tmp'] == 1 else row['Logic_name_roman_1'], axis=1)

    df_conditions['Label'] = 'c_q' + df_conditions['Logic_name_roman']


    def add_string_qc(text, replace_text_list):
        for item in replace_text_list:
            if item in text:
                text = text.replace(item, 'qc_' + item)
        return text

    # rename inside 'logic', add qc_ to all question names inside the literal
    df_conditions['Logic'] = df_conditions.apply(lambda row: add_string_qc(row['Logic_reform'], [s[0] for s in row['Logic_name']]) if row['Logic_name'] != [] else row['Logic_reform'], axis = 1)

    df_conditions.rename(columns={'title': 'Literal'}, inplace=True)
    #df_conditions = df_conditions.drop(['Logic_c', 'Logic_c1', 'Logic_c3', 'Logic_r', 'Logic_name', 'Logic_name1', 'tmp', 'tmp2', 'Logic_name2', 'Logic_name3', 'Logic_name_new', 'Logic_name_roman', 'Logic_name_roman_1'], 1)

    return df_conditions


def get_loops(df):
    """
    Build loops table: 
    """
    df_sub = df.loc[(df.source == 'Loop'), ['sourceline', 'questions', 'title']]

    col_names =  ['Label', 'Variable', 'Start Value', 'End Value', 'Loop While', 'Logic']
    df_loops  = pd.DataFrame(columns = col_names)
    df_loops.loc[len(df_loops)] = ['l_Hdob', 'Hdob', 379, 417, 'Ask for each NEW 4 hhold member', 'each NEW 4 hhold member']
    df_loops.loc[len(df_loops)] = ['l_Household', 'Household', 422, 683, 'QUESTION IN THE BOX TO BE REPEATED FOR EVERY HOUSEHOLD MEMBER.', 'EVERY HOUSEHOLD MEMBER']
    df_loops.loc[len(df_loops)] = ['l_NewHousehold', 'NewHousehold', 691, 734, 'Ask for each NEW household member', 'each NEW household member']
    df_loops.loc[len(df_loops)] = ['l_hhold', 'hhold', 741, 760, 'Ask for each hhold member in a relationship (Marstat=2 or 3 or Livewit=1)', '_Marstat == 2 || 3 || _Livewit == 1']
    df_loops.loc[len(df_loops)] = ['l_JHST', 'JHST', 201654, 201769, 'LOOP ENDS WHEN SEPTEMBER 2006 OR EARLIER IS ENTERED AT JHSTY AND JHSTM OR "Yes" AT JHSTYDK OR JHSTMDK', '_JHSTYDK == "Yes" || _JHSTMDK == "Yes"']
    df_loops.loc[len(df_loops)] = ['l_AVCE', 'AVCE', 201881, 201898, 'IF STUDYING FOR AT LEAST ONE AVCE, REPEAT FOLLOWING QUESTION FOR EACH _AVCE', 'FOR EACH _AVCE']
    df_loops.loc[len(df_loops)] = ['l_KSLev', 'KSLev', 202026, 202041, 'Loop repeats for all the Key Skills mentioned at _KeySkill', 'for all the Key Skills mentioned at _KeySkill']
    df_loops.loc[len(df_loops)] = ['l_GNVQLev', 'GNVQLev', 202100, 202132, 'Loop repeats for each _GNVQ mentioned at _GNVQNo', 'for each _GNVQ mentioned at _GNVQNo']    
    df_loops.loc[len(df_loops)] = ['l_NVQFull', 'NVQFull', 202149, 202191, 'Loop repeats for each NVQ mentioned at _NVQNo', 'for each _NVQ mentioned at _NVQNo']
    df_loops.loc[len(df_loops)] = ['l_EdExSub', 'EdExSub', 202206, 202246, 'Loop repeats for each _Edexcel, _BTEC or _LQL qualification mentioned at _EdExNo', 'for each _Edexcel, _BTEC or _LQL qualification mentioned at _EdExNo']
    df_loops.loc[len(df_loops)] = ['l_OCRSub', 'OCRSub', 202267, 202319, 'Loop repeats for each _OCR qualification mentioned at _OCRNo', 'for each _OCR qualification mentioned at _OCRNo']
    df_loops.loc[len(df_loops)] = ['l_CitySub', 'CitySub', 202336, 202385, 'Loop repeats for each _City and _Guild mentioned at _CityNo', 'for each _City and _Guild mentioned at _CityNo']
    df_loops.loc[len(df_loops)] = ['l_OtherTyp', 'OtherTyp', 202446, 202500, 'Loop repeats for each other qualification mentioned at _OtherNo', 'for each other qualification mentioned at _OtherNo']

    return df_loops


def find_parent(start, stop, df_mapping, source, section_label):
    """
        Find the parent label and parent source
    """
    if isNaN(stop):
        df = df_mapping.loc[(df_mapping.sourceline < start) & (df_mapping.End > start), :]
    else:
        df = df_mapping.loc[(df_mapping.sourceline < start) & (df_mapping.End > stop), :]

    if source not in ['CcQuestions', 'CcCondition']:
        return section_label
    elif not df.empty:
        df['dist'] = start - df['sourceline']
        df['dist'] = pd.to_numeric(df['dist'])
        df_r = df.loc[df['dist'].idxmin()]
        return df_r['Label']
    else:
        return section_label


def isNaN(num):
    return num != num


def get_statements(df):
    """
        Create Statement table: Label,above_label,parent_type,branch,Position,Literal

    """
    df_statement = df.loc[:, ['title', 'sourceline']].reset_index()
    df_statement.rename(columns={'title': 'Literal'}, inplace=True)
    df_statement['ind'] = df_statement.index + 1
    df_statement['Label'] = 'statement_' + df_statement['ind'].astype(str)
    df_statement = df_statement.drop('ind', 1)

    return df_statement

#if True:
def main():
    input_dir = '../LSYPE1/wave4-html'
    html_names = ['W4_household - Questionnaire.htm', 'W4_main_parent - Questionnaire.htm', 'W4_young_person - Questionnaire.htm']

    output_dir = os.path.join(input_dir, 'wave4_parsed')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    appended_data = []
    for idx, val in enumerate(html_names):

        if idx == 0:
            section_name = 'HOUSEHOLD RESPONDENT SECTION'
            line_start = 66
            interviewee = 'Main parent of cohort/sample member'
        elif idx == 1:
            section_name = 'MAIN/INDIVIDUAL PARENT SECTION'
            line_start = 124
            interviewee = 'Main parent of cohort/sample member'
        else:
            section_name = 'YOUNG PERSON SECTION'
            line_start = 145
            interviewee = 'Cohort/sample member'

        htmlFile = os.path.join(input_dir, val)
        tree = html_to_tree(htmlFile)

        title = tree.xpath('//title')[0].text
        # print(title)

        df_q = get_questionnaire(tree)

        # add section line
        # sourceline	section_name	seq	source
        df_q.loc[len(df_q)] = [line_start, section_name, 0, 'Section']  # adding a row
        df_q = df_q.sort_values('sourceline')

        # actual questionnaire
        df_q = df_q.loc[(df_q.sourceline >= line_start) , :]

        df_q['new_sourceline'] = df_q['sourceline'] + 100000*idx
        df_q['Interviewee'] = interviewee
        df_q['section_name'] = section_name

        df_q.to_csv('../LSYPE1/wave4-html/{}.csv'.format(idx), sep= ';', encoding = 'utf-8', index=False)
        appended_data.append(df_q)
    df = pd.concat(appended_data)
    df.to_csv('DF.csv', sep='\t')

    # manual change: add "white", "mix" to the codelist string
    df.loc[df['new_sourceline'] == 634, 'title'] = '1. White: White - British'
    df.loc[df['new_sourceline'] == 635, 'title'] = '2. White: White - Irish'
    df.loc[df['new_sourceline'] == 636, 'title'] = '3. White: Any other White background (specify)'
    df = df[df.new_sourceline != 632]
    df.loc[df['new_sourceline'] == 640, 'title'] = '4. Mixed: White and Black Caribbean'
    df.loc[df['new_sourceline'] == 641, 'title'] = '5. Mixed: White and Black African'
    df.loc[df['new_sourceline'] == 642, 'title'] = '6. Mixed: White and Asian'
    df.loc[df['new_sourceline'] == 643, 'title'] = '7. Mixed: Any other mixed background (specify)'
    df = df[df.new_sourceline != 638]
    df.loc[df['new_sourceline'] == 647, 'title'] = '8. Asian or Asian British: Indian'
    df.loc[df['new_sourceline'] == 648, 'title'] = '9. Asian or Asian British: Pakistani'
    df.loc[df['new_sourceline'] == 649, 'title'] = '10. Asian or Asian British: Bangladeshi'
    df.loc[df['new_sourceline'] == 650, 'title'] = '11. Asian or Asian British: Any other Asian background (specify)'
    df = df[df.new_sourceline != 645]
    df.loc[df['new_sourceline'] == 654, 'title'] = '12. Black or Black British: Caribbean'
    df.loc[df['new_sourceline'] == 655, 'title'] = '13. Black or Black British: African'
    df.loc[df['new_sourceline'] == 656, 'title'] = '14. Black or Black British: Any other Black background (specify)'
    df = df[df.new_sourceline != 652]
    df.loc[df['new_sourceline'] == 660, 'title'] = '15. Chinese or Other ethinic group: Chinese'
    df.loc[df['new_sourceline'] == 661, 'title'] = '16. Chinese or Other ethinic group: Any other'
    df = df[df.new_sourceline != 658]

    df.loc[df['new_sourceline'] == 102786, 'title'] = '1. White: White - British'
    df.loc[df['new_sourceline'] == 102787, 'title'] = '2. White: White - Irish'
    df.loc[df['new_sourceline'] == 102788, 'title'] = '3. White: Any other White background (specify)'
    df = df[df.new_sourceline != 102783]
    df.loc[df['new_sourceline'] == 102794, 'title'] = '4. Mixed: White and Black Caribbean'
    df.loc[df['new_sourceline'] == 102795, 'title'] = '5. Mixed: White and Black African'
    df.loc[df['new_sourceline'] == 102796, 'title'] = '6. Mixed: White and Asian'
    df.loc[df['new_sourceline'] == 102797, 'title'] = '7. Mixed: Any other mixed background (specify)'
    df = df[df.new_sourceline != 102790]
    df.loc[df['new_sourceline'] == 102803, 'title'] = '11. Asian or Asian British: Indian'
    df.loc[df['new_sourceline'] == 102804, 'title'] = '12. Asian or Asian British: Pakistani'
    df.loc[df['new_sourceline'] == 102805, 'title'] = '13. Asian or Asian British: Bangladeshi'
    df.loc[df['new_sourceline'] == 102806, 'title'] = '14. Asian or Asian British: Any other Asian background (specify)'
    df = df[df.new_sourceline != 102799]
    df.loc[df['new_sourceline'] == 102812, 'title'] = '16. Black or Black British: Caribbean'
    df.loc[df['new_sourceline'] == 102813, 'title'] = '17. Black or Black British: African'
    df.loc[df['new_sourceline'] == 102814, 'title'] = '18. Black or Black British: Any other Black background (specify)'
    df = df[df.new_sourceline != 102808]
    df.loc[df['new_sourceline'] == 102818, 'title'] = '20. Chinese'
    df.loc[df['new_sourceline'] == 102819, 'title'] = '21. Any other'

    df.loc[df['new_sourceline'] == 200218, 'title'] = '1. White: White - British'
    df.loc[df['new_sourceline'] == 200219, 'title'] = '2. White: White - Irish'
    df.loc[df['new_sourceline'] == 200220, 'title'] = '3. White: Any other White background (specify)'
    df = df[df.new_sourceline != 200215]
    df.loc[df['new_sourceline'] == 200226, 'title'] = '4. Mixed: White and Black Caribbean'
    df.loc[df['new_sourceline'] == 200227, 'title'] = '5. Mixed: White and Black African'
    df.loc[df['new_sourceline'] == 200228, 'title'] = '6. Mixed: White and Asian'
    df.loc[df['new_sourceline'] == 200229, 'title'] = '7. Mixed: Any other mixed background (specify)'
    df = df[df.new_sourceline != 200222]
    df.loc[df['new_sourceline'] == 200235, 'title'] = '8. Asian or Asian British: Indian'
    df.loc[df['new_sourceline'] == 200236, 'title'] = '9. Asian or Asian British: Pakistani'
    df.loc[df['new_sourceline'] == 200237, 'title'] = '10. Asian or Asian British: Bangladeshi'
    df.loc[df['new_sourceline'] == 200238, 'title'] = '11. Asian or Asian British: Any other Asian background (specify)'
    df = df[df.new_sourceline != 200231]
    df.loc[df['new_sourceline'] == 200244, 'title'] = '12. Black or Black British: Caribbean'
    df.loc[df['new_sourceline'] == 200245, 'title'] = '13. Black or Black British: African'
    df.loc[df['new_sourceline'] == 200246, 'title'] = '14. Black or Black British: Any other Black background (specify)'
    df = df[df.new_sourceline != 200240]
    df.loc[df['new_sourceline'] == 200250, 'title'] = '15. Chinese'
    df.loc[df['new_sourceline'] == 200251, 'title'] = '16. Any other (specify)'

    df.loc[df['new_sourceline'] == 100, ['source']] = 'Instruction'
    df.loc[df['new_sourceline'] == 1654, ['source']] = 'Instruction'
    df.loc[df['new_sourceline'] == 2185, ['source']] = 'codelist'
    df.loc[df['new_sourceline'] == 2187, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 2464, ['source']] = 'Standard'

    df.loc[df['new_sourceline'] == 102186, ['title']] = 'SHOWCARD B12'
    df.loc[df['new_sourceline'] == 102187, ['title']] = 'QualcMP'

    df.loc[df['new_sourceline'] == 100661, ['title']] = ''
    df.loc[df['new_sourceline'] == 123, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 257, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 365, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 466, ['source']] = 'Statement'

    df.loc[df['new_sourceline'] == 296, ['source']] = 'Condition'

    df.loc[df['new_sourceline'] == 101528, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 102880, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 103189, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 200325, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 201933, ['source']] = 'Statement'

    df.loc[df['new_sourceline'] == 901, ['source']] = 'Standard'
    df.loc[df['new_sourceline'] == 989, ['source']] = 'Instruction'

    df.loc[df['new_sourceline'] == 205977, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 205999, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 206010, ['source']] = 'Condition'
    df.loc[df['new_sourceline'] == 206013, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 206031, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 206046, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 206066, ['source']] = 'SectionNumber'

    df.loc[df['new_sourceline'] == 202506, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 202510, ['source']] = 'Condition'
    df.loc[df['new_sourceline'] == 202171, ['source']] = 'codelist'

    df.loc[df['new_sourceline'] == 102766, ['source']] = 'SequenceNumber'


    df = df.drop_duplicates()
    df = df.sort_values('new_sourceline').reset_index()

    #TODO
    # remove duplicated conditions.
    # If there are two conditions with the same text e.g. Extrat5 and Extrat6 can the second one be ignored and the questask allions inside it be added to the first condition instead?
    df = pd.concat([df.loc[df.source != 'Condition'],
                    df.loc[(df.source == 'Condition') & (df.title.str.contains(r'ask all', case=False)) ],
                    df.loc[(df.source == 'Condition') & (~ df.title.str.contains(r'ask all', na=False, case=False)) ].drop_duplicates(['title'],keep='first')]).sort_index()

    # condition end at the next <ask all>
    # 1. find all <ask all> locations
    next_q = df.loc[(df['title'].str.contains(r'ask all', case=False)) | ( df['source'] == 'SequenceNumber' ), 'new_sourceline'].to_list()
    # print(next_q)
    df['condition_end'] = df.apply(lambda row: min( [y for y in next_q if y - row['new_sourceline'] > 0] )
                                               if (row['new_sourceline'] <  max(next_q) and row['source'] == 'Condition')
                                               else None, axis=1)

    #df.to_csv('tmp_sourceline.csv', sep='\t')

    # remove {ask all}
    # df = df[~(df['title'].str.contains(r'ask all', case=False))]
    df = df[~(df['title'].str.lower().isin(['{ask all}', '{ask all)', '{ ask all )', '{ask all }', '{ask all)}', '{ask all)l}']))]

    # rename duplicated question names
    df['tmp'] = df.groupby('title').cumcount() 
    df['title_new'] = df.apply(lambda row: row['title'] + '_' + str(row['tmp']) if row['source'] == 'SectionNumber' else row['title'], axis=1)
    df['title_new'] = df['title_new'].str.strip('_0')

    # find each question
    df['questions'] = df.apply(lambda row: row['title_new'] if row['source'] in ['SectionNumber'] else None, axis=1)
    df['questions'] = df['questions'].ffill()

    df.drop(['tmp', 'sourceline', 'title'], axis=1, inplace=True)
    df.rename(columns={'new_sourceline': 'sourceline', 'title_new': 'title'}, inplace=True)

    # actual questionnaire
    df['seq'] = df['seq'].astype(int)
    df.sort_values('sourceline').to_csv('../LSYPE1/wave4-html/w2_attempt.csv', sep= ';', encoding = 'utf-8', index=False)


    # 1. Codes
    df_codes = df.loc[(df.source == 'codelist'), ['questions', 'sourceline', 'seq', 'title']]
    # label
    df_codes['Label'] = 'cs_q' + df_codes['questions']
    df_codes.rename(columns={'sourceline': 'Number', 'seq': 'codes_order'}, inplace=True)
    #df_codes['value'] = df_codes['codes_order']
    df_codes['value'] = df_codes.apply(lambda row: row['title'].split('. ')[0] if '-' in row['title'] or '. ' in row['title'] else row['codes_order'], axis=1)

    # strip number. out from title
    df_codes['Category_old'] = df_codes['title'].apply(lambda x: re.sub('^-*\d+', '', x).strip('.').strip(',').strip(' '))

    # ignore the GOTO…. in categories
    df_codes['Category'] = df_codes['Category_old'].apply(lambda x: x[:x.index("GOTO")].rstrip() if 'GOTO' in x else x)

    df_codes_out = df_codes.drop(['questions', 'title', 'Category_old'], 1)

    # write out
    df_codes_out.rename(columns={'codes_order': 'Code_Order',
                                 'value': 'Code_Value'},
                        inplace=True)
    df_codes_out = df_codes_out[['Label', 'Code_Order', 'Code_Value', 'Category']]
    #remove duplicate per group;
    df_codes_out = df_codes_out.drop_duplicates(subset=['Label', 'Category'], keep='last')
    df_codes_out.to_csv(os.path.join(output_dir, 'codelist.csv'), encoding = 'utf-8', index=False, sep=';')

    # 2. Response: numeric, text, datetime
    df_response = df.loc[(df.source == 'Response') , ['questions', 'sourceline', 'seq', 'title']]
    #df_response.to_csv('../LSYPE1/wave4-html/df_response.csv', encoding = 'utf-8', index=False, sep=';')

    df_response['Type'] = df_response['title'].apply(lambda x: 'Numeric' if any (c in x for c in ['Numeric', 'RANGE'])
                                                          else 'Date' if x in ['ENTER DATE', 'DATETYPE']
                                                          else 'Text')
    df_response['Numeric_Type/Datetime_type'] = df_response['title'].apply(lambda x: 'Integer' if any (c in x for c in ['Numeric', 'RANGE'])
                                                                                else 'DateTime' if x in ['ENTER DATE', 'DATETYPE']
                                                                                else '')
    df_response['Min'] = df_response['title'].apply(lambda x: re.findall(r'\d+', x)[0] if len(re.findall(r'\d+', x)) == 2 else None)
    df_response['Max'] = df_response['title'].apply(lambda x: re.findall(r'\d+', x)[-1] if len(re.findall(r'\d+', x)) >= 1 else None)

    # request 2: Change all numeric response domains to the format 'Range: 1-18'
    # open answers without a max be entered as Long text
    # open answers with a max be entered as Generic text
    def find_between( s, first, last ):
        try:
            start = s.index( first ) + len( first )
            end = s.index( last, start )
            return s[start:end]
        except ValueError:
            return ""
    df_response['title1'] = df_response.apply(lambda row: row['title'].replace(find_between(row['title'], row['Min'], row['Max']), '-').replace('Numeric', 'Range').replace('Hours', 'Range:') if not pd.isnull(row['Min']) > 0 else 'Long text' if (len(re.findall('(?i)open', row['title'])) > 0 and pd.isnull(row['Max'])) else 'Generic text' if (len(re.findall('(?i)open', row['title'])) > 0 and not pd.isnull(row['Max'])) else 'Generic date' if row['title'] == 'DATETYPE' else row['title'], axis=1)

    # df_response.to_csv('temp_response.csv', sep=';')
    # need to change these in the original df
    vdic = pd.Series(df_response.title1.values, index=df_response.title).to_dict()
    df.loc[df.title.isin(vdic.keys()), 'title'] = df.loc[df.title.isin(vdic.keys()), 'title'].map(vdic)

    df_response = df_response.drop('title', 1)


    df_response.rename(columns={'title1': 'Label'}, inplace=True)

    # de-dup
    response_keep = ['Label', 'Type', 'Numeric_Type/Datetime_type', 'Min', 'Max']
    df_response_sub = df_response.loc[:, response_keep]
    df_response_dedup1 = df_response_sub.drop_duplicates()

    df_response_dedup = df_response_dedup1.drop_duplicates(subset='Label', keep='first')

    df_response_dedup.rename(columns={'Numeric_Type/Datetime_type': 'Type2'},
                             inplace=True)
    df_response_dedup['Max'] = df_response_dedup.apply(lambda row: 255 if row['Label'] == 'Generic text' else row['Max'], axis=1)
    df_response_dedup['Format'] = None
    response_pipeline = ['Label', 'Type', 'Type2', 'Format', 'Min', 'Max']

    df_response_dedup[response_pipeline].to_csv(os.path.join(output_dir, 'response.csv'), sep= ';', encoding = 'utf-8', index=False)


    # 3. Statements
    df_statement = get_statements(df[df['source'] == 'Statement'])

    # 4. question items
    df_question_items = get_question_items(df)

    # 5. Sequences
    df_sequences = df[df['source'].isin(['Section', 'SequenceNumber'])]
#    df_sequences = df.loc[(df.source == 'SequenceNumber'), :].reset_index()
    df_sequences.rename(columns={'title': 'Label'}, inplace=True)
    df_sequences['section_id_1'] = df_sequences.groupby('section_name').cumcount()
    df_sequences['section_id_2'] = df_sequences.groupby('source').cumcount()+1
    df_sequences['section_id'] = df_sequences.apply(lambda row: row['section_id_1'] if row['source'] == 'SequenceNumber' else row['section_id_2'] if row['source'] == 'Section' else None, axis=1)
    df_sequences = df_sequences.drop(columns=['section_id_1', 'section_id_2'])
    df_sequences['Parent_Name'] = df_sequences.apply(lambda row: row['section_name'] if row['source'] == 'SequenceNumber' else 'Wave4' if row['source'] == 'Section' else None, axis=1)
#    df_sequences['section_id'] = df_sequences.index + 1

    df_sequence_input = df_sequences.loc[:, ['sourceline', 'Label', 'section_id', 'Parent_Name']]

    # pipeline columns
    sequence_pipeline = ['Label', 'Parent_Type', 'Parent_Name', 'Branch', 'Position']
    df_sequence_input.rename(columns={'section_id': 'Position'}, inplace=True)
    df_sequence_input['Parent_Type'] = 'CcSequence'

  #  df_sequence_input['Parent_Name'] = 'Wave4'
    df_sequence_input['Branch'] = None
    df_seq_output = df_sequence_input[sequence_pipeline]

    # manual fix: TODO
    df_seq_output['Position'] = df_seq_output.apply(lambda row: row['Position'] + 3 if row['Parent_Name'] == 'MAIN/INDIVIDUAL PARENT SECTION' else row['Position'], axis=1)

    # add top level
    df_seq_output.loc[-1] = ['Wave4', 'CcSequence', None, None, 1]  # adding a row

    df_seq_output.index = df_seq_output.index + 1  # shifting index

    df_seq_output.sort_index(inplace=True)
    df_seq_output.to_csv('tmp_s.csv')
    df_seq_output.to_csv(os.path.join(output_dir, 'sequence.csv'), sep = ';', encoding = 'utf-8', index=False)


    # 6. Conditions
    df_conditions = get_conditions(df)
    #df_conditions.to_csv('../LSYPE1/wave4-html/df_conditions.csv', sep = ';', encoding = 'utf-8', index=False)


    # 7. Loops
    df_loops = get_loops(df)
    #df_loops.to_csv('../LSYPE1/wave4-html/df_loops.csv', sep = ';', encoding = 'utf-8', index=False)


    # 8. Find parent label
    df_sequences_p = df_sequences.loc[:, ['sourceline', 'Label']]
    df_sequences_p['source'] = 'CcSequence'
    df_questions_items_p = df_question_items.loc[:, ['sourceline', 'Label']].drop_duplicates()

    df_questions_items_p['source'] = 'CcQuestions'
    """
    df_questions_grids_p = df_question_grids.loc[:, ['sourceline', 'Label']]
    df_questions_grids_p['source'] = 'CcQuestions'
    """
    df_conditions_p = df_conditions.loc[:, ['sourceline', 'Label', 'condition_end']]
    df_conditions_p.rename(columns={'condition_end': 'End Value'}, inplace=True)
    df_conditions_p['source'] = 'CcCondition'

    df_loops_p = df_loops.loc[:, ['Start Value', 'End Value', 'Label']]
    df_loops_p.rename(columns={'Start Value': 'sourceline'}, inplace=True)
    df_loops_p['source'] = 'CcLoop'
    df_statement_p = df_statement.loc[:, ['sourceline', 'Label']]
    df_statement_p['source'] = 'CcStatement'

    df_sequences_p_1 = pd.DataFrame([[0, 'LSYPE_Wave_1', 'CcSequence']], columns=['sourceline', 'Label', 'source'])
    """
    df_parent = pd.concat([df_sequences_p, df_questions_items_p, df_questions_grids_p, df_conditions_p, df_sequences_p_1, df_loops_p, df_statement_p]).reset_index()
    """
    df_parent = pd.concat([df_sequences_p, df_questions_items_p, df_conditions_p, df_sequences_p_1, df_loops_p, df_statement_p]).reset_index()

    df_parent = df_parent.sort_values(by=['sourceline']).reset_index()
    #df_parent.to_csv('TMP_parent.csv', sep='\t')

    df_sequence_position = df_parent
    df_sequence_position['Position'] = range(0, len(df_sequence_position))
    df_sequence_position.to_csv('../LSYPE1/wave4-html/df_sequence_position.csv', sep = ';', encoding = 'utf-8', index=False)

    df_sequences_out = df_sequence_position.loc[(df_sequence_position['source'] == 'CcSequence') & (df_sequence_position['Label'] != 'LSYPE_Wave_1'), :]
    df_sequences_out.rename(columns={'Position': 'section_id'}, inplace=True)
    df_sequences_out.loc[:, ['sourceline', 'Label', 'section_id']].to_csv('../LSYPE1/wave4-html/sequences_1.csv', sep = ';', encoding = 'utf-8', index=False)

    #TODO
    # End at the next {ask all}
    df_parent['End'] = df_parent.apply(lambda row: row['End Value']  if row['source'] == 'CcCondition' else row['End Value'], axis=1)

    # sections region
    df_sequences_m = df_sequence_position.loc[(df_sequence_position['source'] == 'CcSequence'), ['Label', 'sourceline']]
    df_sequences_m.rename(columns={'Label': 'section_label'}, inplace=True)
    df_sequences_m.to_csv('../LSYPE1/wave4-html/df_sequences_m.csv', sep = ';', encoding = 'utf-8', index=False)


    df_all_new = pd.merge(df_parent, df_sequences_m, how='left', on=['sourceline'])
    #df_all_new['section_id'] = df_all_new['section_id'].fillna(method='ffill')
    df_all_new['section_label'] = df_all_new['section_label'].fillna(method='ffill')
    # df_all_new.to_csv('../LSYPE1/wave4-html/TMP.csv', sep = ';', encoding = 'utf-8', index=False)

    # Label statements after the next question e.g, statement_1 label would be s_qSHGInt
    # find next question for all statements
    d_statement_name = {}
    l_label = df_all_new['Label']
    for index, item in enumerate(l_label):
        if item.startswith('statement'):
            for it in l_label[index:]:
                if it.startswith('qi_'):
                    d_statement_name[item] = it
                    break
    df_statment_name = pd.DataFrame(d_statement_name.items(), columns=['old_name', 'question_item_name'])
    df_statment_name['question_name'] = df_statment_name['question_item_name'].apply(lambda x: x.split('_')[-1])
    df_statment_name['question_name_num'] = df_statment_name.groupby(['question_name']).cumcount()
    df_statment_name['new_question_name'] = df_statment_name.apply(lambda row: 's_q' + row['question_name'] if row['question_name_num'] == 0
                                                                          else 's_q' + row['question_name'] + '_' + str(row['question_name_num']),
                                                                          axis = 1)
    d_statement_replace = dict(zip(df_statment_name.old_name, df_statment_name.new_question_name))
    # print(d_statement_replace)

    df_mapping = df_parent.loc[ df_parent['End'] > 0, ['Label', 'source', 'sourceline', 'End']]

    #df_mapping.to_csv('../LSYPE1/wave4-html/TMP_mapping.csv', sep = ';', encoding = 'utf-8', index=False)

    # find above label
    for index,row in df_all_new.iterrows():
        df_all_new.at[index, 'above_label'] = find_parent(row['sourceline'], row['End'], df_mapping, row['source'], row['section_label'])

    # df_all_new.to_csv('../LSYPE1/wave4-html/TMPTMP.csv', sep = ';', encoding = 'utf-8', index=False)

    # calculate position
    df_all_new['Position'] = df_all_new.groupby('above_label').cumcount() + 1

    df_all_new['parent_type'] = df_all_new['above_label'].apply(lambda x: 'CcCondition' if x[0:1] == 'c'  else 'CcLoop' if x[0:1] == 'l' else 'CcSequence')

    df_all_new['branch'] = 0
    df_all_new['Position'] = df_all_new['Position'].astype(int)

    # replace new name for statement
    df_all_new = df_all_new.replace(d_statement_replace)

    df_all_new.to_csv('../LSYPE1/wave4-html/df_parent.csv', sep = ';', encoding = 'utf-8', index=False)

    # output csv
    df_questions_new = pd.merge(df_question_items, df_all_new, how='left', on=['sourceline', 'Label'])

    questions_keep = ['Label', 'Literal', 'Instructions', 'Response', 'above_label', 'parent_type', 'branch', 'Position', 'rd_order', 'Interviewee']
    df_qi_input = df_questions_new[questions_keep]

    # pipeline columns
    question_item_pipeline = ['Label', 'Literal', 'Instructions', 'Response', 'Parent_Type', 'Parent_Name', 'Branch', 'Position', 'min_responses', 'max_responses', 'rd_order', 'Interviewee']
    df_qi_input.rename(columns={'above_label': 'Parent_Name',
                                'parent_type': 'Parent_Type',
                                'branch': 'Branch'}, inplace=True)
    df_qi_input['min_responses'] = 1
    df_qi_input['max_responses'] = 1

    df_qi_input[question_item_pipeline].to_csv(os.path.join(output_dir, 'question_item.csv'), encoding='utf-8', index=False, sep = ';')
    """
    df_question_grids_new = pd.merge(df_question_grids, df_all_new, how='left', on=['sourceline', 'Label'])
    question_grids_keep = ['Label', 'Literal', 'Instructions', 'horizontal_code_list_name', 'vertical_code_list_name', 'above_label', 'parent_type', 'branch', 'Position']
    df_question_grids_new[question_grids_keep].to_csv(os.path.join(output_dir, 'question_grids.csv'), sep = ';', encoding='utf-8', index=False)
    """
    df_conditions_new = pd.merge(df_conditions, df_all_new, how='left', on=['sourceline', 'Label'])

    conditions_keep = ['Label', 'Literal', 'Logic', 'above_label', 'parent_type', 'branch', 'Position']
    df_condition_input = df_conditions_new[conditions_keep]

    # pipeline columns
    condition_pipeline = ['Label', 'Literal', 'Logic', 'Parent_Type', 'Parent_Name', 'Branch', 'Position']
    df_condition_input.rename(columns={'above_label': 'Parent_Name',
                                'parent_type': 'Parent_Type',
                                'branch': 'Branch'}, inplace=True)

    df_condition_input[condition_pipeline].to_csv(os.path.join(output_dir, 'condition.csv'), sep = ';', encoding='utf-8', index=False)

    df_loops_new = pd.merge(df_loops, df_all_new[['Label', 'sourceline', 'Position', 'above_label', 'parent_type', 'branch']], how='left', on=['Label'])
    loops_keep = ['Label', 'Variable', 'Start Value', 'End Value', 'Loop While', 'Logic', 'above_label', 'parent_type', 'branch', 'Position']

    df_loops_new['Start Value'] = 1
    df_loops_new['End Value'] = ''
    df_loops_new['Loop While'] = ''

    df_loop_input = df_loops_new[loops_keep]

    # pipeline columns
    loop_pipeline = ['Label', 'Loop_While', 'Start_value', 'End_Value', 'Variable', 'Parent_Type', 'Parent_Name', 'Branch', 'Position']
    df_loop_input.rename(columns={'Start Value': 'Start_value',
                                'End Value': 'End_Value',
                                'Logic': 'Loop_While',
                                'above_label': 'Parent_Name',
                                'parent_type': 'Parent_Type',
                                'branch': 'Branch'}, inplace=True)

    df_loop_input[loop_pipeline].to_csv(os.path.join(output_dir, 'loop.csv'), encoding='utf-8', sep=';', index=False)

    # replace new name for statement
    df_statement = df_statement.replace(d_statement_replace)

    df_statement_new = pd.merge(df_statement, df_all_new[['Label', 'sourceline', 'Position', 'above_label', 'parent_type', 'branch']], how='left', on=['Label'])
    statement_keep = ['Label', 'Literal', 'above_label', 'parent_type', 'branch', 'Position']

    df_statement_input = df_statement_new[statement_keep]

    # pipeline columns
    statement_pipeline = ['Label', 'Literal', 'Parent_Type', 'Parent_Name', 'Branch', 'Position']
    df_statement_input.rename(columns={'above_label': 'Parent_Name',
                                'parent_type': 'Parent_Type',
                                'branch': 'Branch'}, inplace=True)

    df_statement_input[statement_pipeline].to_csv(os.path.join(output_dir, 'statement.csv'), encoding='utf-8', sep=';', index=False)


if __name__ == "__main__":
    main()
