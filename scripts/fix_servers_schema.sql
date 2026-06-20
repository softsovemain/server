-- Run on production:
-- PGPASSWORD='...' psql -h 127.0.0.1 -U server -d server -f scripts/fix_servers_schema.sql

-- 1) Inspect
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

-- 3) CRITICAL: add enum values OUTSIDE transactions (DO blocks fail on many PG versions)
ALTER TYPE servertype ADD VALUE IF NOT EXISTS 'frontend';
ALTER TYPE servertype ADD VALUE IF NOT EXISTS 'backend';
ALTER TYPE servertype ADD VALUE IF NOT EXISTS 'other';

-- 4) Verify enum values were added
SELECT t.typname, e.enumlabel
FROM pg_enum e
JOIN pg_type t ON e.enumtypid = t.oid
WHERE t.typname = 'servertype'
ORDER BY e.enumsortorder;

-- 5) Migrate legacy credential columns if they exist
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

-- 6) Map old server_type values to new ones (only after frontend/backend exist)
UPDATE servers SET server_type = 'frontend'
WHERE server_type::text IN ('hosting', 'cdn', 'email', 'domain_registrar');

UPDATE servers SET server_type = 'backend'
WHERE server_type::text = 'database';

CREATE TABLE IF NOT EXISTS user_server_access (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, server_id)
);
