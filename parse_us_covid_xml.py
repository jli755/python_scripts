#!/bin/env python
# -*- coding: utf-8 -*-

"""  
    Python 3
    Parse us covid19 xml file
"""

import re
import os
import pandas as pd
import xml.etree.ElementTree as ET
from collections import OrderedDict

# xml namespace
ns = {'r': 'ddi:reusable:3_3',
      'ddi': 'ddi:instance:3_3',
      'studyunit': 'ddi:studyunit:3_3',
      'datacollection': 'ddi:datacollection:3_3',
      'logicalproduct': 'ddi:logicalproduct:3_3'}


def pretty_print(xml):
    from bs4 import BeautifulSoup
    print(BeautifulSoup(ET.tostring(xml), "xml").prettify()) 


def int_to_roman(num):
    """
        Convert integer to roman numeral.
    """

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


def parse_study(root):
    """
    input: root of ET xml
    output: study 
    """
    columns = ['Agency', 'Title', 'Study_Name', 'Study_Label', 'Instrument']
    df_study = pd.DataFrame(columns=columns)

    StudyUnit = root.find('./ddi:Fragment/studyunit:StudyUnit', ns)
    Agency = StudyUnit.find('r:Agency', ns).text
    ID = StudyUnit.find('r:ID', ns).text
    Title = StudyUnit.find('r:Citation/r:Title/r:String', ns).text
    ref_ID = StudyUnit.find('r:DataCollectionReference/r:ID', ns).text

    DataCollection = root.find('./ddi:Fragment/datacollection:DataCollection', ns)
    data_ID = DataCollection.find('r:ID', ns).text

    if ref_ID == data_ID:
        ModuleName = DataCollection.find('datacollection:DataCollectionModuleName/r:String', ns).text
        ModuleLabel = DataCollection.find('r:Label/r:Content', ns).text

        Modules = DataCollection.find('r:UserAttributePair/r:AttributeValue', ns).text
        for Module in Modules.replace('[', '').replace(']', '').replace('"', '').split(','):
            study_row = [Agency, Title, ModuleName, ModuleLabel, Module.replace('urn:ddi:uk.iser:', '')[:-2]]
            df_study.loc[len(df_study)] = study_row

    else:
        print("Why more than one data collection?")

    return df_study


def parse_Instrument(root):
    """
    input: root of ET xml
    output: instrument element info
    """
    columns = ['Instrument_ID', 'Instrument_Label', 'ref', 'ref_ID']
    df_instrument = pd.DataFrame(columns=columns)

    instruments = root.findall('./ddi:Fragment/datacollection:Instrument', ns)   
    for instrument in instruments:
        ID = instrument.find('r:ID', ns).text
        Label = instrument.find('r:Label/r:Content', ns).text
        ref = instrument.find('datacollection:ControlConstructReference/r:TypeOfObject', ns).text
        ref_ID = instrument.find('datacollection:ControlConstructReference/r:ID', ns).text
   
        df_instrument.loc[len(df_instrument)] = [ID, Label, ref, ref_ID]
        
    return df_instrument
        

def parse_StatementItem(root):
    """ 
    input: root of ET xml
    output: dataframe of statement
    """

    columns = ['Statement_ID', 'Statement_Name', 'Statement_Label', 'Literal']
    df_StatementItem = pd.DataFrame(columns=columns)

    StatementItems = root.findall('./ddi:Fragment/datacollection:StatementItem', ns)
    for StatementItem in StatementItems:
        ID = StatementItem.find('r:ID', ns).text
        Name = StatementItem.find('datacollection:ConstructName/r:String', ns).text
        Label = StatementItem.find('r:Label/r:Content', ns).text
        Literal = StatementItem.find('datacollection:DisplayText/datacollection:LiteralText/datacollection:Text', ns).text
            
        statement_row = [ID, 's_q' + Name, Label, Literal]
        df_StatementItem.loc[len(df_StatementItem)] = statement_row

    return df_StatementItem


def parse_category(root):
    """ 
    input: root of ET xml
    output: dicrionary of category, 
            - key: ID
            - value: Label
    """
    category_dict = dict()
    categories = root.findall('./ddi:Fragment/logicalproduct:Category', ns)
    for category in categories:
        ID = category.find('r:ID', ns).text
        Label = category.find('r:Label/r:Content', ns).text
        category_dict[ID] = Label

    return category_dict


def parse_codelist(root):
    """ 
    input: root of ET xml
    output: dataframe of codelist
    """

    category_dict = parse_category(root)

    columns = ['ID', 'Name', 'Code_Value', 'Value', 'Category']
    codelist_df = pd.DataFrame(columns=columns)

    codelists = root.findall('./ddi:Fragment/logicalproduct:CodeList', ns)
    for codelist in codelists:
        ID = codelist.find('r:ID', ns).text
        CodeListName = codelist.find('logicalproduct:CodeListName/r:String', ns).text
        Label = codelist.find('r:Label/r:Content', ns).text

        codes = codelist.findall('logicalproduct:Code', ns)
        for code in codes:
            code_value = code.find('r:Value', ns).text
            # remove those not in pdf
            if code_value[0] != '-':
                category_ID = code.find('r:CategoryReference/r:ID', ns).text
                category_Label = category_dict[category_ID]

                row = [ID, CodeListName, Label, code_value, category_Label]
                codelist_df.loc[len(codelist_df)] = row

    return codelist_df


def parse_response(root):
    """ 
    input: root of ET xml
    output: 
        - dataframe of response of Text/Numeric/DateTime
        - list of repeated labels
    """

    columns = ['Label', 'Type', 'Type2', 'Format', 'Min', 'Max']
    response_df = pd.DataFrame(columns=columns)

    # Text Domain
    TextDomains = root.findall('.//datacollection:TextDomain', ns) 
    for TextDomain in TextDomains:
        # label
        if TextDomain.find('r:Label', ns) == None:
            Label = 'Generic text'
        else:
            Label = TextDomain.find('r:Label/r:Content', ns).text

        if 'minLength' in TextDomain.attrib.keys():
            minLength = TextDomain.attrib['minLength']
        else:
            minLength = None

        if 'maxLength' in TextDomain.attrib.keys():
            maxLength = TextDomain.attrib['maxLength']
        else:
            maxLength = None

        if Label == 'Generic text' and minLength == None and maxLength == None:
            Label = 'Long text'

        text_row = [Label, 'Text', None, None, minLength, maxLength]
        response_df.loc[len(response_df)] = text_row

    # Numeric Domain
    NumericDomains = root.findall('.//datacollection:NumericDomain', ns) 

    for NumericDomain in NumericDomains:
        
        if NumericDomain.find('r:Label', ns) == None:
            Label = 'Generic number'
        else:
            Label = NumericDomain.find('r:Label/r:Content', ns).text

        if NumericDomain.find('r:NumericTypeCode', ns) == None:
            NumericType = None
        else:
            NumericType = NumericDomain.find('r:NumericTypeCode', ns).text

        if NumericDomain.find('r:NumberRange/r:Low', ns) == None:
            low_value = None
        else:
            low_value = NumericDomain.find('r:NumberRange/r:Low', ns).text

        if NumericDomain.find('r:NumberRange/r:High', ns) == None:
            high_value = None
        else:
            high_value = NumericDomain.find('r:NumberRange/r:High', ns).text

        if Label == 'Generic number' and high_value == None:
            Label = 'Long number'

        numeric_row = [Label, 'Numeric', NumericType, None, low_value, high_value]
        response_df.loc[len(response_df)] = numeric_row

    # DateTime Domain
    DateTimeDomains = root.findall('.//datacollection:DateTimeDomain', ns) 
    for DateTimeDomain in DateTimeDomains:

        Label = 'Generic date'
        
        if DateTimeDomain.find('r:Label', ns) == None:
            Format = None
        else:
            Format = DateTimeDomain.find('r:Label/r:Content', ns).text

        if DateTimeDomain.find('r:DateTypeCode', ns) == None:
            DateType = None
        else:
            DateType = DateTimeDomain.find('r:DateTypeCode', ns).text

        date_row = [Label, 'Date', DateType, Format, None, None]

        response_df.loc[len(response_df)] = date_row

    # find duplicated Label
    df = response_df.drop_duplicates(keep='first')
    df = df.reset_index(drop=True)
    df['dup_number'] = df.groupby(['Label']).cumcount()

    df_sub = df.loc[(df.dup_number >0) , ['Label']]
    repeated_label = df_sub['Label'].unique().tolist()

    df['Label'] = df.apply(lambda row: row['Label'] + ' ' + str(row['dup_number']) if row['dup_number'] > 0 else row['Label'], axis=1)
    df.drop('dup_number', axis=1, inplace=True)

    return df, repeated_label


def parse_QuestionConstruct(root):
    """ 
    input: root of ET xml
    output: QuestionConstruct df
    """
    qc_columns = ['QC_ID', 'QC_Name', 'QuestionReference_type', 'QuestionReference_id']
    df_qc = pd.DataFrame(columns=qc_columns)

    QuestionConstructs = root.findall('./ddi:Fragment/datacollection:QuestionConstruct', ns)
    for QuestionConstruct in QuestionConstructs:
        ID = QuestionConstruct.find('r:ID', ns).text
        Name = QuestionConstruct.find('datacollection:ConstructName/r:String', ns).text
        QuestionReference_type = QuestionConstruct.find('r:QuestionReference/r:TypeOfObject', ns).text
        QuestionReference_id = QuestionConstruct.find('r:QuestionReference/r:ID', ns).text

        df_qc.loc[len(df_qc)] = [ID, Name, QuestionReference_type, QuestionReference_id]

    return df_qc


def parse_QuestionItem(root):
    """ 
    input: root of ET xml
    output: dataframe of QuestionItem
    """

    #TODO: if question has no literal, is this a real question?

    df_r, dup_label_list = parse_response(root)
    codelist_df = parse_codelist(root)

    columns = ['QI_ID', 'Label', 'Literal', 'Instructions', 'Response', 'min_responses', 'max_responses']
    qi_df = pd.DataFrame(columns=columns)

    QuestionItems = root.findall('.//datacollection:QuestionItem', ns) 
    for QuestionItem in QuestionItems:
        ID = QuestionItem.find('r:ID', ns).text
        Name = QuestionItem.find('datacollection:QuestionItemName/r:String', ns).text
        
        if QuestionItem.find('datacollection:QuestionText', ns) == None: 
            Literal = None
        else:
            Literal = QuestionItem.find('datacollection:QuestionText/datacollection:LiteralText/datacollection:Text', ns).text

        # TODO: 1st instruction only?
        Instructions = None
        for k in QuestionItem.findall('r:UserAttributePair', ns):
            if k.find('r:UserAttributeKey', ns) != None and k.find('r:UserAttributeKey', ns).text == 'extension:QuestionInstruction':
                Instructions = k.find('r:UserAttributeValue', ns).text

        ResponseCardinality = QuestionItem.find('r:ResponseCardinality', ns)
        minimumResponses = ResponseCardinality.attrib['minimumResponses']
        maximumResponses = ResponseCardinality.attrib['maximumResponses']

        # response
        TextDomain = QuestionItem.find('.//datacollection:TextDomain', ns) 
        NumericDomain = QuestionItem.find('.//datacollection:NumericDomain', ns) 
        DateTimeDomain = QuestionItem.find('.//datacollection:DateTimeDomain', ns) 
        CodeDomain = QuestionItem.find('.//datacollection:CodeDomain', ns)

        if TextDomain != None:
            if TextDomain.find('r:Label', ns) == None:
                Label = 'Generic text'
            else:
                Label = TextDomain.find('r:Label/r:Content', ns).text

            if 'minLength' in TextDomain.attrib.keys():
                minLength = TextDomain.attrib['minLength']
            else:
                minLength = None

            if 'maxLength' in TextDomain.attrib.keys():
                maxLength = TextDomain.attrib['maxLength']
            else:
                maxLength = None

            if Label == 'Generic text' and minLength == None and maxLength == None:
                Label = 'Long text'

            # which dup label to use
            if Label in dup_label_list:
                if 'minLength' in TextDomain.attrib.keys():
                    minLength = TextDomain.attrib['minLength']
                else:
                    minLength = None

                if 'maxLength' in TextDomain.attrib.keys():
                    maxLength = TextDomain.attrib['maxLength']
                else:
                    maxLength = None

                if minLength == None and maxLength == None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Min.isna()) & (df_r.Max.isna()) ,:]
                elif minLength != None and maxLength == None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Min == minLength) & (df_r.Max.isna()) ,:]
                elif minLength == None and maxLength != None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Min.isna()) & (df_r.Max == maxLength) ,:]
                else:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Min == minLength) & (df_r.Max == maxLength) ,:]

                Response = df_sub['Label'].values[0]
            else:
                Response = Label

        elif NumericDomain != None:
            if NumericDomain.find('r:Label', ns) == None:
                Label = 'Generic number'
            else:
                Label = NumericDomain.find('r:Label/r:Content', ns).text

            if NumericDomain.find('r:NumberRange/r:High', ns) == None:
                high_value = None
            else:
                high_value = NumericDomain.find('r:NumberRange/r:High', ns).text

            if Label == 'Generic number' and high_value == None:
                Label = 'Long number'

            # find correct label
            if Label in dup_label_list:
                if NumericDomain.find('r:NumericTypeCode', ns) == None:
                    NumericType = None
                else:
                    NumericType = NumericDomain.find('r:NumericTypeCode', ns).text

                if NumericDomain.find('r:NumberRange/r:Low', ns) == None:
                    low_value = None
                else:
                    low_value = NumericDomain.find('r:NumberRange/r:Low', ns).text

                if NumericDomain.find('r:NumberRange/r:High', ns) == None:
                    high_value = None
                else:
                    high_value = NumericDomain.find('r:NumberRange/r:High', ns).text

                if NumericType == None and low_value == None and high_value == None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2.isna()) & (df_r.Min.isna()) & (df_r.Max.isna()) ,:]
                elif NumericType == None and low_value == None and high_value != None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2.isna()) & (df_r.Min.isna()) & (df_r.Max == high_value) ,:]
                elif NumericType == None and low_value != None and high_value == None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2.isna()) & (df_r.Min == low_value) & (df_r.Max.isna()) ,:]
                elif NumericType != None and low_value == None and high_value == None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2 == NumericType) & (df_r.Min.isna()) & (df_r.Max.isna()) ,:]
                elif NumericType == None and low_value != None and high_value != None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2.isna()) & (df_r.Min == low_value) & (df_r.Max == high_value) ,:]
                elif NumericType != None and low_value != None and high_value == None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2 == NumericType) & (df_r.Min == low_value) & (df_r.Max.isna()) ,:]
                elif NumericType != None and low_value == None and high_value != None:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2 == NumericType) & (df_r.Min.isna()) & (df_r.Max == high_value) ,:]
                else:
                    df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2 == NumericType) & (df_r.Min == low_value) & (df_r.Max == high_value) ,:]

                Response = df_sub['Label'].values[0]
            else:
                Response = Label


        elif DateTimeDomain != None:
            # select the correct label from response table
            Label = 'Generic date'
            Response = Label

            if DateTimeDomain.find('r:Label', ns) == None:
                Format = None
            else:
                Format = DateTimeDomain.find('r:Label/r:Content', ns).text

            if DateTimeDomain.find('r:DateTypeCode', ns) == None:
                DateType = None
            else:
                DateType = DateTimeDomain.find('r:DateTypeCode', ns).text

            if Format == None and DateType == None:
                df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.TypCodeDomaine2.isna()) &(df_r.Format.isna()) ,:]
            elif Format != None and DateType == None:
                df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2.isna()) &(df_r.Format == Format) ,:]
            elif Format == None and DateType != None:
                df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2 == DateType) &(df_r.Format.isna()) ,:]
            else:
                df_sub = df_r.loc[(df_r.Label.str.startswith(Label)) & (df_r.Type2 == DateType) &(df_r.Format == Format) ,:]

            Response = df_sub['Label'].values[0]

        elif CodeDomain != None:
            CodeID = CodeDomain.find('r:CodeListReference/r:ID', ns).text
            Response = 'cs_' + codelist_df.loc[(codelist_df.ID == CodeID)]['Name'].unique().tolist()[0]
            if CodeDomain.find('r:Label/r:Content', ns) != None:
                CodeLabel = CodeDomain.find('r:Label/r:Content', ns).text
                if Literal == None:
                    Literal = CodeLabel
        else:
            Response = 'Temp'
 
        qi_row = [ID, 'qi_' + Name, Literal, Instructions, Response, minimumResponses, maximumResponses ]
        qi_df.loc[len(qi_df)] = qi_row
    return qi_df


def parse_QuestionGrid(root):
    """ 
    input: root of ET xml
    output: there is only one questiongrid in this study, will conver it to question item
    """
    
    columns = ['QI_ID', 'Label', 'Literal', 'Instructions', 'Response', 'min_responses', 'max_responses']

    qg_df = pd.DataFrame(columns=columns)

    l_id = []
    l_name = []
    qg_dict = dict()
    QuestionGrids = root.findall('.//datacollection:QuestionGrid', ns) 
    for QuestionGrid in QuestionGrids:
        ID = QuestionGrid.find('r:ID', ns).text
        Name = QuestionGrid.find('datacollection:QuestionGridName/r:String', ns).text
        
        if QuestionGrid.find('datacollection:QuestionText', ns) == None: 
            Literal = None
        else:
            Literal = QuestionGrid.find('datacollection:QuestionText/datacollection:LiteralText/datacollection:Text', ns).text

        # Numeric Domain
        NumericDomains = QuestionGrid.findall('.//datacollection:NumericDomain', ns)
        k = 1
        for NumericDomain in NumericDomains:
            if NumericDomain.find('r:Label', ns) == None:
                Label = 'Generic number'
            else:
                Label = NumericDomain.find('r:Label/r:Content', ns).text

            new_id = ID + '_' + str(k)
            new_name = Name + Label.split(' ')[0]
            qg_row = [new_id, 'qi_' + new_name, Literal, None, Label, 1, 1 ]
            qg_df.loc[len(qg_df)] = qg_row
            l_id.append(new_id)
            l_name.append(new_name)
            k = k + 1
    qg_dict[ID] = ','.join(l_id)
    qg_dict[Name] = ','.join(l_name)

    return qg_df, qg_dict


def parse_IfThenElse(root):
    """ 
    input: root of ET xml
    output: dataframe of Conditions
    """
    columns = ['IF_ID', 'IF_Name', 'Literal', 'IfCondition', 'Then_ID', 'Then_type']
    df_IfThenElse = pd.DataFrame(columns=columns)

    IfThenElses = root.findall('.//datacollection:IfThenElse', ns) 
    for IfThenElse in IfThenElses:
        ID = IfThenElse.find('r:ID', ns).text
        Name = IfThenElse.find('datacollection:ConstructName/r:String', ns).text
        Name = Name.lower().replace('condition', '')
        Label = IfThenElse.find('r:Label/r:Content', ns).text
        IfCondition = IfThenElse.find('datacollection:IfCondition/r:Command/r:CommandContent', ns).text
        if 'ff_' in IfCondition:
            IfCondition = None
        else:
            IfCondition = IfCondition.replace('=', " == ").replace('<>', ' != ').replace(' | ', ' || ').replace(' OR ', ' || ').replace(' or ', ' || ').replace(' & ', ' && ').replace(' AND ', ' && ').replace(' and ', ' && ').replace('IF', '')
            IfCondition = IfCondition.strip()
            Logic_parts = re.findall('(\w+)\s*==\s*|(\w+)\s*>\s*|(\w+)\s*<\s*|(\w+)\s*!=\s*', IfCondition)
            Logic_variables = list(set(j for i in Logic_parts for j in i if j!=''))

            # replace with qc_
            for item in Logic_variables: 
                if item in IfCondition: 
                    IfCondition = IfCondition.replace(item, 'qc_' + item)

        for reference in IfThenElse.findall('datacollection:ThenConstructReference', ns):
            Then_ID = reference.find('r:ID', ns).text
            Then_type = reference.find('r:TypeOfObject', ns).text

            if_row = [ID, 'c_q' + Name, Label, IfCondition, Then_ID, Then_type]
            df_IfThenElse.loc[len(df_IfThenElse)] = if_row

    # if name is not unique
    if not df_IfThenElse['IF_Name'].is_unique:

        df_IfThenElse['tmp'] = df_IfThenElse.groupby('IF_Name').cumcount() + 1
        df_IfThenElse['tmp_count'] = df_IfThenElse.groupby('IF_Name')['IF_Name'].transform('count')

        df_IfThenElse['new_label_num'] = df_IfThenElse.apply(lambda row: row['IF_Name'] if row['tmp_count'] == 1 else row['IF_Name'] + '_' + str(row['tmp']), axis=1)
        df_IfThenElse['new_label_roman'] = df_IfThenElse.apply(lambda row: '_'.join([row['new_label_num'].rsplit('_',1)[0], int_to_roman(int( row['new_label_num'].rsplit('_',1)[1]))]) if row['tmp_count'] > 1 else row['new_label_num'], axis=1)

        df_IfThenElse['IF_Label'] = df_IfThenElse['new_label_roman']
    else:
        df_IfThenElse['IF_Label'] = df_IfThenElse['IF_Name']

    return df_IfThenElse
 

def parse_Loop(root):
    """ 
    input: root of ET xml
    output: dataframe of Loop
    """
    columns = ['Loop_ID', 'Loop_Name', 'Literal', 'LoopWhile', 'ref_ID', 'ref_type']
    df_Loop = pd.DataFrame(columns=columns)

    Loops = root.findall('.//datacollection:Loop', ns) 
    for Loop in Loops:
        ID = Loop.find('r:ID', ns).text

        Label = Loop.find('r:Label/r:Content', ns).text
        LoopWhile = Loop.find('datacollection:LoopWhile/r:Command/r:CommandContent', ns).text

        # label should be associated with the variable.
        # in case of missing variable, using the first question name
        # this should be modified after find out the first question
        if Loop.find('datacollection:ConstructName', ns) == None:
            Name = LoopWhile.replace('.', '').split(' ')[-1]
        else:
            Name = Loop.find('datacollection:ConstructName/r:String', ns).text

        Name = 'l_q' + Name.lower().replace('loop', '').replace(' ', '')

        for reference in Loop.findall('datacollection:ControlConstructReference', ns):
            ref_ID = reference.find('r:ID', ns).text
            ref_type = reference.find('r:TypeOfObject', ns).text

            loop_row = [ID, Name, Label, LoopWhile, ref_ID, ref_type]
            df_Loop.loc[len(df_Loop)] = loop_row

    # if name is not unique
    if not df_Loop['Loop_Name'].is_unique:

        df_Loop['tmp'] = df_Loop.groupby('Loop_Name').cumcount() + 1
        df_Loop['tmp_count'] = df_Loop.groupby('Loop_Name')['Loop_Name'].transform('count')

        df_Loop['new_label_num'] = df_Loop.apply(lambda row: row['Loop_Name'] if row['tmp_count'] == 1 else row['Loop_Name'] + '_' + str(row['tmp']), axis=1)
        df_Loop['new_label_roman'] = df_Loop.apply(lambda row: '_'.join([row['new_label_num'].rsplit('_',1)[0], int_to_roman(int( row['new_label_num'].rsplit('_',1)[1]))]) if row['tmp_count'] > 1 else row['new_label_num'], axis=1)

        df_Loop['Loop_Label'] = df_Loop['new_label_roman']
    else:
        df_Loop['Loop_Label'] = df_Loop['Loop_Name']

    return df_Loop


def parse_Sequence(root):
    """
    input: root of ET xml
    output: sequence element 
    """

    df_QC = parse_QuestionConstruct(root)
    df_statement = parse_StatementItem(root)
    df_if = parse_IfThenElse(root)
    df_loop = parse_Loop(root)

    columns = ['ID', 'Label', 'CCRef_ID', 'CCRef_type']
    df_seq = pd.DataFrame(columns=columns)

    sequences = root.findall('./ddi:Fragment/datacollection:Sequence', ns)   
    for sequence in sequences:
        ID = sequence.find('r:ID', ns).text
        Label = sequence.find('r:Label/r:Content', ns).text
        for ref in sequence.findall('datacollection:ControlConstructReference', ns):
            ref_ID = ref.find('r:ID', ns).text
            ref_type = ref.find('r:TypeOfObject', ns).text

            seq_row = [ID, Label, ref_ID, ref_type]
            df_seq.loc[len(df_seq)] = seq_row
            
    df_seq_qc = df_seq.merge(df_QC, left_on='CCRef_ID', right_on='QC_ID', how='left')

    # modify sequence table question grid to question item
    df_QG, qg_dict = parse_QuestionGrid(root)

    df_seq_qc['QC_Name_new'] = df_seq_qc['QC_Name'].apply(lambda x: qg_dict[x] if x in qg_dict.keys() else x)
    df_seq_qc['QuestionReference_id_new'] = df_seq_qc['QuestionReference_id'].apply(lambda x: qg_dict[x] if x in qg_dict.keys() else x)
    df_seq_qc = df_seq_qc.drop(['QC_Name', 'QuestionReference_id'], 1)
    df_seq_qc.rename(columns={'QC_Name_new': 'QC_Name', 'QuestionReference_id_new': 'QuestionReference_id'}, inplace=True)
    # split rows
    df_seq_qc = df_seq_qc.set_index(['ID', 'Label', 'CCRef_ID', 'CCRef_type', 'QC_ID', 'QuestionReference_type']).apply(lambda x: x.str.split(',').explode()).reset_index()

    return df_seq_qc



def get_sequence_table(root):
    """
    input: parsed 'instrument' and 'sequence'
    output: sequence table 
    """

    df_Study = parse_study(root)
    df_Instrument = parse_Instrument(root)
    df = df_Study.merge(df_Instrument, left_on = 'Instrument', right_on = 'Instrument_ID', how='left')

    df_sub = df.loc[:, ['Instrument_Label', 'Study_Label']]
    # add a row about top level study section
    df_sub.loc[-1] = [df_sub['Study_Label'].unique()[0], None]
    # shifting index
    df_sub.index = df_sub.index + 1
    df_sub.sort_index(inplace=True) 
    
    df_sub['Position'] = df_sub.groupby('Study_Label').cumcount() + 1
    df_sub['Parent_Type'] = 'CcSequence'
    df_sub['Branch'] = 1
    df_sub.rename(columns={'Study_Label': 'Parent_Name', 'Instrument_Label': 'Label'}, inplace=True)

    cols = ['Label', 'Parent_Type', 'Parent_Name', 'Branch', 'Position']
    df_sub = df_sub[cols]

    df_s = df_Study.loc[:, ['Agency', 'Title', 'Study_Name', 'Study_Label']].drop_duplicates()

    return df_s, df_sub


def get_codelist_table(root):
    """
    input: parsed 'codelist'
    output: codelist table 
    """

    df_codelist = parse_codelist(root)
    df = df_codelist.loc[:, ['Name', 'Value', 'Category']]
    
    df['Code_Order'] = df.groupby('Name').cumcount() + 1
    df['Name'] = 'cs_' + df['Name']
    df.rename(columns={'Name': 'Label', 'Value': 'Code_Value'}, inplace=True)

    columns = ['Label', 'Code_Order', 'Code_Value', 'Category']
    df = df[columns]

    return df


def get_position(root):
    """
    find parent relationship and position
    """

    df_Sequence = parse_Sequence(root)
    df_IfThenElse = parse_IfThenElse(root)
    df_Loop = parse_Loop(root)
    df_instrument = parse_Instrument(root) 

    # position from parsed loops
    df_loop_seq = df_Loop.merge(df_Sequence, left_on='ref_ID', right_on='ID', how='left')
    df_loop_seq['Position'] = df_loop_seq.groupby(['Loop_ID']).cumcount() + 1
    df_loop_seq['new_ID'] = df_loop_seq.apply(lambda row: row['CCRef_ID'] if pd.isnull(row['QuestionReference_id']) else row['QuestionReference_id'], axis=1)
    df_loop_seq['Parent_Type'] = 'CcLoop'
    df_loop_pos = df_loop_seq.loc[:, ['new_ID', 'Parent_Type', 'Loop_ID', 'Loop_Name', 'Position']]
    df_loop_pos.rename(columns={'Loop_ID': 'Parent_ID', 'Loop_Name': 'Parent_Name'}, inplace=True)

    # position from parsed conditions
    df_if_seq = df_IfThenElse.merge(df_Sequence, left_on='Then_ID', right_on='ID', how='left')
    df_if_seq['Position'] = df_if_seq.groupby(['IF_ID']).cumcount() + 1
    df_if_seq['new_ID'] = df_if_seq.apply(lambda row: row['CCRef_ID'] if pd.isnull(row['QuestionReference_id']) else row['QuestionReference_id'], axis=1)
    df_if_seq['Parent_Type'] = 'CcCondition'
    df_if_pos = df_if_seq.loc[:, ['new_ID', 'Parent_Type', 'IF_ID', 'IF_Label', 'Position']]
    df_if_pos.rename(columns={'IF_ID': 'Parent_ID', 'IF_Label': 'Parent_Name'}, inplace=True)

    # position from parsed instrument
    df_inst_seq = df_instrument.merge(df_Sequence, left_on='ref_ID', right_on='ID', how='left')
    df_inst_seq['Position'] = df_inst_seq.groupby(['Instrument_ID']).cumcount() + 1
    df_inst_seq['new_ID'] = df_inst_seq.apply(lambda row: row['CCRef_ID'] if pd.isnull(row['QuestionReference_id']) else row['QuestionReference_id'], axis=1)
    df_inst_seq['Parent_Type'] = 'CcSequence'
    df_inst_pos = df_inst_seq.loc[:, ['new_ID', 'Parent_Type', 'Instrument_ID', 'Instrument_Label', 'Position']]
    df_inst_pos.rename(columns={'Instrument_ID': 'Parent_ID', 'Instrument_Label': 'Parent_Name'}, inplace=True)

    df = pd.concat([df_loop_pos, df_if_pos, df_inst_pos])
    df['Branch'] = df['Parent_Type'].apply(lambda x: 0 if x == 'CcCondition' else 1)

    return df
   

def get_ordered_tables(root):
    df_pos = get_position(root)

    statement_columns = ['Label', 'Literal', 'Parent_Type', 'Parent_Name', 'Branch', 'Position']
    df_StatementItem = parse_StatementItem(root)
    df_statement = df_StatementItem.merge(df_pos, left_on = 'Statement_ID', right_on='new_ID', how='left')
    df_statement.rename(columns={'Statement_Name': 'Label'}, inplace=True)
    df_statement = df_statement[statement_columns]

    if_columns = ['Label', 'Literal', 'Logic', 'Parent_Type', 'Parent_Name', 'Branch', 'Position']
    df_IfThenElse = parse_IfThenElse(root)
    df_if = df_IfThenElse.merge(df_pos, left_on = 'IF_ID', right_on='new_ID', how='left')
    df_if.rename(columns={'IF_Label': 'Label', 'IfCondition': 'Logic'}, inplace=True)
    df_if = df_if[if_columns]

    loop_columns = ['Label', 'Loop_While', 'Start_value', 'End_Value', 'Variable', 'Parent_Type', 'Parent_Name', 'Branch', 'Position']
    df_Loop_p = parse_Loop(root)
    df_loop = df_Loop_p.merge(df_pos, left_on = 'Loop_ID', right_on='new_ID', how='left')
    df_loop.rename(columns={'Loop_Label': 'Label', 'LoopWhile': 'Loop_While'}, inplace=True)
    df_loop['Start_value'] = None
    df_loop['End_Value'] = None
    df_loop['Variable'] = None
    df_loop = df_loop[loop_columns]

    QI_columns = ['Label', 'Literal', 'Instructions', 'Response', 'Parent_Type', 'Parent_Name', 'Branch', 'Position', 'min_responses', 'max_responses']
    df_QI_p = parse_QuestionItem(root)
    df_QG_p, qg_dict = parse_QuestionGrid(root)
    df_QI_all =pd.concat([df_QI_p, df_QG_p])

    # Removed DERIVED questions
    df_QI_remove = df_QI_all.loc[df_QI_all['Literal'].isnull(), :]
    df_QI_keep = df_QI_all.append(df_QI_remove).drop_duplicates(keep=False)

    # split instrutions with the format *please .. *
    df_QI_keep['Instructions'] = df_QI_keep['Literal'].apply(lambda x: re.findall('\*Please.*?\*', x)[0] if not pd.isnull(x) and len(re.findall('\*Please.*?\*', x)) > 0  else None)
    df_QI_keep['Literal'] = df_QI_keep.apply(lambda row: row['Literal'] if pd.isnull(row['Instructions']) else row['Literal'].replace(row['Instructions'], ''), axis = 1)
    df_QI_keep['Instructions'] = df_QI_keep['Instructions'].str.replace('*', '')

    df_QI = df_QI_keep.merge(df_pos, left_on = 'QI_ID', right_on='new_ID', how='left')
    df_QI = df_QI[QI_columns]

    return df_statement, df_if, df_loop, df_QI

def modify_loop_label(root):
    """
        Loop has no variable, using the first question name for it's label
    """
    df_statement, df_if, df_loop, df_QI = get_ordered_tables(root)
    df_QI_sub = df_QI.loc[(df_QI['Parent_Type'] == 'CcLoop') & (df_QI['Position'] == 1), ['Label', 'Parent_Name']]
    df_QI_sub['new_Parent_Name'] = 'l_' + df_QI['Label'].str.replace('qi', 'qc')
    new_loop_dict = dict(zip(df_QI_sub.Parent_Name, df_QI_sub.new_Parent_Name)) 
    
    df_loop['Label'] = df_loop['Label'].apply(lambda x: new_loop_dict[x] if x in new_loop_dict.keys() else x)
    df_QI['Parent_Name'] = df_QI['Parent_Name'].apply(lambda x: new_loop_dict[x] if x in new_loop_dict.keys() else x)
    
    return df_statement, df_if, df_loop, df_QI


def main():
    main_dir = '../Jenny_ucl/us_covid19_xml/2020_06'
    input_name = 'UKHLSCovidJun20_v01_20200804.xml'
    xmlFile = os.path.join(main_dir, input_name)

    output_dir_name = input_name.split('_')[0]
    output_dir = os.path.join(main_dir, output_dir_name, 'archivist_table')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    tree = ET.parse(xmlFile)
    root = tree.getroot()

    # inspect xml
    section_names = set([i.tag for i in root.findall('./ddi:Fragment/', ns)])
    for section_name in section_names:
        print("****** {} ******".format(section_name))

    get_ordered_tables(root)
    df_study, df_sequence = get_sequence_table(root)
    df_study.to_csv(os.path.join(output_dir, 'study.csv'), index=False, sep=';')
    df_sequence.to_csv(os.path.join(output_dir, 'sequence.csv'), index=False, sep=';')

    df_response, dup_label_list = parse_response(root)
    df_response.to_csv(os.path.join(output_dir, 'response.csv'), index=False, sep=';')

    df_codelist = get_codelist_table(root)
    df_codelist.to_csv(os.path.join(output_dir, 'codelist.csv'), index=False, sep=';')

    df_statement, df_if, df_loop, df_QI = modify_loop_label(root)
    df_statement.to_csv(os.path.join(output_dir, 'statement.csv'), index=False, sep=';')
    df_if.to_csv(os.path.join(output_dir, 'condition.csv'), index=False, sep=';')
    df_loop.to_csv(os.path.join(output_dir, 'loop.csv'), index=False, sep=';')
    df_QI.to_csv(os.path.join(output_dir, 'question_item.csv'), index=False, sep=';')


if __name__ == "__main__":
    main()
