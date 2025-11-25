"""Initial schema migration

Revision ID: 0001
Revises:
Create Date: 2024-12-19

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""

    # Enable PostgreSQL extensions for search functionality
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Create the users table for authentication
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            google_id TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )

    # Create the conversations table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            import_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            content JSONB NOT NULL,
            is_locked BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            summary TEXT,
            imported_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            search_vector tsvector
        )
        """
    )

    # Create the conversation_summary table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_summary (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        """
    )

    # Create the project_drafts table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_drafts (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            active_version_id INTEGER,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT
        )
        """
    )

    # Create the project_draft_versions table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_draft_versions (
            id SERIAL PRIMARY KEY,
            project_draft_id INTEGER NOT NULL REFERENCES project_drafts(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            is_manual_edit BOOLEAN NOT NULL DEFAULT FALSE,
            version_number INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            search_vector tsvector
        )
        """
    )

    # Create the llm_prompts table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_prompts (
            id SERIAL PRIMARY KEY,
            prompt_type TEXT NOT NULL,
            system_prompt TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT
        )
        """
    )

    # Create unique constraint on active prompts
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS unique_active_prompt
        ON llm_prompts (prompt_type)
        WHERE is_active = TRUE
        """
    )

    # Create the chat_messages table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            project_draft_id INTEGER NOT NULL REFERENCES project_drafts(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            sequence_number INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            sent_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            search_vector tsvector
        )
        """
    )

    # Create unique constraint on sequence numbers within a project draft
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS unique_sequence_per_project
        ON chat_messages (project_draft_id, sequence_number)
        """
    )

    # Create the projects table for Linear integration
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            linear_project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            linear_url TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT
        )
        """
    )

    # Create the default_llm_parameters table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS default_llm_parameters (
            id SERIAL PRIMARY KEY,
            prompt_type TEXT NOT NULL UNIQUE,
            llm_provider TEXT NOT NULL,
            llm_model TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT
        )
        """
    )

    # Create the file_attachments table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS file_attachments (
            id SERIAL PRIMARY KEY,
            chat_message_id INTEGER REFERENCES chat_messages(id) ON DELETE CASCADE,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_type TEXT NOT NULL,
            s3_key TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            uploaded_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT
        )
        """
    )

    # Create index for conversation_id to optimize joins
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_file_attachments_conversation_id
        ON file_attachments(conversation_id)
        """
    )

    # Create index for file_type to optimize image/pdf queries
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_file_attachments_file_type
        ON file_attachments(file_type)
        """
    )

    # Create the user_sessions table for session management
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )

    # Create index for session token lookups
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_sessions_token
        ON user_sessions(session_token)
        """
    )

    # Create index for session expiration cleanup
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at
        ON user_sessions(expires_at)
        """
    )

    # Create the service_keys table for service-to-service authentication
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS service_keys (
            id SERIAL PRIMARY KEY,
            service_name TEXT NOT NULL UNIQUE,
            api_key_hash TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            last_used_at TIMESTAMP WITH TIME ZONE
        )
        """
    )

    # Create index for service key hash lookups
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_service_keys_hash
        ON service_keys(api_key_hash)
        """
    )

    # Create search indexes for full-text search functionality
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_search
        ON conversations USING GIN(search_vector)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_search
        ON chat_messages USING GIN(search_vector)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_project_draft_versions_search
        ON project_draft_versions USING GIN(search_vector)
        """
    )

    # Create trigram indexes for fuzzy title matching
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_title_trgm
        ON conversations USING GIN(title gin_trgm_ops)
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_project_draft_versions_title_trgm
        ON project_draft_versions USING GIN(title gin_trgm_ops)
        """
    )

    # Create search vector update functions and triggers
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_conversation_search_vector()
        RETURNS TRIGGER AS $$
        DECLARE
            content_text TEXT := '';
            msg_record RECORD;
        BEGIN
            -- Extract text content from JSONB messages
            FOR msg_record IN
                SELECT (msg_item->>'content')::text as content
                FROM jsonb_array_elements(NEW.content) AS msg_item
                WHERE msg_item->>'content' IS NOT NULL
            LOOP
                content_text := content_text || ' ' || COALESCE(msg_record.content, '');
            END LOOP;

            -- Create search vector with weighted content
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.summary, '')), 'B') ||
                setweight(to_tsvector('english', content_text), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_chat_message_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Create search vector from message content
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_project_draft_version_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Create search vector with weighted title and description
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create triggers to automatically update search vectors
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.triggers
                WHERE trigger_name = 'conversations_search_update'
                AND event_object_table = 'conversations'
            ) THEN
                CREATE TRIGGER conversations_search_update
                    BEFORE INSERT OR UPDATE ON conversations
                    FOR EACH ROW EXECUTE FUNCTION update_conversation_search_vector();
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.triggers
                WHERE trigger_name = 'chat_messages_search_update'
                AND event_object_table = 'chat_messages'
            ) THEN
                CREATE TRIGGER chat_messages_search_update
                    BEFORE INSERT OR UPDATE ON chat_messages
                    FOR EACH ROW EXECUTE FUNCTION update_chat_message_search_vector();
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.triggers
                WHERE trigger_name = 'project_draft_versions_search_update'
                AND event_object_table = 'project_draft_versions'
            ) THEN
                CREATE TRIGGER project_draft_versions_search_update
                    BEFORE INSERT OR UPDATE ON project_draft_versions
                    FOR EACH ROW EXECUTE FUNCTION update_project_draft_version_search_vector();
            END IF;
        END $$;
        """
    )

    # Add foreign key constraint for active_version_id after project_draft_versions table exists
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'project_drafts_active_version_fk'
            ) THEN
                ALTER TABLE project_drafts
                ADD CONSTRAINT project_drafts_active_version_fk
                FOREIGN KEY (active_version_id) REFERENCES project_draft_versions (id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    pass
