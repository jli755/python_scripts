#!/bin/env python3

"""
    Python 3
    Parse wave8 pdf file directly
"""

import pandas as pd
import numpy as np
import pdfplumber
import re
import os


def do_replace(s, d):
    """
    replace key with value from a dictionary
    """
    for k, v in d.items():
        # print((k,))
        s = s.replace(k, v)
    return s


def QuestionTextInsert(out_file, out_key, out_key_modified):
    """
    modify out_file and out_key from pdf_to_text function

    QuestionTextInsert:
        - replace all #*TextInsert part with it's actual text
    """
    with open(out_file, 'r') as file:
        out_file_text = file.read()

    # generate dictionary for question text intsert
    #                    no hash
    #                                                      at least one (nonpipe or nonwhite)
    l = re.findall('(\|*[^\#\s]*TextInsert.*)\n((?:\|*.*[^\|\s].*\n)+)\|*\s*\n', out_file_text)

    text_dict = {}
    for item in l:
        if len(item[0].strip().split(' ')) == 1 :
            k = item[0].replace('|', '').strip()
            v = 'TextInsert: ' + item[1].replace('|', '').strip()
            text_dict[k] = v

    # other text insert, not answer from question insert
    refer_list = re.findall('.*\{\#(\w+)\}.*', out_file_text)

    l1 = [x for x in refer_list if x not in text_dict.keys()]
    l1_names = '|'.join(['\|*' + x + '\s+' for x in l1])
    l1_search = re.findall('({0})\n((?:\|*.*[^\|\s].*\n)+)\|*\s*\n'.format(l1_names), out_file_text) 

    add_dict = {}
    for item in l1_search:
        k = item[0].replace('|', '').strip()
        if k in l1:
            v = 'TextInsert: ' + item[1].replace('|', '').strip()
            add_dict[k] = v

    # combine two dict
    text_dict.update(add_dict)

    # remove *QuestionTextInsert from key file
    with open(out_key, 'r') as in_f, open(out_key_modified, 'w') as out_f:
        for line in in_f:
            if not line.replace('|', '').strip() in text_dict.keys():
                out_f.write(line)

    return text_dict


def rreplace(s, old, new, occurrence):
    """
    Reverse replace string
    """
    li = s.rsplit(old, occurrence)
    return new.join(li)


def pdf_to_text(pdf_file, out_file, out_key):
    """
    input: pdf file, page number
    output:
        - raw text
        - key file contains section name, question name and if/loop
    """
    # TODO: quite possibly more
    prefixes = ['MODULE', 'Section', 'IF', 'PREVRELLOOP', 'ChildrenLoop']

    # TODO: these ones have an if before them
    prefixes.extend(['PELSLoop', 'Hist8loop', 'BENALOOP'])

    with pdfplumber.open(pdf_file) as pdf, open(out_file, 'w+') as f_out, open(out_key, 'w+') as k_out:
        for page in pdf.pages:
            text = page.extract_text()

            # remove page number
            n = page.page_number
            # manually fix change to new page
            if n in (26, 27, 71, 83, 89, 112, 121, 147, 182, 46, 6, 166):
               new_text = rreplace(text, str(n), '', 1).strip() + '\n'
            else:
                new_text = rreplace(text, str(n), ' \n', 1)
            f_out.write(new_text)

            for line in new_text.splitlines():
                # problem with line 583 or so | QI_Hist8_Date
                # see "Hist8=1,2,3,6" in pdf
                # hacked parsed output to add "| IF Hist8=..."
                # Also two more IF couple lines below
                # Also 599 no if
                # 695 delete one line
                # 746 del
                # 762 del
                # | Credit. -> join above line

                if line.startswith('| Hist8='):
                    line = line.replace('| Hist8=', '| IF Hist8=')
                elif line.startswith('| Hist8<>'):
                    line = line.replace('| Hist8<>', '| IF Hist8<>')
                elif line.startswith('IF any(GROP5, 12, 14) OR GROP4=3 OR (any(Groa,-8,-9) and (GROP2 = 3 or'):
                    line = 'IF any(GROP5, 12, 14) OR GROP4=3 OR (any(Groa,-8,-9) and (GROP2 = 3 or any(GROP3,12,14)))'
                elif line.startswith('any(GROP3,12,14)))'):
                    line = line.replace('any(GROP3,12,14)))', '')
                elif line.startswith('IF any(NETP5,12,14) OR NETP4=3 OR (any(NETA,-8,-9) AND (NETP2=3 OR'):
                    line = 'IF any(NETP5,12,14) OR NETP4=3 OR (any(NETA,-8,-9) AND (NETP2=3 OR any(NETP3,12,14)))'
                elif line.startswith('any(NETP3,12,14)))'):
                    line = line.replace('any(NETP3,12,14)))', '')
                elif line.startswith('IF (NETA >= 0 or NAWB >= 0 or NAFB >= 0 or NAMB >= 0 or NAYB >= 0 or NAOB>= 0 or any(-'):
                    line = 'IF (NETA >= 0 or NAWB >= 0 or NAFB >= 0 or NAMB >= 0 or NAYB >= 0 or NAOB>= 0 or any(-NAOB))'
                elif line.startswith('NAOB))'):
                    line = line.replace('NAOB))', '')
                elif line.startswith('| Tax Credit: Include Working Tax Credit, including Disabled Person’s Tax Credit, Child Tax'):
                    line = '| Tax Credit: Include Working Tax Credit, including Disabled Person’s Tax Credit, Child Tax Credit.'
                elif line.startswith('| Credit.'):
                    line = line.replace('| Credit.', '')

                if not any(x in line for x in ['{', '..', 'COMPUTE:', 'IF LOOP', 'IF CRNOWMA = 1 OR 2', 'Dummy', 'DUMMY', '?', 'Content', 'Never', 'Always', 'Include:', 'Exclude:', 'Credit.']):

                    if line.startswith(tuple(prefixes)):
                        k_out.write(line.strip() + '\n')
                    elif len(line.split()) == 1 and sum(1 for c in line if c.isupper()) > 0 :
                        k_out.write(line.strip() + '\n')
                    elif any(x in line.split() for x in ['|', '||', '|||']):
                        if 'Cintro' in line or 'Other state benefit' in line:
                            k_out.write(line.strip() + '\n')
                        if len(line.replace('|', '').split()) == 1 and sum(1 for c in line if c.isupper()) > 1:
                            k_out.write(line.strip() + '\n')
                        elif line.replace('|', '').lstrip().startswith(tuple(prefixes)):
                            k_out.write(line.strip() + '\n')


def get_sequence(key_file, order_sequences):
    """
    input: key file contains section names
    output: ordered sequence file with parent name and relative order
    """
    n = 0
    p = 0
    parent_name = ''
    sequences = ['MODULE', 'Section']
    with open(key_file) as in_file, open(order_sequences, 'w+') as out_sequences:
        out_sequences.write('Label,Parent_name,Position\n')

        for num, line in enumerate(in_file, 1):
            if line.startswith(tuple(sequences)):
                if line.startswith('MODULE'):
                    n = n + 1
                    p = 0

                    out_sequences.write('%s,,%4d\n' %(line.rstrip(), n))
                    parent_name = line.rstrip()
                else:
                    p = p + 1
                    out_sequences.write('%s,%s,%4d\n' %(line.rstrip(), parent_name, p))
                parent_type = 'CcSequence'


def get_condition(key_file, order_condition, order_loop, order_question):
    """
    input: key file contains 'IF'
    output: ordered condition file with parent name and relative order
    """
    current_p = 0
    current_parent = ''
    global_loop = 0
    pre_name = ''
    i = 0
    question_names = []
    sequences = ['IF', '| IF', '|| IF', '||| IF']

    # get the whole input as a list (so we can zip it later)
    with open(key_file) as in_file:
        content = in_file.readlines()
    # now in_file is a list
    in_file = content
    in_file.append("ADD DUMMY LINE TO BE IGNORED FOR ZIP")

    with open(order_condition, 'w+') as out_condition, open(order_loop, 'w+') as out_loop, open(order_question, 'w+') as out_question:
        out_condition.write('Label;Literal;above_label;parent_type;Position\n')
        out_loop.write('Label;Loop_While;above_label;parent_type;Position\n')
        out_question.write('Label;above_label;Position\n')

        L = []
        depth = 0
        #for num, line in enumerate(in_file, 1):
        # Sometimes want nextline as well
        for num, (line, nextline) in enumerate(zip(in_file, in_file[1:]), 1):
            line = line.rstrip()
            if num == 1:
                # print(line)
                assert line.startswith("MODULE")
                modname = line.lstrip("MODULE")
                # TODO hardcoded for now
                modname = line.lstrip("1: ")
                L.append([0, modname])
                continue


            def startsWithNPipes(s, n):
                return s.count('|') == n and line[0:n] == '|'*n

            def numberOfPipesAtStart(s):
                n = 0
                for j in range(0, len(s)):
                   if s[j] == '|':
                       n += 1
                   else:
                       return n

            # funny hack b/c sections can be inside loops but are not marked so
            # so we check the next line too
            if line.startswith('Section'):
                # print("="*78)
                # print("We are {} deep, found a section, might hack...".format(depth))
                # print(L)
                # print(line)
                # print(nextline)
                #if startsWithNPipes(nextline, depth):
                if nextline.startswith('|'):  # any number of pipes
                    # print("we think this is a nested section")
                    tmp = numberOfPipesAtStart(nextline)
                    # print("the line after as {0} pipes so hacking {0} pipes onto the section".format(tmp))
                    line = '|'*tmp + line
                else:
                    print("no we are not hacking this section, not nested")
                # print("="*78)

            m = numberOfPipesAtStart(line)
            if m == depth:
               # normal in a loop
               line = line.lstrip('| ')
            elif m > depth:
               # print(num)
               # print(m)
               # print(depth)
               # print(line)
               raise ValueError('something not right!')
            else:  # m < depth
               # above not true, multiple if/loops count end
               for j in range(0, depth - m):
                  b = L.pop()
                  # print('d{}]{}: conditional ended: "{}" back to "{}"'.format(depth, num, b[1], L[-1][1]))
                  depth = depth - 1
                  # print(L)
               assert depth >= 0
               line = line.lstrip('| ')

            if line.startswith('Section') or line.startswith('MODULE'):
               # depth unchanged but reset pos and new parent name
               # print('='*78)
               if line.startswith('Section 8.13'):
                   print(depth)
                   #print(m)
                   #print(numberOfPipesAtStart(line))
                   #print(line)
               # print(L)
               L[-1] = [0, line]
               #if line.startswith('Section 8.13'):
               # print(L)
               # print('='*78)
               continue  # TODO?  really?  output somewhere?


            elif line.startswith('IF') :
               # line = line.encode("unicode_escape").decode()  # get rid of non-ascii in IF

               L[-1][0] += 1
               pos = L[-1][0]
               parent = L[-1][1]
               # print(L)
               if line.startswith('IF FieldSerial'):
                   print(("***", line, parent))
               global_loop += 1
               label = 'c_IF_{}'.format(global_loop)
               #label = line.lstrip('IF ')])
               depth = depth + 1
               L.append([0, label])
               # TODO: output
               #print('[d{}]{}: IF w/ pos {} parent "{}", label: "{}"'.format(depth, num, pos, parent, label))
               if parent.startswith('Section') or parent.startswith('MODULE'):
                   parent_type = 'CcSequence'
               elif parent.startswith('c_IF'):
                   parent_type = 'CcCondition'
               elif parent.startswith('l_'):
                   parent_type = 'CcLoop'
               else:
                   parent_type = 'other'

               out_condition.write('%s;%s;%s;%s;%4d\n' %(label,line.rstrip().replace('"', ''), parent, parent_type, pos))

            elif 'loop' in line.split()[0].lower():  # .endswith not enough
                L[-1][0] += 1
                pos = L[-1][0]
                parent = L[-1][1]
                global_loop += 1
                label = 'l_{}'.format(line.split()[0])
                depth = depth + 1
                L.append([0, label])
                # TODO: output
                # print('[d{}]{}: LOOP w/ pos {} parent "{}", label: "{}"'.format(depth, num, pos, parent, label))
                if parent.startswith('Section') or parent.startswith('MODULE'):
                    parent_type = 'CcSequence'
                elif parent.startswith('c_IF'):
                    parent_type = 'CcCondition'
                elif parent.startswith('l_'):
                    parent_type = 'CcLoop'
                else:
                    parent_type = 'other'

                if ('End' not in line) and (line.rstrip() !='BENALOOP'):
                    out_loop.write('%s;%s;%s;%s;%4d\n' %(label,line.rstrip(), parent, parent_type, pos))

            else:  # Question
                L[-1][0] += 1
                pos = L[-1][0]
                parent = L[-1][1]
                label = line
                if label in question_names:
                    label = label + '_' + str(i)
                    question_names.append(label)
                    i = i + 1
                    # print(label)
                else:
                    label = label
                    question_names.append(label)

                out_question.write('%s;%s;%4d\n' %(label, parent, pos))


# need a hack to get code list between current question and next question
def get_condition_2(key_file, order_question):
    """
    input: key file contains 'IF'
    output: ordered condition file with parent name and relative order
    """
    current_p = 0
    current_parent = ''
    global_loop = 0
    pre_name = ''
    i = 0
    question_names = []
    sequences = ['IF', '| IF', '|| IF', '||| IF']

    # get the whole input as a list (so we can zip it later)
    with open(key_file) as in_file:
        content = in_file.readlines()
    # now in_file is a list
    in_file = content
    in_file.append("ADD DUMMY LINE TO BE IGNORED FOR ZIP")

    with open(order_question, 'w+') as out_question:
        out_question.write('Label;above_label;Position\n')

        L = []
        depth = 0
        #for num, line in enumerate(in_file, 1):
        # Sometimes want nextline as well
        for num, (line, nextline) in enumerate(zip(in_file, in_file[1:]), 1):
            line = line.rstrip()
            if num == 1:
                assert line.startswith("MODULE")
                modname = line.lstrip("MODULE")
                # TODO hardcoded for now
                modname = line.lstrip("1: ")
                L.append([0, modname])
                continue


            def startsWithNPipes(s, n):
                return s.count('|') == n and line[0:n] == '|'*n

            def numberOfPipesAtStart(s):
                n = 0
                for j in range(0, len(s)):
                   if s[j] == '|':
                       n += 1
                   else:
                       return n

            # funny hack b/c sections can be inside loops but are not marked so
            # so we check the next line too
            if line.startswith('Section'):
                # print("="*78)
                # print("We are {} deep, found a section, might hack...".format(depth))
                # print(L)
                # print(line)
                # print(nextline)
                #if startsWithNPipes(nextline, depth):
                if nextline.startswith('|'):  # any number of pipes
                    # print("we think this is a nested section")
                    tmp = numberOfPipesAtStart(nextline)
                    # print("the line after as {0} pipes so hacking {0} pipes onto the section".format(tmp))
                    line = '|'*tmp + line
                else:
                    print("no we are not hacking this section, not nested")
                # print("="*78)

            m = numberOfPipesAtStart(line)
            if m == depth:
               # normal in a loop
               line = line.lstrip('| ')
            elif m > depth:
               # print(num)
               # print(m)
               # print(depth)
               # print(line)
               raise ValueError('something not right!')
            else:  # m < depth
               # above not true, multiple if/loops count end
               for j in range(0, depth - m):
                  b = L.pop()
                  # print('d{}]{}: conditional ended: "{}" back to "{}"'.format(depth, num, b[1], L[-1][1]))
                  depth = depth - 1
                  # print(L)
               assert depth >= 0
               line = line.lstrip('| ')

            if line.startswith('Section') or line.startswith('MODULE'):
               # depth unchanged but reset pos and new parent name
               # print('='*78)
               if line.startswith('Section 8.13'):
                   print(depth)
                   # print(m)
                   # print(numberOfPipesAtStart(line))
                   # print(line)
               # print(L)
               L[-1] = [0, line]
               #if line.startswith('Section 8.13'):
               # print(L)
               # print('='*78)
               continue  # TODO?  really?  output somewhere?


            elif line.startswith('IF') :
               # line = line.encode("unicode_escape").decode()  # get rid of non-ascii in IF
               # print(L)
               L[-1][0] += 1
               pos = L[-1][0]
               parent = L[-1][1]
               # print(L)
               if line.startswith('IF FieldSerial'):
                   print(("***", line, parent))
               global_loop += 1
               label = 'c_IF_{}'.format(global_loop)
               #label = line.lstrip('IF ')])
               depth = depth + 1
               L.append([0, label])
               # TODO: output
               #print('[d{}]{}: IF w/ pos {} parent "{}", label: "{}"'.format(depth, num, pos, parent, label))
               if parent.startswith('Section') or parent.startswith('MODULE'):
                   parent_type = 'CcSequence'
               elif parent.startswith('c_IF'):
                   parent_type = 'CcCondition'
               elif parent.startswith('l_'):
                   parent_type = 'CcLoop'
               else:
                   parent_type = 'other'
               # out_condition.write('%s;%s;%s;%s;%4d\n' %(label,line.rstrip().replace('"', ''), parent, parent_type, pos))

            elif 'loop' in line.split()[0].lower():  # .endswith not enough
               L[-1][0] += 1
               pos = L[-1][0]
               parent = L[-1][1]
               global_loop += 1
               label = 'l_{}'.format(line.split()[0])
               depth = depth + 1
               L.append([0, label])
               # TODO: output
               # print('[d{}]{}: LOOP w/ pos {} parent "{}", label: "{}"'.format(depth, num, pos, parent, label))
               if parent.startswith('Section') or parent.startswith('MODULE'):
                   parent_type = 'CcSequence'
               elif parent.startswith('c_IF'):
                   parent_type = 'CcCondition'
               elif parent.startswith('l_'):
                   parent_type = 'CcLoop'
               else:
                   parent_type = 'other'

               # if ('End' not in line) and (line.rstrip() !='BENALOOP'):
               #     out_loop.write('%s;%s;%s;%s;%4d\n' %(label,line.rstrip(), parent, parent_type, pos))

            else:  # Question

               L[-1][0] += 1
               pos = L[-1][0]
               parent = L[-1][1]
               label = line
               if label in question_names:
                   label = label + '_' + str(i)
                   question_names.append(label)
                   i = i + 1
                   # print(label)
               else:
                   label = label
                   question_names.append(label)

               # print('[d{}]{}: Q w/ pos {} parent "{}", label: "{}"'.format(depth, num, pos, parent, label))
               out_question.write('%s;%s;%4d\n' %(label, parent, pos))


def get_question_item(question_item, order_question):
    """
        From question items and orders get the final db input temp file
    """
    keep_col = ['Name','Text', 'CodeListID', 'Label']

    df_question_item = pd.read_csv(question_item, sep=',')

    df_order = pd.read_csv(order_question, sep=';')
    df_order['new_name'] = df_order['Label'].map(lambda x: re.sub('(_\d+)$', '', x))

    df_QI = pd.merge(df_question_item.loc[:, keep_col], df_order, how='right', left_on='Name', right_on='new_name')
    df_QI.to_csv('TEMP.csv', sep = ';', index=False)

    df_QI['code_name_old'] = 'cs_' + df_QI['Label_y']
    df_QI['code_name'] = df_QI['code_name_old'].map(lambda x: re.sub('(_\d+)$', '', x) if not pd.isnull(x) else x)

    df_QI = df_QI.rename(columns={'Label_x': 'response_domain_name'})
    df_QI.drop(['Name', 'new_name'], axis=1, inplace=True)

    df_QI['Response_domain'] = df_QI.apply(lambda row: next(item for item in [row['response_domain_name'], row['code_name']] if item is not np.NaN), axis=1)

    df_QI_new = df_QI.loc[:, ['Label_y', 'Text', 'Response_domain', 'above_label', 'Position']]
    df_QI_new = df_QI_new.rename(columns={'Label_y': 'Label', 'Text': 'Literal'})
    df_QI_new['parent_type'] = df_QI_new['above_label'].apply(lambda x: 'CcSequence' if x.startswith('Section') else 'CcCondition' if x.startswith('c_IF') else 'CcLoop')   

    return df_QI_new.drop_duplicates(subset=['Label', 'above_label', 'Position', 'parent_type'], keep="last")


def get_question_grid(question_grid, order_question):
    """
        From question items and orders get the final db input temp file
    """
    df_question_grid = pd.read_csv(question_grid, sep=',')
    df_order = pd.read_csv(order_question, sep=';')
    df_QG = pd.merge(df_question_grid, df_order, how='inner', left_on='Label', right_on='Label')

    df_QG.drop(['vertical_code_list_id', 'horizontal_code_list_id'], axis=1, inplace=True)
    df_QG['parent_type'] = df_QG['above_label'].apply(lambda x: 'CcSequence' if x.startswith('Section') else 'CcCondition' if x.startswith('c_IF') else 'CcLoop')
    return df_QG


def get_codes(codeslist, question_item, question_grid):
    """
        From question items and orders get the final db input temp file
        TODO: order of the codes seems off
    """
    df_CO = pd.read_csv(codeslist, sep=',')
    df_QI = pd.read_csv(question_item, sep=',')
    df_QuestionItem_codes = pd.merge(df_QI.loc[df_QI['CodeListID'].notnull(), ['Name', 'CodeListID']], df_CO, how='left', left_on='CodeListID', right_on='CodeList_ID')
    df_QuestionItem_codes['Label'] = 'cs_' + df_QuestionItem_codes['Name']

    df_QuestionItem_codes_keep = df_QuestionItem_codes.loc[:, ['Label', 'Category', 'Value', 'codes_order']]
    # TODO
    # df_QuestionItem_codes_keep['Codes_Order'] = df_QuestionItem_codes_keep.groupby('Label').cumcount() + 1
    # df_QuestionItem_codes_keep['Value'] = df_QuestionItem_codes_keep['Codes_Order']

    df_QG = pd.read_csv(question_grid, sep=',')
    df_QuestionGrid_codes_h = pd.merge(df_QG, df_CO, how='inner', left_on='horizontal_code_list_id', right_on='CodeList_ID')
    df_QuestionGrid_codes_h_keep = df_QuestionGrid_codes_h.loc[:, ['horizontal_code_list_name', 'Category', 'Value', 'codes_order']]
    df_QuestionGrid_codes_h_keep = df_QuestionGrid_codes_h_keep.rename(columns={'horizontal_code_list_name': 'Label'})

    df_QuestionGrid_codes_v = pd.merge(df_QG, df_CO, how='inner', left_on='vertical_code_list_id', right_on='CodeList_ID')
    df_QuestionGrid_codes_v_keep = df_QuestionGrid_codes_h.loc[:, ['vertical_code_list_name', 'Category', 'Value', 'codes_order']]
    df_QuestionGrid_codes_v_keep = df_QuestionGrid_codes_v_keep.rename(columns={'vertical_code_list_name': 'Label'})

    return pd.concat([df_QuestionItem_codes_keep, df_QuestionGrid_codes_h_keep, df_QuestionGrid_codes_v_keep])


def get_code_list_from_questionpair(txt_file, question_1, question_2, debug=False):
    with open(txt_file, 'r') as content_file:
        content = content_file.read()

    #question_1 = 'REHB'
    #question_2 = 'REGR'

    result = re.findall('%s\s*\n(.*?)%s\s*\n' % (question_1, question_2), content, re.DOTALL)

    # hack here
    if question_1.upper() in ('RAGE', 'RENT'):
        result = None

    if not result:
        return []
    if not len(result) == 1:
        pass
        #print("PANIC: results might be garbage")
        #print(result)
        #raise NameError('foo')
    result = result[0]

    def stuff(res, debug=debug):
        if debug:
            print("--------------------"*2)
            print(res)
            print("--------------------"*2)
        codes = re.findall('(\d+)\. (.*)', res)
        return codes

    #if 'GRID COLS' in result:
    A = result.split('GRID COLS')

    if len(A) == 1:
        return ["REGULAR", stuff(result)]
    elif len(A) == 2:
        A, B = A
        #print(A)
        #print(B)
        return ["HORIZ", stuff(A), "VERTICAL", stuff(B)]
    else:
        #print(A)
        #print(question_1)
        #print(question_2)
        # TODO: something horrid here
        return []
        #raise ValueError("too many GRID COLS")


def get_code_list_from_questionpair_nogridcol(txt_file, question_1, question_2, debug=False):
    with open(txt_file, 'r') as content_file:
        content = content_file.read()

    #question_1 = 'REHB'
    #question_2 = 'REGR'

    result = re.findall('%s\s*\n(.*?)%s\s*\n' % (question_1, question_2), content, re.DOTALL)
    if not result:
        return []
    if not len(result) == 1:
        pass
        #print("PANIC: results might be garbage")
        #print(result)
        #raise NameError('foo')
    result = result[0]

    if debug:
        print("--------------------"*2)
        print(result)
        print("--------------------"*2)
    codes = re.findall('(\d+)\. (.*)', result)
    #print(codes.group(1))
    #print(codes.group(2))
    #codes = [codes.group(i) for i in range(0, len(codes))]
    #print(codes)
    return codesget_code_list_from_questionpair


def generate_code_list(txt_file, question_file, output_code):
    df = pd.read_csv(question_file, sep=';')
    L = question_name_list = df['Label']
    g = get_code_list_from_questionpair

    # print("="*80)


    with open(output_code, 'w+') as out_code:
        out_code.write('Label;Value;Category;codes_order\n')
        # this line is for the question grid
        out_code.write('-;1;-;1\n')

        for i in range(0, len(L)-1):
            # print("="*80)
            # print("{}: {}..{}".format(i, L[i], L[i+1]))
            #if 'HusbandWifePartnepirrTextInsert' in L[i]:
            if True:
                end_with_number = re.search(r'\d+', L[i+1])
                second = re.sub('(_\d+)$', '', L[i+1])
                if end_with_number is not None and second in L:
                    c = g(txt_file, L[i], second)
                else:
                    c = g(txt_file, L[i], L[i+1])
                # print("{}: {}: {}".format(i, L[i], c))
                if len(c) == 2:
                    name = "cs_{}".format(L[i])
                    assert c[0] == 'REGULAR'
                    code_list = c[1]
                    for j in range(0, len(code_list)):
                        value = code_list[j][0]
                        cat = code_list[j][1]
                        #print("{}\t{}\t{}\t{}".format(name, value, cat, j+1))
                        out_code.write('%s;%4d;%s;%4d\n' %(name, int(value), cat, j+1))
                elif len(c) == 4:
                    #print(L[i])
                    #print(c)
                    name = "cs_{}_horizontal".format(L[i])
                    assert c[0] == 'HORIZ'
                    code_list = c[1]
                    for j in range(0, len(code_list)):
                        value = code_list[j][0]
                        cat = code_list[j][1]
                        # print("{}\t{}\t{}\t{}".format(name, value, cat, j+1))
                        out_code.write('%s;%4d;%s;%4d\n' %(name, int(value), cat, j+1))
                    name = "cs_{}_vertical".format(L[i])
                    assert c[2] == 'VERTICAL'
                    code_list = c[3]
                    for j in range(0, len(code_list)):
                        value = code_list[j][0]
                        cat = code_list[j][1]
                        # print("{}\t{}\t{}\t{}".format(name, value, cat, j+1))
                        out_code.write('%s;%4d;%s;%4d\n' %(name, int(value), cat, j+1))
                elif len(c) == 0:
                    pass
                else:
                    print(c)
                    raise ValueError("unexpected return")


def main():
# if True:
    base_dir = '../LSYPE1/wave8-xml/pdf'
    wave8_pdf = os.path.join(base_dir, 'wave8.pdf')
    out_file = os.path.join(base_dir, 'wave8_all_pages.txt')
    key_file = os.path.join(base_dir, 'wave8_all_keys.txt')
    order_question = os.path.join(base_dir, 'wave8_order_question.csv')
    order_question_2 = os.path.join(base_dir, 'wave8_order_question_2.csv')

    db_input_dir = '../LSYPE1/wave8-xml/db_temp_input'
    order_sequences = os.path.join(db_input_dir, 'wave8_sequences.csv')
    order_condition = os.path.join(db_input_dir, 'wave8_condition.csv')
    order_loop = os.path.join(db_input_dir, 'wave8_order_loop.csv')

    # pdf to text
    pdf_to_text(wave8_pdf, out_file, key_file)

    # remove question text insert from key file
    key_file_modify = os.path.join(base_dir, 'wave8_all_keys_modify.txt')
    text_insert_dict = QuestionTextInsert(out_file, key_file, key_file_modify)

    # import json
    # # Serialize data into file:
    # json.dump( text_insert_dict, open( os.path.join(base_dir, 'question_text_insert.json'), 'w' ), indent=2 )
    # # print(text_insert_dict['CRDIVORQuestionTextInsert'])

    # produce sequence input file
    get_sequence(key_file_modify, order_sequences)

    # produce condition file
    get_condition(key_file_modify, order_condition, order_loop, order_question)

    get_condition_2(key_file, order_question_2)

    # gather all information for db input
    df_question_item = get_question_item('../LSYPE1/wave8-xml/db_input/QuestionItem.csv', order_question)
    df_question_grid = get_question_grid('../LSYPE1/wave8-xml/db_input/QuestionGrid.csv', order_question)

    # replace *QuestionTextInsert using question text dictionary
    df_question_item['Literal_new'] = df_question_item['Literal'].apply(lambda x: do_replace(x, text_insert_dict) if not pd.isnull(x) else x)
    df_question_item['Literal'] = df_question_item['Literal_new']
    df_question_item = df_question_item.drop('Literal_new', 1)

    df_question_grid['Literal_new'] = df_question_grid['Literal'].apply(lambda x: do_replace(x, text_insert_dict) if not pd.isnull(x) else x)
    df_question_grid['Literal'] = df_question_grid['Literal_new']
    df_question_grid = df_question_grid.drop('Literal_new', 1)

    generate_code_list(out_file,
                       order_question_2,
                       os.path.join(db_input_dir, 'codes.csv'))

    df_codes = pd.read_csv(os.path.join(db_input_dir, 'codes.csv'), sep=';')
    df_codes_sub = df_codes[~df_codes['Label'].isin(['cs_' + i for i in text_insert_dict.keys()])]
    df_codes_sub = df_codes_sub.drop_duplicates(subset=['Label', 'Value'], keep="first")

    df_codes_sub.to_csv(os.path.join(db_input_dir, 'wave8_codes.csv'), sep=';', index=False)

    print("rescue question literal")
    def fill_question_literal(question, codelist, txt_content):
        result = re.findall('%s\s*\n(.*?)%s\s*\n' % (question, codelist), txt_content, re.DOTALL)

        if result != []:
            return result[0].replace('|', '').strip()
        else:
            return None

    with open(out_file, 'r') as content_file:
        wave8_content = content_file.read()

    df_question_item['Literal_new'] = df_question_item.apply(lambda row: fill_question_literal(row['Label'], df_codes_sub.loc[(df_codes_sub.Label == 'cs_' + row['Label']) & (df_codes_sub.codes_order == 1)]['Category'].values[0], wave8_content) if pd.isnull(row['Literal']) and 'cs_' + row['Label'] in df_codes_sub.Label.tolist() else row['Literal'], axis=1)
    df_question_item.drop(['Literal'], axis=1, inplace=True)
    df_question_item = df_question_item.rename(columns={'Literal_new': 'Literal'})

    # convert question grid to question item, modify position
    # code list lable
    df_code_horizontal = df_codes_sub.loc[ df_codes_sub['Label'].str.contains("_horizontal") , :]

    # merge question grid with horizontal code
    df_qg_horizontal = df_question_grid.merge(df_code_horizontal, left_on='horizontal_code_list_name', right_on='Label', how='left')
    df_qg_horizontal['Label'] = df_qg_horizontal.apply(lambda row: row['Label_x'].replace('qg', 'qi') + '_' + str(int(row['codes_order'])) if not pd.isnull(row['codes_order']) else row['Label_x'].replace('qg', 'qi'), axis=1 )
    df_qg_horizontal['Literal_new'] = df_qg_horizontal['Literal'] + ' < ' + df_qg_horizontal['Value'].astype(str) + ', ' + df_qg_horizontal['Category'] + ' >'

    df_qg_horizontal['Response_domain'] = df_qg_horizontal['vertical_code_list_name']
    df_qg_horizontal['Position_new'] = df_qg_horizontal['Position'] + df_qg_horizontal['codes_order'] - 1
    df_qg_horizontal = df_qg_horizontal.drop(['vertical_code_list_name', 'Label_y', 'Literal', 'Position'], 1)
    df_qg_horizontal.rename(columns={'Literal_new': 'Literal', 'Position_new': 'Position'}, inplace=True)

    # for each question group item find it's original parent/position
    df_qg_postion = df_qg_horizontal[['Label', 'above_label', 'Position', 'parent_type']]
    # for each question group item find the number need to be added to the position
    df_size = df_qg_horizontal.groupby(['Label_x']).size().to_frame('size').reset_index()

    # if size=1 in gq, no need to modify position
    size_one_label = df_size[df_size['size'] == 1]['Label_x'].tolist() 

    df_qg_horizontal['qi_position'] = df_qg_horizontal['Label'].apply(lambda x: df_question_item[df_question_item['Label'] == x.split('_')[0]]['Position'].values[0] )
    # modified position
    df_qg_horizontal['position_mod'] = df_qg_horizontal.apply(lambda row: row['Position'] if row['Label'] in size_one_label else row['qi_position'] * 10 + row['Position'], axis=1)

    df_condition = pd.read_csv(order_condition, sep=';')
    df_loop = pd.read_csv(order_loop, sep=';')

    keep_cols = ['Label', 'above_label', 'Position']
    df_qi_cols = df_question_item[keep_cols]
    df_if_cols = df_condition[keep_cols]
    df_loop_cols = df_loop[keep_cols]

    df_qi_cols['position_mod'] = df_qi_cols['Position'] * 10
    df_if_cols['position_mod'] = df_if_cols['Position'] * 10
    df_loop_cols['position_mod'] = df_loop_cols['Position'] * 10

    df_qg_cols = df_qg_horizontal[['Label', 'above_label', 'Position', 'position_mod']]
    # stack
    df_mod_pos = pd.concat([df_qi_cols, df_qg_cols, df_if_cols, df_loop_cols], ignore_index=True)
    # sort
    df_mod_pos = df_mod_pos.sort_values(['above_label', 'position_mod'], ascending=[True, True])
    # create new position
    df_mod_pos['New'] = df_mod_pos.groupby('above_label').cumcount()
    mod_dict = dict(zip(df_mod_pos.Label, df_mod_pos.New))

    df_mod_pos.to_csv('TMP.csv', sep=';')

    qi_cols = ['Label', 'Literal', 'Response_domain', 'above_label', 'Position', 'parent_type']
    df_qi_add = df_qg_horizontal[qi_cols]

    # shift position after question grid for same parent[['Label', 'above_label', 'Position',
    df_question_item = df_question_item[~df_question_item.Label.isin(df_question_grid.Label)]
    df_qi_new = pd.concat([df_question_item, df_qi_add], ignore_index=True)

    df_qi_new['Position'] = df_qi_new['Position'].map(mod_dict)
    df_condition['Position'] = df_condition['Position'].map(mod_dict)
    df_loop['Position'] = df_loop['Position'].map(mod_dict)

    df_qi_new.to_csv(os.path.join(db_input_dir, 'wave8_question_item.csv'), sep=';', index=False)
    pd.DataFrame(columns=df_question_grid.columns).to_csv(os.path.join(db_input_dir, 'wave8_question_grid.csv'), sep='@', index=False)
    df_condition.to_csv(order_condition, sep=';', index=False)
    df_loop.to_csv(order_loop, sep=';', index=False)


if __name__ == "__main__":
    main()

