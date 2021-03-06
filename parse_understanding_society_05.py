#!/bin/env python
# -*- coding: utf-8 -*-

"""
    Python 3
    Parse understanding society xml
"""

from collections import OrderedDict
import xml.etree.ElementTree as ET
import pandas as pd
import re
import os


def int_to_roman(num):
    """Convert integer to roman numeral."""

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


def extractText(node):
    """Extract text from all <something> of an elementree node."""
    chunks = []
    for sub in node.iter():
        add_brackets = False
        if sub.tag == 'format' and sub.attrib['code'] == 'TF':
            add_brackets = True 
        if sub.text is not None:
            if add_brackets:
                chunks.append('[')
            chunks.append(sub.text)
            if add_brackets:
                chunks.append(']')
        if sub.tail is not None:
            chunks.append(sub.tail)

    return "".join(chunks)


def get_question_response(question_element):
    """ 
        from question element, find it's response 
    """

    qi_label = 'qi_' + question_element.find('./context').text
    if not question_element.find('./qt_properties/text') is None:
        literal_node = question_element.find('./qt_properties/text')
        qi_literal = extractText(literal_node)
    else:
        qi_literal = ''

    if not question_element.find('./qt_properties/iiposttext') is None:
        qi_instruction = extractText(question_element.find('./qt_properties/iiposttext'))
    elif not question_element.find('./qt_properties/iipretext') is None:
        qi_instruction = extractText(question_element.find('./qt_properties/iipretext'))
    else:
        qi_instruction = ''

    # shift instruction to literal
    if qi_literal == '' and qi_instruction != '':
        qi_literal = qi_instruction
        qi_instruction = ''

    qi_names =  ['QuestionLabel', 'Label', 'Literal', 'Instructions', 'Response']
    df_question_answer = pd.DataFrame(columns = qi_names)

    codelist_names =  ['Label', 'Order', 'Value', 'Category']
    df_codelist = pd.DataFrame(columns = codelist_names)

    response_names =  ['Label', 'Type', 'Numeric_Type/Datetime_type', 'Min', 'Max']
    df_response = pd.DataFrame(columns = response_names)
  
    question_label = question_element.attrib['name'] 
    question_label = 'qi_' + question_label.replace('.', '_')

    # from this quesion, find it's code list
    if question_element.attrib['type'] in ('choice', 'multichoice'):
        response_label = 'cs_' + question_label.replace('qi_', '')
        response_label = response_label.replace('.', '_')

        for index, item in enumerate( question_element.findall('./qt_properties/options/option') ):
           df_codelist.loc[len(df_codelist)] = [response_label, index+1, item.attrib['value'], item.find('./label').text]  

    # datetime response
    elif question_element.attrib['type'] in ('date', 'time'): 
        response_label = 'DATETYPE'
        df_response.loc[len(df_response)] = [response_label, 'Datetime', 'Date', None, None]
    # text response
    elif question_element.attrib['type'] in ('text', 'string'): 
        response_label = 'Generic text'
        df_response.loc[len(df_response)] = [response_label, 'Text', None, None, None]
    # numeric response
    elif question_element.attrib['type'] == 'number':
        decim = question_element.find('./qt_properties/decimals').text
        if decim == '0':
            Numeric_Type = 'Integer'
        else:
            Numeric_Type = 'Float'

        if not question_element.find('./qt_properties/range') is None: 
            e = question_element.find('./qt_properties/range')

            if 'min' in e.attrib.keys():
                min_v = e.attrib['min']
            else:
                min_v = None
            if 'max' in e.attrib.keys():
                max_v = e.attrib['max']
            else:
                max_v = None
            response_label = 'Range: ' + min_v + '-' + max_v 

        else:
            response_label = 'How many'
            min_v = None
            max_v = None
        df_response.loc[len(df_response)] = [response_label, 'Numeric', Numeric_Type, min_v, max_v]
    else:
        #print(question_element.attrib['type'])
        response_label = 'TOCHECK'

    df_question_answer.loc[len(df_question_answer)] = [question_label, qi_label, qi_literal, qi_instruction, response_label]

    return df_question_answer, df_response, df_codelist


def get_sequence(sequence_element):
    """
        Find sequence label
    """
    ModuleName = sequence_element.attrib['name']
    label = sequence_element.find('./rm_properties/label').text

    sequence_names =  ['ModuleName', 'Label']
    df_sequence = pd.DataFrame(columns = sequence_names)
    df_sequence.loc[len(df_sequence)] = [ModuleName, label]
    return df_sequence


def node_level(parent_map, node): 
    return node_level(parent_map, parent_map[node])+1 if node in parent_map else 0      


def gimme_index(p, c): 
    """
        Find index of c in parent p's children list
    """ 
    for (n,ee) in enumerate(p.getchildren()): 
        if e is ee: 
            return n


def _get_useful_parent(e, parmap):
    """Only interested in module/question/condition/loop relationship."""
    tag_list = ['qsrx', 'module', 'if', 'loop', 'question']
 
    # print("/" + "="*78 + "\\")
    # print("doing a search for useful parent")
    # print("self: {}".format(e))
    p = parmap[e]
    # print("immediate parent: {}".format(p))
    c = 0
    while p.tag not in tag_list:

        p = parmap[p]
        c += 1

        if p is None:
            break
    # print("\\" + "="*78 + "/")
    return p


def get_useful_parent_info(e, parmap):
    """Get the meaningful parent and some other info about it."""

    parent = _get_useful_parent(e, parmap)
    # TODO: change MYKEY to meaningful
    parent_key = parent.get('MYKEY')   # returns None if can't find
    # parent_type = parent.tag
    parent_type = 'CcSequence' if parent.tag == 'module' else 'CcCondition' if parent.tag == 'if' else 'CcLoop' if parent.tag == 'loop' else ''
    if parent.tag == 'if' and parent_key is None:
        raise RuntimeError('oh no')
    branch = 0 if parent_type == 'CcCondition' else 1
    return parent, parent_type, parent_key, branch


def TreeToTables(root, parmap):
    """ 
    Do a Depth-first search (DFS) from root.

    Visit the nodes of the tree in DFS order.  Certain type of elements
    are inserted into tables (the return values below).  The elements
    need some processing to locate meaningful parents.

    Args:
        root (xmltree): big tree.
        parmap (dict): a mapping from element to their direct parent.

    Returns:
        df_qi (df): question items table
        df_response (df): etc
        df_codelist (df):
        df_condition (df):
        df_sequence (df):
        df_loop (df):

    tODO: check this todo ;)
    TODO: parmap created in here. instead?
    """

    # a global variable we will update as we traverse the tree
    global_pos = 0

    def do_if(e):
        """process a "if" element, extracting data needed for a row in the If Table.
 
        TODO: uses parmap as global vars: improve?

        Args:
            An element of a elementree

        Returns:
            k (str): the key/label that was generated from the logic of
                the element. May not be unique.
            row (tuple): a row of data for the table.
	"""
        logic = extractText(e.find('./condition'))

        if e.find('./sd_properties/label') is None:
            literal = ''
        else:
            literal = e.find('./sd_properties/label').text
 
        if any(ext in logic for ext in ['=', '>', '<']):
            l = re.findall(r'(\w*\.*\w+) *(=|>|<)', logic)
            if l != []:
                k_all = [item[0] for item in l]
                k = l[0][0]
            else:
                all_capital_words = [word for word in logic.split(' ') if word[0].isupper() ]
                if all_capital_words == []:
                    k = logic.split(' ')[0]
                else:
                    k = all_capital_words[0]
                k_all = [k]
        else:
            all_capital_words = [word for word in logic.split(' ') if word[0].isupper() ]
            if all_capital_words == []:
                k = logic.split(' ')[0]
            else:
                k = all_capital_words[0]   

            k_all = [k]

        k = 'c_q' + k
  
        # add qc_ to the question namesiipretext
        for st in set(k_all):
            if st in logic:
                logic = logic.replace(st, 'qc_' + st)

        logic = logic.replace('=', " == ").replace('<>', ' != ').replace(' | ', ' || ').replace(' OR ', ' || ').replace(' or ', ' || ').replace(' & ', ' && ').replace(' AND ', ' && ').replace(' and ', ' && ')

        parent, parent_type, parent_key, branch = get_useful_parent_info(e, parmap)
        return k, (literal, logic, k_all, parent_type, parent_key, branch, global_pos)


    def do_loop(e):
        """process a loop element, extracting data needed for a row in the Loop Table.
 
        Args:
            An element of a elementree

        Returns:
            k (str): the key/label that was generated from the loop_while
                of the element. May not be unique.
            row (tuple): a row of data for the table.
	"""
        loop_while = e.attrib['args']
        if e.find('./sd_properties/label') is None: 
            loop_label = ''
        else:
            loop_label = e.find('./sd_properties/label').text  

        if loop_label != '':
            k = loop_label.split(' ')[0]
        elif any(ext in loop_while for ext in ['foreach', 'for each', 'until']):
            k = re.findall(r'(foreach|for each|until) (\w+)*', loop_while.replace('[', '').replace('(', ''))[0][1].replace(':', '')
        else:
            k = 'Loop'
        label = 'l_' + k
        parent, parent_type, parent_key, branch = get_useful_parent_info(e, parmap)
        return label, (k, loop_while, parent_type, parent_key, branch, global_pos)

    def do_mod(e):
        """
        Returns a new single-line table with the module in it.
        """
        label = e.find('./rm_properties/label').text
        df_mod = get_sequence(e)
        parent, parent_type, parent_key, branch = get_useful_parent_info(e, parmap)
        
        df_mod['parent_type'] = 'CcSequence'
        df_mod['parent_name'] = parent_key
        df_mod['branch'] = branch
        df_mod['global_pos'] = global_pos

        return label, df_mod

    def do_q(e):
        """insert e into the Question Table and return the key."""
        df_qi, df_response, df_codelist = get_question_response(e)

        parent, parent_type, parent_key, branch = get_useful_parent_info(e, parmap)
        
        df_qi['parent_type'] = parent_type
        df_qi['parent_name'] = parent_key
        df_qi['branch'] = branch
        df_qi['global_pos'] = global_pos

        return df_qi, df_response, df_codelist

    def make_unique_key(k, d):
        """Appends enough roman numerals until key is unique in dict."""
        count = 0
        kk = k
        while True:
            if d.get(kk, False):
                count += 1
                kk = k + '_' + int_to_roman(count)
            else:
                break
        return kk

    # concate all elements together
    # TODO: better to just create the df here
    #dict_df = pandas.new_table_with_columns('KEY_TODO', 'LoopWhile', 'Logic', 'parent_type', 'parent_name', 'Branch', 'global_pos')
    dict_if = {}
    dict_loop = {}
    appended_question_answer = []
    appended_response = []
    appended_codelist = []
    appended_sequence = []

    for e in root.iter():
        global_pos += 1
        if e.tag.lower() == 'question':
            if e.find('./method') is None:
                df_question_answer, df_response, df_codelist = do_q(e)
            elif e.find('./method').attrib['name'] == 'computeiforask':
                df_question_answer, df_response, df_codelist = do_q(e)
            else:
                df_question_answer = pd.DataFrame()
                df_response = pd.DataFrame()
                df_codelist = pd.DataFrame()

            appended_question_answer.append(df_question_answer)
            appended_response.append(df_response)
            appended_codelist.append(df_codelist)

        elif e.tag.lower() == 'module':
            k, df_sequence = do_mod(e)
            appended_sequence.append(df_sequence)
            e.set('MYKEY', k)
        elif e.tag.lower() == 'if':
            k, row = do_if(e)
            k = make_unique_key(k, dict_if)
            dict_if[k] = row
            #print(k)
            e.set('MYKEY', k)
            #print(e)
            #input('press enter')
        elif e.tag.lower() == 'loop':
            k, row = do_loop(e)
            k = make_unique_key(k, dict_loop)
            dict_loop[k] = row
            #print(k)
            e.set('MYKEY', k)
            #print(e)
            #input('got a loop, press enter')
        else:
            # raise RuntimeError('not handled yet')
            #print('not handled yet: {}'.format(e.tag))
            pass

    df_appended_question_answer = pd.concat(appended_question_answer)    
    df_appended_response = pd.concat(appended_response)
    df_appended_codelist = pd.concat(appended_codelist)

    df_appended_response = df_appended_response.drop_duplicates(keep = 'first', inplace=False)

    # question long/short names
#    print(df_appended_question_answer.head(1).transpose())
#    dict_qi_names = dict(zip(df_appended_question_answer['QuestionLabel'].str.replace('qi_', ''), df_appended_question_answer['Label'].str.replace('qi_', '')))
#    print(len(dict_qi_names))
#    print(dict_qi_names.values())
    df_qi_name_pos = df_appended_question_answer.loc[:, ['QuestionLabel', 'Label', 'global_pos']]
    df_qi_name_pos['QuestionLabel'] = df_qi_name_pos['QuestionLabel'].str.replace('qi_', '')
    df_qi_name_pos['Label'] = df_qi_name_pos['Label'].str.replace('qi_', '')

    df_appended_question_answer.drop('Label', axis=1, inplace=True)

    # dict_if to df
    df_condition = pd.DataFrame(dict_if).T.rename_axis('Label').add_prefix('Value').reset_index() 
    df_condition.rename(columns={'Value0': 'Literal', 'Value1': 'Logic', 'Value2': 'Logic_q_names', 'Value3': 'parent_type', 'Value4': 'parent_name', 'Value5': 'Branch', 'Value6': 'global_pos'}, inplace=True)

    # modify condition table logic field: if the question is not in the parsed questions, then delete that part in logic
    # tmp = df_condition[['Label', 'Logic', 'Logic_q_names']]
    df_condition['exist_q'] = df_condition['Logic_q_names'].apply(lambda x: [i in df_qi_name_pos['Label'].tolist() for i in x])
    df_condition['Logic_parts'] = df_condition['Logic'].apply(lambda x: re.findall('\w*\.*\w+[ ]{1,}==[ ]{1,}\w*\|*\w*\|*\w*\|*\w*\|*\w*\|*\w*\|*|\w*\.*\w+[ ]{1,}>[ ]{1,}\w*\|*\w*\|*\w*\|*\w*\|*\w*\|*\w*\|*|\w*\.*\w+[ ]{1,}<[ ]{1,}\w*\|*\w*\|*\w*\|*\w*\|*\w*\|*\w*\|*|\w*\.*\w+[ ]{1,}!=[ ]{1,}\w*\|*\w*\|*\w*\|*\w*\|*\w*\|*\w*\|*',x))
    df_condition['Logic_new'] = df_condition.apply(lambda row: [row['Logic_parts'][i] for i, e in enumerate(row['exist_q']) if e == False and row['Logic_parts'] != []] if False in row['exist_q'] else row['Logic'], axis=1)

    def replace_multiple_str(s, l):
        """Replace item if a list with empty string"""
        for item in l:
            s = s.replace(item, '')
        return s

    # rename logic text: Condition logic referring to a question should match it exactly so qc_PERGRID == 0 should be qc_hhgrid_w4_pergrid == 0
    def replace_logic_text(s, l, logic_pos, df_qi_name_pos):
        """Find the closest full question name to replace the question label"""
        for item in l:
            df = df_qi_name_pos.loc[(df_qi_name_pos.Label == item), :] 
            if not df.empty:
                df['diff_pos'] = logic_pos - df['global_pos']
                new_label = df[df['diff_pos'] == df['diff_pos'].min()]['QuestionLabel'].values[0]

                s = s.replace(item, new_label)
            else:
                s = s
        return s

    df_condition['Logic_re'] = df_condition.apply(lambda row: replace_logic_text(row['Logic'], row['Logic_q_names'], row['global_pos'], df_qi_name_pos), axis=1)

    df_condition['Logic_new_n'] = df_condition.apply(lambda row: '' if not True in row['exist_q'] else replace_logic_text(row['Logic_re'], row['Logic_q_names'], row['global_pos'], df_qi_name_pos) if all(x==True for x in row['exist_q']) else replace_multiple_str(row['Logic_re'], row['Logic_new']), axis=1)

    df_condition['Logic_clean'] = df_condition['Logic_new_n'].apply(lambda x: re.sub('^ \$\$ |^ \|\| ', '', x))

    # rename label: Conditions are labelled after the last part of the question e.g. c_qhhgrid_w4_pergrid should be c_qpergrid_i and c_qPERGRID should be c_qpergrid_ii.

    df_condition.drop(['Logic', 'Logic_q_names', 'exist_q', 'Logic_parts', 'Logic_new', 'Logic_new_n'], axis=1, inplace=True)
    df_condition.rename(columns={'Logic_clean': 'Logic'}, inplace=True)
    df_condition = df_condition[['Label', 'Literal', 'Logic', 'parent_type', 'parent_name', 'Branch', 'global_pos']]

    #df_condition.to_csv('TMP.csv', sep=';', index=False)

    # dict_loop to df
    df_loop = pd.DataFrame(dict_loop).T.rename_axis('Label').add_prefix('Value').reset_index() 
    # print(df_loop.head())
    df_loop.rename(columns={'Value0': 'Loop_Var', 'Value1': 'Loop_While', 'Value2': 'parent_type', 'Value3': 'parent_name', 'Value4': 'Branch', 'Value5': 'global_pos'}, inplace=True)

    # sequence 
    df_appended_sequence = pd.concat(appended_sequence)  
    df_appended_sequence= df_appended_sequence.sort_values('global_pos')

    # reset index
    df_appended_question_answer.reset_index(drop=True, inplace=True)
    df_appended_response.reset_index(drop=True, inplace=True)
    df_appended_codelist.reset_index(drop=True, inplace=True)
    df_condition.reset_index(drop=True, inplace=True)
    df_appended_sequence.reset_index(drop=True, inplace=True)
    df_loop.reset_index(drop=True, inplace=True)

    return (df_appended_question_answer, df_appended_response, df_appended_codelist, df_condition, df_appended_sequence, df_loop)


def find_in_SeqTable(elem):
    name = elem.find('./context').text
    return name
    

def find_in_IfTable(elem):
    name = elem.find('./context').text
    return name
        

def update_position(df_qi, df_condition, df_loop, df_sequence):
    """
        Update the position from global position
    """
    df_qi_sub = df_qi.loc[:, ["QuestionLabel", "parent_type", "parent_name", "global_pos"]]
    df_qi_sub.rename(columns={"QuestionLabel": "Label"})
    df_condition_sub = df_condition.loc[:, ["Label", "parent_type", "parent_name", "global_pos"]]
    df_loop_sub = df_loop.loc[:, ["Label", "parent_type", "parent_name", "global_pos"]]
    df_sequence_sub = df_sequence.loc[:, ["Label", "parent_type", "parent_name", "global_pos"]]

    # concat
    pdList = [df_qi_sub, df_condition_sub, df_loop_sub, df_sequence_sub] 
    df_pos = pd.concat(pdList)

    # sort by global position
    df_pos = df_pos.sort_values("global_pos")

    df_pos["Position"] = df_pos.groupby(["parent_type", "parent_name"]).cumcount() + 1
    # update position
    df_qi['Position'] = df_qi['global_pos'].map(df_pos.set_index('global_pos')['Position'])
    df_condition['Position'] = df_condition['global_pos'].map(df_pos.set_index('global_pos')['Position'])
    df_loop['Position'] = df_loop['global_pos'].map(df_pos.set_index('global_pos')['Position'])
    df_sequence['Position'] = df_sequence['global_pos'].map(df_pos.set_index('global_pos')['Position'])

    df_qi.drop('global_pos', axis=1, inplace=True)
    df_condition.drop('global_pos', axis=1, inplace=True)
    df_loop.drop('global_pos', axis=1, inplace=True)
    df_sequence.drop(['ModuleName', 'global_pos'], axis=1, inplace=True)

    return df_qi, df_condition, df_loop, df_sequence


def get_new_label(df):
    """
        Go though codes table, find re-used codes
    """
    label_dict = {}
    codes_dict = {}

    for old_label in df['Label'].unique():
        # print(old_label)
        df_codes = df.loc[(df.Label == old_label), ['Order', 'Value', 'Category']].reset_index(drop=True)

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
    # print("\n".join("{}\t{}".format(k, v) for k, v in label_dict.items()))
    df_codes_dict = pd.concat(codes_dict, axis=0).reset_index().drop('level_1', 1)
    df_codes_dict.rename(columns={'level_0': 'Label'}, inplace=True)

    df_qi['Response'] = df_qi['Response'].map(label_dict).fillna(df_qi['Response'])

    return df_codes_dict, df_qi


def update_loop_condition_label(df_qi, df_condition, df_loop):
    """
        Label is:
            Loop: l_q + first question name
            Condition: if no logic, c_q + first question name
    """


    # update condition label only if it has no logic text
    def find_first_q(if_label, loop_label, df_condition, df_loop, df_qi):
        #Given condition name, find it's first question name
        question_name = ''

        #i = 1
        while question_name == '':
            #print(i)
            df_condition_sub = df_condition.loc[(df_condition.parent_type == 'CcCondition') & (df_condition.Position == 1) & (df_condition.parent_name == if_label), ['parent_name', 'Label']]
            df_loop_sub = df_loop.loc[(df_loop.parent_type == 'CcCondition') & (df_loop.Position == 1) & (df_loop.parent_name == if_label),  ['parent_name', 'Label']]
            df_qi_sub = df_qi.loc[(df_qi.parent_type == 'CcCondition') & (df_qi.Position == 1) & (df_qi.parent_name == if_label), ['parent_name', 'QuestionLabel']]

            df_condition_sub1 = df_condition.loc[(df_condition.parent_type == 'CcLoop') & (df_condition.Position == 1) & (df_condition.parent_name == loop_label), ['parent_name', 'Label']]
            df_loop_sub1 = df_loop.loc[(df_loop.parent_type == 'CcLoop') & (df_loop.Position == 1) & (df_loop.parent_name == loop_label),  ['parent_name', 'Label']]
            df_qi_sub1 = df_qi.loc[(df_qi.parent_type == 'CcLoop') & (df_qi.Position == 1) & (df_qi.parent_name == loop_label), ['parent_name', 'QuestionLabel']]

            if not df_condition_sub.empty:
                if_label = df_condition_sub['Label'].values[0]
                loop_label = ''
                question_name == ''
                #print('1 condition')
            elif not df_loop_sub.empty:
                loop_label = df_loop_sub['Label'].values[0]
                if_label = ''
                question_name == ''
                #print('1 loop')
            elif not df_qi_sub.empty:
                question_name = df_qi_sub['QuestionLabel'].values[0]
                #print('1 question')
            elif not df_condition_sub1.empty:
                if_label = df_condition_sub1['Label'].values[0]
                loop_label = ''
                question_name == ''
                #print('2 condition')
            elif not df_loop_sub1.empty:
                loop_label = df_loop_sub1['Label'].values[0]
                if_label = ''
                question_name == ''
                #print('2 loop')
            elif not df_qi_sub1.empty:
                question_name = df_qi_sub1['QuestionLabel'].values[0]
                #print('3 question')
            else:
                #print('no first question?')
                # print(if_label)
                question_name = 'unknown'
            #i = i + 1
        return question_name

    df_loop['first_question'] = df_loop.apply(lambda row: find_first_q('', row['Label'], df_condition, df_loop, df_qi) if row['Loop_While'] == '' else '', axis=1)

    df_loop['new_label'] = df_loop.apply(lambda row: row['Label'] if row['first_question'] == 'unknown' else row['Label'] if row['first_question'] == '' else 'l_q' + row['first_question'].split('_')[-1], axis=1)

    dict_loop_label = dict(zip(df_loop['Label'], df_loop['new_label']))
    df_loop.drop(['first_question', 'new_label'], axis=1, inplace=True)
 
    df_loop.to_csv('TMP1.csv', sep=';', index=False)

    # update loop labels
    df_qi['parent_name'] = df_qi['parent_name'].map(dict_loop_label).fillna(df_qi['parent_name'])
    df_condition['parent_name'] = df_condition['parent_name'].map(dict_loop_label).fillna(df_condition['parent_name'])
    df_loop['parent_name'] = df_loop['parent_name'].map(dict_loop_label).fillna(df_loop['parent_name'])
    df_loop['Label'] = df_loop['Label'].map(dict_loop_label).fillna(df_loop['Label'])



    def relabel_if(logic):

        if any(ext in logic for ext in ['==', '!=', '<', '>']):
            l = re.findall(r'(\w*\.*\w+) *(==|!=|>|<)', logic)
            if l != []:
                k_all = [item[0] for item in l]
                k = l[0][0]
            else:
                all_capital_words = [word for word in logic.split(' ') if word[0].isupper() ]
                if all_capital_words == []:
                    k = logic.split(' ')[0]
                else:
                    k = all_capital_words[0]
                k_all = [k]
        else:
            all_capital_words = [word for word in logic.split(' ') if word[0].isupper() ]
            if all_capital_words == []:
                k = logic.split(' ')[0]
            else:
                k = all_capital_words[0]   

            k_all = [k]

        k = 'c_q' + k.replace('.','_').split('_')[-1]
        return k

    df_condition['first_question'] = df_condition.apply(lambda row: find_first_q(row['Label'], '', df_condition, df_loop, df_qi) if row['Logic'] == '' else '', axis=1)

    df_condition['new_label'] = df_condition.apply(lambda row: row['Label'] if row['first_question'] == 'unknown' else relabel_if(row['Logic']) if row['first_question'] == '' else 'c_q' + row['first_question'].split('_')[-1], axis=1)

    df_condition['tmp'] = df_condition.groupby('new_label').cumcount() + 1
    df_condition['tmp_count'] = df_condition.groupby('new_label')['new_label'].transform('count')

    df_condition['new_label_num'] = df_condition.apply(lambda row: row['new_label'] if row['tmp_count'] == 1 else row['new_label'] + '_' + str(row['tmp']), axis=1)
    df_condition['new_label_roman'] = df_condition.apply(lambda row: '_'.join([row['new_label_num'].rsplit('_',1)[0], int_to_roman(int( row['new_label_num'].rsplit('_',1)[1]))]) if row['tmp_count'] > 1 else row['new_label_num'], axis=1)

    dict_if_label = dict(zip(df_condition['Label'], df_condition['new_label_roman']))
    df_condition.drop(['first_question', 'new_label', 'tmp', 'tmp_count', 'new_label_num', 'new_label_roman'], axis=1, inplace=True)
 

    # update condition labels
    df_qi['parent_name'] = df_qi['parent_name'].map(dict_if_label).fillna(df_qi['parent_name'])
    df_condition['parent_name'] = df_condition['parent_name'].map(dict_if_label).fillna(df_condition['parent_name'])
    df_loop['parent_name'] = df_loop['parent_name'].map(dict_if_label).fillna(df_loop['parent_name'])
    df_condition['Label'] = df_condition['Label'].map(dict_if_label).fillna(df_condition['Label'])


    return df_qi, df_condition, df_loop


def manual_fix(df_sequence):
    """Manually modify sequence order"""

    df_sequence.reset_index(drop=True, inplace=True)

    df_line = pd.DataFrame({'Label': 'Individual Questionnaire', 
                         'parent_type': 'CcSequence',
                         'parent_name': 'main05',
                         'branch': 1,
                         'Position': None}, 
                        index=[2.5])

    df = df_sequence.append(df_line, ignore_index=False)
    df = df.sort_index().reset_index(drop=True)

    df['parent_name'] = df['Label'].apply(lambda x: 'Individual Questionnaire' if x not in ('Household Grid module', 'Grid Variables module', 'Household Questionnaire', 'Individual Intro module', 'Proxy Questionnaire', 'Individual Questionnaire') else 'main05')
    df['Position'] = df.groupby(['parent_name']).cumcount() + 1
    return df


def main():
#if True:
    input_dir = '../understanding_society/wave5/'
    xmlFile = os.path.join(input_dir, 'main05.specification.v03.qsrx.xml')

    output_dir = os.path.join(input_dir, "archivist_tables")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    tree = ET.parse(xmlFile)
    root = tree.getroot()
 
    file_name = root.find('./specification').items()[0][-1]

    # create a child-to-parent mapping for a whole tree
    parent_map = {c:p for p in tree.iter() for c in p}

    df_qi, df_response, df_codelist, df_condition, df_sequence, df_loop = TreeToTables(root, parent_map)

    df_qi, df_condition, df_loop, df_sequence = update_position(df_qi, df_condition, df_loop, df_sequence)
    # df_qi.to_csv(os.path.join(output_dir, 'question_items_TMP.csv'), encoding='utf-8', sep=';', index=False)

    # same codelist can be used for multiple questions
    df_codes_dict, df_qi = update_codelist(df_codelist, df_qi)

    # update loop and if labels: use first question name
    df_qi, df_condition, df_loop = update_loop_condition_label(df_qi, df_condition, df_loop)

    # manual fix the sequence layout
    df_sequence = manual_fix(df_sequence)

    # literal cannot be empty 
    df_condition['Literal'] = df_condition['Literal'].apply(lambda x: 'CHECK' if x=='' else x)

    df_qi.to_csv(os.path.join(output_dir, 'question_items.csv'), encoding='utf-8', sep=';', index=False)
    df_response.to_csv(os.path.join(output_dir, 'response.csv'), encoding='utf-8', sep=';', index=False)
    df_codes_dict.to_csv(os.path.join(output_dir, 'codes.csv'), encoding='utf-8', sep=';', index=False)
    df_condition.to_csv(os.path.join(output_dir, 'conditions.csv'), encoding='utf-8', sep=';', index=False)
    df_loop.to_csv(os.path.join(output_dir, 'loops.csv'), encoding='utf-8', sep=';', index=False)
    df_sequence.to_csv(os.path.join(output_dir, 'sequences.csv'), encoding='utf-8', sep=';', index=False)


if __name__ == "__main__":
    main()

