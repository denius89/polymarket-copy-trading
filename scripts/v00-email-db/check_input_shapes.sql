\set ON_ERROR_STOP on
-- Operator-only regression: validators + capture preflight, no fixtures/network/persistent writes.
-- Requires the isolated gate open/trusted; valid capture stops at unknown context404.
-- Run after 008; this file is NOT installation and has not been run by the DB chat.
BEGIN;
SET LOCAL ROLE v00_email_owner;
DO $$
DECLARE item jsonb; rejected boolean;
BEGIN
  PERFORM v00_email.keys('{"entries":[]}',ARRAY['entries'],'{}','{}',ARRAY['entries']);
  PERFORM v00_email.keys('{"action":"C01","challenge_id":null,"locale":"en","email_binding":{"address_digest":"x"}}',
    ARRAY['action','challenge_id','locale','email_binding'],ARRAY['challenge_id','locale','email_binding'],ARRAY['email_binding']);
  PERFORM v00_email.keys('{"action":"C03","email_binding":null}',ARRAY['action','email_binding'],ARRAY['email_binding'],ARRAY['email_binding']);
  FOREACH item IN ARRAY ARRAY['{"action":"C01"}'::jsonb,'{"action":"C03"}','{"action":"C02"}','{"action":"AUTH_TOTP_VERIFY"}'] LOOP
    PERFORM v00_email.keys(item,ARRAY['action']);
  END LOOP;
  FOREACH item IN ARRAY ARRAY['{}'::jsonb,'{"action":"C01","extra":"x"}','{"action":null}',
    '{"action":""}','{"action":12}','{"action":{}}','{"action":"claim"}'] LOOP
    rejected:=false;
    BEGIN PERFORM v00_email.keys(item,ARRAY['action']); EXCEPTION WHEN raise_exception THEN rejected:=true; END;
    IF NOT rejected THEN RAISE EXCEPTION 'invalid action/shape accepted'; END IF;
  END LOOP;
  FOREACH item IN ARRAY ARRAY['{"entries":null}'::jsonb,'{"entries":{}}','{"entries":"x"}'] LOOP
    rejected:=false;
    BEGIN PERFORM v00_email.keys(item,ARRAY['entries'],'{}','{}',ARRAY['entries']); EXCEPTION WHEN raise_exception THEN rejected:=true; END;
    IF NOT rejected THEN RAISE EXCEPTION 'invalid entries accepted'; END IF;
  END LOOP;
  FOREACH item IN ARRAY ARRAY['{"email_binding":[]}'::jsonb,'{"email_binding":"x"}'] LOOP
    rejected:=false;
    BEGIN PERFORM v00_email.keys(item,ARRAY['email_binding'],ARRAY['email_binding'],ARRAY['email_binding']); EXCEPTION WHEN raise_exception THEN rejected:=true; END;
    IF NOT rejected THEN RAISE EXCEPTION 'invalid binding accepted'; END IF;
  END LOOP;
  rejected:=false;
  BEGIN PERFORM v00_email.keys('{"proof_digest":"invalid"}',ARRAY['proof_digest']); EXCEPTION WHEN raise_exception THEN rejected:=true; END;
  IF NOT rejected THEN RAISE EXCEPTION 'digest validation lost'; END IF;
  -- Existing dependency routes retain the old enum and scalar-only boundary.
  rejected:=false;
  BEGIN PERFORM v00_upstream.keys('{"action":"C01"}',ARRAY['action']); EXCEPTION WHEN raise_exception THEN rejected:=true; END;
  IF NOT rejected THEN RAISE EXCEPTION 'legacy action widened'; END IF;
  rejected:=false;
  BEGIN PERFORM v00_upstream.keys('{"entries":[]}',ARRAY['entries']); EXCEPTION WHEN raise_exception THEN rejected:=true; END;
  IF NOT rejected THEN RAISE EXCEPTION 'legacy shape widened'; END IF;
END $$;
DO $$
DECLARE cid uuid:=gen_random_uuid(); op uuid:=gen_random_uuid(); ch uuid:=gen_random_uuid();
  base jsonb; item jsonb; answer jsonb; rejected boolean; act text;
BEGIN
  IF NOT EXISTS(SELECT 1 FROM v00_upstream.gate WHERE singleton AND is_open AND clock_trusted) THEN
    RAISE EXCEPTION 'capture regression requires open trusted isolated gate';
  END IF;
  IF EXISTS(SELECT 1 FROM v00_email.contexts WHERE id=cid) THEN RAISE EXCEPTION 'unexpected regression context'; END IF;
  base:=jsonb_build_object('context_id',cid,'proof_digest',repeat('a',64),'operation_id',op,
    'action','C01','fingerprint',repeat('b',64),'comparison_hmac',repeat('c',64),'comparison_key_id','comparison-1',
    'executor_id',gen_random_uuid(),'executor_proof_digest',repeat('d',64),'challenge_id',NULL,
    'locale','en','email_binding',jsonb_build_object('address_digest',repeat('e',64),'address_key_id','email-address-1'),
    'request_started_at',v00_session.utc(clock_timestamp()));
  -- Valid shapes reach the ordinary access guard, without creating a context or admission.
  FOREACH act IN ARRAY ARRAY['C01','C03','C02','AUTH_TOTP_VERIFY'] LOOP
    item:=base || jsonb_build_object('action',act,'request_started_at',v00_session.utc(clock_timestamp()));
    IF act<>'C01' THEN item:=item || jsonb_build_object('challenge_id',ch,'email_binding',NULL); END IF;
    IF act IN ('C02','AUTH_TOTP_VERIFY') THEN item:=item || jsonb_build_object('locale',NULL); END IF;
    answer:=v00_email.capture(item);
    IF answer IS DISTINCT FROM v00_session.error(404,'RESOURCE_NOT_FOUND') THEN
      RAISE EXCEPTION 'valid capture shape did not reach access guard';
    END IF;
  END LOOP;
  FOREACH item IN ARRAY ARRAY[
    base || jsonb_build_object('challenge_id',ch),
    base || jsonb_build_object('locale',NULL),
    base || jsonb_build_object('locale','de'),
    base || jsonb_build_object('email_binding',NULL),
    base || jsonb_build_object('email_binding',jsonb_build_object('address_digest',repeat('e',64))),
    base || jsonb_build_object('email_binding',(base->'email_binding') || '{"extra":"x"}'::jsonb),
    base || jsonb_build_object('email_binding',jsonb_build_object('address_digest','x','address_key_id','email-address-1')),
    base || jsonb_build_object('action','C03','challenge_id',ch),
    base || jsonb_build_object('action','C03','email_binding',NULL),
    base || jsonb_build_object('action','C02','challenge_id',ch,'email_binding',NULL),
    base || jsonb_build_object('action','AUTH_TOTP_VERIFY','challenge_id',ch,'email_binding',NULL)
  ] LOOP
    rejected:=false;
    BEGIN PERFORM v00_email.capture(item); EXCEPTION WHEN raise_exception THEN rejected:=true; END;
    IF NOT rejected THEN RAISE EXCEPTION 'invalid dependent/nested capture shape accepted'; END IF;
  END LOOP;
  IF EXISTS(SELECT 1 FROM v00_email.contexts WHERE id=cid)
    OR EXISTS(SELECT 1 FROM v00_email.admissions WHERE context_id=cid) THEN
    RAISE EXCEPTION 'preflight regression unexpectedly wrote context/admission';
  END IF;
END $$;
SELECT 'input_shapes_checked_no_runtime_claim' AS status;
ROLLBACK;
