-- Content Library Tables Migration

-- Table for tracking content library processing jobs
CREATE TABLE IF NOT EXISTS contentlibraryjobs (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL UNIQUE,
    org_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    source_count INTEGER NOT NULL DEFAULT 0,
    processed_count INTEGER NOT NULL DEFAULT 0,
    source_ids UUID[] NOT NULL,
    error TEXT,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for content sources (files, URLs, etc.)
CREATE TABLE IF NOT EXISTS orgcontentsources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL, -- file, url, manual
    source_metadata JSONB,
    parsed_content TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    job_id UUID,
    error TEXT,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for content library items
CREATE TABLE IF NOT EXISTS orgcontentlibrary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    source_id UUID NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_contentlibraryjobs_job_id ON contentlibraryjobs(job_id);
CREATE INDEX IF NOT EXISTS idx_contentlibraryjobs_org_id ON contentlibraryjobs(org_id);
CREATE INDEX IF NOT EXISTS idx_orgcontentsources_org_id ON orgcontentsources(org_id);
CREATE INDEX IF NOT EXISTS idx_orgcontentsources_job_id ON orgcontentsources(job_id);
CREATE INDEX IF NOT EXISTS idx_orgcontentlibrary_org_id ON orgcontentlibrary(org_id);
CREATE INDEX IF NOT EXISTS idx_orgcontentlibrary_source_id ON orgcontentlibrary(source_id);
CREATE INDEX IF NOT EXISTS idx_orgcontentlibrary_content_type ON orgcontentlibrary(content_type);

-- Add foreign key constraints
ALTER TABLE orgcontentsources 
    ADD CONSTRAINT fk_orgcontentsources_job_id 
    FOREIGN KEY (job_id) 
    REFERENCES contentlibraryjobs(job_id) 
    ON DELETE SET NULL;

ALTER TABLE orgcontentlibrary 
    ADD CONSTRAINT fk_orgcontentlibrary_source_id 
    FOREIGN KEY (source_id) 
    REFERENCES orgcontentsources(id) 
    ON DELETE CASCADE;
