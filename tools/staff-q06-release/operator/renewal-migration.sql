\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL ROLE polygon_owner;
CREATE FUNCTION polygon.pilot_staff_current_target(uid uuid, sid uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE current_id uuid;
BEGIN
 SELECT current_session_id INTO current_id FROM polygon.user_session_slots WHERE user_id=uid FOR SHARE;
 RETURN current_id IS NOT NULL AND current_id=sid;
END $$;
REVOKE ALL ON FUNCTION polygon.pilot_staff_current_target(uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION polygon.pilot_staff_current_target(uuid,uuid) TO pilot_staff_owner;

RESET ROLE;
SET LOCAL ROLE pilot_staff_owner;
ALTER TABLE pilot_staff.audit DROP CONSTRAINT audit_action_check;
ALTER TABLE pilot_staff.audit ADD CONSTRAINT audit_action_check CHECK(action IN(
 'provision','activate','bind_sessions','permit_revoked','permit_rotated','pilot_closed','pilot_renewed',
 'context_prepared','login_completed','login_rejected','login_replaced','login_outcome_read','cookie_recovered','own_me',
 'logout_prepared','logout_continued','logout_completed','logout_outcome_read','session_list','session_read',
 'session_events','access_denied','cookie_windows_expired'));

CREATE TABLE pilot_staff.renewals (
 request_id pilot_staff.u PRIMARY KEY,
 request_digest pilot_staff.h NOT NULL,
 prior_profile jsonb NOT NULL,
 new_epoch bigint NOT NULL UNIQUE,
 new_run_id pilot_staff.u NOT NULL UNIQUE,
 audit_id uuid NOT NULL UNIQUE REFERENCES pilot_staff.audit(id),
 result jsonb NOT NULL
);
CREATE TRIGGER immutable_renewals BEFORE UPDATE OR DELETE ON pilot_staff.renewals
 FOR EACH ROW EXECUTE FUNCTION pilot_staff.immutable();
REVOKE ALL ON pilot_staff.renewals FROM PUBLIC,pilot_staff_auth,pilot_staff_reader,pilot_staff_operator;

CREATE FUNCTION pilot_staff.prepare_renewal(p jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE
 c pilot_staff.control; receipt pilot_staff.renewals; target pilot_staff.targets; principal record;
 permit jsonb; request_hash text; rid pilot_staff.u; run pilot_staff.u; digest pilot_staff.h;
 opened timestamptz; cutoff timestamptz; now_at timestamptz; lid uuid; aid uuid; answer jsonb; expected_targets jsonb;
BEGIN
 IF NOT pg_has_role(session_user,'pilot_staff_operator','USAGE') THEN RAISE EXCEPTION 'operator required' USING ERRCODE='42501'; END IF;
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001'; END IF;
 IF pilot_staff._exact(p,ARRAY['request_id','expected_epoch','expected_deployment_digest','run_id',
  'deployment_digest','origin','opened_at','cutoff_at','session_ids','permits']) IS DISTINCT FROM true
 THEN RAISE EXCEPTION 'invalid renewal shape' USING ERRCODE='22023'; END IF;
 rid:=(p->>'request_id')::pilot_staff.u;
 run:=(p->>'run_id')::pilot_staff.u;
 digest:=(p->>'deployment_digest')::pilot_staff.h;
 opened:=(p->>'opened_at')::timestamptz;
 cutoff:=(p->>'cutoff_at')::timestamptz;
 request_hash:=pilot_staff._hash(p);

 -- The same control lock serializes renewal, login, reads and activation.
 SELECT * INTO STRICT c FROM pilot_staff.control WHERE singleton FOR UPDATE;
 IF p->>'expected_deployment_digest' IS DISTINCT FROM current_setting('pilot_staff.expected_deployment_digest',true)
 THEN PERFORM pilot_staff._fail('SERVICE_UNAVAILABLE',503); END IF;
 SELECT * INTO receipt FROM pilot_staff.renewals WHERE request_id=rid;
 IF FOUND THEN
  IF receipt.request_digest IS DISTINCT FROM request_hash THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
  RETURN receipt.result;
 END IF;

 now_at:=date_trunc('milliseconds',clock_timestamp());
 IF p->>'expected_epoch' IS DISTINCT FROM c.epoch::text OR p->>'expected_deployment_digest' IS DISTINCT FROM c.deployment_digest
  OR c.closed_at IS NOT NULL OR c.cutoff_at>now_at
 THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
 IF run IS NULL OR digest IS NULL OR run=c.run_id OR digest=c.deployment_digest OR EXISTS (
  SELECT FROM pilot_staff.renewals WHERE renewals.new_run_id=run OR prior_profile->>'run_id'=run::text
  OR prior_profile->>'deployment_digest'=digest OR result#>>'{data,deploymentDigest}'=digest
 ) OR p->>'origin' IS NULL OR (p->>'origin' ~ '^https://[^/@?#[:space:]]+$') IS DISTINCT FROM true
  OR opened IS NULL OR opened<c.cutoff_at OR opened>now_at OR cutoff IS NULL OR cutoff<=now_at
  OR cutoff<>(((opened AT TIME ZONE 'Europe/Warsaw')::date+1+time '23:00') AT TIME ZONE 'Europe/Warsaw')
  OR cutoff>now_at+interval '48 hours'
  OR jsonb_typeof(p->'permits') IS DISTINCT FROM 'array'
 THEN RAISE EXCEPTION 'invalid new period' USING ERRCODE='22023'; END IF;
 IF jsonb_array_length(p->'permits')<>2 THEN RAISE EXCEPTION 'two permits required' USING ERRCODE='22023'; END IF;

 SELECT jsonb_agg(session_id ORDER BY ordinal) INTO expected_targets FROM pilot_staff.targets;
 IF jsonb_array_length(expected_targets) IS DISTINCT FROM 2 OR expected_targets IS DISTINCT FROM p->'session_ids'
 THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
 FOR target IN SELECT * FROM pilot_staff.targets ORDER BY ordinal LOOP
  IF polygon.pilot_staff_current_target(target.user_id,target.session_id) IS DISTINCT FROM true
  THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
  PERFORM pilot_staff._source(target);
 END LOOP;
 IF (SELECT count(*) FROM pilot_staff.assignments WHERE enabled)<>2
 THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
 IF p#>>'{permits,0,permit_digest}' IS NOT DISTINCT FROM p#>>'{permits,1,permit_digest}'
 THEN RAISE EXCEPTION 'distinct permits required' USING ERRCODE='22023'; END IF;

 FOR lid IN SELECT id FROM pilot_staff.logins WHERE revoked_at IS NULL ORDER BY id LOOP
  PERFORM pilot_staff._revoke(lid,now_at);
 END LOOP;
 UPDATE pilot_staff.permits SET revoked_at=now_at WHERE revoked_at IS NULL;
 FOR principal IN
  SELECT pr.id,pr.ordinal,pe.version FROM pilot_staff.principals pr
   JOIN pilot_staff.permits pe ON pe.id=pr.current_permit_id ORDER BY pr.ordinal
 LOOP
  permit:=p->'permits'->(principal.ordinal-1);
  IF pilot_staff._exact(permit,ARRAY['principal_id','permit_id','permit_digest']) IS DISTINCT FROM true
   OR permit->>'principal_id' IS DISTINCT FROM principal.id::text
  THEN RAISE EXCEPTION 'invalid permit assignment' USING ERRCODE='22023'; END IF;
  INSERT INTO pilot_staff.permits(id,principal_id,version,digest,created_at,expires_at)
   VALUES((permit->>'permit_id')::pilot_staff.u,principal.id,principal.version+1,
          (permit->>'permit_digest')::pilot_staff.h,now_at,cutoff);
  UPDATE pilot_staff.principals SET current_permit_id=(permit->>'permit_id')::pilot_staff.u WHERE id=principal.id;
 END LOOP;

 UPDATE pilot_staff.control SET run_id=run,deployment_digest=digest,origin=p->>'origin',
  opened_at=opened,cutoff_at=cutoff,epoch=c.epoch+1,enabled=false WHERE singleton;
 aid:=pilot_staff._audit(rid,'pilot_renewed',NULL,NULL,NULL,NULL,NULL,NULL);
 answer:=pilot_staff._ok(jsonb_build_object('epoch',c.epoch+1,'runId',run,'enabled',false,
  'deploymentDigest',digest,'auditId',aid));
 INSERT INTO pilot_staff.renewals VALUES(rid,request_hash,to_jsonb(c),c.epoch+1,run,aid,answer);
 RETURN answer;
EXCEPTION WHEN SQLSTATE 'PS001' THEN
 DECLARE message text; detail text;
 BEGIN
  GET STACKED DIAGNOSTICS message=MESSAGE_TEXT,detail=PG_EXCEPTION_DETAIL;
  RETURN jsonb_build_object('status','error','http',detail::integer,'reason_code',message);
 END;
END $$;
REVOKE ALL ON FUNCTION pilot_staff.prepare_renewal(jsonb) FROM PUBLIC,pilot_staff_auth,pilot_staff_reader;
GRANT EXECUTE ON FUNCTION pilot_staff.prepare_renewal(jsonb) TO pilot_staff_operator;
COMMIT;
