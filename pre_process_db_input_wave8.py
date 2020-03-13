#!/bin/env python
# -*- coding: utf-8 -*-

"""  
    Python 3
    pre-process wave8 for database input
"""

import os
import pandas as pd

def get_codes(Category, CategoryScheme):
    """
    input: Category, CategoryScheme
    output: codes

    this is the same as Codelist.csv .. no need anymore
    """
    df_Category = pd.read_csv(Category)
    df_Category.rename(columns = {'ID': 'CategoryReference_ID',
                                  'Label_Content_@xml:lang': 'CategoryLanguage',
                                  'Label_Content_#text': 'Category'}, 
                       inplace = True)

    df_CategoryScheme = pd.read_csv(CategoryScheme)
    df_CategoryScheme.rename(columns = {'CategorySchemeName_String_#text': 'Name'}, 
                       inplace = True)
    
    df_codes = df_CategoryScheme.merge(df_Category, on='CategoryReference_ID', how='left')

    # add order
    df_codes['codes_order'] = df_codes.groupby('ID').cumcount() + 1
    # TOCHECK: value stored in xml at all?
    df_codes['Value'] =  df_codes['codes_order']

    df_codes['Label'] = df_codes['Name'] + '_' + df_codes['ID']

    keep_col = ['ID', 'Value', 'Category', 'codes_order', 'Label']
    return df_codes.loc[:, keep_col]


def get_Codelist(Codelist):
    """
    input: Codelist.csv
    """
    df_Codelist = pd.read_csv(Codelist)

    df_Codelist.rename(columns = {'CodeListName_String_#text': 'CodeListName',
                                  'Code_Value': 'Category',
                                  'ID': 'CodeList_ID',
                                  'Code_CategoryReference_ID': 'Cagegory_ID'}, 
                       inplace = True)

    keep_col = ['CodeList_ID', 'CodeListName', 'Cagegory_ID', 'Category']
    df_keep = df_Codelist.loc[:, keep_col]

    # add order
    df_keep['codes_order'] = df_keep.groupby('CodeList_ID').cumcount() + 1
    # TOCHECK: value stored in xml at all?
    df_keep['Value'] =  df_keep['codes_order']

    df_keep.loc[:, 'CodeList_ID'] = df_keep.loc[:, 'CodeList_ID'].ffill()
    return df_keep


def get_AnswerType(num_answered, 
                   CodeDomainBlank, TextDomainBlank, NumericDomainBlank, DateTimeDomainBlank,
                   MixedCodeDomainBlank, MixedTextDomainBlank, MixedNumericDomainBlank, MixedDateTimeDomainBlank):
    """
        Get the answer type for each question
    """

    if num_answered == 0:
        AnswerType = 'No answer'
    elif num_answered == 1:
        if CodeDomainBlank == False:
            AnswerType = 'CodeList'
        elif TextDomainBlank == False:
            AnswerType = 'Text'
        elif NumericDomainBlank == False:
            AnswerType = 'Numeric'
        elif DateTimeDomainBlank == False:
            AnswerType = 'DateTime'
        else:
            AnswerType = ''
    else:        
        if MixedCodeDomainBlank == False:
            AnswerType = 'CodeList'
        elif MixedTextDomainBlank == False:
            AnswerType = 'Text'
        elif MixedNumericDomainBlank == False:
            AnswerType = 'Numeric'
        elif MixedDateTimeDomainBlank == False:
            AnswerType = 'DateTime'
        else:
            AnswerType = ''

    return AnswerType


def get_AnswerCode(AnswerType, CodeDomainID, MixedCodeDomainID):
    """
        Find code list ID for each question item
    """
    if AnswerType == 'CodeList':
        if not pd.isnull(CodeDomainID):
            AnswerCode = CodeDomainID
        else:
            AnswerCode = MixedCodeDomainID
    else:        
        AnswerCode = ''

    return AnswerCode

def get_AnswerNumeric(AnswerType, NumericTypeCode, NumberRange_Low, NumberRange_High,
                      MixedNumericTypeCode, MixedNumberRange_Low, MixedNumberRange_High):
    """
        Find numerical answers to each question item
    """
    if AnswerType == 'Numeric':
        if not pd.isnull(NumericTypeCode):
            NumericType = NumericTypeCode
        else:
            NumericType = MixedNumericTypeCode


        if not pd.isnull(NumberRange_Low):
            NumericRange_low = NumberRange_Low
        else:
            NumericRange_low = MixedNumberRange_Low


        if not pd.isnull(NumberRange_High):
            NumericRange_high = NumberRange_High
        else:
            NumericRange_high = MixedNumberRange_High
        # NumericType = next(item for item in [NumericTypeCode, MixedNumericTypeCode] if not pd.isnull(item), '')
        # NumericRange_low = next(item for item in [NumberRange_Low, MixedNumberRange_Low] if not pd.isnull(item), None)
        # NumericRange_high = next(item for item in [NumberRange_High, MixedNumberRange_High] if not pd.isnull(item), None)
    else:        
        NumericType = ''
        NumericRange_low = None
        NumericRange_high = None

    return NumericType, NumericRange_low, NumericRange_high


def get_AnswerDate(AnswerType, DateTypeCode, MixedDateTypeCode):
    """
        Find if the answer is a date 
    """
    if AnswerType == 'DateTime':
        if not pd.isnull(DateTypeCode):
            AnswerDate = DateTypeCode
        else:
            AnswerDate = MixedDateTypeCode
    else:        
        AnswerDate = ''

    return AnswerDate


def get_AnswerText(AnswerType, minLength, maxLength, 
                   MixedMinLength, MixedMaxLength):
    """
        Find text answers for each question item
    """
    if AnswerType == 'Text':
        if not pd.isnull(minLength):
            AnswerMin = minLength
        else:
            AnswerMin = MixedMinLength

        if not pd.isnull(maxLength):
            AnswerMax = maxLength
        else:
            AnswerMax = MixedMaxLength
    else:        
        AnswerMin = None
        AnswerMax = None

    return AnswerMin, AnswerMax


def get_QuestionItem(QuestionItem):
    """
    input: QuestionItem.csv
    Every row contains only one answer, so we can find the not null field.

    1. if there is only one answer, then need to check
        - CodeDomain_@blankIsMissingValue
        - TextDomain_@blankIsMissingValue
        - NumericDomain_@blankIsMissingValue
        - DateTimeDomain_@blankIsMissingValue
    2. if there are more than one answerget_AnswerDate then need to check
        - StructuredMixedResponseDomain_ResponseDomainInMixed_***

    """

    df_QuestionItem = pd.read_csv(QuestionItem)
    #print(df_QuestionItem.columns)

    # remove 'Codes'
    df_QuestionItem = df_QuestionItem[df_QuestionItem['QuestionItemName_String_#text'].values != 'Codes']

    # forward fill NA
    df_QuestionItem.loc[:, ['ID', 'ResponseCardinality_@maximumResponses']] = df_QuestionItem.loc[:, ['ID', 'ResponseCardinality_@maximumResponses']].ffill()
    
    # add question number
    df_QuestionItem['QuestionNum'] = df_QuestionItem.groupby('ID', sort=False).ngroup() + 1

    df_QuestionItem['AnswerType'] = df_QuestionItem.apply(lambda row: 
                                    get_AnswerType(row['ResponseCardinality_@maximumResponses'], 
                                                   row['CodeDomain_@blankIsMissingValue'],
                                                   row['TextDomain_@blankIsMissingValue'],
                                                   row['NumericDomain_@blankIsMissingValue'],
                                                   row['DateTimeDomain_@blankIsMissingValue'],
                                                   row['StructuredMixedResponseDomain_ResponseDomainInMixed_CodeDomain_@blankIsMissingValue'],
                                                   row['StructuredMixedResponseDomain_ResponseDomainInMixed_TextDomain_@blankIsMissingValue'],
                                                   row['StructuredMixedResponseDomain_ResponseDomainInMixed_NumericDomain_@blankIsMissingValue'],
                                                   row['StructuredMixedResponseDomain_ResponseDomainInMixed_DateTimeDomain_@blankIsMissingValue']),
                                                   axis=1)

    df_QuestionItem['CodeListID'] = df_QuestionItem.apply(lambda row: 
                                    get_AnswerCode(row['AnswerType'], 
                                                   row['CodeDomain_CodeListReference_ID'],
                                                   row['StructuredMixedResponseDomain_ResponseDomainInMixed_CodeDomain_CodeListReference_ID']),
                                                   axis=1)

    df_QuestionItem[['NumericType', 'NumericRange_low', 'NumericRange_high']] = df_QuestionItem.apply(lambda row: 
                                    get_AnswerNumeric(row['AnswerType'], 
                                                      row['NumericDomain_NumericTypeCode'], 
                                                      row['NumericDomain_NumberRange_Low_#text'], 
                                                      row['NumericDomain_NumberRange_High_#text'],
                                                      row['StructuredMixedResponseDomain_ResponseDomainInMixed_NumericDomain_NumericTypeCode'], 
                                                      row['StructuredMixedResponseDomain_ResponseDomainInMixed_NumericDomain_NumberRange_Low_#text'], 
                                                      row['StructuredMixedResponseDomain_ResponseDomainInMixed_NumericDomain_NumberRange_High_#text']), 
                                                      axis=1, 
                                                      result_type='expand')

    df_QuestionItem['DateTypeCode'] = df_QuestionItem.apply(lambda row: 
                                      get_AnswerDate(row['AnswerType'], 
                                                     row['DateTimeDomain_DateTypeCode'],
                                                     row['StructuredMixedResponseDomain_ResponseDomainInMixed_DateTimeDomain_DateTypeCode']),
                                                     axis=1)

    df_QuestionItem[['Text_minLength', 'Text_maxLength']] = df_QuestionItem.apply(lambda row: 
                                      get_AnswerText(row['AnswerType'], 
                                                     row['TextDomain_@minLength'], 
                                                     row['TextDomain_@maxLength'], 
                                                     row['StructuredMixedResponseDomain_ResponseDomainInMixed_TextDomain_@minLength'],
                                                     row['StructuredMixedResponseDomain_ResponseDomainInMixed_TextDomain_@maxLength']), 
                                                     axis=1, 
                                                     result_type='expand')

    df_QuestionItem.rename(columns = {'ID': 'QuestionItem_ID',
                                      'QuestionItemName_String_#text': 'Name',
                                      'ResponseCardinality_@maximumResponses': 'ResponseCardinality',
                                      'QuestionText_LiteralText_Text': 'Text'}, 
                           inplace = True)

    # print(df_QuestionItem['QuestionText_@audienceLanguage'].unique())
    keep_col = ['QuestionNum', 'QuestionItem_ID', 
                'QuestionText_@audienceLanguage', 'QuestionItemName_String_@xml:lang', 
                'Name', 'Text', 'ResponseCardinality', 'AnswerType',
                'CodeListID',  
                'NumericType', 'NumericRange_low', 'NumericRange_high',
                'DateTypeCode',
                'Text_minLength', 'Text_maxLength']
    df_keep = df_QuestionItem.loc[:, keep_col]

    # keep only en-GB text fields
    df_question_text = df_keep.loc[:, ['QuestionItem_ID', 'QuestionText_@audienceLanguage', 'Text']]
    df_question_text_en = df_question_text[(df_question_text['QuestionText_@audienceLanguage'] == 'en-GB')]

    df_question_answers = df_keep.drop(['QuestionText_@audienceLanguage', 'Text'], axis=1)
    df_question_answers_first = df_question_answers.groupby(['QuestionItem_ID', 'AnswerType'], as_index=False).first()
    df_question_answers_first['AnswerOrder'] = df_question_answers_first.groupby(['QuestionItem_ID']).cumcount() + 1

    df_merge = pd.merge(df_question_text_en, df_question_answers_first,
                        on='QuestionItem_ID', 
                        how='outer')
    # drop language columns
    df_merge.drop(['QuestionText_@audienceLanguage', 'QuestionItemName_String_@xml:lang'], axis=1, inplace=True)

    return df_merge.sort_values('QuestionNum')


def check_codelist(number_answers, c_id, df_codelist):
    """
        Check to see if one of the answers is from codelist, and it contains 'don't know' or 'no answer'
    """

    l = ['dontknow', 'noanswer', 'NaN', 'Dontknowopage']  
    regstr = '|'.join(l)

    if number_answers > 1 and len(c_id) > 0:
        df = df_codelist.loc[(df_codelist.CodeList_ID == c_id), ['CodeList_ID', 'Category']]
        
        if df['Category'].str.contains(regstr).any():
            return 'no'


def clean_QuestionItem(df_QuestionItem, df_codelist):
    """
        Clean the output from get_QuestionItem
    """

    num_cols = ['AnswerType', 'NumericType', 'NumericRange_low', 'NumericRange_high']
    df_numeric = df_QuestionItem.loc[(df_QuestionItem.AnswerType == 'Numeric'), num_cols].drop_duplicates()
    df_numeric['Label'] = df_numeric[num_cols].apply(lambda row: '_'.join(row.values.astype(str)), axis=1)
    df_numeric.rename(columns={'NumericType': 'Type2', 'NumericRange_low': 'Min', 'NumericRange_high': 'Max'}, inplace=True)
    #print(df_numeric.head())
    
    text_cols = ['AnswerType', 'Text_minLength', 'Text_maxLength']
    df_text = df_QuestionItem.loc[(df_QuestionItem.AnswerType == 'Text'), text_cols].drop_duplicates()
    df_text['Label'] = df_text[text_cols].apply(lambda row: '_'.join(row.values.astype(str)), axis=1)
    df_text.rename(columns={'Text_minLength': 'Min', 'Text_maxLength': 'Max'}, inplace=True)
    #print(df_text.head())

    date_cols = ['AnswerType', 'DateTypeCode']
    df_date = df_QuestionItem.loc[(df_QuestionItem.AnswerType == 'DateTime'), date_cols].drop_duplicates()
    df_date['Label'] = df_date[date_cols].apply(lambda row: '_'.join(row.values.astype(str)), axis=1)
    df_date.rename(columns={'DateTypeCode': 'Type2'}, inplace=True)
    #print(df_date.head())


    df_response = pd.concat([df_numeric, df_text, df_date], sort=False)[['Label', 'AnswerType', 'Type2', 'Min', 'Max']]
    # 1.0 become 1
    df_response['Label'] = df_response['Label'].str.replace('\.0','')

    
    df_QuestionItem['Label'] = df_QuestionItem.apply(lambda row: '_'.join(row[num_cols].values.astype(str)) if row['AnswerType'] == 'Numeric'
                                                            else '_'.join(row[text_cols].values.astype(str)) if row['AnswerType'] == 'Text'
                                                            else '_'.join(row[date_cols].values.astype(str)) if row['AnswerType'] == 'DateTime'
                                                            else '', axis=1)
    df_QuestionItem['Label'] = df_QuestionItem['Label'].str.replace('\.0','')
    # drop values only keep label
    df_QuestionItem.drop(list(set(num_cols + text_cols + date_cols)) , axis=1, inplace=True)


    # If num_answers > 1 and one of them is code list of don't know or not answer, then we can ignore this
    df_QuestionItem['check_codelist'] = df_QuestionItem.apply(lambda row: check_codelist(row['ResponseCardinality'], row['CodeListID'], df_codelist), axis=1)
    df_QuestionItem_removed = df_QuestionItem.loc[(df_QuestionItem.check_codelist != 'no'), :]
        
    # update the number of answers and answer order
    df_QuestionItem_removed['answer_order'] = df_QuestionItem_removed.groupby('QuestionItem_ID').cumcount()+1
    df_QuestionItem_removed['num_answers'] = df_QuestionItem_removed.groupby('QuestionItem_ID')['QuestionItem_ID'].transform('count')

    df_QuestionItem_removed = df_QuestionItem_removed.drop(['ResponseCardinality', 'AnswerOrder', 'check_codelist'], axis=1)

    # remove \t from Text column
    df_QuestionItem_removed['Text'] = df_QuestionItem_removed['Text'].str.replace('\t', ' ')
    # output sections
    mask = (df_QuestionItem_removed['Text'].str.contains('Section')==True)

    df_section = df_QuestionItem_removed[mask]
    df_QI = df_QuestionItem_removed[~mask]

    # interger
    df_response['Min'] = df_response['Min'].apply(lambda x: int(x) if x == x else '')
    df_response['Max'] = df_response['Max'].apply(lambda x: int(x) if x == x else '')
    return df_response, df_QI, df_section


def get_Order(sequence_order, QuestionConstruct, df_QI, IfThenElse):
   
    df_Sequence = pd.read_csv(sequence_order)
    df_QuestionConstruct = pd.read_csv(QuestionConstruct)
    df_IfThenElse = pd.read_csv(IfThenElse)


    df_QC = pd.merge(df_Sequence, df_QuestionConstruct, left_on='ControlConstructReference_ID', right_on = 'ID', how='left')

    df_QI = pd.merge(df_QC, df_QI[['QuestionItem_ID', 'Text']], left_on='QuestionReference_ID', right_on = 'QuestionItem_ID', how='left')
    #df_keep = df_QC.loc[:, ['Label_Content_#text', 'ControlConstructReference_TypeOfObject', 'ConstructName_String_#text', 'QuestionReference_ID', 'QuestionReference_TypeOfObject']]

    
    df_If = pd.merge(df_QI, df_IfThenElse, left_on='ControlConstructReference_ID', right_on = 'ID', how='left')


    return df_If


def get_question_grid(questiongrid_input):
    """
        input xml question grid file
        output question grid name and answer
    """
    df_input = pd.read_csv(questiongrid_input)
    keep_col = ['QuestionGridName_String_#text', 'QuestionText_LiteralText_Text', 'GridDimension_CodeDomain_CodeListReference_ID', 'CodeDomain_CodeListReference_ID']
    df = df_input.loc[df_input['QuestionGridName_String_#text'].notnull(), keep_col]

    df.rename(columns = {'QuestionGridName_String_#text': 'Label',
                         'QuestionText_LiteralText_Text': 'Literal',
                         'GridDimension_CodeDomain_CodeListReference_ID': 'vertical_code_list_id',
                         'CodeDomain_CodeListReference_ID': 'horizontal_code_list_id'}, 
              inplace = True)

    df_keep = df.loc[df['vertical_code_list_id'].notnull(), :]
    df_keep['horizontal_code_list_name'] = 'cs_' + df_keep['Label'] + '_horizontal'
    df_keep['vertical_code_list_name'] = 'cs_' + df_keep['Label'] + '_vertical'
    return df_keep


def get_category_scheme(category_scheme_file):
    df_input = pd.read_csv(category_scheme_file)
    return df_input


def main():
    xml_output_dir = '../LSYPE1/wave8-xml/xml_output/'
    onlyfiles = [f for f in os.listdir(xml_output_dir) if os.path.isfile(os.path.join(xml_output_dir, f))]
    print(onlyfiles)

    db_input_dir = '../LSYPE1/wave8-xml/db_input/'

    # find CodeList
    df_codelist = get_Codelist(os.path.join(xml_output_dir, 'CodeList.csv'))
    df_codelist.to_csv(os.path.join(db_input_dir, 'CodeList.csv'), index = False)
 
    ### these 2 ways are the same ...

    # find QuestionItem
    df_QuestionItem = get_QuestionItem(os.path.join(xml_output_dir, 'QuestionItem.csv'))
    df_QuestionItem.to_csv(os.path.join(db_input_dir, 'QuestionItem1.csv'), index = False)

    df_n, df_q, df_s = clean_QuestionItem(df_QuestionItem, df_codelist)
    df_n.to_csv(os.path.join(db_input_dir, 'Response.csv'), index = False)
    df_q.to_csv(os.path.join(db_input_dir, 'QuestionItem.csv'), index = False)
    df_s.to_csv(os.path.join(db_input_dir, 'Section.csv'), index = False)




    # find order
    #df_order = get_Order(os.path.join(xml_output_dir, 'Sequence.csv'), os.path.join(xml_output_dir, 'QuestionConstruct.csv'), df_q,
    #                     os.path.join(xml_output_dir, 'IfThenElse.csv') )
    #df_order.to_csv(os.path.join(db_input_dir, 'Orders.csv'), index = False)


    # find QuestionGrid
    df_QuestionGrid = get_question_grid(os.path.join(xml_output_dir, 'QuestionGrid.csv'))
    df_QuestionGrid.to_csv(os.path.join(db_input_dir, 'QuestionGrid.csv'), index = False)


    df_category_scheme = get_category_scheme(os.path.join(xml_output_dir, 'CategoryScheme.csv'))
    df_category_scheme.to_csv(os.path.join(db_input_dir, 'CategoryScheme.csv'), index = False)

if __name__ == "__main__":
    main()
