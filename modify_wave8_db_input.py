#!/bin/env python3

"""  
    Python 3
    Parse wave8 pdf file directly
"""

from collections import OrderedDict
import pandas as pd
import numpy as np
import os
import re


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


def modify_condition(old_file, new_file):
    """
    Add Logic
    Modify Label, using first logic question if possible
    """
    df = pd.read_csv(old_file, sep=';')

    df['Logic'] = df['Literal'].apply(lambda x: x[3:])
    df['Logic'] = df['Logic'].str.replace('=', ' == ').str.replace('<>', ' != ').str.replace(' OR ', ' || ').str.replace(' or ', ' || ').str.replace(' AND ', ' && ').str.replace(' and ', ' && ')

    df['Logic_name'] = df['Literal'].apply(lambda x: re.findall(r"(\w+) *(=|>|<)", x)) 
    df['Logic_name1'] = df['Logic_name'].apply(lambda x: '' if len(x) ==0 else x[0][0])

    # rename duplicates logic names
    df['Logic_name_new'] = df.groupby('Logic_name1').Logic_name1.apply(lambda n: n.str.strip() + '_' + (np.arange(len(n))).astype(str))
    df['Logic_name_roman'] = df['Logic_name_new'].apply(lambda x: '_'.join([x.rsplit('_', 1)[0], int_to_roman(int(x.rsplit('_', 1)[1]))]))
    df['Logic_name_roman'] = df['Logic_name_roman'].str.strip('_0')

    df['Logic_new'] = df.apply(lambda row: row['Label'] if row['Logic_name_roman'] == '' else row['Logic_name_roman'], axis = 1)

    df['Logic_new'] = df['Logic_new'].str.replace('&', '_').str.replace('.', '').str.replace('(', '_').str.replace(')', '_').str.replace('<>', '_')

    df['Label_new'] = 'c_q' + df['Logic_new']

    # rename inside 'logic', add qc_
    df['Logic_m'] = df.apply(lambda row: row['Logic'].replace(row['Logic_name1'], 'qc_' + row['Logic_name1']) if (row['Logic_name1'] in row['Logic_new'] and row['Logic_name1'] != '') else row['Logic'], axis = 1)

    # return condition_dict to modify other filesdf_loops['Label'] = df_loops['Label'].str.replace('&', '_')
    condition_dict = dict(zip(df.Label, df.Label_new))

    df['above_label_new'] = df['above_label'].map(condition_dict).fillna(df['above_label'])


    df = df.drop(['Label', 'Logic', 'Logic_name', 'Logic_name1', 'Logic_name_new', 'Logic_name_roman', 'Logic_new', 'above_label'], 1)
    df.rename(columns={'Label_new': 'Label', 'Logic_m': 'Logic', 'above_label_new': 'above_label'}, inplace=True)
    cols = ['Label', 'Literal', 'Logic', 'above_label', 'parent_type', 'Position']
    df = df[cols]

    df.to_csv(new_file, index=False, sep=';')

    return condition_dict

def main():
    old_dir = '../LSYPE1/wave8-xml/db_temp_input'
    new_dir = '../LSYPE1/wave8-xml/db_input_modified'
   
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    # code list lable 
    df_code = pd.read_csv(os.path.join(old_dir, 'wave8_codes.csv'), sep=';')
    # code dict
    df_code['Label_new'] = df_code['Label'].str.replace('&', '_').str.replace('.', '').str.replace(':', '').str.replace(')', '_').str.replace('<>', '_')
    code_dict = dict(zip(df_code.Label, df_code.Label_new))
    df_code = df_code.drop(['Label'], 1)
    df_code.rename(columns={'Label_new': 'Label'}, inplace=True)

    codecols = ['Label', 'Value', 'Category', 'codes_order']
    df_code[codecols].to_csv(os.path.join(new_dir, 'wave8_codes.csv'), index=False, sep=';')
    
    # condition Label
    condition_dict = modify_condition(os.path.join(old_dir, 'wave8_condition.csv'), os.path.join(new_dir, 'wave8_condition_inter.csv'))
    #print(condition_dict)

    # change parent in loop with condition_dict
    df_loop = pd.read_csv(os.path.join(old_dir, 'wave8_order_loop.csv'), sep=';')
    df_loop['above_label_new'] = df_loop['above_label'].map(condition_dict).fillna(df_loop['above_label'])
    df_loop = df_loop.drop(['above_label'], 1)
    df_loop.rename(columns={'above_label_new': 'above_label'}, inplace=True)

    # Loop dict
    df_loop['Label_new'] = df_loop['Label'].str.replace('&', '_').str.replace('.', '').str.replace('(', '_').str.replace(')', '_').str.replace('<>', '_')
    loop_dict = dict(zip(df_loop.Label, df_loop.Label_new))
    df_loop = df_loop.drop(['Label'], 1)
    df_loop.rename(columns={'Label_new': 'Label'}, inplace=True)

    loopcols = ['Label', 'Loop_While', 'above_label', 'parent_type', 'Position']
    df_loop[loopcols].to_csv(os.path.join(new_dir, 'wave8_order_loop.csv'), index=False, sep=';')
    
    # question item
    df_QI = pd.read_csv(os.path.join(old_dir, 'wave8_question_item.csv'), sep=';')
    df_QI['Literal'].fillna('?', inplace=True)
    # QI dict
    df_QI['Label_new'] = 'qi_' + df_QI['Label'].str.replace('&', '_').str.replace('.', '').str.replace('(', '_').str.replace(')', '_').str.replace('<>', '_')
    QI_dict = dict(zip(df_QI.Label, df_QI.Label_new))
    # change Response_domain with code_dict
    df_QI['Response_domain_new'] = df_QI['Response_domain'].map(code_dict).fillna(df_QI['Response_domain'])
    # change parent with condition_dict, loop_dict
    df_QI['above_label_new'] = df_QI['above_label'].map(condition_dict).fillna(df_QI['above_label'])
    df_QI['above_label_new1'] = df_QI['above_label_new'].map(loop_dict).fillna(df_QI['above_label_new'])
    df_QI = df_QI.drop(['above_label', 'Label', 'above_label_new', 'Response_domain'], 1)
    df_QI.rename(columns={'Response_domain_new': 'Response_domain', 'Label_new': 'Label', 'above_label_new1': 'above_label'}, inplace=True)
    QIcols = ['Label', 'Literal', 'Response_domain', 'above_label', 'Position', 'parent_type']

    df_QI[QIcols].to_csv(os.path.join(new_dir, 'wave8_question_item.csv'), index=False, sep=';')
    

    # question grid
    df_QG = pd.read_csv(os.path.join(old_dir, 'wave8_question_grid.csv'), sep='@')
    # QI dict
    df_QG['Label_new'] = 'qg_' + df_QG['Label'].str.replace('&', '_').str.replace('.', '').str.replace('(', '_').str.replace(')', '_').str.replace('<>', '_')
    QG_dict = dict(zip(df_QG.Label, df_QG.Label_new))
    # change horizontal_code_list_name, vertical_code_list_name with code_dict

    df_QG['horizontal_code_list_name_new'] = df_QG['horizontal_code_list_name'].map(code_dict).fillna(df_QG['horizontal_code_list_name'])
    df_QG['vertical_code_list_name_new'] = df_QG['vertical_code_list_name'].map(code_dict).fillna(df_QG['vertical_code_list_name'])
    df_QG = df_QG.drop(['horizontal_code_list_name', 'vertical_code_list_name'], 1)
    df_QG.rename(columns={'horizontal_code_list_name_new': 'horizontal_code_list_name', 'vertical_code_list_name_new': 'vertical_code_list_name'}, inplace=True)

    # change parent with condition_dict
    df_QG['above_label_new'] = df_QG['above_label'].map(condition_dict).fillna(df_QG['above_label'])
    df_QG['above_label_new1'] = df_QG['above_label_new'].map(loop_dict).fillna(df_QG['above_label_new'])
    df_QG = df_QG.drop(['above_label', 'Label', 'above_label_new'], 1)
    df_QG.rename(columns={'Label_new': 'Label', 'above_label_new1': 'above_label'}, inplace=True)
    QGcols = ['Label', 'Literal', 'horizontal_code_list_name', 'vertical_code_list_name', 'above_label', 'Position', 'parent_type']

    df_QG[QGcols].to_csv(os.path.join(new_dir, 'wave8_question_grid.csv'), index=False, sep='@')
    


    # condition file needs to modify parent with loop_dict
    df_condition = pd.read_csv(os.path.join(new_dir, 'wave8_condition_inter.csv'), sep=';')
    df_condition['above_label_new'] = df_condition['above_label'].map(loop_dict).fillna(df_condition['above_label'])
    cols = ['Label', 'Literal', 'Logic', 'above_label', 'parent_type', 'Position']
    df_condition[cols].to_csv(os.path.join(new_dir, 'wave8_condition.csv'), index=False, sep=';')



   
    os.system('cp ../LSYPE1/wave8-xml/db_temp_input/wave8_sequences.csv ../LSYPE1/wave8-xml/db_input_modified/wave8_sequences.csv') 


if __name__ == "__main__":
    main()
