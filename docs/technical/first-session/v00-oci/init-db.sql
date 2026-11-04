\set ON_ERROR_STOP on
\getenv auth_password V00_AUTH_PASSWORD
CREATE ROLE v00_auth LOGIN PASSWORD :'auth_password';
CREATE SCHEMA auth AUTHORIZATION v00_auth;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER ROLE v00_auth IN DATABASE shadow_v00 SET search_path TO auth, public;
