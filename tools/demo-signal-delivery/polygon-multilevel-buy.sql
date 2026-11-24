-- Multi-level estimates for the isolated queued BUY path.
BEGIN;
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '3s';

DO $gate$
BEGIN
    IF current_database() <> 'shadow_v00'
       OR NOT EXISTS (SELECT FROM demo_delivery.pilot_marker WHERE kind='isolated-public-market-pilot-v1')
       OR to_regprocedure('demo_delivery.polygon_waiting_open(uuid,jsonb)') IS NULL
    THEN RAISE EXCEPTION 'Expected the closed queued Polygon schema'; END IF;
END
$gate$;
GRANT SELECT ON demo_delivery.closed_polygon_source TO polygon_owner;
SET LOCAL ROLE polygon_owner;

CREATE FUNCTION polygon_buy.multilevel_plan(q jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $plan$
DECLARE
    est jsonb := q->'estimate';
    ev jsonb := est->'evidence';
    policy jsonb := ev->'policy';
    legs jsonb := est->'fills';
    ids jsonb := q->'fillIds';
    leg jsonb;
    count_legs integer;
    none jsonb := live_buy_core.q(0,1);
    one jsonb := live_buy_core.q(1,1);
    quantity jsonb := none;
    gross jsonb := none;
    fee jsonb := none;
    accrued jsonb := none;
    last_price jsonb := none;
    rate jsonb;
    step numeric;
    price jsonb;
    leg_quantity jsonb;
    notional jsonb;
    next_fee jsonb;
BEGIN
    IF jsonb_typeof(legs) IS DISTINCT FROM 'array' OR jsonb_typeof(ids) IS DISTINCT FROM 'array'
       OR policy->'demoMultiLevelBuy' IS DISTINCT FROM 'true'::jsonb
       OR policy->>'feeModel' IS DISTINCT FROM 'polymarket-v2-single-match'
       OR policy->>'feeRounding' IS DISTINCT FROM 'floor-5dp'
       OR ev->>'side' IS DISTINCT FROM 'BUY'
       OR (policy->>'feeRate' ~ '^(0|1)([.][0-9]{1,12})?$') IS DISTINCT FROM true
       OR (policy->>'quantityStep' ~ '^(0|1)([.][0-9]{1,12})?$') IS DISTINCT FROM true
       OR live_buy_core.positive(ev->'priceLimit') IS DISTINCT FROM true
    THEN RETURN NULL; END IF;
    count_legs := jsonb_array_length(legs);
    IF count_legs NOT BETWEEN 2 AND 128 OR jsonb_array_length(ids) <> count_legs
       OR ids->0 IS DISTINCT FROM q->'fillId'
       OR EXISTS(SELECT FROM jsonb_array_elements(ids) id WHERE NOT polygon_live_activity.uuid_value(id))
       OR (SELECT count(DISTINCT id) FROM jsonb_array_elements(ids) id) <> count_legs
    THEN RETURN NULL; END IF;
    rate := live_buy_core.q((policy->>'feeRate')::numeric*1000000000000,1000000000000);
    step := (policy->>'quantityStep')::numeric;
    IF step <= 0 OR live_buy_core.cmp(rate,none) <= 0 OR live_buy_core.cmp(rate,one)>0 THEN RETURN NULL; END IF;
    FOR leg IN SELECT value FROM jsonb_array_elements(legs) LOOP
        price := leg->'price';
        leg_quantity := leg->'quantity';
        IF live_buy_core.keys(leg,ARRAY['quantity','price','cashFee']) IS DISTINCT FROM true
           OR live_buy_core.positive(leg_quantity) IS DISTINCT FROM true
           OR live_buy_core.positive(price) IS DISTINCT FROM true
           OR live_buy_core.nonnegative(leg->'cashFee') IS DISTINCT FROM true
           OR live_buy_core.cmp(price,last_price)<=0 OR live_buy_core.cmp(price,one)>=0
           OR live_buy_core.cmp(price,ev->'priceLimit')>0
        THEN RETURN NULL; END IF;
        notional := live_buy_core.mulq(leg_quantity,price);
        accrued := live_buy_core.addq(accrued,live_buy_core.mulq(rate,
                   live_buy_core.mulq(notional,live_buy_core.subq(one,price))));
        next_fee := live_buy_core.q(div((accrued->>'n')::numeric*100000,(accrued->>'d')::numeric),100000);
        IF leg->'cashFee' IS DISTINCT FROM live_buy_core.subq(next_fee,fee) THEN RETURN NULL; END IF;
        fee := next_fee;
        last_price := price;
        quantity := live_buy_core.addq(quantity,leg_quantity);
        gross := live_buy_core.addq(gross,notional);
    END LOOP;
    IF ev->'quantity' IS DISTINCT FROM quantity OR ev->'gross' IS DISTINCT FROM gross
       OR ev->'cashFee' IS DISTINCT FROM fee
       OR mod((quantity->>'n')::numeric,(quantity->>'d')::numeric*step) <> 0
       OR mod((quantity->>'n')::numeric*1000000,(quantity->>'d')::numeric) <> 0
       OR mod((gross->>'n')::numeric*1000000,(gross->>'d')::numeric) <> 0
    THEN RETURN NULL; END IF;
    RETURN jsonb_build_object('quantity',quantity,'fee',fee,'priceCap',last_price,
                              'reserveNotional',live_buy_core.mulq(quantity,last_price));
END
$plan$;

CREATE FUNCTION polygon_buy.multilevel_fills(q jsonb, executed text)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog AS $fills$
    SELECT jsonb_agg(jsonb_build_object('fillId',q->'fillIds'->((n-1)::integer),'price',leg->'price',
       'quantityGross',leg->'quantity','quantityFee',live_buy_core.q(0,1),'cashFee',leg->'cashFee',
       'executedAt',executed) ORDER BY n)
    FROM jsonb_array_elements(q#>'{estimate,fills}') WITH ORDINALITY AS f(leg,n)
$fills$;

REVOKE ALL ON FUNCTION polygon_buy.multilevel_plan(jsonb),polygon_buy.multilevel_fills(jsonb,text)
    FROM PUBLIC,polygon_executor;

DO $issuer$
DECLARE
    definition text := pg_get_functiondef('polygon.personal_quote_issue_v1(jsonb)'::regprocedure);
    legacy text;
    start_marker text := 'AND jsonb_array_length(est->''fills'')=1 AND evidence->>''side''=''BUY''';
    end_marker text := ' AND length(book->>''evidenceRef'')>0';
    a integer;
    b integer;
BEGIN
    a:=strpos(definition,start_marker);
    b:=strpos(definition,end_marker);
    IF a=0 OR b<=a OR cardinality(string_to_array(definition,'req jsonb; k text;'))<>2
       OR cardinality(string_to_array(definition,'now_at:=clock_timestamp();'))<>2
       OR cardinality(string_to_array(definition,'''feeCashBound'',f->''cashFee'''))<>2
    THEN RAISE EXCEPTION 'Unexpected personal quote issuer'; END IF;
    legacy:=substr(definition,a,b-a);
    definition:=replace(definition,legacy,
      'AND (CASE WHEN q ? ''fillIds'' THEN plan IS NOT NULL
           AND EXISTS (SELECT FROM demo_delivery.closed_polygon_source s WHERE s.session_id=sid
                       AND s.run_id=a.run_id AND s.wallet=a.owner_address AND s.cutoff_at>now_at)
           AND live_buy_core.cmp(live_buy_core.addq(plan->''reserveNotional'',plan->''fee''),
                                live_buy_core.q(st.fixed_n,st.fixed_d))<=0
           ELSE TRUE ' || legacy || ' END)');
    definition:=replace(definition,'req jsonb; k text;','req jsonb; k text; plan jsonb;');
    definition:=replace(definition,'now_at:=clock_timestamp();',
      'now_at:=clock_timestamp(); IF q ? ''fillIds'' THEN plan:=polygon_buy.multilevel_plan(q); END IF;');
    definition:=replace(definition,'''desiredNotional'',evidence->''gross''',
      '''desiredNotional'',coalesce(plan->''reserveNotional'',evidence->''gross'')');
    definition:=replace(definition,'''fullQuantity'',f->''quantity''',
      '''fullQuantity'',coalesce(plan->''quantity'',f->''quantity'')');
    definition:=replace(definition,'''priceCap'',f->''price''',
      '''priceCap'',coalesce(plan->''priceCap'',f->''price'')');
    EXECUTE replace(definition,'''feeCashBound'',f->''cashFee''',
      '''feeCashBound'',coalesce(plan->''fee'',f->''cashFee'')');
END
$issuer$;

DO $apply$
DECLARE
    definition text := pg_get_functiondef('polygon.personal_quote_apply_v1(uuid,text)'::regprocedure);
    marker text := 'INSERT INTO polygon_buy.admissions VALUES(v.settle_id';
BEGIN
    IF cardinality(string_to_array(definition,marker)) <> 2
       OR position('polygon_waiting_open' in definition)=0
    THEN RAISE EXCEPTION 'Expected personal queued quote application'; END IF;
    EXECUTE replace(definition,marker,
      'IF q ? ''fillIds'' THEN
         req:=jsonb_set(req,''{fills}'',polygon_buy.multilevel_fills(q,captured));
       END IF;
       ' || marker);
END
$apply$;

CREATE OR REPLACE FUNCTION polygon_buy.admitted_notional(sid uuid,oid uuid) RETURNS jsonb
LANGUAGE sql STABLE SET search_path=pg_catalog AS $notional$
    SELECT coalesce((SELECT CASE WHEN v.quote ? 'fillIds'
              THEN polygon_buy.multilevel_plan(v.quote)->'reserveNotional'
              ELSE v.quote#>'{estimate,evidence,gross}' END
        FROM polygon_buy.verified_quotes v
        JOIN polygon_buy.admissions a ON (a.id,a.session_id)=(v.reserve_id,v.session_id)
        WHERE v.session_id=sid AND a.request->>'observationId'=oid::text),polygon_buy.sized_notional(sid,oid))
$notional$;

DO $valid$
DECLARE
    definition text := pg_get_functiondef('polygon_buy.command_valid(uuid)'::regprocedure);
    marker text := 'OR t<a.issued_at OR t>=a.expires_at';
BEGIN
    IF cardinality(string_to_array(definition,marker)) <> 2
    THEN RAISE EXCEPTION 'Unexpected Polygon command validator'; END IF;
    EXECUTE replace(definition,marker,
      'OR (c.kind=''settle'' AND EXISTS (
          SELECT FROM polygon_buy.verified_quotes quoted
          WHERE quoted.session_id=sid AND quoted.settle_id=a.id AND quoted.quote ? ''fillIds''
            AND r.request->''fills'' IS DISTINCT FROM polygon_buy.multilevel_fills(
                quoted.quote,r.request#>>''{fills,0,executedAt}'')))
       ' || marker);
END
$valid$;
COMMIT;
