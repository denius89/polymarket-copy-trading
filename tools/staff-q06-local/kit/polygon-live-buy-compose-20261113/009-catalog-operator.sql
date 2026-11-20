-- Execute as the trusted database operator AFTER 010 creates the private schema.
-- PGlite/native catalog ACL differences must not remove the database identity check.
-- The owner receives only this fixed, argument-free read, not catalog mutation.
CREATE FUNCTION polygon_buy.database_oid() RETURNS oid LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT oid FROM pg_catalog.pg_database WHERE datname=current_database()
$$;
REVOKE ALL ON FUNCTION polygon_buy.database_oid() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION polygon_buy.database_oid() TO polygon_owner;
