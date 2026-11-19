\set ON_ERROR_STOP on
BEGIN;
SET LOCAL ROLE v00_session_owner;
-- The bridge exports no credential, secret, email or provider token. Runtime
-- cannot call it directly. Auth rows stay under their existing owner.
CREATE FUNCTION v00_session.polygon_identity(p jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE l v00_session.logins; r v00_session.results; c v00_session.contexts; e jsonb;
BEGIN
 PERFORM v00_session.require_keys(p,ARRAY['login_id','cookie_digest']);
 l:=v00_session.lock_login((p->>'login_id')::uuid);
 IF l.id IS NULL OR NOT EXISTS(SELECT 1 FROM v00_session.credentials cr WHERE cr.login_id=l.id AND cr.cookie_digest=p->>'cookie_digest')
 THEN RETURN v00_session.error(401,'AUTH_REQUIRED'); END IF;
 e:=v00_session.login_guard(l); IF e IS NOT NULL THEN RETURN e; END IF;
 SELECT * INTO c FROM v00_session.contexts WHERE id=l.context_id;
 IF c.revoked_at IS NOT NULL THEN RETURN v00_session.error(401,'AUTH_REVOKED'); END IF;
 SELECT * INTO r FROM v00_session.results WHERE context_id=l.context_id AND operation_id=l.operation_id;
 IF v00_session.valid_result(r) IS DISTINCT FROM true THEN RETURN v00_session.error(503,'RECORD_UNAVAILABLE'); END IF;
 IF (SELECT fixed_time FROM v00_session.actors WHERE id=l.actor_id) IS NOT NULL THEN
   RETURN v00_session.error(503,'SERVICE_UNAVAILABLE'); -- no frozen fixture clock on permanent profile
 END IF;
 RETURN jsonb_build_object('http',200,'auth_actor_id',l.actor_id,'login_id',l.id);
END $$;
REVOKE ALL ON FUNCTION v00_session.polygon_identity(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION v00_session.polygon_identity(jsonb) TO polygon_owner;
RESET ROLE;
SET LOCAL ROLE polygon_owner;

CREATE FUNCTION polygon.err(code text, status integer DEFAULT 503) RETURNS jsonb
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('http',status,'reason',code)
$$;
CREATE FUNCTION polygon.exact_keys(p jsonb, names text[]) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN jsonb_typeof(p)='object' THEN
 (SELECT array_agg(k ORDER BY k) FROM jsonb_object_keys(p) k) IS NOT DISTINCT FROM
 (SELECT array_agg(k ORDER BY k) FROM unnest(names) k) ELSE false END
$$;
CREATE FUNCTION polygon.uuid_text(t text) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT COALESCE(t ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',false)
$$;
CREATE FUNCTION polygon.version_text(t text) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN t ~ '^[1-9][0-9]{0,18}$' THEN t::numeric<=9223372036854775807 ELSE false END
$$;
CREATE FUNCTION polygon.guard(auth jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE g v00_upstream.gate; pr polygon.profile; a jsonb; u polygon.users; sc polygon.read_scopes;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 IF NOT polygon.exact_keys(auth,ARRAY['login_id','cookie_digest']) OR NOT polygon.uuid_text(auth->>'login_id')
   OR jsonb_typeof(auth->'login_id')<>'string' OR jsonb_typeof(auth->'cookie_digest')<>'string'
   OR COALESCE(auth->>'cookie_digest','') !~ '^[0-9a-f]{64}$'
 THEN RETURN polygon.err('AUTH_REQUIRED',401); END IF;
 -- Global gate before Auth actor/login/context, matching the installed Auth protocol.
 SELECT * INTO g FROM v00_upstream.gate WHERE singleton FOR SHARE;
 SELECT * INTO pr FROM polygon.profile WHERE singleton FOR SHARE;
 IF g.singleton IS NULL OR pr.singleton IS NULL OR NOT g.is_open OR NOT g.clock_trusted OR NOT pr.enabled
 THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 -- Operator writers must acquire X profile before changing scope/catalog/control.
 -- Runtime never owns or writes these rows. The bound is checked, never truncated.
 a:=v00_session.polygon_identity(auth); IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO u FROM polygon.users WHERE auth_actor_id=(a->>'auth_actor_id')::uuid;
 IF u.id IS NULL THEN RETURN polygon.err('ACCESS_DENIED',403); END IF;
 SELECT * INTO sc FROM polygon.read_scopes WHERE user_id=u.id FOR SHARE;
 IF sc.id IS NULL THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 RETURN jsonb_build_object('http',200,'user_id',u.id,'login_id',a->>'login_id',
  'read_context_id',u.id,'scope_id',sc.id,'scope_revision','q02-read-scope-v1:'||sc.id::text||':'||sc.revision::text,'environment',pr.environment,'epoch',g.epoch::text);
END $$;
CREATE FUNCTION polygon.current_identity(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb;
BEGIN
 IF NOT polygon.exact_keys(p,ARRAY['auth']) THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth');
 IF a->>'http'<>'200' THEN RETURN a; END IF;
 RETURN a-'login_id'-'epoch'-'environment';
END $$;
CREATE FUNCTION polygon.money(n numeric, d numeric DEFAULT 1) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE a numeric; b numeric; x numeric; scale_n integer;
BEGIN
 IF n IS NULL OR d IS NULL THEN RETURN NULL; END IF;
 IF d<=0 OR n<0 OR n::text IN ('NaN','Infinity','-Infinity') OR d::text IN ('NaN','Infinity','-Infinity') THEN
   RAISE EXCEPTION 'invalid exact money'; END IF;
 scale_n:=greatest(scale(n),scale(d));
 n:=n*power(10::numeric,scale_n); d:=d*power(10::numeric,scale_n);
 a:=n; b:=d;
 WHILE b<>0 LOOP x:=mod(a,b); a:=b; b:=x; END LOOP;
 n:=div(n,a); d:=div(d,a);
 IF length(n::text)>64 OR length(d::text)>64 THEN RAISE EXCEPTION 'money range'; END IF;
 RETURN jsonb_build_object('n',n::text,'d',d::text);
END $$;
CREATE FUNCTION polygon.percent(n numeric) RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN n IS NULL THEN NULL ELSE to_char(n,'FM990.00') END
$$;
CREATE FUNCTION polygon.field_value(n numeric, is_money boolean) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT CASE WHEN is_money THEN polygon.money(n) ELSE to_jsonb(polygon.percent(n)) END
$$;
-- Private transport only. Public Raw remains the exact Unicode string/null.
CREATE FUNCTION polygon.raw_encoded(b bytea) RETURNS text LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT replace(encode(b,'base64'),E'\n','')
$$;
CREATE FUNCTION polygon.raw_bytes(t text) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE b bytea; part bytea; at_zero integer; count_points integer:=0;
BEGIN
 IF t IS NULL THEN RETURN NULL; END IF;
 IF length(t)>344 THEN RAISE EXCEPTION 'raw transport too long'; END IF;
 b:=decode(t,'base64');
 IF polygon.raw_encoded(b) IS DISTINCT FROM t THEN RAISE EXCEPTION 'noncanonical raw transport'; END IF;
 part:=b;
 LOOP
  at_zero:=position(decode('00','hex') IN part);
  IF at_zero=0 THEN count_points:=count_points+length(convert_from(part,'UTF8')); EXIT; END IF;
  count_points:=count_points+length(convert_from(substring(part FROM 1 FOR at_zero-1),'UTF8'))+1;
  part:=substring(part FROM at_zero+1);
 END LOOP;
 IF count_points>64 THEN RAISE EXCEPTION 'raw code point limit'; END IF;
 RETURN b;
END $$;
CREATE FUNCTION polygon.numeric_text(t text) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE b bytea:=polygon.raw_bytes(t);
BEGIN
 IF b IS NULL THEN RETURN NULL; END IF;
 -- NUL is valid Raw but never an ASCII decimal. No mutation of the stored bytes.
 IF position(decode('00','hex') IN b)>0 THEN RETURN chr(1); END IF;
 RETURN convert_from(b,'UTF8');
END $$;
CREATE FUNCTION polygon.raw_json(t text) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE b bytea:=polygon.raw_bytes(t); result text:='"'; part text; zero_at integer;
BEGIN
 IF b IS NULL THEN RETURN 'null'; END IF;
 LOOP
  zero_at:=position(decode('00','hex') IN b);
  part:=to_jsonb(convert_from(CASE WHEN zero_at=0 THEN b ELSE substring(b FROM 1 FOR zero_at-1) END,'UTF8'))::text;
  result:=result||substring(part FROM 2 FOR length(part)-2);
  IF zero_at=0 THEN EXIT; END IF;
  result:=result||chr(92)||'u0000'; b:=substring(b FROM zero_at+1);
 END LOOP;
 RETURN result||'"';
END $$;
-- Narrow JCS for this closed ASCII-key/string/boolean/null/integer contract.
-- Not a general JSON number serializer. Raw base64 is decoded before hashing.
CREATE FUNCTION polygon.intent_jcs(p jsonb, raw_value boolean DEFAULT false) RETURNS text
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE result text; e record; first_item boolean:=true; typ text:=jsonb_typeof(p);
BEGIN
 IF raw_value THEN RETURN polygon.raw_json(p#>>'{}'); END IF;
 IF typ='object' THEN
  result:='{';
  FOR e IN SELECT key,value FROM jsonb_each(p) ORDER BY key COLLATE "C" LOOP
   IF e.key !~ '^[A-Za-z][A-Za-z0-9]*$' THEN RAISE EXCEPTION 'unsupported intent key'; END IF;
   IF NOT first_item THEN result:=result||','; END IF; first_item:=false;
   result:=result||to_jsonb(e.key)::text||':'||polygon.intent_jcs(e.value,e.key=ANY(ARRAY['rawBudget','rawFixedAmount','rawCopyPercent','rawMarketLimitPercent','rawDailyBuyLimitPercent']));
  END LOOP;
  RETURN result||'}';
 ELSIF typ='array' THEN
  result:='[';
  FOR e IN SELECT value FROM jsonb_array_elements(p) WITH ORDINALITY q(value,ordinality) ORDER BY ordinality LOOP
   IF NOT first_item THEN result:=result||','; END IF; first_item:=false;
   result:=result||polygon.intent_jcs(e.value);
  END LOOP;
  RETURN result||']';
 ELSIF typ IN ('null','boolean','string') THEN RETURN p::text;
 ELSIF typ='number' AND p::text ~ '^(0|[1-9][0-9]*)$' AND (p::text)::numeric<=9007199254740991 THEN RETURN p::text;
 ELSE RAISE EXCEPTION 'unsupported intent value'; END IF;
END $$;
CREATE FUNCTION polygon.command_hash(actor uuid, kind text, op text, target uuid, request jsonb, config jsonb DEFAULT 'null') RETURNS bytea
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT sha256(convert_to(polygon.intent_jcs(jsonb_build_object('environment','shadow-polygon-synthetic-v1',
  'actorRealm','user','actorId',actor,'commandType',kind,'operation',op,'targetDraftId',target,'request',request,'reviewConfiguration',config)),'UTF8'))
$$;
CREATE FUNCTION polygon.numeric_settings(form jsonb, policy polygon.paper_policy_versions) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE names text[]; vals numeric[]:=ARRAY[NULL::numeric,NULL,NULL,NULL]; errors jsonb[]:=ARRAY[NULL::jsonb,NULL,NULL,NULL];
 result_errors jsonb:='[]'; i integer; raw text; code text; params jsonb; lo numeric; hi numeric; step_n numeric;
 money_field boolean; maximum numeric; mode text:=form->>'selectedMode'; valid boolean;
BEGIN
 names:=ARRAY['rawBudget',CASE mode WHEN 'fixed' THEN 'rawFixedAmount' WHEN 'percent' THEN 'rawCopyPercent' ELSE NULL END,
 'rawMarketLimitPercent','rawDailyBuyLimitPercent'];
 FOR i IN 1..4 LOOP
  IF names[i] IS NULL THEN CONTINUE; END IF;
  raw:=polygon.numeric_text(form->>names[i]); code:=NULL; params:='{}'; money_field:=(i=1 OR (i=2 AND mode='fixed'));
  CASE i
   WHEN 1 THEN lo:=policy.budget_min; hi:=policy.budget_max; step_n:=policy.budget_step;
   WHEN 2 THEN IF mode='fixed' THEN lo:=policy.fixed_min; hi:=policy.fixed_max; step_n:=policy.fixed_step;
     ELSE lo:=policy.copy_min; hi:=policy.copy_max; step_n:=policy.copy_step; END IF;
   WHEN 3 THEN lo:=policy.market_min; hi:=policy.market_max; step_n:=policy.market_step;
   WHEN 4 THEN lo:=policy.daily_min; hi:=policy.daily_max; step_n:=policy.daily_step;
  END CASE;
  IF raw IS NULL OR raw='' THEN code:='REQUIRED';
  ELSIF raw !~ '^[0-9]+([.,][0-9]+)?$' THEN code:='INVALID_DECIMAL';
  ELSE
   vals[i]:=replace(raw,',','.')::numeric;
   IF vals[i]<lo OR vals[i]>hi THEN code:='OUT_OF_RANGE';
    params:=jsonb_build_object('min',polygon.field_value(lo,money_field),'max',polygon.field_value(hi,money_field),
     'unit',CASE WHEN money_field THEN 'virtual_USD' ELSE 'percentage_points' END);
   ELSIF mod(vals[i]-lo,step_n)<>0 THEN code:='INVALID_STEP';
    params:=jsonb_build_object('step',polygon.field_value(step_n,money_field),'origin',polygon.field_value(lo,money_field),
     'unit',CASE WHEN money_field THEN 'virtual_USD' ELSE 'percentage_points' END);
   END IF;
  END IF;
  IF code IS NOT NULL THEN errors[i]:=jsonb_build_object('field',names[i],'code',code,'params',params); vals[i]:=NULL; END IF;
 END LOOP;
 IF mode='fixed' AND vals[1] IS NOT NULL AND vals[2] IS NOT NULL AND vals[3] IS NOT NULL AND vals[4] IS NOT NULL THEN
  maximum:=floor(least(vals[1]*vals[3]/100,vals[1]*vals[4]/100));
  IF vals[2]>maximum THEN errors[2]:=jsonb_build_object('field','rawFixedAmount','code','FIXED_LIMIT_EXCEEDED',
   'params',jsonb_build_object('max',polygon.money(maximum),'unit','virtual_USD')); END IF;
 END IF;
 FOR i IN 1..4 LOOP IF errors[i] IS NOT NULL THEN result_errors:=result_errors||jsonb_build_array(errors[i]); END IF; END LOOP;
 valid:=(result_errors='[]'::jsonb AND mode IN ('fixed','percent')) IS TRUE;
 RETURN jsonb_build_object('fieldErrors',result_errors,'normalizationValid',valid,
 'budget',CASE WHEN valid THEN polygon.money(vals[1]) END,
 'fixedAmount',CASE WHEN valid AND mode='fixed' THEN polygon.money(vals[2]) END,
 'copyPercent',CASE WHEN valid AND mode='percent' THEN polygon.percent(vals[2]) END,
 'marketLimitPercent',CASE WHEN valid THEN polygon.percent(vals[3]) END,
 'dailyBuyLimitPercent',CASE WHEN valid THEN polygon.percent(vals[4]) END,
 'effectiveMarketLimit',CASE WHEN valid THEN polygon.money(vals[1]*vals[3]/100) END,
 'effectiveDailyBuyLimit',CASE WHEN valid THEN polygon.money(vals[1]*vals[4]/100) END);
END $$;
CREATE FUNCTION polygon.draft_form(d polygon.drafts) RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('locale',d.locale,'step',d.step,'entryContext',d.entry_context,'venueId',d.venue_id,
 'traderId',d.trader_id,'selectedMode',d.selected_mode,'rawBudget',polygon.raw_encoded(d.raw_budget),'rawFixedAmount',polygon.raw_encoded(d.raw_fixed_amount),
 'rawCopyPercent',polygon.raw_encoded(d.raw_copy_percent),'rawMarketLimitPercent',polygon.raw_encoded(d.raw_market_limit_percent),
 'rawDailyBuyLimitPercent',polygon.raw_encoded(d.raw_daily_buy_limit_percent),'proposedTimezone',d.proposed_timezone)
$$;
CREATE FUNCTION polygon.visible_trader(trader uuid, venue uuid, scope uuid) RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT EXISTS(SELECT 1 FROM polygon.traders t JOIN polygon.catalog_sources s ON s.id=t.source_id
 JOIN polygon.scope_sources ss ON ss.source_id=s.id WHERE t.id=trader AND t.venue_id=venue AND ss.scope_id=scope
 AND t.is_catalog_visible AND s.is_catalog_visible)
$$;
CREATE FUNCTION polygon.c04_shape(b jsonb, updating boolean) RETURNS boolean LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE names text[]:=ARRAY['requestSchemaVersion','clientCommandId','locale','step','entryContext','venueId','traderId','selectedMode',
 'rawBudget','rawFixedAmount','rawCopyPercent','rawMarketLimitPercent','rawDailyBuyLimitPercent','proposedTimezone']; k text;
BEGIN
 IF updating THEN names:=names||'expectedDraftVersion'::text; END IF;
 IF NOT polygon.exact_keys(b,names) THEN RETURN false; END IF;
 IF b->>'requestSchemaVersion' IS DISTINCT FROM 'v1' OR NOT polygon.uuid_text(b->>'clientCommandId')
  OR (b->>'locale' IN ('ru','en')) IS DISTINCT FROM true OR (b->>'step' IN ('select_trader','configure','review')) IS DISTINCT FROM true
 THEN RETURN false; END IF;
 FOREACH k IN ARRAY names LOOP
  IF jsonb_typeof(b->k) NOT IN ('string','null') THEN RETURN false; END IF;
 END LOOP;
 IF b->'entryContext'<>'null' AND (b->>'entryContext' IN ('catalog','trader_details','session_summary')) IS DISTINCT FROM true THEN RETURN false; END IF;
 IF b->'selectedMode'<>'null' AND (b->>'selectedMode' IN ('fixed','percent')) IS DISTINCT FROM true THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['venueId','traderId'] LOOP
  IF b->k<>'null' AND NOT polygon.uuid_text(b->>k) THEN RETURN false; END IF;
 END LOOP;
 IF b->'traderId'<>'null' AND b->'venueId'='null' THEN RETURN false; END IF;
 FOREACH k IN ARRAY ARRAY['rawBudget','rawFixedAmount','rawCopyPercent','rawMarketLimitPercent','rawDailyBuyLimitPercent'] LOOP
  BEGIN PERFORM polygon.raw_bytes(b->>k);
  EXCEPTION WHEN character_not_in_repertoire OR invalid_parameter_value OR raise_exception THEN RETURN false; END;
 END LOOP;
 IF updating AND NOT polygon.version_text(b->>'expectedDraftVersion') THEN RETURN false; END IF;
 -- The pinned backend timezone registry remains authoritative. PG validates that
 -- it is a supported named zone too; backend must not accept arbitrary offsets.
 IF b->'proposedTimezone'<>'null' AND NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=b->>'proposedTimezone') THEN RETURN false; END IF;
 RETURN true;
END $$;
CREATE FUNCTION polygon.reason(code text, capability text DEFAULT NULL) RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $$
 SELECT jsonb_build_object('code',code,'params',CASE WHEN code='CAPABILITY_UNAVAILABLE' THEN jsonb_build_object('capabilityReasonCode',capability) ELSE '{}'::jsonb END)
$$;
CREATE FUNCTION polygon.capability(trader uuid, control polygon.paper_controls) RETURNS text LANGUAGE plpgsql STABLE SET search_path=pg_catalog AS $$
DECLARE t polygon.traders; s polygon.catalog_sources;
BEGIN
 IF NOT control.enabled THEN RETURN 'PAPER_START_DISABLED'; END IF;
 SELECT * INTO t FROM polygon.traders WHERE id=trader;
 IF t.id IS NULL THEN RETURN NULL; END IF;
 SELECT * INTO s FROM polygon.catalog_sources WHERE id=t.source_id;
 IF NOT s.paper_start_enabled THEN RETURN 'CATALOG_SOURCE_DISABLED'; END IF;
 IF NOT t.paper_start_enabled THEN RETURN 'TRADER_START_DISABLED'; END IF;
 RETURN NULL;
END $$;
COMMIT;
