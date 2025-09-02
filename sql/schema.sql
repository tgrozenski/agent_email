-- PostgreSQL Schema for the User and Document Tables
DROP TABLE IF EXISTS document CASCADE;
DROP TABLE IF EXISTS "user" CASCADE;

-- Create the "user" table
CREATE TABLE "user" (
    user_id SERIAL PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    history_id VARCHAR(255) UNIQUE,
    -- Store the ENCRYPTED refresh token, never plain text.
    encrypted_refresh_token TEXT
);

CREATE TABLE document (
    document_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    content TEXT,
    embedding_vector VECTOR(1536),

    -- This sets up the one-to-many relationship between users and documents
    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES "user"(user_id)
        ON DELETE CASCADE
);

-- Create an index on the user_id in the document table for faster lookups of documents by user.
CREATE INDEX IF NOT EXISTS idx_document_user_id ON document(user_id);