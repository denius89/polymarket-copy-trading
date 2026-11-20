-- Included inside 001 transaction as polygon_owner. Not a standalone installer.
CREATE OR REPLACE FUNCTION polygon.real_trader_resolve(p jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE a jsonb; cfg polygon_live.public_source; src polygon.catalog_sources; tr polygon.traders;
 rev polygon.trader_revisions; ctl polygon.paper_controls; venue polygon.venues;
 account text; read_scope jsonb; lookup jsonb; card jsonb; admission jsonb;
BEGIN
 IF polygon.exact_keys(p,ARRAY['auth','venue_code','external_trader_id']) IS DISTINCT FROM true
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 IF jsonb_typeof(p->'venue_code') IS DISTINCT FROM 'string' OR p->>'venue_code' NOT IN ('polymarket','limitless')
  OR jsonb_typeof(p->'external_trader_id') IS DISTINCT FROM 'string'
  OR p->>'external_trader_id' !~ '^0x[0-9a-fA-F]{40}$'
 THEN RETURN polygon.err('INVALID_REQUEST',400); END IF;
 a:=polygon.guard(p->'auth');
 IF a IS NULL OR jsonb_typeof(a) IS DISTINCT FROM 'object' OR jsonb_typeof(a->'http') IS DISTINCT FROM 'number'
 THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 IF a->>'http'<>'200' THEN RETURN a; END IF;
 SELECT * INTO cfg FROM polygon_live.public_source WHERE singleton;
 IF cfg.singleton IS NULL OR cfg.database_name<>current_database() OR cfg.purpose<>'empty_session_only'
 THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 IF NOT EXISTS(SELECT FROM polygon_live.admissions WHERE user_id=(a->>'user_id')::uuid AND source_id=cfg.source_id) THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 -- This profile intentionally admits only one Polymarket identity. No Limitless fallback.
 IF p->>'venue_code'<>'polymarket' THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 SELECT * INTO venue FROM polygon.venues WHERE id=cfg.venue_id;
 SELECT * INTO src FROM polygon.catalog_sources WHERE id=cfg.source_id;
 SELECT * INTO tr FROM polygon.traders WHERE id=cfg.trader_id;
 SELECT * INTO rev FROM polygon.trader_revisions WHERE id=cfg.revision_id;
 SELECT * INTO ctl FROM polygon.paper_controls WHERE singleton;
 IF venue.id IS NULL OR venue.code<>'polymarket' OR src.id IS NULL OR tr.id IS NULL OR rev.id IS NULL OR ctl.id IS NULL
  OR src.venue_id<>venue.id OR src.data_origin<>'public_api' OR src.version<>1
  OR tr.source_id<>src.id OR tr.venue_id<>venue.id OR tr.current_revision_id<>rev.id OR tr.control_version<>1
  OR tr.external_trader_id<>'0x1111111111111111111111111111111111111111'
  OR rev.trader_id<>tr.id OR rev.source_id<>src.id OR rev.venue_id<>venue.id OR rev.revision<>1
  OR rev.catalog_version_at_creation<>1
 THEN RETURN polygon.err('RECORD_UNAVAILABLE'); END IF;
 IF NOT ctl.enabled OR NOT src.paper_start_enabled OR NOT tr.paper_start_enabled THEN RETURN polygon.err('SERVICE_UNAVAILABLE'); END IF;
 IF NOT polygon.visible_trader(tr.id,venue.id,(a->>'scope_id')::uuid)
 THEN RETURN polygon.err('RESOURCE_NOT_FOUND',404); END IF;
 account:=lower(p->>'external_trader_id');
 read_scope:=jsonb_build_object('venueCode',venue.code,'venueId',venue.id,'canonicalSourceId',src.id);
 lookup:=jsonb_build_object('venueCode',venue.code,'externalTraderId',account,'matches','[]'::jsonb);
 IF account<>tr.external_trader_id THEN
  RETURN jsonb_build_object('http',200,'read_scope',read_scope,'lookup',lookup);
 END IF;
 card:=jsonb_build_object('traderId',tr.id,'venueId',venue.id,'catalogSourceId',src.id,
  'venueCode',venue.code,'externalTraderId',tr.external_trader_id,'displayName',rev.display_name,
  'traderRevisionId',rev.id,'traderRevision',rev.revision::text,'dataOrigin',src.data_origin,
  'sourceRef',rev.source_ref,'observedAt',v00_session.utc(rev.observed_at),'revisionCreatedAt',v00_session.utc(rev.created_at),
  'catalogVersionAtCreation',rev.catalog_version_at_creation::text,'catalogVersion',src.version::text,
  'traderControlVersion',tr.control_version::text,'paperControlVersion',ctl.version::text,
  'startAvailability',jsonb_build_object('available',true,'capabilityReasonCode',NULL));
 admission:=jsonb_build_object('state',cfg.purpose,'admissionId',cfg.admission_id,'venueId',venue.id,
  'catalogSourceId',src.id,'traderId',tr.id,'traderRevisionId',rev.id,'catalogVersion',src.version::text,
  'traderControlVersion',tr.control_version::text,'paperControlVersion',ctl.version::text,
  'sourceBindingVersion',cfg.source_binding_version::text,'adapterVersion',cfg.adapter_version,'policyVersion',cfg.policy_version);
 RETURN jsonb_build_object('http',200,'read_scope',read_scope,'lookup',lookup||
  jsonb_build_object('matches',jsonb_build_array(jsonb_build_object('trader',card,'admission',admission))));
END $$;
REVOKE ALL ON FUNCTION polygon.real_trader_resolve(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION polygon.real_trader_resolve(jsonb) TO polygon_executor;
