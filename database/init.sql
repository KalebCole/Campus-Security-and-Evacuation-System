-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create employees table with updated photo_url
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
    photo_url TEXT -- Stores the URL from Supabase Storage
);

CREATE INDEX IF NOT EXISTS employees_face_embedding_idx 
    ON employees USING ivfflat (face_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS employees_rfid_tag_idx ON employees(rfid_tag);

-- Create access_logs table (removing verification_image_path)
CREATE TABLE IF NOT EXISTS access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID REFERENCES employees(id),
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    access_granted BOOLEAN NOT NULL,
    verification_method TEXT NOT NULL,
    session_id TEXT NOT NULL UNIQUE,
    verification_confidence FLOAT,
    -- verification_image_path TEXT, -- REMOVED
    review_status VARCHAR(20) DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS access_logs_timestamp_idx ON access_logs(timestamp);
CREATE INDEX IF NOT EXISTS access_logs_employee_id_idx ON access_logs(employee_id);

-- Create verification_images table (removing image_data, adding storage_url)
CREATE TABLE IF NOT EXISTS verification_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL UNIQUE,
    -- image_data BYTEA NOT NULL, -- REMOVED
    storage_url TEXT NOT NULL, -- ADDED: URL from Supabase Storage
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    embedding vector(512),
    confidence FLOAT,
    matched_employee_id UUID REFERENCES employees(id),
    device_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verification_images_timestamp ON verification_images(timestamp);

-- Create cleanup function for old verification images
CREATE OR REPLACE FUNCTION cleanup_old_verification_images() RETURNS void AS $$
BEGIN
    DELETE FROM verification_images 
    WHERE timestamp < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- Notification History Table
CREATE TABLE notification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT, -- Can be NULL if notification is not session-related
    user_id UUID, -- Can be NULL if notification is not user-related (matches employees.id)
    message TEXT,
    image_url TEXT,
    additional_data JSONB, -- Store extra context as JSON
    status VARCHAR(20) NOT NULL, -- e.g., 'Sent', 'Failed', 'Logged'
    created_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES employees (id) ON DELETE SET NULL -- Optional: Link to employee
);

CREATE INDEX IF NOT EXISTS idx_notification_history_timestamp ON notification_history (timestamp DESC);

-- Clean up existing data
TRUNCATE TABLE access_logs CASCADE;
TRUNCATE TABLE verification_images CASCADE;
TRUNCATE TABLE notification_history CASCADE;

-- Reset sequences
ALTER SEQUENCE IF EXISTS access_logs_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS verification_images_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS notification_history_id_seq RESTART WITH 1;
