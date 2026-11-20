\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE pilot_staff_owner;
CREATE FUNCTION pilot_staff._operator(route text,p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE c pilot_staff.control; t timestamptz:=date_trunc('milliseconds',clock_timestamp()); rid uuid; x jsonb; i integer:=0;
 keys text[]; pe pilot_staff.permits; pr pilot_staff.principals; target pilot_staff.targets; b jsonb; lid uuid; code text; detail text;
BEGIN
 IF NOT pg_has_role(session_user,'pilot_staff_operator','USAGE') THEN RAISE EXCEPTION 'operator required' USING ERRCODE='42501'; END IF;
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'serializable required' USING ERRCODE='25001'; END IF;
 keys:=CASE route WHEN 'provision' THEN ARRAY['request_id','run_id','deployment_digest','origin','opened_at','cutoff_at','principals','targets']
 WHEN 'bind_sessions' THEN ARRAY['request_id','session_ids'] WHEN 'revoke_permit' THEN ARRAY['request_id','permit_id']
 WHEN 'rotate_permit' THEN ARRAY['request_id','old_permit_id','new_permit_id','new_permit_digest'] ELSE ARRAY['request_id'] END;
 IF pilot_staff._exact(p,keys) IS DISTINCT FROM true THEN RAISE EXCEPTION 'operator shape' USING ERRCODE='22023'; END IF;
 rid:=(p->>'request_id')::pilot_staff.u;
 IF route='provision' THEN
  IF EXISTS(SELECT FROM pilot_staff.control) THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
  IF p->>'deployment_digest' IS DISTINCT FROM current_setting('pilot_staff.expected_deployment_digest',true)
   OR jsonb_typeof(p->'principals')<>'array' OR jsonb_array_length(p->'principals')<>2
   OR jsonb_typeof(p->'targets')<>'array' OR jsonb_array_length(p->'targets')<>2
   OR (p->>'opened_at')::timestamptz>t OR (p->>'cutoff_at')::timestamptz<=t
  THEN RAISE EXCEPTION 'invalid pinned pilot' USING ERRCODE='22023'; END IF;
  INSERT INTO pilot_staff.control(singleton,run_id,deployment_digest,origin,opened_at,cutoff_at)
   VALUES(true,(p->>'run_id')::uuid,p->>'deployment_digest',p->>'origin',(p->>'opened_at')::timestamptz,(p->>'cutoff_at')::timestamptz) RETURNING * INTO c;
  FOR x IN SELECT value FROM jsonb_array_elements(p->'principals') LOOP
   i:=i+1;
   IF pilot_staff._exact(x,ARRAY['principal_id','permit_id','permit_digest']) IS DISTINCT FROM true THEN RAISE EXCEPTION 'invalid principal config' USING ERRCODE='22023'; END IF;
   INSERT INTO pilot_staff.principals VALUES((x->>'principal_id')::uuid,i,'владелец '||i,(x->>'permit_id')::uuid);
   INSERT INTO pilot_staff.permits VALUES((x->>'permit_id')::uuid,(x->>'principal_id')::uuid,1,x->>'permit_digest',t,c.cutoff_at,NULL);
   INSERT INTO pilot_staff.assignments(principal_id) VALUES((x->>'principal_id')::uuid);
   INSERT INTO pilot_staff.slots(principal_id) VALUES((x->>'principal_id')::uuid);
  END LOOP;
  i:=0;
  FOR x IN SELECT value FROM jsonb_array_elements(p->'targets') LOOP
   i:=i+1;
   IF pilot_staff._exact(x,ARRAY['user_id']) IS DISTINCT FROM true THEN RAISE EXCEPTION 'invalid target config' USING ERRCODE='22023'; END IF;
   INSERT INTO pilot_staff.targets VALUES(i,(x->>'user_id')::uuid,'участник пилота '||i,NULL);
  END LOOP;
  PERFORM pilot_staff._audit(rid,'provision',NULL,NULL,NULL,NULL,NULL,NULL);
 ELSE
  c:=pilot_staff._barrier(false);
  IF route='bind_sessions' THEN
   IF c.enabled OR c.closed_at IS NOT NULL OR jsonb_typeof(p->'session_ids')<>'array' OR jsonb_array_length(p->'session_ids')<>2
   THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
   FOR target IN SELECT * FROM pilot_staff.targets ORDER BY ordinal LOOP
    IF target.session_id IS NOT NULL THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
    target.session_id:=(p->'session_ids'->>(target.ordinal-1))::uuid;
    b:=pilot_staff._source(target);
    UPDATE pilot_staff.targets SET session_id=target.session_id WHERE ordinal=target.ordinal;
   END LOOP;
   PERFORM pilot_staff._audit(rid,'bind_sessions',NULL,NULL,NULL,NULL,NULL,NULL);
  ELSIF route='activate' THEN
   IF c.enabled OR c.closed_at IS NOT NULL OR c.cutoff_at<=t OR (SELECT count(*) FROM pilot_staff.targets WHERE session_id IS NOT NULL)<>2
    OR (SELECT count(*) FROM pilot_staff.permits WHERE revoked_at IS NULL AND expires_at>t)<>2
   THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
   FOR target IN SELECT * FROM pilot_staff.targets ORDER BY ordinal LOOP PERFORM pilot_staff._source(target); END LOOP;
   UPDATE pilot_staff.control SET enabled=true WHERE singleton;
   PERFORM pilot_staff._audit(rid,'activate',NULL,NULL,NULL,NULL,NULL,NULL);
  ELSIF route IN('revoke_permit','rotate_permit') THEN
   SELECT * INTO pe FROM pilot_staff.permits WHERE id=coalesce(p->>'permit_id',p->>'old_permit_id')::uuid;
   IF NOT FOUND THEN PERFORM pilot_staff._fail('RESOURCE_NOT_FOUND',404); END IF;
   SELECT * INTO STRICT pr FROM pilot_staff.principals WHERE id=pe.principal_id;
   IF route='rotate_permit' AND (pr.current_permit_id<>pe.id OR c.closed_at IS NOT NULL OR t>=c.cutoff_at) THEN PERFORM pilot_staff._fail('AUTH_CONTEXT_STATE_CONFLICT',409); END IF;
   UPDATE pilot_staff.permits SET revoked_at=t WHERE id=pe.id AND revoked_at IS NULL;
   FOR lid IN SELECT id FROM pilot_staff.logins WHERE permit_id=pe.id AND revoked_at IS NULL LOOP PERFORM pilot_staff._revoke(lid,t); END LOOP;
   IF route='rotate_permit' THEN
    INSERT INTO pilot_staff.permits VALUES((p->>'new_permit_id')::uuid,pr.id,pe.version+1,p->>'new_permit_digest',t,c.cutoff_at,NULL);
    UPDATE pilot_staff.principals SET current_permit_id=(p->>'new_permit_id')::uuid WHERE id=pr.id;
   END IF;
   PERFORM pilot_staff._audit(rid,CASE route WHEN 'revoke_permit' THEN 'permit_revoked' ELSE 'permit_rotated' END,pr.id,NULL,NULL,NULL,NULL,NULL);
  ELSIF route='close_pilot' THEN
   IF c.closed_at IS NULL THEN UPDATE pilot_staff.control SET enabled=false,closed_at=t,epoch=epoch+1 WHERE singleton; END IF;
   UPDATE pilot_staff.permits SET revoked_at=t WHERE revoked_at IS NULL;
   FOR lid IN SELECT id FROM pilot_staff.logins WHERE revoked_at IS NULL LOOP PERFORM pilot_staff._revoke(lid,t); END LOOP;
   UPDATE pilot_staff.assignments SET enabled=false;
   PERFORM pilot_staff._audit(rid,'pilot_closed',NULL,NULL,NULL,NULL,NULL,NULL);
  ELSIF route='erase_expired_material' THEN
   PERFORM pilot_staff._erase_expired(rid);
  ELSE RAISE EXCEPTION 'operator route' USING ERRCODE='22023'; END IF;
 END IF;
 RETURN pilot_staff._ok(jsonb_build_object('completed',true));
EXCEPTION WHEN SQLSTATE 'PS001' THEN
 GET STACKED DIAGNOSTICS code=MESSAGE_TEXT,detail=PG_EXCEPTION_DETAIL;
 RETURN jsonb_build_object('status','error','http',detail::integer,'reason_code',code);
END $$;
DO $$DECLARE r text; BEGIN
 FOREACH r IN ARRAY ARRAY['provision','bind_sessions','activate','revoke_permit','rotate_permit','close_pilot','erase_expired_material'] LOOP
  EXECUTE format('CREATE FUNCTION pilot_staff.%I(p jsonb) RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS %L',r,format('SELECT pilot_staff._operator(%L,p)',r));
  EXECUTE format('REVOKE ALL ON FUNCTION pilot_staff.%I(jsonb) FROM PUBLIC',r);
  EXECUTE format('GRANT EXECUTE ON FUNCTION pilot_staff.%I(jsonb) TO pilot_staff_operator',r);
 END LOOP;
END $$;
COMMIT;
