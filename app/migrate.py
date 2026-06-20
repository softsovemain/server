import logging

from sqlalchemy import text

from app.core.database import engine

logger = logging.getLogger(__name__)

ENUM_VALUES: dict[str, list[str]] = {
    "servertype": ["frontend", "backend", "other"],
    "serverprovider": ["vercel", "hostinger", "aws", "digitalocean", "cloudflare", "vps", "other"],
    "serverstatus": ["active", "expired", "maintenance"],
}


def _add_enum_values(conn, type_name: str, values: list[str]) -> None:
    for value in values:
        conn.execute(
            text(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = '{type_name}') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_enum e
                            JOIN pg_type t ON e.enumtypid = t.oid
                            WHERE t.typname = '{type_name}' AND e.enumlabel = '{value}'
                        ) THEN
                            ALTER TYPE {type_name} ADD VALUE '{value}';
                        END IF;
                    END IF;
                END $$;
                """
            )
        )


def run_migrations() -> None:
    statements = [
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS server_os VARCHAR(255)",
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS server_ip VARCHAR(100)",
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS panel_url VARCHAR(500)",
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS username_encrypted TEXT",
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS password_encrypted TEXT",
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS ssh_key_encrypted TEXT",
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS renewal_cost NUMERIC(10, 2)",
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS tags VARCHAR[]",
        """
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
        """,
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS domain_name VARCHAR(255)",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS frontend_server_id UUID REFERENCES servers(id) ON DELETE SET NULL",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS backend_server_id UUID REFERENCES servers(id) ON DELETE SET NULL",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS backend_api_url VARCHAR(500)",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS database_name VARCHAR(255)",
        """
        UPDATE projects SET database_name = d.name
        FROM databases d
        WHERE projects.database_id = d.id AND projects.database_name IS NULL
        """,
        "UPDATE servers SET server_type = 'frontend' WHERE server_type::text IN ('hosting', 'cdn', 'email', 'domain_registrar')",
        "UPDATE servers SET server_type = 'backend' WHERE server_type::text = 'database'",
        "UPDATE projects SET domain_name = COALESCE(domain_name, frontend_url, main_url) WHERE domain_name IS NULL",
        "UPDATE projects SET frontend_server_id = server_id WHERE frontend_server_id IS NULL AND server_id IS NOT NULL",
        "UPDATE projects SET backend_api_url = backend_url WHERE backend_api_url IS NULL AND backend_url IS NOT NULL",
        """
        CREATE TABLE IF NOT EXISTS project_commands (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            label VARCHAR(255) NOT NULL,
            command TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
    ]

    with engine.begin() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception as exc:
                logger.warning("Migration skipped/failed: %s", exc)

        for type_name, values in ENUM_VALUES.items():
            try:
                _add_enum_values(conn, type_name, values)
            except Exception as exc:
                logger.warning("Enum migration failed for %s: %s", type_name, exc)
