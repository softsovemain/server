-- Run on production to fix server create errors:
-- PGPASSWORD='...' psql -h 127.0.0.1 -U server -d server -f scripts/fix_servers_schema.sql

-- 1) Inspect current schema (check output)
\d servers

SELECT t.typname, e.enumlabel
FROM pg_enum e
JOIN pg_type t ON e.enumtypid = t.oid
WHERE t.typname IN ('servertype', 'serverprovider', 'serverstatus')
ORDER BY t.typname, e.enumsortorder;

-- 2) Missing columns
ALTER TABLE servers ADD COLUMN IF NOT EXISTS server_os VARCHAR(255);
ALTER TABLE servers ADD COLUMN IF NOT EXISTS server_ip VARCHAR(100);
ALTER TABLE servers ADD COLUMN IF NOT EXISTS panel_url VARCHAR(500);
ALTER TABLE servers ADD COLUMN IF NOT EXISTS username_encrypted TEXT;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS password_encrypted TEXT;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS ssh_key_encrypted TEXT;
ALTER TABLE servers ADD COLUMN IF NOT EXISTS renewal_cost NUMERIC(10, 2);
ALTER TABLE servers ADD COLUMN IF NOT EXISTS tags VARCHAR[];

-- 3) Migrate legacy plain-text credential columns if they exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'servers' AND column_name = 'username'
    ) THEN
        UPDATE servers
        SET username_encrypted = username
        WHERE username_encrypted IS NULL AND username IS NOT NULL AND username <> '';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'servers' AND column_name = 'password'
    ) THEN
        UPDATE servers
        SET password_encrypted = password
        WHERE password_encrypted IS NULL AND password IS NOT NULL AND password <> '';
    END IF;
END $$;

-- 4) Ensure server_type enum values exist (required for frontend/backend/other)
DO $$
DECLARE
    val TEXT;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'servertype') THEN
        FOREACH val IN ARRAY ARRAY['frontend', 'backend', 'other'] LOOP
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'servertype' AND e.enumlabel = val
            ) THEN
                EXECUTE format('ALTER TYPE servertype ADD VALUE %L', val);
            END IF;
        END LOOP;
    END IF;
END $$;

-- 5) Ensure provider enum has "other" (default on insert)
DO $$
DECLARE
    val TEXT;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'serverprovider') THEN
        FOREACH val IN ARRAY ARRAY['vercel', 'hostinger', 'aws', 'digitalocean', 'cloudflare', 'vps', 'other'] LOOP
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'serverprovider' AND e.enumlabel = val
            ) THEN
                EXECUTE format('ALTER TYPE serverprovider ADD VALUE %L', val);
            END IF;
        END LOOP;
    END IF;
END $$;

-- 6) Ensure status enum values exist
DO $$
DECLARE
    val TEXT;
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'serverstatus') THEN
        FOREACH val IN ARRAY ARRAY['active', 'expired', 'maintenance'] LOOP
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum e
                JOIN pg_type t ON e.enumtypid = t.oid
                WHERE t.typname = 'serverstatus' AND e.enumlabel = val
            ) THEN
                EXECUTE format('ALTER TYPE serverstatus ADD VALUE %L', val);
            END IF;
        END LOOP;
    END IF;
END $$;

-- 7) Map old server_type values to new ones
UPDATE servers SET server_type = 'frontend'
WHERE server_type::text IN ('hosting', 'cdn', 'email', 'domain_registrar');

UPDATE servers SET server_type = 'backend'
WHERE server_type::text = 'database';
