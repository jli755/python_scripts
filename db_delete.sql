-- heroku psql -a closer-archivist-jenny < db_delete.sql;

-- delete all tables contains ncds_04_cai;

delete from rds_qs where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from cc_questions where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from question_items where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from instructions where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from cc_loops where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from cc_conditions where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from codes where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from categories where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from response_domain_codes where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from code_lists where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from response_domain_datetimes where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from response_domain_texts where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from response_domain_numerics where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from control_constructs where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from cc_sequences where instrument_id = (select id from instruments where prefix = 'ncds_04_cai');

delete from instruments where prefix = 'ncds_04_cai';
