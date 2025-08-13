-- PostgreSQL Schema for the User and Document Tables
DROP TABLE IF EXISTS document CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

-- Create the "user" table
CREATE TABLE "user" (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    -- Store the ENCRYPTED refresh token, never plain text.
    encrypted_refresh_token TEXT
);

-- Create the "document" table
CREATE TABLE document (
    document_id SERIAL PRIMARY KEY,
    -- Foreign key that links to the user table
    user_id INTEGER NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    content TEXT,

    -- This sets up the one-to-many relationship between users and documents
    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES "user"(user_id)
        -- If a user is deleted, all their documents are deleted as well.
        ON DELETE CASCADE
);

-- Create an index on the user_id in the document table for faster lookups of documents by user.
CREATE INDEX IF NOT EXISTS idx_document_user_id ON document(user_id);

-- Grant basic privileges to a hypothetical app user.
-- Replace 'your_app_user' with the actual database user your application will use.
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
