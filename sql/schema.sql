-- PostgreSQL Schema for the User and Document Tables
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Enable the vector extension for handling embedding vectors
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    history_id VARCHAR(255) UNIQUE,
    -- Store the ENCRYPTED refresh token, never plain text.
    encrypted_refresh_token TEXT
);

--Operators for calculating similarity
    -- <-> - Euclidean distance (L2 distance)
    -- <#> - negative inner product
    -- <=> - cosine distance

CREATE TABLE documents (
    doc_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    embedding vector(384),
    content TEXT,

    -- This sets up the one-to-many relationship between users and documents
    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
);

-- Create an index on the user_id in the document table for faster lookups of documents by user.
CREATE INDEX IF NOT EXISTS idx_document_user_id ON documents(user_id);
