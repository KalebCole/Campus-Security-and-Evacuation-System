-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create employees table with additional columns
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    rfid_tag TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    face_embedding vector(512),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE,
    last_verified TIMESTAMPTZ,
    verification_count INTEGER DEFAULT 0,
    photo_url TEXT
);

CREATE INDEX IF NOT EXISTS employees_face_embedding_idx 
    ON employees USING ivfflat (face_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS employees_rfid_tag_idx ON employees(rfid_tag);

-- Create access_logs table
CREATE TABLE IF NOT EXISTS access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID REFERENCES employees(id),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    access_granted BOOLEAN NOT NULL,
    verification_method TEXT NOT NULL,
    session_id TEXT NOT NULL,
    verification_confidence FLOAT,
    verification_image_path TEXT
);

CREATE INDEX IF NOT EXISTS access_logs_timestamp_idx ON access_logs(timestamp);
CREATE INDEX IF NOT EXISTS access_logs_employee_id_idx ON access_logs(employee_id);

-- Create verification_images table
CREATE TABLE IF NOT EXISTS verification_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL,
    image_data BYTEA NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    embedding vector(512),
    confidence FLOAT,
    matched_employee_id UUID REFERENCES employees(id),
    device_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verification_images_session ON verification_images(session_id);
CREATE INDEX IF NOT EXISTS idx_verification_images_timestamp ON verification_images(timestamp);

-- Create cleanup function for old verification images
CREATE OR REPLACE FUNCTION cleanup_old_verification_images() RETURNS void AS $$
BEGIN
    DELETE FROM verification_images 
    WHERE timestamp < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;
