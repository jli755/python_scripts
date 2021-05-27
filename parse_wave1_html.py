#!/bin/env python
# -*- coding: utf-8 -*-

"""
    Parse wave 1 html file:
"""

from collections import OrderedDict
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

    df['source_new'] = df.apply(lambda row: 'codelist' if (row['title'][0].isdigit() == True and row['source'] in ['Standard', 'PlainText'])
                                            else 'Instruction' if row['title'].lower().startswith('show')
                                            else 'Instruction' if row['title'].lower().startswith('- ')
                                            # All text which starts with upper case words should be added to instructions
                                            else 'Instruction' if (len(row['title'].split(' ')) > 1 and row['source'] in ['Standard', 'PlainText'] and row['title'].split(' ')[0].upper() == row['title'].split(' ')[0])
                                            # Open answer should be a response domain Generic text rather than used/added to question literal.
                                            # Open type: long verbatim answer is the response domain Long text
                                            else 'Response' if row['title'].lower().startswith('open')
                                            else row['source'], axis=1)

    df['seq_new'] = df.apply(lambda row: re.search(r'\d+', row['title']).group() if (row['source_new'] == 'codelist') else row['seq'], axis=1)

    df.drop(['source', 'seq'], axis=1, inplace=True)
    df['source'] = df.apply(lambda row: row['source_new'] if row['source_new'] != 'listlevel1WW8Num' else 'codelist' , axis=1)
    df['seq'] = df['seq_new']
    df.drop(['source_new', 'seq_new'], axis=1, inplace=True)

    df = df[pd.notnull(df['title'])]

    df['title'] = df['title'].replace('\s+', ' ', regex=True)
    df['title'] = df['title'].str.strip()
    df.drop_duplicates(keep = 'first', inplace = True)

    # remove {Ask all}, Refused, Dont know, Dont Know
    new_df_1 = df[~df['title'].str.lower().str.contains('ask all')]
    new_df = new_df_1.loc[(new_df_1['title'] != 'Refused') & (new_df_1['title'] != 'Dont know') & (new_df_1['title'] != 'Dont Know'), :]
    # special case:
    new_df['condition_source'] = new_df.apply(lambda row: 'Condition' if any(re.findall(r'Ask if|{|{If|{\(If|\(If|{ If|If claiming sickness', row['title'], re.IGNORECASE)) 
else 'Loop' if any(re.findall(r'loop repeats|loop ends|end loop|start loop|END OF AVCE LOOP', row['title'], re.IGNORECASE))
else row['source'], axis=1)
    new_df['new_source'] = new_df.apply(lambda row: 'Instruction' if (((row['title'].isupper() == True and row['title'] not in('NOT USING INTERPRETER, MAIN PARENT ANSWERING QUESTIONS', 'USING INTERPRETER')) or 'INTERVIEWER' in row['title'] or 'Interviewer' in row['title'] or ('look at this card' in row['title']) or ('NOTE' in row['title']) or ('[STATEMENT]' in row['title']) or ('{Ask for each' in row['title'])) and row['condition_source'] not in ['SequenceNumber', 'SectionNumber', 'Loop']) and 'DATETYPE' not in row['title'] else row['condition_source'], axis=1) 

    question_list = ['Hdob']
    new_df['question_source'] = new_df.apply(lambda row: 'SectionNumber' if row['title'] in question_list else row['new_source'], axis=1)

    new_df['response_source'] = new_df.apply(lambda row: 'Response' if any(re.findall(r'Numeric|Open answer|Open type|OPEN ENDED|ENTER DATE|DATETYPE|DATETYPE', row['title'], flags=re.IGNORECASE)) & ~(row['question_source'] in ('Instruction', 'Loop'))
else 'Response' if row['title'].lower().startswith('enter ') else row['question_source'], axis=1)

    new_df.drop(['source', 'condition_source', 'new_source', 'question_source'], axis=1, inplace=True)

    new_df.rename(columns={'response_source': 'source'}, inplace=True)

    # request 1: Change all text response domains to 'Generic text'
    new_df['Type_text'] = new_df.apply(lambda row: 2 if row['source'] == 'Response' and row['title'] == 'ENTER DATE'
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
    df_question_all['Label'] = 'qi_' + df_question_all['questions']
    # df_question_all['Label'] = df_question_all.groupby('questions').questions.apply(lambda n: 'qi_' + n.str.strip() + '_' + (np.arange(len(n))).astype(str))
    # df_question_all['Label'] = df_question_all['Label'].str.strip('_0')

    df_question_all = df_question_all.drop_duplicates(subset=['Label'], keep='first')

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
    df_conditions = df.loc[(df.source == 'Condition'), ['sourceline', 'questions', 'title']]

    # if can not parse (a=b), use the name of the NEXT question
    df_conditions['next_question'] = df_conditions['questions'].shift(-1)

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

    df_conditions['Logic_name_roman_1'] = df_conditions['Logic_name_new'].apply(lambda x: '_'.join([x.split('_')[0], int_to_roman(int(x.split('_')[1]))]))

    df_conditions['Logic_name_roman'] = df_conditions.apply(lambda row: row['Logic_name_roman_1'].strip('_i') if row['tmp'] == 1 else row['Logic_name_roman_1'], axis=1)

    df_conditions['Label'] = 'c_q' + df_conditions['Logic_name_roman']


    def add_string_qc(text, replace_text_list):
        for item in replace_text_list:
            if item in text:
                text = text.replace(item, 'qc_' + item)
        return text

    # rename inside 'logic', add qc_ to all question names inside the literal
    df_conditions['Logic'] = df_conditions.apply(lambda row: add_string_qc(row['Logic_r2'], [s[0] for s in row['Logic_name']]) if row['Logic_name'] != [] else row['Logic_r2'], axis = 1)

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

    df_loops.loc[len(df_loops)] = ['l_Household', 'Household', 296, 450, 'Ask for each household member', 'for each household member']
    df_loops.loc[len(df_loops)] = ['l_R', 'R', 452, 501, 'Ask for each household member', 'for each household member']
    df_loops.loc[len(df_loops)] = ['l_JHAct', 'JHAct', 100908, 101034, 'Ask for all activities since young person’s birth/parent’s arrival in same household', 'for all activities since young person’s birth/parent’s arrival in same household']

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


def main():
    input_dir = '../LSYPE1/wave1-html'
    html_names = ['W1_HOUSEHOLD_SECTION - Questionnaire.htm', 'W1_INDIVIDUAL_PARENT - Questionnaire.htm', 'W1__MAIN_PARENT - Questionnaire.htm', 'W1__YOUNG_PERSON - Questionnaire.htm']

    appended_data = []
    for idx, val in enumerate(html_names):
        if idx == 0:
            section_name = 'HOUSEHOLD RESPONDENT SECTION'
            line_start = 78
        elif idx == 1:
            section_name = 'MAIN/INDIVIDUAL PARENT SECTION'
            line_start = 111.5
        elif idx == 2:
            section_name = 'YOUNG PERSON SECTION'
            line_start = 101
        else:
            section_name = 'YOUNG PERSON SECTION'
            line_start = 108

        htmlFile = os.path.join(input_dir, val)
        tree = html_to_tree(htmlFile)

        title = tree.xpath('//title')[0].text
        # print(title)

        df_q = get_questionnaire(tree)

        # add section line
        # sourceline	section_name	seq	source
        df_q.loc[-1] = [line_start, section_name, 0, 'Section']  # adding a row
        df_q = df_q.sort_values('sourceline')

        # actual questionnaire
        df_q = df_q.loc[(df_q.sourceline >= line_start) , :]

        df_q['new_sourceline'] = df_q['sourceline'] + 100000*idx

        df_q.to_csv('../LSYPE1/wave1-html/{}.csv'.format(idx), sep= ';', encoding = 'utf-8', index=False)
        appended_data.append(df_q)
    df = pd.concat(appended_data)

    # manual fix SHOWCARD C2Qualc, split into two rows
    df.loc[-1] = [168, 'SHOWCARD C2', 0, 'Instruction', 100168 ]  # adding a row
    df = df.sort_values('new_sourceline')

    df.at[df['new_sourceline'] == 100169, 'title'] = 'Qualc'
    df.at[df['new_sourceline'] == 100169, 'source'] = ' SectionNumber'
    df.at[df['new_sourceline'] == 100170, 'source'] = 'Standard'

    df.at[df['new_sourceline'] == 102, 'title'] = '3. NHS/Health trust or other establishment providing nursing care'
    df = df[df.new_sourceline != 103]

    # manual change: add "white", "mix" to the codelist string
    df.at[df['new_sourceline'] == 254, 'title'] = '1. White: White - British'
    df.at[df['new_sourceline'] == 255, 'title'] = '2. White: White - Irish'
    df.at[df['new_sourceline'] == 256, 'title'] = '3. White: Any other White background (specify)'
    df = df[df.new_sourceline != 251]
    df.at[df['new_sourceline'] == 262, 'title'] = '4. Mixed: White and Black Caribbean'
    df.at[df['new_sourceline'] == 263, 'title'] = '5. Mixed: White and Black African'
    df.at[df['new_sourceline'] == 264, 'title'] = '6. Mixed: White and Asian'
    df.at[df['new_sourceline'] == 265, 'title'] = '7. Mixed: Any other mixed background (specify)'
    df = df[df.new_sourceline != 258]
    df.at[df['new_sourceline'] == 271, 'title'] = '8. Asian or Asian British: Indian'
    df.at[df['new_sourceline'] == 272, 'title'] = '9. Asian or Asian British: Pakistani'
    df.at[df['new_sourceline'] == 273, 'title'] = '10. Asian or Asian British: Bangladeshi'
    df.at[df['new_sourceline'] == 274, 'title'] = '11. Asian or Asian British: Any other Asian background (specify)'
    df = df[df.new_sourceline != 267]
    df.at[df['new_sourceline'] == 280, 'title'] = '12. Black or Black British: Caribbean'
    df.at[df['new_sourceline'] == 281, 'title'] = '13. Black or Black British: African'
    df.at[df['new_sourceline'] == 282, 'title'] = '14. Black or Black British: Any other Black background (specify)'
    df = df[df.new_sourceline != 276]
    df.at[df['new_sourceline'] == 286, 'title'] = '15. Chinese'
    df.at[df['new_sourceline'] == 287, 'title'] = '16. Any other (specify)'

    df.at[df['new_sourceline'] == 407, 'title'] = '1. White: White - British'
    df.at[df['new_sourceline'] == 408, 'title'] = '2. White: White - Irish'
    df.at[df['new_sourceline'] == 409, 'title'] = '3. White: Any other White background (specify)'
    df = df[df.new_sourceline != 405]
    df.at[df['new_sourceline'] == 413, 'title'] = '4. Mixed: White and Black Caribbean'
    df.at[df['new_sourceline'] == 414, 'title'] = '5. Mixed: White and Black African'
    df.at[df['new_sourceline'] == 415, 'title'] = '6. Mixed: White and Asian'
    df.at[df['new_sourceline'] == 416, 'title'] = '7. Mixed: Any other mixed background (specify)'
    df = df[df.new_sourceline != 411]
    df.at[df['new_sourceline'] == 420, 'title'] = '8. Asian or Asian British: Indian'
    df.at[df['new_sourceline'] == 421, 'title'] = '9. Asian or Asian British: Pakistani'
    df.at[df['new_sourceline'] == 422, 'title'] = '10. Asian or Asian British: Bangladeshi'
    df.at[df['new_sourceline'] == 423, 'title'] = '11. Asian or Asian British: Any other Asian background (specify)'
    df = df[df.new_sourceline != 418]
    df.at[df['new_sourceline'] == 427, 'title'] = '12. Black or Black British: Caribbean'
    df.at[df['new_sourceline'] == 428, 'title'] = '13. Black or Black British: African'
    df.at[df['new_sourceline'] == 429, 'title'] = '14. Black or Black British: Any other Black background (specify)'
    df = df[df.new_sourceline != 425]
    df.at[df['new_sourceline'] == 433, 'title'] = '15. Chinese or Other ethnic group: Chinese'
    df.at[df['new_sourceline'] == 434, 'title'] = '16. Chinese or Other ethnic group: Any other'
    df = df[df.new_sourceline != 431]

    df.at[df['new_sourceline'] == 101096, 'title'] = '1. White: White - British'
    df.at[df['new_sourceline'] == 101097, 'title'] = '2. White: White - Irish'
    df.at[df['new_sourceline'] == 101098, 'title'] = '3. White: Any other White background (specify)'
    df = df[df.new_sourceline != 101093]
    df.at[df['new_sourceline'] == 101104, 'title'] = '4. Mixed: White and Black Caribbean'
    df.at[df['new_sourceline'] == 101105, 'title'] = '5. Mixed: White and Black African'
    df.at[df['new_sourceline'] == 101106, 'title'] = '6. Mixed: White and Asian'
    df.at[df['new_sourceline'] == 101107, 'title'] = '7. Mixed: Any other mixed background (specify)'
    df = df[df.new_sourceline != 101100]
    df.at[df['new_sourceline'] == 101113, 'title'] = '11. Asian or Asian British: Indian'
    df.at[df['new_sourceline'] == 101114, 'title'] = '12. Asian or Asian British: Pakistani'
    df.at[df['new_sourceline'] == 101115, 'title'] = '13. Asian or Asian British: Bangladeshi'
    df.at[df['new_sourceline'] == 101116, 'title'] = '14. Asian or Asian British: Any other Asian background'
    df = df[df.new_sourceline != 101109]
    df.at[df['new_sourceline'] == 101122, 'title'] = '16. Black or Black British: Caribbean'
    df.at[df['new_sourceline'] == 101123, 'title'] = '17. Black or Black British: African'
    df.at[df['new_sourceline'] == 101124, 'title'] = '18. Black or Black British: Any other Black background (specify)'
    df = df[df.new_sourceline != 101118]
    df.at[df['new_sourceline'] == 101128, 'title'] = '20. Chinese'
    df.at[df['new_sourceline'] == 101129, 'title'] = '21. Any other'

    df.loc[df['new_sourceline'] == 156, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 181, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 214, ['source']] = 'SectionNumber'

    df.loc[df['new_sourceline'] == 301233, ['source']] = 'Standard'

    # statement
    df.loc[df['new_sourceline'] == 113, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 100380, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 100858, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 101038, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 200860, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 201291, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 201717, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 202020, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 202028, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 300959, ['source']] = 'Statement'

    df.loc[df['new_sourceline'] == 100169, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 202144, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 202166, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 202182, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 202197, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 202216, ['source']] = 'SectionNumber'
    df.loc[df['new_sourceline'] == 202230, ['source']] = 'SectionNumber'

    df.loc[df['new_sourceline'] == 303198, ['source']] = 'Instruction'
    df.loc[df['new_sourceline'] == 303199, ['source']] = 'Standard'
    df.loc[df['new_sourceline'] == 303200, ['source']] = 'Instruction'
    df.loc[df['new_sourceline'] == 303201, ['source']] = 'Statement'

    df.loc[df['new_sourceline'] == 100134, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 100135, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 100137, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 100139, ['source']] = 'Statement'
    df.loc[df['new_sourceline'] == 100909, ['source']] = 'Statement'

    question_grid_names = ['Qualb', 'Quald', 'Qualf', 'QualH']
    df.loc[df['new_sourceline'] == 100192, ['source']] = 'Standard'
    df = df[df.new_sourceline != 100140]
    df = df[df.new_sourceline != 100141]
    df = df[df.new_sourceline != 100142]
    df.loc[df['new_sourceline'] == 100148, ['new_sourceline']] = 100140
    df.loc[df['new_sourceline'] == 100151, ['new_sourceline']] = 100141
    df.loc[df['new_sourceline'] == 100152, ['new_sourceline']] = 100142
    df = df.sort_values(['new_sourceline', 'seq']).reset_index(drop=True)

    df.loc[df.index[266], ['new_sourceline']] = 100143
    df.loc[df.index[267], ['new_sourceline']] = 100144
    df.loc[df.index[268], ['new_sourceline']] = 100145
    df.loc[df['new_sourceline'] == 100142, ['source']] = 'Standard'

    df = df[df.new_sourceline != 100209]
    df = df[df.new_sourceline != 100210]
    df = df[df.new_sourceline != 100211]
    df.loc[df['new_sourceline'] == 100221, ['new_sourceline']] = 100209
    df.loc[df['new_sourceline'] == 100229, ['new_sourceline']] = 100210
    df.loc[df['new_sourceline'] == 100230, ['new_sourceline']] = 100211

    df = df[df.new_sourceline != 100245]
    df = df[df.new_sourceline != 100246]
    df = df[df.new_sourceline != 100247]
    df.loc[df['new_sourceline'] == 100253, ['new_sourceline']] = 100244
    df.loc[df['new_sourceline'] == 100256, ['new_sourceline']] = 100245
    df.loc[df['new_sourceline'] == 100257, ['new_sourceline']] = 100246
    df.loc[df['new_sourceline'] == 100258, ['new_sourceline']] = 100247
    df.loc[df['new_sourceline'] == 100250, ['new_sourceline']] = 100249
    df.loc[df['new_sourceline'] == 100267, ['source']] = 'codelist'

    df = df.drop_duplicates()
    df = df.sort_values('new_sourceline').reset_index()

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
    df.sort_values('sourceline').to_csv('../LSYPE1/wave1-html/w1_attempt.csv', sep= ';', encoding = 'utf-8', index=False)


    # 1. Codes
    df_codes = df.loc[(df.source == 'codelist') & (~df.questions.isin(question_grid_names)), ['questions', 'sourceline', 'seq', 'title']]
    # label
    df_codes['Label'] = 'cs_' + df_codes['questions']
    df_codes.rename(columns={'sourceline': 'Number', 'seq': 'codes_order'}, inplace=True)
    df_codes['value'] = df_codes['codes_order']

    # strip number. out from title
    df_codes['Category'] = df_codes['title'].apply(lambda x: re.sub('^\d+', '', x).strip('.').strip(',').strip(' '))
    df_codes_out = df_codes.drop(['questions', 'title'], 1)

    # need to add codes from question grid before write out
    #df_codes_out.to_csv('../LSYPE1/wave1-html/codes.csv', encoding = 'utf-8', index=False, sep=';')

    # 2. Response: numeric, text, datetime
    df_response = df.loc[(df.source == 'Response') , ['questions', 'sourceline', 'seq', 'title']]
    # df_response.to_csv('../LSYPE1/wave1-html/df_response.csv', encoding = 'utf-8', index=False, sep=';')

    df_response['Type'] = df_response['title'].apply(lambda x: 'Numeric' if any (c in x for c in ['Numeric', 'RANGE']) else 'Datetime' if x in ['ENTER DATE', 'DATETYPE'] else 'Text')
    df_response['Numeric_Type/Datetime_type'] = df_response['title'].apply(lambda x: 'Integer' if any (c in x for c in ['Numeric', 'RANGE']) else 'Date' if x in ['ENTER DATE', 'DATETYPE'] else '')
    df_response['Min'] = df_response['title'].apply(lambda x: re.findall(r'\d+', x)[0] if len(re.findall(r'\d+', x)) == 2
                                                              else None)
    df_response['Max'] = df_response['title'].apply(lambda x: re.findall(r'\d+', x)[-1] if len(re.findall(r'\d+', x)) >= 1 else None)

    # request 2: Change all numeric response domains to the format 'Range: 1-18'
    def find_between( s, first, last ):
        try:
            start = s.index( first ) + len( first )
            end = s.index( last, start )
            return s[start:end]
        except ValueError:
            return ""
    df_response['title1'] = df_response.apply(lambda row: row['title'].replace(find_between(row['title'], row['Min'], row['Max']), '-') if not pd.isnull(row['Min']) > 0 else row['title'], axis=1)

    # need to change these in the original df
    vdic = pd.Series(df_response.title1.values, index=df_response.title).to_dict()
    df.loc[df.title.isin(vdic.keys()), 'title'] = df.loc[df.title.isin(vdic.keys()), 'title'].map(vdic)


    df_response = df_response.drop('title', 1)


    df_response.rename(columns={'title1': 'Label'}, inplace=True)

    # de-dup
    response_keep = ['Label', 'Type', 'Numeric_Type/Datetime_type', 'Min', 'Max']
    df_response_sub = df_response.loc[:, response_keep]
    df_response_dedup = df_response_sub.drop_duplicates()
    df_response_dedup.to_csv('../LSYPE1/wave1-html/response.csv', sep= ';', encoding = 'utf-8', index=False)


    # 3. Statements
    df_statement = get_statements(df[df['source'] == 'Statement'])

    # 3. Question grids
    df_question_grids, df_qg_codes = get_question_grids(df[df['questions'].isin(question_grid_names)])
    df_question_grids.to_csv('../LSYPE1/wave1-html/df_qg.csv', sep = ';', encoding = 'utf-8', index=False)

    df_codes_out['codes_order'] = df_codes_out['codes_order'].astype(int)
    df_codes_out['value'] = df_codes_out['value'].astype(int)
    df_codes_final = df_codes_out.append(df_qg_codes, ignore_index=True)
    df_codes_final.to_csv('../LSYPE1/wave1-html/codes.csv', sep = ';', encoding = 'utf-8', index=False)
    # add one more line here for question grids
    with open('../LSYPE1/wave1-html/codes.csv', 'a') as file:
        file.write(';1;-;1;-\n')


    # 4. Question items
    # minus question grids
    df_all_questions = df[~df['questions'].isin(question_grid_names)]

    df_question_items = get_question_items(df_all_questions)
    df_question_items.to_csv('../LSYPE1/wave1-html/df_qi.csv', sep = ';', encoding = 'utf-8', index=False)


    # 5. Sequences
    df_sequences = df.loc[(df.source == 'SequenceNumber'), :].reset_index()
    df_sequences.rename(columns={'title': 'Label'}, inplace=True)
    df_sequences['section_id'] = df_sequences.index + 1
    df_sequences.loc[:, ['sourceline', 'Label', 'section_id']].to_csv('../LSYPE1/wave1-html/sequences.csv', sep = ';', encoding = 'utf-8', index=False)


    # 6. Conditions
    df_conditions = get_conditions(df)
    #df_conditions.to_csv('../LSYPE1/wave1-html/df_conditions.csv', sep = ';', encoding = 'utf-8', index=False)


    # 7. Loops
    df_loops = get_loops(df)
    #df_loops.to_csv('../LSYPE1/wave1-html/df_loops.csv', sep = ';', encoding = 'utf-8', index=False)


    # 8. Find parent label
    df_sequences_p = df_sequences.loc[:, ['sourceline', 'Label']]
    df_sequences_p['source'] = 'CcSequence'
    df_questions_items_p = df_question_items.loc[:, ['sourceline', 'Label']]
    df_questions_items_p['source'] = 'CcQuestions'
    df_questions_grids_p = df_question_grids.loc[:, ['sourceline', 'Label']]
    df_questions_grids_p['source'] = 'CcQuestions'
    df_conditions_p = df_conditions.loc[:, ['sourceline', 'Label']]
    df_conditions_p['source'] = 'CcCondition'
    df_loops_p = df_loops.loc[:, ['Start Value', 'End Value', 'Label']]
    df_loops_p.rename(columns={'Start Value': 'sourceline'}, inplace=True)
    df_loops_p['source'] = 'CcLoop'
    df_statement_p = df_statement.loc[:, ['sourceline', 'Label']]
    df_statement_p['source'] = 'CcStatement'

    df_sequences_p_1 = pd.DataFrame([[0, 'LSYPE_Wave_1', 'CcSequence']], columns=['sourceline', 'Label', 'source'])

    df_parent = pd.concat([df_sequences_p, df_questions_items_p, df_questions_grids_p, df_conditions_p, df_sequences_p_1, df_loops_p, df_statement_p]).reset_index()
    df_parent = df_parent.sort_values(by=['sourceline']).reset_index()

    df_sequence_position = df_parent
    df_sequence_position['Position'] = range(0, len(df_sequence_position))
    df_sequence_position.to_csv('../LSYPE1/wave1-html/df_sequence_position.csv', sep = ';', encoding = 'utf-8', index=False)

    df_sequences_out = df_sequence_position.loc[(df_sequence_position['source'] == 'CcSequence') & (df_sequence_position['Label'] != 'LSYPE_Wave_1'), :]
    df_sequences_out.rename(columns={'Position': 'section_id'}, inplace=True)
    df_sequences_out.loc[:, ['sourceline', 'Label', 'section_id']].to_csv('../LSYPE1/wave1-html/sequences_1.csv', sep = ';', encoding = 'utf-8', index=False)

    df_parent['End'] = df_parent.apply(lambda row: row['sourceline'] + 5 if row['source'] == 'CcCondition' else row['End Value'], axis=1)

    # sections region
    df_sequences_m = df_sequence_position.loc[(df_sequence_position['source'] == 'CcSequence'), ['Label', 'sourceline']]
    df_sequences_m.rename(columns={'Label': 'section_label'}, inplace=True)
    df_sequences_m.to_csv('../LSYPE1/wave1-html/df_sequences_m.csv', sep = ';', encoding = 'utf-8', index=False)


    df_all_new = pd.merge(df_parent, df_sequences_m, how='left', on=['sourceline'])
    #df_all_new['section_id'] = df_all_new['section_id'].fillna(method='ffill')
    df_all_new['section_label'] = df_all_new['section_label'].fillna(method='ffill')
    # df_all_new.to_csv('../LSYPE1/wave1-html/TMP.csv', sep = ';', encoding = 'utf-8', index=False)

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
    print(d_statement_replace)

    df_mapping = df_parent.loc[ df_parent['End'] > 0, ['Label', 'source', 'sourceline', 'End']]

    df_mapping.to_csv('../LSYPE1/wave1-html/TMP_mapping.csv', sep = ';', encoding = 'utf-8', index=False)

    # find above label
    for index,row in df_all_new.iterrows():
        df_all_new.at[index, 'above_label'] = find_parent(row['sourceline'], row['End'], df_mapping, row['source'], row['section_label'])

    # df_all_new.to_csv('../LSYPE1/wave1-html/TMPTMP.csv', sep = ';', encoding = 'utf-8', index=False)

    # calculate position
    df_all_new['Position'] = df_all_new.groupby('above_label').cumcount() + 1

    df_all_new['parent_type'] = df_all_new['above_label'].apply(lambda x: 'CcCondition' if x[0:1] == 'c'  else 'CcLoop' if x[0:1] == 'l' else 'CcSequence')

    df_all_new['branch'] = 0
    df_all_new['Position'] = df_all_new['Position'].astype(int)

    # replace new name for statement
    df_all_new = df_all_new.replace(d_statement_replace)

    df_all_new.to_csv('../LSYPE1/wave1-html/df_parent.csv', sep = ';', encoding = 'utf-8', index=False)

    # output csv
    df_questions_new = pd.merge(df_question_items, df_all_new, how='left', on=['sourceline', 'Label'])
    questions_keep = ['Label', 'Literal', 'Instructions', 'Response', 'above_label', 'parent_type', 'branch', 'Position']
    df_questions_new[questions_keep].to_csv(os.path.join(input_dir, 'question_items.csv'), encoding='utf-8', index=False, sep = ';')

    df_question_grids_new = pd.merge(df_question_grids, df_all_new, how='left', on=['sourceline', 'Label'])
    question_grids_keep = ['Label', 'Literal', 'Instructions', 'horizontal_code_list_name', 'vertical_code_list_name', 'above_label', 'parent_type', 'branch', 'Position']
    df_question_grids_new[question_grids_keep].to_csv(os.path.join(input_dir, 'question_grids.csv'), sep = ';', encoding='utf-8', index=False)

    df_conditions_new = pd.merge(df_conditions, df_all_new, how='left', on=['sourceline', 'Label'])

    conditions_keep = ['Label', 'Literal', 'Logic', 'above_label', 'parent_type', 'branch', 'Position']
    df_conditions_new[conditions_keep].to_csv(os.path.join(input_dir, 'conditions.csv'), sep = ';', encoding='utf-8', index=False)

    df_loops_new = pd.merge(df_loops, df_all_new[['Label', 'sourceline', 'Position', 'above_label', 'parent_type', 'branch']], how='left', on=['Label'])
    loops_keep = ['Label', 'Variable', 'Start Value', 'End Value', 'Loop While', 'Logic', 'above_label', 'parent_type', 'branch', 'Position']

    df_loops_new['Start Value'] = 1
    df_loops_new['End Value'] = ''
    df_loops_new['Loop While'] = ''
    df_loops_new[loops_keep].to_csv(os.path.join(input_dir, 'loops.csv'), encoding='utf-8', sep=';', index=False)

    # replace new name for statement
    df_statement = df_statement.replace(d_statement_replace)

    df_statement_new = pd.merge(df_statement, df_all_new[['Label', 'sourceline', 'Position', 'above_label', 'parent_type', 'branch']], how='left', on=['Label'])
    statement_keep = ['Label', 'Literal', 'above_label', 'parent_type', 'branch', 'Position']
    df_statement_new[statement_keep].to_csv(os.path.join(input_dir, 'statements.csv'), encoding='utf-8', sep=';', index=False)


if __name__ == "__main__":
    main()
