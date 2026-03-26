-- Supabase Schema for Healthcare Copilot

-- Create User Table
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(256) NOT NULL
);

-- Create Prescription Table
CREATE TABLE IF NOT EXISTS "prescription" (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image_base64 TEXT,
    prescription_text TEXT,
    extracted_data TEXT NOT NULL,
    CONSTRAINT fk_user
        FOREIGN KEY(user_id) 
        REFERENCES "user"(id)
        ON DELETE SET NULL
);
