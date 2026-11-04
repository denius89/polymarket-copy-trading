\set ON_ERROR_STOP on
-- Explicit isolated dependency. Actual pgcrypto 1.3 availability was attested.
-- Refuse an existing extension rather than silently relocating it.
BEGIN;
DO $$ BEGIN
  IF EXISTS(SELECT 1 FROM pg_extension WHERE extname='pgcrypto') THEN
    RAISE EXCEPTION 'pgcrypto already installed; inspect isolated dependency';
  END IF;
END $$;
CREATE SCHEMA v00_upstream_crypto;
REVOKE ALL ON SCHEMA v00_upstream_crypto FROM PUBLIC;
CREATE EXTENSION pgcrypto WITH SCHEMA v00_upstream_crypto VERSION '1.3';
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA v00_upstream_crypto FROM PUBLIC;
GRANT USAGE ON SCHEMA v00_upstream_crypto TO v00_upstream_owner;
GRANT EXECUTE ON FUNCTION v00_upstream_crypto.hmac(bytea,bytea,text) TO v00_upstream_owner;
SET LOCAL ROLE v00_upstream_owner;
CREATE FUNCTION v00_upstream.base32(s text) RETURNS bytea LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE alphabet constant text:='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'; acc integer:=0; bits integer:=0; i integer; out bytea:=''::bytea;
BEGIN
  IF s IS NULL OR s !~ '^[A-Z2-7]+$' OR length(s)>128 OR length(s)%8 NOT IN (0,2,4,5,7) THEN RAISE EXCEPTION 'unsupported factor encoding'; END IF;
  FOR i IN 1..length(s) LOOP
    acc:=(acc<<5) | (strpos(alphabet,substr(s,i,1))-1); bits:=bits+5;
    IF bits>=8 THEN
      bits:=bits-8; out:=out || set_byte(decode('00','hex'),0,(acc>>bits)&255); acc:=acc & ((1<<bits)-1);
    END IF;
  END LOOP;
  IF acc<>0 OR octet_length(out)=0 THEN RAISE EXCEPTION 'unsupported factor encoding'; END IF;
  RETURN out;
END $$;
CREATE FUNCTION v00_upstream.hotp(seed bytea, step bigint) RETURNS text LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE h bytea; off integer; n bigint;
BEGIN
  IF seed IS NULL OR step IS NULL OR step<0 THEN RAISE EXCEPTION 'invalid totp input'; END IF;
  h:=v00_upstream_crypto.hmac(int8send(step),seed,'sha1'); off:=get_byte(h,19)&15;
  n:=((get_byte(h,off)&127)::bigint<<24) | (get_byte(h,off+1)::bigint<<16) | (get_byte(h,off+2)::bigint<<8) | get_byte(h,off+3)::bigint;
  RETURN lpad((n%1000000)::text,6,'0');
END $$;
CREATE FUNCTION v00_upstream.matches(seed_text text, code text, now_at timestamptz) RETURNS bigint[] LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog AS $$
DECLARE seed bytea; current_step bigint; step bigint; found bigint[]:='{}';
BEGIN
  IF code IS NULL OR code !~ '^[0-9]{6}$' OR now_at IS NULL OR NOT isfinite(now_at) OR now_at<timestamptz '1970-01-01 00:00:00+00' THEN
    RAISE EXCEPTION 'invalid totp input';
  END IF;
  seed:=v00_upstream.base32(seed_text); current_step:=floor(extract(epoch FROM now_at)/30)::bigint;
  FOR step IN SELECT generate_series(greatest(0,current_step-1),current_step+1) LOOP
    IF v00_upstream.hotp(seed,step)=code THEN found:=array_append(found,step); END IF;
  END LOOP;
  RETURN found;
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA v00_upstream FROM PUBLIC;
COMMIT;
