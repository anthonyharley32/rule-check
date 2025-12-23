-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create chunks table
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding VECTOR(768),
    type TEXT NOT NULL CHECK (type IN ('rule_article', 'situation', 'ruling', 'emphasis', 'manual')),
    book TEXT NOT NULL CHECK (book IN ('rules', 'casebook', 'manual')),
    source_ref TEXT NOT NULL,
    section_ref TEXT,
    rule_ref TEXT,
    title TEXT,
    penalty_text TEXT,
    page_number INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create indexes for filtering
CREATE INDEX chunks_book_idx ON chunks (book);
CREATE INDEX chunks_type_idx ON chunks (type);
CREATE INDEX chunks_source_ref_idx ON chunks (source_ref);

-- Create function for similarity search
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding VECTOR(768),
    match_count INT DEFAULT 5,
    filter_book TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    type TEXT,
    book TEXT,
    source_ref TEXT,
    section_ref TEXT,
    rule_ref TEXT,
    title TEXT,
    penalty_text TEXT,
    page_number INTEGER,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        c.type,
        c.book,
        c.source_ref,
        c.section_ref,
        c.rule_ref,
        c.title,
        c.penalty_text,
        c.page_number,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE (filter_book IS NULL OR c.book = filter_book)
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
