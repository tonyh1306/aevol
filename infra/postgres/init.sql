-- Enable extensions for text search and UUID generation
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Ensure the database is properly configured
ALTER DATABASE evaldb SET timezone TO 'UTC';
