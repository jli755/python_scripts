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

def get_modules(root):
    """ 
    Do a Depth-first search (DFS) from root, finding only modules 
    """
    module_elements = [] 
    for e in root.iter(): 
        if e.tag.lower() == 'module': 
            module_elements.append(e) 

    return module_elements


def get_questions(root):
    """ 
    Do a Depth-first search (DFS) from root, finding only questions 
    """
    questions = []
    for e in root.iter(): 
        if e.tag.lower() == 'question': 
            questions.append(e) 

    return questions


def get_question_response(question_element):
    """ 
        Do a Depth-first search (DFS) from question element, find it's response 
    """

    qi_label = 'qi_' + question_element.find('./context').text
    if not question_element.find('./qt_properties/text') is None:
        literal_node = question_element.find('./qt_properties/text')
        qi_literal = extractText(literal_node)
    else:
        qi_literal = ''

    if not question_element.find('./qt_properties/iiposttext') is None:
        qi_instruction = extractText(question_element.find('./qt_properties/iiposttext'))
    else:
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
        df_response.loc[len(df_response)] = [response_label, 'text', None, None, None]
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
            response_label = 'Numeric: ' + min_v + '-' + max_v 

        else:
            response_label = 'Generic number'
            min_v = None
            max_v = None
        df_response.loc[len(df_response)] = [response_label, 'Numeric', Numeric_Type, min_v, max_v]
    else:
        #print(question_element.attrib['type'])
        response_label = 'TOCHECK'

    df_question_answer.loc[len(df_question_answer)] = [question_label, qi_label, qi_literal, qi_instruction, response_label]

    return df_question_answer, df_response, df_codelist


def get_condition(condition_element):
    """
        Find condition label, logic etc.
    """
    logic = extractText(condition_element.find('./condition'))

    if condition_element.find('./sd_properties/label') is None:
        literal = ''
    else:
        literal = condition_element.find('./sd_properties/label').text

    if any(ext in logic for ext in ['=', '>', '<', '-']):
        k = re.findall(r'(\w+) *(=|>|<|-)', logic)[0][0]
        #print('  new label is "{}"'.format(k))
    else:
        k = logic.split(' ')[0]
    k = 'c_' + k

    count = 0
    kk = k
    while True:
        if dict_if.get(kk, False):
            count += 1
            kk = k + '_' + str(count)
        else:
            break
        k = kk

    logic = logic.replace('&lt;', '<').replace('&gt;', '>')

    condition_names =  ['Label', 'Literal', 'Logic']
    df_condition = pd.DataFrame(columns = condition_names)
    df_condition.loc[len(df_condition)] = [k, literal, logic]

    return df_condition


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


def get_all_response(root):
    """
        Find all response and code list associated with all questions.
    """
    question_list = get_questions(root)

    appended_question_answer = []
    appended_response = []
    appended_codelist = []
   
    for q in question_list:
        df_question_answer, df_response, df_codelist = get_question_response(q)

        appended_question_answer.append(df_question_answer)
        appended_response.append(df_response)
        appended_codelist.append(df_codelist)   

    df_appended_question_answer = pd.concat(appended_question_answer)    
    df_appended_response = pd.concat(appended_response)
    df_appended_codelist = pd.concat(appended_codelist)

    df_appended_response = df_appended_response.drop_duplicates(keep = 'first', inplace=False)

    df_appended_question_answer.to_csv('../understanding_society/wave4/df_question_answer.csv', encoding='utf-8', sep=';', index=False)
    df_appended_response.to_csv('../understanding_society/wave4/df_response.csv', encoding='utf-8', sep=';', index=False)
    df_appended_codelist.to_csv('../understanding_society/wave4/df_codelist.csv', encoding='utf-8', sep=';', index=False)

    return df_appended_question_answer, df_appended_response, df_appended_codelist


def node_level(parent_map, node): 
    return node_level(parent_map, parent_map[node])+1 if node in parent_map else 0      


def get_labels(root):
    """
        Find all labels for module and question 
    """
    col_names =  ['Source', 'Label']
    df = pd.DataFrame(columns = col_names)
    
    module_elements = get_modules(root)
    for m in module_elements:
        module_label = m.findall('./rm_properties/label')[0].text
        df.loc[len(df)] = ['module', module_label]

        question_elements = get_questions(m)
        for q in question_elements:
            question_label = q.findall('./context')[0].text
            df.loc[len(df)] = ['question', question_label]

    return df


def gimme_index(p, c): 
    """
        Find index of c in parent p's children list
    """ 
    for (n,ee) in enumerate(p.getchildren()): 
        if e is ee: 
            return n


def get_useful_parent(e, parmap):
    """
        Only instested in module/question/condition/loop reletionship
    """
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

    dict_if = {}
    df_q = {}
    dict_mod = {}
    dict_loop = {}

    global_pos = 0

    def do_if(e):
        """process and insert an element into the If Table return the key
 
        TODO: uses df_if and parmap as global vars: improve?

        Args:
            An element of a elementree

        Returns:
            The key/label that was generated and used.  The key is extracted
            from the logic of the element.  In some cases it will have some
            'i', 'ii', etc or similar added for uniqueness.
	"""

        logic = extractText(e.find('./condition'))

        if e.find('./sd_properties/label') is None:
            literal = ''
        else:
            literal = e.find('./sd_properties/label').text
 
        if any(ext in logic for ext in ['=', '>', '<', '-']):
            k = re.findall(r'(\w+) *(=|>|<|-)', logic)[0][0]
            #print('  new label is "{}"'.format(k))
        else:
            k = logic.split(' ')[0]
        k = 'c_' + k

        count = 0
        kk = k
        while True:
            if dict_if.get(kk, False):
                count += 1
                kk = k + '_' + int_to_roman(count)
            else:
                break
        k = kk

        # possible refactor of duplicated code
        parent = get_useful_parent(e, parmap)
        parent_key = parent.get('MYKEY')   # returns None if can't find
        # parent_type = parent.tag
        parent_type = 'CcSequence' if parent.tag == 'module' else 'CcCondition' if parent.tag == 'if' else 'CcLoop' if parent.tag == 'loop' else ''

        if parent.tag == 'if' and parent_key is None:
            raise RuntimeError('oh no')

        dict_if[k] = (literal, logic, parent_type, parent_key, None, global_pos)
        return k, dict_if


    def do_loop(e):
        """process and insert an element into the Loop Table return the key
 
        TODO: uses df_if and parmap as global vars: improve?

        Args:
            An element of a elementree

        Returns:
            The key/label that was generated and used.  The key is extracted
            from the logic of the element.  In some cases it will have some
            'i', 'ii', etc or similar added for uniqueness.
	"""

        logic = e.attrib['args']

        if e.find('./sd_properties/label') is None: 
            loop_label = ''
        else:
            loop_label = e.find('./sd_properties/label').text  

        if loop_label != '':
            k = loop_label.split(' ')[0]
        elif any(ext in logic for ext in ['foreach', 'for each', 'until']):
            k = re.findall(r'(foreach|for each|until) (\w+)*', logic.replace('[', '').replace('(', ''))[0][1].replace(':', '')
        else:
            k = 'Loop'

        k = 'l_' + k

        count = 0
        kk = k
        while True:
            if dict_loop.get(kk, False):
                count += 1
                kk = k + '_' + int_to_roman(count)
            else:
                break
        k = kk

        # possible refactor of duplicated code
        parent = get_useful_parent(e, parmap)
        parent_key = parent.get('MYKEY')   # returns None if can't find

        parent_type = 'CcSequence' if parent.tag == 'module' else 'CcCondition' if parent.tag == 'if' else 'CcLoop' if parent.tag == 'loop' else ''

        if parent.tag == 'if' and parent_key is None:
            raise RuntimeError('oh no')

        dict_loop[k] = (k, loop_label, logic, parent_type, parent_key, None, global_pos)
       
        return k, dict_loop

    def do_mod(e):

        label = e.find('./rm_properties/label').text
       
        df_mod = get_sequence(e)

        parent = get_useful_parent(e, parmap)
        parent_key = parent.get('MYKEY')   # returns None if can't find

        parent_type = 'CcSequence' if parent.tag == 'module' else 'CcCondition' if parent.tag == 'if' else 'CcLoop' if parent.tag == 'loop' else ''

        if parent.tag == 'if' and parent_key is None:
            raise RuntimeError('oh no')

        # manual fix
        if e.attrib['name'] not in ('hhgrid_w4', 'gridvariables_w4', 'household_w4', 'indintro_w3', 'proxy_w4' ):
            parent_key = 'Individual Questionnaire'
        else:
            parent_key = 'main04'
        
        df_mod['parent_type'] = 'CcSequence'
        df_mod['parent_name'] = parent_key
        df_mod['branch'] = None
        df_mod['global_pos'] = global_pos

        return label, df_mod

    def do_q(e):
        """insert e into the Question Table and return the key

	TODO: do you need it to return key?
        """

        df_qi, df_response, df_codelist = get_question_response(e)

        parent = get_useful_parent(e, parmap)
        parent_key = parent.get('MYKEY')   # returns None if can't find

        parent_type = 'CcSequence' if parent.tag == 'module' else 'CcCondition' if parent.tag == 'if' else 'CcLoop' if parent.tag == 'loop' else ''

        if parent.tag == 'if' and parent_key is None:
            raise RuntimeError('oh no')
        
        df_qi['parent_type'] = parent_type
        df_qi['parent_name'] = parent_key
        df_qi['branch'] = 1
        df_qi['global_pos'] = global_pos

        return df_qi, df_response, df_codelist

    # concate all elements together
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
            k, dict_if = do_if(e)
            #print(k)
            e.set('MYKEY', k)
            #print(e)
            #input('press enter')
        elif e.tag.lower() == 'loop':
            k, dict_loop = do_loop(e)
            #print(k)
            e.set('MYKEY', k)
            #print(e)
            #input('got a loop, press enter')
        else:
            # raise RuntimeError('not handled yet')
            print('not handled yet: {}'.format(e.tag))

    df_appended_question_answer = pd.concat(appended_question_answer)    
    df_appended_response = pd.concat(appended_response)
    df_appended_codelist = pd.concat(appended_codelist)

    df_appended_response = df_appended_response.drop_duplicates(keep = 'first', inplace=False)

    df_appended_question_answer.drop('Label', axis=1, inplace=True)

    # dict_if to df
    df_condition = pd.DataFrame(dict_if).T.rename_axis('Label').add_prefix('Value').reset_index() 

    df_condition.rename(columns={'Value0': 'Literal', 'Value1': 'Logic', 'Value2': 'parent_type', 'Value3': 'parent_name', 'Value4': 'Branch', 'Value5': 'global_pos'}, inplace=True)

    # dict_loop to df
    df_loop = pd.DataFrame(dict_loop).T.rename_axis('Label').add_prefix('Value').reset_index() 

    df_loop.rename(columns={'Value1': 'LoopWhile', 'Value2': 'Logic', 'Value3': 'parent_type', 'Value4': 'parent_name', 'Value5': 'Branch', 'Value6': 'global_pos'}, inplace=True)
    df_loop.drop('Value0', axis=1, inplace=True)

    # sequence 
    df_appended_sequence = pd.concat(appended_sequence)  
    df_appended_sequence.loc[len(df_appended_sequence)] = ['Individual Questionnaire', 'Individual Questionnaire',  'CcSequence', 'main04', None, 8280]
    df_appended_sequence= df_appended_sequence.sort_values('global_pos')

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
    df_codes_dict = pd.concat(codes_dict, axis=0).reset_index().drop('level_1', 1)
    df_codes_dict.rename(columns={'level_0': 'Label'}, inplace=True)

    df_qi['Response'] = df_qi['Response'].map(label_dict)

    return df_codes_dict, df_qi


def main():
#if True:
    input_dir = '../understanding_society/wave4/'
    xmlFile = os.path.join(input_dir, 'main04.specification.v03.qsrx.xml')

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

    df_codes_dict, df_qi = update_codelist(df_codelist, df_qi)

    df_qi.to_csv(os.path.join(output_dir, 'question_items.csv'), encoding='utf-8', sep=';', index=False)
    df_response.to_csv(os.path.join(output_dir, 'response.csv'), encoding='utf-8', sep=';', index=False)
    df_codes_dict.to_csv(os.path.join(output_dir, 'codes.csv'), encoding='utf-8', sep=';', index=False)
    df_condition.to_csv(os.path.join(output_dir, 'conditions.csv'), encoding='utf-8', sep=';', index=False)
    df_loop.to_csv(os.path.join(output_dir, 'loops.csv'), encoding='utf-8', sep=';', index=False)
    df_sequence.to_csv(os.path.join(output_dir, 'sequences.csv'), encoding='utf-8', sep=';', index=False)


if __name__ == "__main__":
    main()

