\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE pilot_staff_owner;
-- Each deferred trigger checks only its affected root. No historical table scan.
CREATE FUNCTION pilot_staff._assert_roots() RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM pilot_staff.control) OR
  (SELECT count(*) FROM pilot_staff.principals)<>2 OR (SELECT count(*) FROM pilot_staff.slots)<>2 OR
  (SELECT count(*) FROM pilot_staff.targets)<>2 OR (SELECT count(*) FROM pilot_staff.assignments)<>2
 THEN RAISE EXCEPTION 'incomplete pilot roots' USING ERRCODE='23514'; END IF;
END $$;
CREATE FUNCTION pilot_staff._assert_context(cid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM pilot_staff.contexts WHERE id=cid) OR NOT EXISTS(
  SELECT FROM pilot_staff.audit WHERE context_id=cid AND action='context_prepared')
 THEN RAISE EXCEPTION 'incomplete entry context' USING ERRCODE='23514'; END IF;
END $$;
CREATE FUNCTION pilot_staff._assert_operation(cid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE o pilot_staff.operations; l pilot_staff.logins;
BEGIN
 SELECT * INTO o FROM pilot_staff.operations WHERE context_id=cid;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing integrity root' USING ERRCODE='23514'; END IF;
 PERFORM pilot_staff._assert_context(cid);
  IF o.outcome='succeeded' THEN
   SELECT * INTO l FROM pilot_staff.logins WHERE id=o.login_id;
   IF NOT FOUND OR ROW(l.context_id,l.operation_id,l.permit_id,l.issued_at) IS DISTINCT FROM ROW(o.context_id,o.operation_id,o.permit_id,o.completed_at)
    OR o.result IS DISTINCT FROM jsonb_build_object('kind','pilot_login_completed','operationId',o.operation_id,'loginId',l.id,'completedAt',pilot_staff._utc(o.completed_at))
    OR NOT EXISTS(SELECT FROM pilot_staff.audit WHERE action='login_completed' AND login_id=l.id AND principal_id=l.principal_id AND context_id=o.context_id AND operation_id=o.operation_id)
   THEN RAISE EXCEPTION 'incomplete successful login' USING ERRCODE='23514'; END IF;
  ELSE
   IF o.result IS DISTINCT FROM jsonb_build_object('kind','pilot_login_rejected','operationId',o.operation_id,'reasonCode','AUTH_REQUIRED','completedAt',pilot_staff._utc(o.completed_at))
    OR NOT EXISTS(SELECT FROM pilot_staff.audit WHERE action='login_rejected' AND context_id=o.context_id AND operation_id=o.operation_id AND login_id IS NULL)
   THEN RAISE EXCEPTION 'incomplete rejected login' USING ERRCODE='23514'; END IF;
  END IF;

END $$;
CREATE FUNCTION pilot_staff._assert_login(lid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE l pilot_staff.logins;
BEGIN
 SELECT * INTO l FROM pilot_staff.logins WHERE id=lid;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing integrity root' USING ERRCODE='23514'; END IF;
 PERFORM pilot_staff._assert_operation(l.context_id);
  IF NOT EXISTS(SELECT FROM pilot_staff.envelope_nonces n WHERE n.login_id=l.id AND
     (l.cookie_envelope IS NULL OR (n.key_id::text=l.cookie_envelope->>'key_id' AND n.nonce=l.cookie_envelope->>'nonce')))
  THEN RAISE EXCEPTION 'missing unique envelope nonce evidence' USING ERRCODE='23514'; END IF;
  IF NOT EXISTS(SELECT FROM pilot_staff.operations WHERE context_id=l.context_id AND operation_id=l.operation_id AND login_id=l.id AND outcome='succeeded')
   OR (l.revoked_at IS NULL AND NOT EXISTS(SELECT FROM pilot_staff.slots WHERE principal_id=l.principal_id AND login_id=l.id))
   OR (l.revoked_at IS NOT NULL AND EXISTS(SELECT FROM pilot_staff.slots WHERE login_id=l.id))
   OR (l.revoked_at IS NULL AND EXISTS(SELECT FROM pilot_staff.permits pe JOIN pilot_staff.principals pr ON pr.id=pe.principal_id
    WHERE pe.id=l.permit_id AND (pe.revoked_at IS NOT NULL OR pr.current_permit_id<>pe.id)))
   OR (l.revoked_at IS NULL AND NOT EXISTS(SELECT FROM pilot_staff.assignments WHERE principal_id=l.principal_id AND enabled))
   OR (l.revoked_at IS NULL AND EXISTS(SELECT FROM pilot_staff.control WHERE singleton AND (closed_at IS NOT NULL OR epoch<>l.epoch)))
  THEN RAISE EXCEPTION 'incomplete login or active slot' USING ERRCODE='23514'; END IF;
  IF l.confirmed_at IS NOT NULL AND NOT EXISTS(SELECT FROM pilot_staff.audit WHERE action='own_me' AND login_id=l.id AND principal_id=l.principal_id)
  THEN RAISE EXCEPTION 'confirmation without audit' USING ERRCODE='23514'; END IF;
  IF l.envelope_erased_at IS NOT NULL AND l.confirmed_at IS NULL AND l.revoked_at IS NULL AND NOT EXISTS(
   SELECT FROM pilot_staff.cookie_erasures ce JOIN pilot_staff.audit au ON au.id=ce.audit_id
   WHERE ce.login_id=l.id AND ce.erased_at=l.envelope_erased_at AND ce.erased_at>=l.delivery_deadline AND au.action='cookie_windows_expired')
  THEN RAISE EXCEPTION 'erasure without evidence' USING ERRCODE='23514'; END IF;

END $$;
CREATE FUNCTION pilot_staff._assert_logout_context(cid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE lc pilot_staff.logout_contexts;
BEGIN
 SELECT * INTO lc FROM pilot_staff.logout_contexts WHERE id=cid;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing integrity root' USING ERRCODE='23514'; END IF;
  IF NOT EXISTS(SELECT FROM pilot_staff.logins target JOIN pilot_staff.logins authorizer ON authorizer.principal_id=target.principal_id
    WHERE target.id=lc.target_login_id AND authorizer.id=lc.authorizing_login_id)
   OR (lc.source_context_id IS NOT NULL AND NOT EXISTS(SELECT FROM pilot_staff.logout_contexts src WHERE src.id=lc.source_context_id AND src.target_login_id=lc.target_login_id))
   OR NOT EXISTS(SELECT FROM pilot_staff.audit WHERE context_id=lc.id AND login_id=lc.target_login_id AND action=CASE WHEN lc.source_context_id IS NULL THEN 'logout_prepared' ELSE 'logout_continued' END)
  THEN RAISE EXCEPTION 'incomplete logout context' USING ERRCODE='23514'; END IF;

END $$;
CREATE FUNCTION pilot_staff._assert_logout_result(cid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE lr pilot_staff.logout_results;
BEGIN
 SELECT * INTO lr FROM pilot_staff.logout_results WHERE context_id=cid;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing integrity root' USING ERRCODE='23514'; END IF;
 PERFORM pilot_staff._assert_logout_context(cid);
  IF NOT EXISTS(SELECT FROM pilot_staff.logout_contexts WHERE id=lr.context_id AND target_login_id=lr.target_login_id)
   OR NOT EXISTS(SELECT FROM pilot_staff.logins WHERE id=lr.target_login_id AND revoked_at IS NOT NULL)
   OR EXISTS(SELECT FROM pilot_staff.slots WHERE login_id=lr.target_login_id)
   OR lr.result IS DISTINCT FROM jsonb_build_object('kind','logout_completed','operationId',lr.operation_id,'targetLoginId',lr.target_login_id,'completedAt',pilot_staff._utc(lr.completed_at))
   OR NOT EXISTS(SELECT FROM pilot_staff.audit WHERE action='logout_completed' AND context_id=lr.context_id AND operation_id=lr.operation_id AND login_id=lr.target_login_id)
  THEN RAISE EXCEPTION 'incomplete logout result' USING ERRCODE='23514'; END IF;

END $$;
CREATE FUNCTION pilot_staff._assert_read(aid uuid) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE a pilot_staff.audit; t pilot_staff.targets; e pilot_staff.read_evidence; expected integer;
BEGIN
 SELECT * INTO a FROM pilot_staff.audit WHERE id=aid;
 IF NOT FOUND THEN RAISE EXCEPTION 'missing integrity root' USING ERRCODE='23514'; END IF;
 IF a.action NOT IN('session_list','session_read','session_events') THEN RAISE EXCEPTION 'wrong evidence parent' USING ERRCODE='23514'; END IF;
  expected:=CASE a.action WHEN 'session_list' THEN 2 WHEN 'session_read' THEN 3 ELSE 1 END;
  IF (a.action='session_list' AND a.target_session_id IS NOT NULL) OR (a.action<>'session_list' AND a.target_session_id IS NULL) OR a.principal_id IS NULL OR a.login_id IS NULL OR a.assignment_version IS DISTINCT FROM 1
   OR NOT EXISTS(SELECT FROM pilot_staff.logins WHERE id=a.login_id AND principal_id=a.principal_id)
   OR (SELECT count(*) FROM pilot_staff.read_evidence WHERE audit_id=a.id)<>expected
  THEN RAISE EXCEPTION 'incomplete read audit' USING ERRCODE='23514'; END IF;
  FOR e IN SELECT * FROM pilot_staff.read_evidence WHERE audit_id=a.id LOOP
   SELECT * INTO STRICT t FROM pilot_staff.targets WHERE ordinal=e.target_ordinal;
   IF e.session_id IS DISTINCT FROM t.session_id OR (a.target_session_id IS NOT NULL AND (a.target_session_id<>e.session_id OR a.snapshot_version<>e.snapshot_version))
    OR NOT (e.granted_group=ANY(CASE a.action WHEN 'session_list' THEN ARRAY['pilot.sessions.list'] WHEN 'session_events' THEN ARRAY['pilot.session.events'] ELSE ARRAY['session.summary','session.settings','session.financial_snapshot'] END))
   THEN RAISE EXCEPTION 'wrong read evidence' USING ERRCODE='23514'; END IF;
  END LOOP;

END $$;
CREATE FUNCTION pilot_staff._complete() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE v jsonb; oldv jsonb; lid uuid; pid uuid; peid uuid;
BEGIN
 IF TG_OP='DELETE' THEN v:=to_jsonb(OLD); ELSE v:=to_jsonb(NEW); END IF;
 IF TG_OP='UPDATE' THEN oldv:=to_jsonb(OLD); END IF;
 IF TG_TABLE_NAME IN('control','principals','slots','assignments','targets') THEN
  PERFORM pilot_staff._assert_roots();
 END IF;
 CASE TG_TABLE_NAME
 WHEN 'contexts' THEN PERFORM pilot_staff._assert_context((v->>'id')::uuid);
 WHEN 'operations' THEN PERFORM pilot_staff._assert_operation((v->>'context_id')::uuid);
 WHEN 'logins' THEN PERFORM pilot_staff._assert_login((v->>'id')::uuid);
 WHEN 'envelope_nonces' THEN PERFORM pilot_staff._assert_login((v->>'login_id')::uuid);
 WHEN 'cookie_erasures' THEN PERFORM pilot_staff._assert_login((v->>'login_id')::uuid);
 WHEN 'logout_contexts' THEN PERFORM pilot_staff._assert_logout_context((v->>'id')::uuid);
 WHEN 'logout_results' THEN PERFORM pilot_staff._assert_logout_result((v->>'context_id')::uuid);
 WHEN 'read_evidence' THEN PERFORM pilot_staff._assert_read((v->>'audit_id')::uuid);
 WHEN 'audit' THEN
  CASE v->>'action'
  WHEN 'context_prepared' THEN PERFORM pilot_staff._assert_context((v->>'context_id')::uuid);
  WHEN 'login_completed' THEN PERFORM pilot_staff._assert_operation((v->>'context_id')::uuid);
  WHEN 'login_rejected' THEN PERFORM pilot_staff._assert_operation((v->>'context_id')::uuid);
  WHEN 'logout_prepared' THEN PERFORM pilot_staff._assert_logout_context((v->>'context_id')::uuid);
  WHEN 'logout_continued' THEN PERFORM pilot_staff._assert_logout_context((v->>'context_id')::uuid);
  WHEN 'logout_completed' THEN PERFORM pilot_staff._assert_logout_result((v->>'context_id')::uuid);
  WHEN 'session_list' THEN PERFORM pilot_staff._assert_read((v->>'id')::uuid);
  WHEN 'session_read' THEN PERFORM pilot_staff._assert_read((v->>'id')::uuid);
  WHEN 'session_events' THEN PERFORM pilot_staff._assert_read((v->>'id')::uuid);
  ELSE NULL;
  END CASE;
  IF v->>'login_id' IS NOT NULL THEN PERFORM pilot_staff._assert_login((v->>'login_id')::uuid); END IF;
 WHEN 'slots' THEN
  IF v->>'login_id' IS NOT NULL THEN PERFORM pilot_staff._assert_login((v->>'login_id')::uuid); END IF;
  IF oldv->>'login_id' IS NOT NULL AND oldv->>'login_id' IS DISTINCT FROM v->>'login_id'
  THEN PERFORM pilot_staff._assert_login((oldv->>'login_id')::uuid); END IF;
 ELSE
  -- Only the at-most-two unrevoked logins can depend on mutable root state.
  -- Partial indexes avoid scanning historical logins for permit/principal edits.
  IF TG_TABLE_NAME='permits' THEN
   peid:=(v->>'id')::uuid;
   FOR lid IN SELECT id FROM pilot_staff.logins WHERE permit_id=peid AND revoked_at IS NULL LOOP
    PERFORM pilot_staff._assert_login(lid);
   END LOOP;
  ELSIF TG_TABLE_NAME IN('principals','assignments') THEN
   pid:=coalesce(v->>'principal_id',v->>'id')::uuid;
   FOR lid IN SELECT id FROM pilot_staff.logins WHERE principal_id=pid AND revoked_at IS NULL LOOP
    PERFORM pilot_staff._assert_login(lid);
   END LOOP;
  ELSE
   FOR lid IN SELECT id FROM pilot_staff.logins WHERE revoked_at IS NULL LOOP
    PERFORM pilot_staff._assert_login(lid);
   END LOOP;
  END IF;
 END CASE;
 RETURN NULL;
END $$;
DO $$DECLARE n text; BEGIN
 FOREACH n IN ARRAY ARRAY['control','principals','permits','slots','contexts','operations','logins','logout_contexts','logout_results','targets','assignments','audit','read_evidence','envelope_nonces','cookie_erasures'] LOOP
  EXECUTE format('CREATE CONSTRAINT TRIGGER pilot_complete AFTER INSERT OR UPDATE OR DELETE ON pilot_staff.%I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION pilot_staff._complete()',n);
 END LOOP;
END $$;
-- All runtime entry points require SERIALIZABLE; private helpers are not RPCs.
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA pilot_staff FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA pilot_staff FROM PUBLIC,pilot_staff_auth,pilot_staff_reader,pilot_staff_operator;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA pilot_staff FROM PUBLIC,pilot_staff_auth,pilot_staff_reader,pilot_staff_operator;
COMMIT;
