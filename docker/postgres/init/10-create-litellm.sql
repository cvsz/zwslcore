\getenv litellm_password LITELLM_DB_PASSWORD
SELECT format('CREATE ROLE litellm LOGIN PASSWORD %L', :'litellm_password') \gexec
CREATE DATABASE litellm OWNER litellm;
