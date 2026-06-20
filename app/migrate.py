from sqlalchemy import text

from app.core.database import engine


def run_migrations() -> None:
    statements = [
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS server_os VARCHAR(255)",
        "ALTER TABLE servers ADD COLUMN IF NOT EXISTS server_ip VARCHAR(100)",
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
        """
        DO $$ BEGIN
            ALTER TYPE servertype ADD VALUE IF NOT EXISTS 'frontend';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """,
        """
        DO $$ BEGIN
            ALTER TYPE servertype ADD VALUE IF NOT EXISTS 'backend';
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
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
            except Exception:
                pass
