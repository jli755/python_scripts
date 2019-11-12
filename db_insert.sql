-- heroku psql -a closer-archivist-jenny < db_insert.sql;

-- populate database from temp tables;

-- 1. instruments;
INSERT INTO instruments (agency, version, prefix, label, study, created_at, updated_at, slug)
VALUES ('uk.cls.ncds',
        '1.0',
        'ncds_04_cai',
        'NCDS7 CAI Questionnaire (2004)',
        'NCDS',
        current_timestamp,
        current_timestamp,
        'ncds_04_cai');

-- 2. cc_sequences;
INSERT INTO cc_sequences (instrument_id, created_at, updated_at)
(select id,
        current_timestamp,
        current_timestamp
from instruments
where prefix = 'ncds_04_cai');
-- INSERT 0 1
 
SELECT pg_sleep(5);

INSERT INTO cc_sequences (instrument_id, created_at, updated_at, label, parent_id, parent_type, position, branch)
(select b.id,
        current_timestamp,
        current_timestamp,
        b.prefix,
        a.id,
        'CcSequence',
        1,
        0
from cc_sequences a
left join instruments b on b.id = a.instrument_id
where b.prefix = 'ncds_04_cai'
and a.label is null);
-- INSERT 0 1
 
SELECT pg_sleep(5); 

INSERT INTO cc_sequences (instrument_id, created_at, updated_at, label, parent_id, parent_type, position, branch)
(select b.instrument_id,
        current_timestamp,
        current_timestamp,
        a.label,
        b.id,
        'CcSequence',
        a.section_id,
        0
from jenny_sequences a
cross join cc_sequences b
where b.label= 'ncds_04_cai');
-- INSERT 0 21

SELECT pg_sleep(5);

-- 3. response_domain_numerics;
INSERT INTO response_domain_numerics (numeric_type, label, min, max, created_at, updated_at, instrument_id, response_domain_type)
(select a.Type2,
        a.label,
        a.min,
        a.max,
        current_timestamp,
        current_timestamp,
        b.id,
        'ResponseDomainNumeric'
from Jenny_response a
cross join instruments b
where a.type = 'Numeric'
and b.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 4. response_domain_texts;
INSERT INTO response_domain_texts (label, maxlen, created_at, updated_at, instrument_id, response_domain_type)
(select a.label,
        a.max,
        current_timestamp,
        current_timestamp,
        b.id,
        'ResponseDomainText'
from Jenny_response a
cross join instruments b
where a.type = 'Text'
and prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 5.response_domain_datetimes;
INSERT INTO response_domain_datetimes (datetime_type, label, created_at, updated_at, instrument_id, response_domain_type)
(select a.type2,
        a.label,
        current_timestamp,
        current_timestamp,
        b.id,
        'ResponseDomainDatetime'
from Jenny_response a
cross join instruments b
where a.type = 'Datetime'
and b.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 6. code_lists;
INSERT INTO code_lists (label, created_at, updated_at, instrument_id)
(select distinct a.label,
                 current_timestamp,
                 current_timestamp,
                 b.id
from jenny_codes a
cross join instruments b
where b.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 7. response_domain_codes;
INSERT INTO response_domain_codes (code_list_id, created_at, updated_at, response_domain_type, instrument_id, min_responses, max_responses)
(select a.id,
        current_timestamp,
        current_timestamp,
        'ResponseDomainCode',
        b.id,
        1,
        1
from code_lists a
cross join instruments b
where b.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 8. categories;
INSERT INTO categories (label, created_at, updated_at, instrument_id)
(select distinct a.category,
        current_timestamp,
        current_timestamp,
        b.id
from jenny_codes a
cross join instruments b
where b.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 9. codes;
INSERT INTO codes (value, "order", code_list_id, category_id, created_at, updated_at, instrument_id)
(select to_char(a.value,  'FM999999999999999999') as value,
        a.codes_order,
        b.id as code_lists_id,
        c.id as category_id,
        current_timestamp,
        current_timestamp,
        c.instrument_id
from jenny_codes a
left join code_lists b on a.label = b.label and b.instrument_id = (select id from instruments where prefix = 'ncds_04_cai')
left join categories c on a.category = c.label and c.instrument_id = (select id from instruments where prefix = 'ncds_04_cai') );

SELECT pg_sleep(5);

-- 10. cc_conditions;
INSERT INTO cc_conditions (instrument_id, label, literal, logic, parent_id, parent_type, position, branch, created_at, updated_at)
(select b.id,
        a.Label,
        a.Literal,
        a.Logic,
        d.id,
        a.Parent_type,
        a.Position,
        a.branch,
        current_timestamp,
        current_timestamp
from jenny_conditions a
cross join instruments b
left join cc_sequences d on a.above_label = d.label and d.instrument_id = b.id
where b.prefix = 'ncds_04_cai');
 
SELECT pg_sleep(5);

-- 11. cc_loops;
INSERT INTO cc_loops (label, start_val, end_val, loop_while, loop_var, parent_id, parent_type, position, branch, created_at, updated_at, instrument_id)
(select a.label,
        a.start_value,
        a.end_value,
        a.loop_while,
        a.logic,
        d.id,
        a.Parent_type,
        a.Position,
        a.branch,
        current_timestamp,
        current_timestamp,
        b.id
from jenny_loops a
cross join instruments b
left join cc_sequences d on a.above_label = d.label and d.instrument_id = b.id
where b.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 12. instructions;
INSERT INTO instructions (text, created_at, updated_at, instrument_id)
(select distinct a.instructions,
        current_timestamp,
        current_timestamp,
        b.id
from jenny_questions a
cross join instruments b
where b.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 13. question_items;
INSERT INTO question_items (label, literal, instruction_id, created_at, updated_at, instrument_id, question_type)
(select a.label, a.literal,
b.id,
        current_timestamp,
        current_timestamp,
        c.id,
        'QuestionItem'
from jenny_questions a
cross join instruments c
left join instructions b on a.instructions = b.text and b.instrument_id = c.id
where c.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

-- 14. cc_questions;

INSERT INTO response_units (label, created_at, updated_at, instrument_id)
(SELECT 'Cohort/sample member', current_timestamp, current_timestamp, id
FROM instruments
WHERE prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

INSERT INTO cc_questions (instrument_id, question_id, question_type, response_unit_id, created_at, updated_at, label, parent_id, parent_type, position, branch)
(select c.id,
b.id as question_id,
'QuestionItem',
d.id,
current_timestamp,
current_timestamp,
a.label,
f.id,
a.parent_type,
a.position,
a.branch
from jenny_questions a
cross join instruments c
left join question_items b on a.label = b.label and b.instrument_id = c.id
left join response_units d on c.id = d.instrument_id and d.instrument_id = c.id
join cc_sequences f on a.above_label = f.label and f.instrument_id = c.id
where c.prefix = 'ncds_04_cai'
UNION
select c.id,
b.id as question_id,
'QuestionItem',
d.id,
current_timestamp,
current_timestamp,
a.label,
g.id,
a.parent_type,
a.position,
a.branch
from jenny_questions a
cross join instruments c
left join question_items b on a.label = b.label and b.instrument_id = c.id
left join response_units d on c.id = d.instrument_id and d.instrument_id = c.id
join cc_conditions g on a.above_label = g.label and g.instrument_id = c.id
where c.prefix = 'ncds_04_cai');

SELECT pg_sleep(5);

INSERT INTO rds_qs (instrument_id, question_id, question_type, code_id, response_domain_id, response_domain_type, created_at, updated_at, rd_order)
(
select ccq.instrument_id, ccq.question_id, ccq.question_type, f.id, b.id, b.response_domain_type, current_timestamp, current_timestamp, 1
from jenny_questions a
cross join instruments
join cc_questions ccq on a.label = ccq.label and ccq.instrument_id = instruments.id
join code_lists f on a.Response_domain = f.label and f.instrument_id = instruments.id
join response_domain_codes b on f.id = b.code_list_id and b.instrument_id = instruments.id
where instruments.prefix = 'ncds_04_cai'
union
select ccq.instrument_id, ccq.question_id, ccq.question_type, null, c.id, c.response_domain_type, current_timestamp, current_timestamp, 1
from jenny_questions a
cross join instruments
join cc_questions ccq on a.label = ccq.label and ccq.instrument_id = instruments.id
join response_domain_datetimes c on a.response_domain = c.label and c.instrument_id = instruments.id
where instruments.prefix = 'ncds_04_cai'
union
select ccq.instrument_id, ccq.question_id, ccq.question_type, null, d.id, d.response_domain_type, current_timestamp, current_timestamp, 1
from jenny_questions a
cross join instruments
join cc_questions ccq on a.label = ccq.label and ccq.instrument_id = instruments.id
join response_domain_numerics d on a.response_domain = d.label and d.instrument_id = instruments.id
where instruments.prefix = 'ncds_04_cai'
union
select ccq.instrument_id, ccq.question_id, ccq.question_type, null, e.id, e.response_domain_type, current_timestamp, current_timestamp, 1
from jenny_questions a
cross join instruments
join cc_questions ccq on a.label = ccq.label and ccq.instrument_id = instruments.id
join response_domain_texts e on a.response_domain = e.label and e.instrument_id = instruments.id
where instruments.prefix = 'ncds_04_cai'
);
  
