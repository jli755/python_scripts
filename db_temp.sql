-- heroku psql -a closer-archivist-jenny < db_temp.sql;

-- copy all csv files from output files of pre_process_db_input.py;

-- 1. codes;

CREATE TABLE Jenny_codes (
  Number int,
  Value int,
  Category varchar(1000),
  Codes_order int,
  Label varchar(255)
);
 
\COPY Jenny_codes FROM '../NCDS_2004/codes.csv' DELIMITER ',' CSV HEADER;

-- 2. response_domain, I changed "Numeric_Type/Datetime_type" to "Type2";

CREATE TABLE Jenny_response (
  Label varchar(1000),                                                   
  Type varchar(255),
  Type2 varchar(255),
  Min int,
  Max int
);
 
\COPY Jenny_response FROM '../NCDS_2004/response.csv' DELIMITER ',' CSV HEADER;


-- 3. sequences;
CREATE TABLE Jenny_sequences (
  Number int,
  Label varchar(1000),
  section_id int
);
 
\COPY Jenny_sequences FROM '../NCDS_2004/sequences.csv' DELIMITER ',' CSV HEADER;

-- 4. questions;
CREATE TABLE Jenny_questions (
  Label varchar(255),
  Literal varchar(1000),
  Instructions varchar(1000),
  Response_domain varchar(255),
  above_label varchar(255),
  parent_type varchar(255),
  branch int,
  Position int
);
 
\COPY Jenny_questions FROM '../NCDS_2004/questions.csv' DELIMITER ',' CSV HEADER;


-- 5. conditions;
CREATE TABLE Jenny_conditions (
  Label varchar(255),
  Literal varchar(1000),
  Logic varchar(1000),
  above_label varchar(255),
  parent_type varchar(255),
  branch int,
  Position int
);
 
\COPY Jenny_conditions FROM '../NCDS_2004/conditions.csv' DELIMITER ',' CSV HEADER;


-- 6. loops;

CREATE TABLE Jenny_loops (
  Label varchar(255),
  Variable varchar(1000),
  Start_Value varchar(255),
  End_Value varchar(255),
  Loop_While varchar(1000),
  Logic varchar(1000),
  above_label varchar(255),
  parent_type varchar(255),
  branch int,
  Position int
);
 
\COPY Jenny_loops FROM '../NCDS_2004/loops.csv' DELIMITER ',' CSV HEADER;



-- 7. topics, no topics for NCDS_2004 study, TODO: later;
CREATE TABLE Jenny_topics (
  name varchar(255),
  parent_id int,
  code int,
  description varchar(1000)
);

\COPY Jenny_topics FROM '../NCDS_2004/Topics_table_main_archivist.csv' DELIMITER ',' CSV HEADER;

INSERT INTO topics (Name, code, parent_id, description, created_at, updated_at)
(select name, code, parent_id, description,
        current_timestamp,
        current_timestamp
from Jenny_topics);
