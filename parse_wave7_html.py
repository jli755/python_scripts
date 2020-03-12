#!/bin/env python
# -*- coding: utf-8 -*-

"""
    Parse html file:
"""
from lxml import etree
import pandas as pd
import numpy as np
import os
import re
from collections import OrderedDict

# https://stackoverflow.com/questions/28777219/basic-program-to-convert-integer-to-roman-numerals/28777781
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
        ##strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        ##s = strip_unicode.sub('', s)
	
        #if elem.text is not None:
        #    if elem.text.strip():
        if s:
            dicts.append({"source": search_string, 
                          "sourceline": elem.sourceline, 
                          "title": s})
    return pd.DataFrame(dicts)


def get_SectionNumber(tree):
    """
    get line numbers and text from html elements of type 'h3' (SectionNumber)
    """
    dicts = []
    for elem in tree.xpath("//h3"):
        L = list(elem.itertext())
        s = "".join(L).strip()        
        strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?\<\>\\]+|[^\s]+)")
        s = strip_unicode.sub('', s)
        if s:
            dicts.append({"source": 'SectionNumber', 
                          "sourceline": elem.sourceline, 
                          "title": s})
    return pd.DataFrame(dicts)

def get_questions(tree):
    """
    Build questions table 
    """
    df_SectionNumber = get_SectionNumber(tree)
    df_Standard = get_class(tree, 'Standard')
    df = pd.concat([df_SectionNumber,
                    df_Standard
                 ])
    df.sort_values(by=['sourceline'], inplace=True)    
    # actual questions
    df = df.loc[(df.sourceline >= 77), :]
    # find each question
    df['questions'] = df.apply(lambda row: row['title'] if row['source'] in ['SectionNumber'] else None, axis=1)
    df['questions'] = df['questions'].ffill()
	
    df_question_name = df.loc[(df.source == 'SectionNumber'), :]
    
    df_Standard = df.loc[(df.source == 'Standard'), :]	
    df_Standard_literal = df_Standard.groupby('questions')['title'].apply('\n'.join).reset_index()
	
    df_question = pd.merge(df_question_name[['sourceline', 'questions']], df_Standard_literal, how='left', on=['questions'])
    df_question['source'] = 'question'
    #df_question.to_csv('../LSYPE1/wave7-html/df_question.csv', encoding = 'utf-8', index=False)

	
    # footnote (instruction in questions)
    df_footnotetext = get_class(tree, 'footnotetext')
    # manual
    df_footnotetext['Num'] = df_footnotetext.apply(lambda row: 161 if row['sourceline'] in [5183, 5184] else int(re.findall(r"(\d+) ", row['title'])[0]), axis = 1)
    df_footnote = df_footnotetext.groupby('Num')['title'].apply('  '.join).reset_index()
    
    df_footnotereference = get_class(tree, 'footnotereference')
    df_footnotereference.rename(columns={'title': 'Num'}, inplace=True)
    df_footnotereference['Num'] = df_footnotereference['Num'].astype(int)
    df_footnote_pos = pd.merge(df_footnotereference[['sourceline', 'Num']], df_footnote, how='inner', on='Num')
    df_footnote_pos['source'] = 'instruction'
    #df_footnote_pos.to_csv('../LSYPE1/wave7-html/df_footnote_pos.csv', encoding = 'utf-8', index=False) 
	
    # link to which question
    # broken footnote 7, 8 ... where are they?
    df_all = pd.concat([df_question, df_footnote_pos], sort=True)
    df_all.sort_values(by=['sourceline'], ascending=[True], inplace=True)
    df_all['questions'] = df_all['questions'].ffill()
	
    df_instructions = df_all.loc[(df_all.source == 'instruction'), :].groupby('questions')['title'].apply('\n'.join).reset_index()
    df_instructions.rename(columns={'title': 'Instructions'}, inplace=True)
	
    # all questions
    df_all_questions = pd.merge(df_question, df_instructions, how='left', on ='questions')
    df_all_questions.sort_values(by=['sourceline'], inplace=True)
    df_all_questions.rename(columns={'questions': 'Label', 'title': 'Literal'}, inplace=True)
    return df_all_questions
    
     
	
def get_questionnaire(tree):
    """
    combine individual parts, return questionnaire dataframe
    'Heading1Char' has duplicated sequence information
    """
    df_SectionNumber = get_SectionNumber(tree)
    #df_Heading1Char = get_class(tree,'Heading1Char')
    df_Instructions = get_class(tree, 'Instructions')
    df_toc1 = get_class(tree, 'toc1')
    df_Standard = get_class(tree, 'Standard')
    df_Answerlist = get_class(tree, 'Answerlist')
   # df_Answerlist.to_csv('../LSYPE1/wave7-html/temp.csv', encoding = 'utf-8', index=False)

    df_RoutingFilter = get_class(tree, 'RoutingFilter')
    df_listlevel1RTFNum2 = get_class(tree, 'listlevel1RTFNum2')
    df_footnotetext = get_class(tree, 'footnotetext')
    df_footnotereference = get_class(tree, 'footnotereference')
    df_Heading1Char = get_class(tree, 'Heading1Char')

    df = pd.concat([df_SectionNumber,
                    #df_Heading1Char,
                    df_Instructions,
                    df_toc1,
                    df_Standard,
                    df_Answerlist,
                    df_RoutingFilter,
                    df_listlevel1RTFNum2,
                    df_footnotetext,
                    df_footnotereference,
                    df_Heading1Char
                 ])
    df.sort_values(by=['sourceline'], inplace=True)
    df = df[pd.notnull(df['title'])]

    df = df.apply(lambda x: x.replace('U+00A9',''))
    return df


def main():
    input_dir = '../LSYPE1/wave7-html'
    htmlFile = os.path.join(input_dir, 'YP-W7-final - Questionnaire.htm')
    tree = html_to_tree(htmlFile)

    title = tree.xpath('//title')[0].text

    df = get_questionnaire(tree)	
    # find each question
    df['questions'] = df.apply(lambda row: row['title'] if row['source'] in ['SectionNumber'] else None, axis=1)
    df['questions'] = df['questions'].ffill()
    # actual questionnaire
    df = df.loc[(df.sourceline >= 77), :]
    df.to_csv('../LSYPE1/wave7-html/YP-W7-final_attempt.csv', encoding = 'utf-8', index=False)

    # Questions
    df_all_questions = get_questions(tree)


    # add qg_ to all df_question_grids
    # add qi_ to all question_items
    df_all_questions['Label'] = df_all_questions.apply(lambda row: 'qg_' + row['Label'] if (type(row["Literal"]) != float  and 'GRID: FOR EACH ITEM' in row["Literal"] ) else 'qi_' + row['Label'], axis=1)



    df_all_questions.to_csv('../LSYPE1/wave7-html/df_all.csv', encoding = 'utf-8', index=False)
	
    # df_codes = df.loc[(df.source == 'Answerlist'), ['questions', 'sourceline', 'title']]
    df_codes = df.loc[(df.source == 'Answerlist') | (df.source == 'listlevel1RTFNum2'), ['questions', 'sourceline', 'title']]
    # response: numeric, text, datetime	
    search_values = ['Numeric', 'TEXTFILL', 'ENTER', 'RANGE', 'OPEN ENDED']
    df_response = df_codes.loc[(df_codes.title.str.contains('|'.join(search_values ))), ['questions', 'sourceline', 'title']]
    df_response['Type'] = df_response['title'].apply(lambda x: 'Numeric' if any (c in x for c in ['Numeric', 'RANGE']) else 'Text')
    df_response['Numeric_Type/Datetime_type'] = df_response['title'].apply(lambda x: 'Integer' if any (c in x for c in ['Numeric', 'RANGE']) else '')
    df_response['Min'] = df_response['title'].apply(lambda x: re.findall(r"(\d+.\d+|\d+)\-", x.replace('...','-').replace('..', '-'))[-1] if any (c in x for c in ['..', '-']) else None)
    df_response['Max'] = df_response['title'].apply(lambda x: re.findall(r"\-(\d+)", x.replace('...','-').replace('..', '-'))[0] if any (c in x for c in ['..', '-']) else None)
    df_response.rename(columns={'title': 'Label'}, inplace=True)


    # take the last row if duplicates in 'title'
    response_keep = ['Label', 'Type', 'Numeric_Type/Datetime_type', 'Min', 'Max']
    df_response = df_response.groupby(response_keep).tail(1)

    df_response.loc[:, response_keep].to_csv('../LSYPE1/wave7-html/response.csv', encoding = 'utf-8', index=False)	

    # code lists
    df_codes = df_codes[~df_codes.index.isin(df_response.index)]
    # split listlevel1RTFNum2 into different rows
    df_codes = (df_codes.set_index(['questions', 'sourceline']).apply(lambda x: x.str.split('\n').explode()).reset_index()) 

    # remove 'READ OUT'
    df_codes = df_codes.loc[(df_codes.title != 'READ OUT'), :]


    df_codes['codes_order'] = df_codes.groupby('questions').cumcount() + 1
    # split 1. yes to separate columns
    df_codes['value'] = df_codes.title.str.extract('(\d+)')

    # if missing value, fill with 'codes_order'
    df_codes['value'] = df_codes['value'].fillna(df_codes['codes_order']) 

    df_codes['Category_o'] = df_codes.apply(lambda row: re.sub('^{}|\.'.format(row['value']), '', row['title']), axis=1)
    df_codes['Category_o'] = df_codes['Category_o'].apply(lambda x: x.strip())
    # remove brackets
    df_codes['Category'] = df_codes['Category_o'].apply(lambda x: re.sub('\((.*?)\)', '', x))
    df_codes['Label'] = 'cs_' + df_codes['questions'].astype(str)
    df_codes.rename(columns={'sourceline': 'Number'}, inplace=True)
    df_codes_out = df_codes.drop(['questions', 'title', 'Category_o'], 1)
    #df_codes_out.to_csv('../LSYPE1/wave7-html/codes.csv', encoding = 'utf-8', index=False, sep=';')
	
	
    df_r = df_response.loc[:, ['questions', 'Label']]
    df_r.rename(columns={'Label': 'Response domain', 'questions': 'Label'}, inplace=True) 	
    df_question_answer = pd.merge(df_all_questions, df_r, how='left', on ='Label')
    df_question_answer['Response domain'] = df_question_answer.apply(lambda row: row['Response domain'] if row['Response domain'] == row['Response domain'] else 'cs_' + row['Label'].replace('qg_', '').replace('qi_', ''), axis=1)
    # rename duplicates names
    df_question_answer['Label_new'] = df_question_answer.groupby('Label').Label.apply(lambda n: n.str.strip() + '_' + (np.arange(len(n))).astype(str))
    df_question_answer['Label_new'] = df_question_answer['Label_new'].str.strip('_0')


    # rename
    df_question_answer = df_question_answer.drop('Label', 1)
    df_question_answer.rename(columns = {'Label_new': 'Label'}, inplace = True) 
    df_question_answer.to_csv('../LSYPE1/wave7-html/df_question_answer.csv', encoding = 'utf-8', index=False)
	
    # only question items here
    df_question_items = df_question_answer[~df_question_answer["Literal"].str.contains('GRID: FOR EACH ITEM', na=False)]

    # fill missing question literal with "?"
    df_question_items['Literal'].fillna('?', inplace=True)

    df_question_items.to_csv('../LSYPE1/wave7-html/df_question_items.csv', encoding = 'utf-8', index=False)
	
    # question grids
    df_question_grids = df_question_answer[df_question_answer["Literal"].str.contains('GRID: FOR EACH ITEM', na=False)]

    def f(string, match):
        string_list = string.split('GRID: FOR EACH ITEM')[1].split()
        match_list = []
        for word in string_list:
            if match in word:
                match_list.append(word)
        return match_list[0]

    df_question_grids['vertical_codes'] = df_question_grids['Literal'].apply(lambda x: f(x, '/'))
    df_question_grids['vertical_code_list_name'] = 'cs_' + df_question_grids['vertical_codes'].str.replace('/', '')

    df_question_grids.rename(columns = {'Response domain': 'horizontal_code_list_name'}, inplace = True)


    df_question_grids.to_csv('../LSYPE1/wave7-html/df_question_grids.csv', encoding = 'utf-8', index=False)
	
    # add vertical code into codes.csv
    df_qg_codes = df_question_grids.loc[:, ['vertical_code_list_name', 'vertical_codes']]
    df_qg_codes = df_qg_codes.drop_duplicates()

    df_qg_codes = (df_qg_codes.set_index(['vertical_code_list_name']).apply(lambda x: x.str.split('/').explode()).reset_index()) 

    df_qg_codes.rename(columns={'vertical_code_list_name': 'Label', 'vertical_codes': 'Category'}, inplace=True)
    df_qg_codes['codes_order'] = df_qg_codes.groupby(['Label']).cumcount() + 1
    df_qg_codes['value'] = df_qg_codes['codes_order']
    df_qg_codes['Number'] = ''
    

    df_codes_out.append(df_qg_codes, ignore_index=True).to_csv('../LSYPE1/wave7-html/codes.csv', encoding = 'utf-8', index=False, sep=';')
    # add one more line here for question grids
    with open('../LSYPE1/wave7-html/codes.csv', 'a') as file:
        file.write('-;-;;1;1\n')


    # sequences
    df_sequences = df.loc[(df.source == 'Heading1Char'), :]
    df_sequences.rename(columns={'title': 'Label'}, inplace=True)
  #  df_sequences['section_id'] = df_sequences.index + 1
  #  df_sequences.loc[:, ['sourceline', 'Label', 'section_id']].to_csv('../LSYPE1/wave7-html/sequences.csv', encoding = 'utf-8', index=False)
	

    # conditions
    df_conditions = df.loc[(df.source == 'RoutingFilter'), :]

    # remove {ask all} from conditions    
    df_conditions = df_conditions.loc[df_conditions.title != '{Ask all}', :]


    df_conditions['Logic_c'] = df_conditions['title'].apply(lambda x: re.findall('(?<=\().*(?=\))', x))
    df_conditions['Logic_c1'] = df_conditions['Logic_c'].apply(lambda x: '' if len(x) ==0 else x[0])

    df_conditions['Logic_r'] = df_conditions['Logic_c1'].str.replace('=', ' == ').str.replace('<>', ' != ').str.replace(' OR ', ' || ').str.replace(' AND ', ' && ').str.replace(' or ', ' || ').str.replace(' and ', ' && ')

    df_conditions['Logic_name'] = df_conditions['title'].apply(lambda x: re.findall(r"(\w+) *(=|>|<)", x)) 
    df_conditions['Logic_name1'] = df_conditions['Logic_name'].apply(lambda x: '' if len(x) ==0 else x[0][0])
    # needs two words 
    df_conditions['Logic_name2'] = df_conditions.apply(lambda row: row['questions'].strip() if (row['Logic_name1'].isdigit() or row['Logic_name1'] == '') else row['Logic_name1'].strip(), axis = 1)

    # rename duplicates logic names
    df_conditions['Logic_name_new'] = df_conditions.groupby('Logic_name2').Logic_name2.apply(lambda n: n.str.strip() + '_' + (np.arange(len(n))).astype(str))

    df_conditions['Logic_name_roman'] = df_conditions['Logic_name_new'].apply(lambda x: '_'.join([x.split('_')[0], int_to_roman(int(x.split('_')[1]))]))

    df_conditions['Logic_name_roman'] = df_conditions['Logic_name_roman'].str.strip('_0')
  
    df_conditions['Label'] = 'c_q' + df_conditions['Logic_name_roman']

    # rename inside 'logic', add qc_
    df_conditions['Logic'] = df_conditions.apply(lambda row: row['Logic_r'].replace(row['Logic_name2'], 'qc_' + row['Logic_name2']) if (row['Logic_name2'] in row['Logic_r']) else row['Logic_r'], axis = 1)


    df_conditions.rename(columns={'title': 'Literal'}, inplace=True)
    df_conditions = df_conditions.drop(['Logic_c', 'Logic_c1', 'Logic_r', 'Logic_name', 'Logic_name1', 'Logic_name2', 'Logic_name_new', 'Logic_name_roman'], 1)
    df_conditions.to_csv('../LSYPE1/wave7-html/df_conditions.csv', encoding = 'utf-8', index=False)

 
    # find parent label
    df_sequences_p = df_sequences.loc[:, ['sourceline', 'Label']]
    df_sequences_p['source'] = 'CcSequence'
    df_questions_p = df_question_answer.loc[:, ['sourceline', 'Label']]
    df_questions_p['source'] = 'CcQuestions'
    df_conditions_p = df_conditions.loc[:, ['sourceline', 'Label']]
    df_conditions_p['source'] = 'CcCondition'
    
    df_sequences_p_1 = pd.DataFrame([[0, 'LSYPE_Wave_7', 'CcSequence']], columns=['sourceline', 'Label', 'source']) 	

    df_parent = pd.concat([df_sequences_p, df_questions_p, df_conditions_p, df_sequences_p_1]).reset_index()
    df_parent = df_parent.sort_values(by=['sourceline']).reset_index()


    # hack to get intro before the first sequence
    l = df_parent.index[df_parent['source'] == 'CcSequence'].tolist()
    df_sequence_position = df_parent.iloc[[x for x in range(l[0], l[1]+1)] + l[2:], :]

    df_sequence_position['Position'] = range(0, len(df_sequence_position))
    df_sequence_position.to_csv('../LSYPE1/wave7-html/df_sequence_position.csv', encoding = 'utf-8', index=False)
    
    df_sequences_out = df_sequence_position.loc[(df_sequence_position['source'] == 'CcSequence') & (df_sequence_position['Label'] != 'LSYPE_Wave_7'), :]
    df_sequences_out.rename(columns={'Position': 'section_id'}, inplace=True)
    df_sequences_out.loc[:, ['sourceline', 'Label', 'section_id']].to_csv('../LSYPE1/wave7-html/sequences.csv', encoding = 'utf-8', index=False)

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
 
    df_parent.to_csv('../LSYPE1/wave7-html/df_parent.csv', encoding = 'utf-8', index=False)

    # output csv
    df_questions_new = pd.merge(df_question_items, df_parent, how='left', on=['sourceline', 'Label'])
    questions_keep = ['Label', 'Literal', 'Instructions', 'Response domain', 'above_label', 'parent_type', 'branch', 'Position']
    questions_keep_out = df_questions_new[questions_keep]

    # quick fix: statement: 
    # if the question has no answer, these become statement
    # needs: label, literal, parent_id, parent_type, position, branch

    no_answer_list = list(set(questions_keep_out['Response domain'])-set(df_codes_out['Label'])) 
    # print(no_answer_list)

    questions_keep_out_sub = questions_keep_out[~questions_keep_out['Response domain'].isin(no_answer_list)]
    questions_keep_out_sub.to_csv(os.path.join(input_dir, 'question_items.csv'), encoding='utf-8', index=False)

    df_statement = questions_keep_out[questions_keep_out['Response domain'].isin(no_answer_list)]

    QI_change_parent = list(set(questions_keep_out_sub['above_label']).intersection(set(df_statement['Label'])) )
    print( QI_change_parent )
    # checked question_grids, question_items, conditions, no parent_label is effected

    df_statement['Literal_new'] = df_statement['Literal'] + '\n' + df_statement['Instructions'].map(str)
    df_statement = df_statement.drop(['Literal', 'Instructions', 'Response domain'], 1)
    df_statement['Literal'] = df_statement['Literal_new'].apply(lambda x: x.replace('\nnan', ''))
    df_statement = df_statement.drop('Literal_new', 1)

    df_statement['Label'] = df_statement['Label'].apply(lambda x: x.replace('qi_', 's_'))
    df_statement.to_csv(os.path.join(input_dir, 'statements.csv'), encoding='utf-8', index=False)
    
 
    df_question_grids_new = pd.merge(df_question_grids, df_parent, how='left', on=['sourceline', 'Label'])
    question_grids_keep = ['Label', 'Literal', 'Instructions', 'horizontal_code_list_name', 'vertical_code_list_name', 'above_label', 'parent_type', 'branch', 'Position']
    df_question_grids_new[question_grids_keep].to_csv(os.path.join(input_dir, 'question_grids.csv'), encoding='utf-8', index=False)
 
    df_conditions_new = pd.merge(df_conditions, df_parent, how='left', on=['sourceline', 'Label'])

    conditions_keep = ['Label', 'Literal', 'Logic', 'above_label', 'parent_type', 'branch', 'Position']
    df_conditions_new[conditions_keep].to_csv(os.path.join(input_dir, 'conditions.csv'), encoding='utf-8', index=False)
	

if __name__ == "__main__":
    main()



