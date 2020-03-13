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
            n = page.page_number 
            new_text = rreplace(text, str(n), '', 1)
            f_out.write(new_text)

            for line in new_text.splitlines():
                if not any(x in line for x in ['{', '..', 'COMPUTE:', 'IF LOOP', 'IF CRNOWMA = 1 OR 2']):
                    if line.startswith(tuple(prefixes)):
                        k_out.write(line + '\n')
                    elif len(line.split()) == 1 and sum(1 for c in line if c.isupper()) > 2 :
                        k_out.write(line + '\n')
                    elif any(x in line.split() for x in ['|', '||', '|||']):
                        if len(line.replace('|', '').split()) == 1 and sum(1 for c in line if c.isupper()) > 0:
                            k_out.write(line + '\n')
                        elif line.replace('|', '').lstrip().startswith(tuple(prefixes)):
                            k_out.write(line + '\n')


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
    in_file.append("DUMMY LINE TO BE IGNORED FOR ZIP")
    

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
                print("="*78)
                print("We are {} deep, found a section, might hack...".format(depth))
                print(L)
                print(line)
                print(nextline)
                #if startsWithNPipes(nextline, depth):
                if nextline.startswith('|'):  # any number of pipes
                    print("we think this is a nested section")
                    tmp = numberOfPipesAtStart(nextline)
                    print("the line after as {0} pipes so hacking {0} pipes onto the section".format(tmp))
                    line = '|'*tmp + line
                else:
                    print("no we are not hacking this section, not nested")
                print("="*78)

            m = numberOfPipesAtStart(line)
            if m == depth:
               # normal in a loop
               line = line.lstrip('| ')          
            elif m > depth:
               print(num)
               print(line)
               raise ValueError('something not right!')
            else:  # m < depth
               # above not true, multiple if/loops count end
               for j in range(0, depth - m):
                  b = L.pop()
                  print('d{}]{}: conditional ended: "{}" back to "{}"'.format(depth, num, b[1], L[-1][1]))
                  depth = depth - 1
                  print(L)
               assert depth >= 0
               line = line.lstrip('| ')          

            if line.startswith('Section') or line.startswith('MODULE'):
               # depth unchanged but reset pos and new parent name
               print('='*78)
               if line.startswith('Section 8.13'):
                   print(depth)
                   print(m)
                   print(numberOfPipesAtStart(line))
                   print(line)
               print(L)
               L[-1] = [0, line]
               #if line.startswith('Section 8.13'):
               print(L)
               print('='*78)
               continue  # TODO?  really?  output somewhere?

            # problem with line 583 or so | QI_Hist8_Date 
            # see "Hist8=1,2,3,6" in pdf
            # hacked parsed output to add "| IF Hist8=..."
            # Also two more IF couple lines below
            # Also 599 no if
            # 695 delete one line
            # 746 del
            # 762 del

            elif line.startswith('IF'):
               # line = line.encode("unicode_escape").decode()  # get rid of non-ascii in IF
               print(L)
               L[-1][0] += 1
               pos = L[-1][0]
               parent = L[-1][1]
               print(L)
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
               print('[d{}]{}: LOOP w/ pos {} parent "{}", label: "{}"'.format(depth, num, pos, parent, label))
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
                   print(label)
               else:
                   label = label
                   question_names.append(label)
                 
                   

               print('[d{}]{}: Q w/ pos {} parent "{}", label: "{}"'.format(depth, num, pos, parent, label))
               out_question.write('%s;%s;%4d\n' %(label, parent, pos))

            # if line.startswith(tuple(sequences)):
                
            #     Label = 'c_' + pre_name
            #     Literal = line.rstrip()
            #     out_condition.write('%s;%s;%s;%4d\n' %(Label, Literal,current_parent,n))
            #     parent_name = Label


            # current_p = n
            # pre_name = line.rstrip().replace('|','').lstrip()

            
            # if line.startswith('Section'):
            #     n = 0
            #     current_parent = line.rstrip()
            #     L.append([0, current_parent])
            #     #top_level = line.rstrip()

            # if line.startswith('|'):
            #     n = current_p
            #     current_parent = top_level
            #     top_level = pre_name

            # else:
            #     n = L[-1][0]               
            #     n = n + 1
            #     L[-1][0] = n
            #     #top_level = pre_level

          
def get_question_item(question_item, order_question):
    """
        From question items and orders get the final db input temp file
    """
    keep_col = ['Name','Text', 'CodeListID', 'Label']

    df_question_item = pd.read_csv(question_item, sep=',')

    df_order = pd.read_csv(order_question, sep=';')
    df_order['new_name'] = df_order['Label'].map(lambda x: re.sub('(_\d+)$', '', x))

    df_QI = pd.merge(df_question_item.loc[:, keep_col], df_order, how='inner', left_on='Name', right_on='new_name')
    df_QI.to_csv('TEMP.csv', sep = ';', index=False)
 
    df_QI['code_name_old'] = 'cs_' + df_QI['Label_y']
    df_QI['code_name'] = df_QI['code_name_old'].map(lambda x: re.sub('(_\d+)$', '', x))

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

    print("="*80)


    with open(output_code, 'w+') as out_code:
        out_code.write('Label;Value;Category;codes_order\n')
        # this line is for the question grid
        out_code.write('-;1;-;1\n')

        for i in range(0, len(L)-1): 
            #print("="*80) 
            #print("{}: {}..{}".format(i, L[i], L[i+1])) 
            #if 'HusbandWifePartnepirrTextInsert' in L[i]:
            if True:
                end_with_number = re.search(r'\d+', L[i+1]) 
                second = re.sub('(_\d+)$', '', L[i+1])
                if end_with_number is not None and second in L:
                    c = g(txt_file, L[i], second)
                else:                 
                    c = g(txt_file, L[i], L[i+1])
                #print("{}: {}: {}".format(i, L[i], c)) 
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
                    name = "cs_{}_horizontal".format(L[i])
                    assert c[0] == 'HORIZ'
                    code_list = c[1]
                    for j in range(0, len(code_list)):
                        value = code_list[j][0]
                        cat = code_list[j][1]
                        #print("{}\t{}\t{}\t{}".format(name, value, cat, j+1))
                        out_code.write('%s;%4d;%s;%4d\n' %(name, int(value), cat, j+1))
                    name = "cs_{}_vertical".format(L[i])
                    assert c[2] == 'VERTICAL'
                    code_list = c[3]
                    for j in range(0, len(code_list)):
                        value = code_list[j][0]
                        cat = code_list[j][1]
                        #print("{}\t{}\t{}\t{}".format(name, value, cat, j+1))
                        out_code.write('%s;%4d;%s;%4d\n' %(name, int(value), cat, j+1))
                elif len(c) == 0:
                    pass
                else:
                    print(c)
                    raise ValueError("unexpected return")
      
def main():
    base_dir = '../LSYPE1/wave8-xml/pdf'
    wave8_pdf = os.path.join(base_dir, 'wave8.pdf')
    out_file = os.path.join(base_dir, 'wave8_all_pages.txt')
    key_file = os.path.join(base_dir, 'wave8_all_keys.txt')
    #order_question = os.path.join(base_dir, 'wave8_order_question.csv')
    order_question = "bar.csv"
    

    db_input_dir = '../LSYPE1/wave8-xml/db_temp_input'
    order_sequences = os.path.join(db_input_dir, 'wave8_sequences.csv')
    order_condition = os.path.join(db_input_dir, 'wave8_condition.csv')
    order_loop = os.path.join(db_input_dir, 'wave8_order_loop.csv')

    # pdf to text
    #pdf_to_text(wave8_pdf, out_file, key_file)

    # produce sequence input file
    get_sequence(key_file, order_sequences)

    # produce condition file
    get_condition(key_file, order_condition, order_loop, order_question)

    # gather all information for db input

    df_question_item = get_question_item('../LSYPE1/wave8-xml/db_input/QuestionItem.csv', order_question)
    df_question_grid = get_question_grid('../LSYPE1/wave8-xml/db_input/QuestionGrid.csv', order_question)
    df_question_item.to_csv(os.path.join(db_input_dir, 'wave8_question_item.csv'), sep=';', index=False)
    df_question_grid.to_csv(os.path.join(db_input_dir, 'wave8_question_grid.csv'), sep='@', index=False)
  
    # df_codelist = get_codes('../LSYPE1/wave8-xml/db_input/CodeList.csv', '../LSYPE1/wave8-xml/db_input/QuestionItem.csv',  '../LSYPE1/wave8-xml/db_input/QuestionGrid.csv')
    # df_codelist.to_csv(os.path.join(db_input_dir, 'wave8_codes.csv'), index=False)   

    #get_code_list(os.path.join(base_dir, 'wave8_all_pages.txt'), 'temp.txt')
    generate_code_list(os.path.join(base_dir, 'wave8_all_pages.txt'),
                       os.path.join(base_dir, 'wave8_order_question.csv'),
                       os.path.join(db_input_dir, 'wave8_codes.csv'))

if __name__ == "__main__":
    main()
