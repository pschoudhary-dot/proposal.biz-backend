-- First, drop existing tables (in reverse order to avoid constraint violations)
DROP TABLE IF EXISTS extracted_links CASCADE;
DROP TABLE IF EXISTS markdown_content CASCADE;
DROP TABLE IF EXISTS markdown_extraction_jobs CASCADE;
DROP TABLE IF EXISTS document_content CASCADE;
DROP TABLE IF EXISTS document_conversion_jobs CASCADE;
DROP TABLE IF EXISTS extraction_jobs CASCADE;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pgvector"; -- For vector embeddings

-- Organization Structure Tables
CREATE TABLE Organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    settings JSONB DEFAULT '{}',
    logo TEXT,
    color_palette JSONB,
    website TEXT,
    domain TEXT,
    plan_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE OrgContacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    contact_type TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    ph_number TEXT,
    designation TEXT,
    company_name TEXT,
    created_by UUID,
    deleted_by UUID,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE OrgUsers (
    org_id UUID NOT NULL REFERENCES Organizations(id),
    user_id UUID NOT NULL,
    role TEXT NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (org_id, user_id)
);

-- Content Sources and Library
CREATE TABLE OrgContentSources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    name TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'url', 'file', 'manual'
    source_metadata JSONB DEFAULT '{}',
    created_by UUID,
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    status_metadata JSONB DEFAULT '{}',
    parsed_content TEXT,
    job_id TEXT, -- Reference to extraction job if applicable
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for semantic chunks (for RAG)
CREATE TABLE ContentChunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    source_id UUID NOT NULL REFERENCES OrgContentSources(id),
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_metadata JSONB DEFAULT '{}',
    embedding vector(1536), -- Vector embedding for the chunk (standard OpenAI dimension)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE OrgContentLibrary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    source_id UUID REFERENCES OrgContentSources(id),
    content JSONB NOT NULL,
    content_type TEXT NOT NULL, -- 'about_us', 'services', 'testimonial', etc.
    sort_order INTEGER DEFAULT 0,
    is_default BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    embedding vector(1536), -- Vector embedding for the entire content item
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Website Data Extraction
CREATE TABLE ExtractionJobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    job_id TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    logo_file_path TEXT,
    favicon_file_path TEXT,
    color_palette JSONB,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Markdown Extraction
CREATE TABLE MarkdownExtractionJobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    job_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    total_urls INTEGER NOT NULL,
    completed_urls INTEGER DEFAULT 0,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE MarkdownContent (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    job_id TEXT NOT NULL,
    url TEXT NOT NULL,
    markdown_text TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    metadata JSONB,
    html TEXT,
    screenshot TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (job_id) REFERENCES MarkdownExtractionJobs(job_id)
);

CREATE TABLE ExtractedLinks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    job_id TEXT NOT NULL,
    url TEXT NOT NULL,
    link TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (job_id) REFERENCES MarkdownExtractionJobs(job_id)
);

-- Document Conversion
CREATE TABLE DocumentConversionJobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    job_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    total_files INTEGER NOT NULL DEFAULT 0,
    completed_files INTEGER DEFAULT 0,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE DocumentContent (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    job_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    markdown_text TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (job_id) REFERENCES DocumentConversionJobs(job_id)
);

-- Documents (Business Documents)
CREATE TABLE Documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    document_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content JSONB,
    sender TEXT,
    receiver TEXT,
    currency TEXT,
    value DECIMAL,
    status TEXT DEFAULT 'draft',
    created_by UUID,
    updated_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RAG Chat History
CREATE TABLE ChatSessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES Organizations(id),
    title TEXT DEFAULT 'New Chat',
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE ChatMessages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES ChatSessions(id),
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]', -- References to chunks used in response
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_orgcontacts_org_id ON OrgContacts(org_id);
CREATE INDEX idx_orgusers_org_id ON OrgUsers(org_id);
CREATE INDEX idx_orgusers_user_id ON OrgUsers(user_id);
CREATE INDEX idx_orgcontentsources_org_id ON OrgContentSources(org_id);
CREATE INDEX idx_orgcontentsources_status ON OrgContentSources(status);
CREATE INDEX idx_orgcontentsources_job_id ON OrgContentSources(job_id);
CREATE INDEX idx_orgcontentlibrary_org_id ON OrgContentLibrary(org_id);
CREATE INDEX idx_orgcontentlibrary_source_id ON OrgContentLibrary(source_id);
CREATE INDEX idx_orgcontentlibrary_content_type ON OrgContentLibrary(content_type);
CREATE INDEX idx_extractionjobs_org_id ON ExtractionJobs(org_id);
CREATE INDEX idx_extractionjobs_job_id ON ExtractionJobs(job_id);
CREATE INDEX idx_markdownextractionjobs_org_id ON MarkdownExtractionJobs(org_id);
CREATE INDEX idx_markdownextractionjobs_job_id ON MarkdownExtractionJobs(job_id);
CREATE INDEX idx_markdowncontent_org_id ON MarkdownContent(org_id);
CREATE INDEX idx_markdowncontent_job_id ON MarkdownContent(job_id);
CREATE INDEX idx_markdowncontent_url ON MarkdownContent(url);
CREATE INDEX idx_extractedlinks_org_id ON ExtractedLinks(org_id);
CREATE INDEX idx_extractedlinks_job_id ON ExtractedLinks(job_id);
CREATE INDEX idx_extractedlinks_url ON ExtractedLinks(url);
CREATE INDEX idx_documentconversionjobs_org_id ON DocumentConversionJobs(org_id);
CREATE INDEX idx_documentconversionjobs_job_id ON DocumentConversionJobs(job_id);
CREATE INDEX idx_documentcontent_org_id ON DocumentContent(org_id);
CREATE INDEX idx_documentcontent_job_id ON DocumentContent(job_id);
CREATE INDEX idx_documentcontent_filename ON DocumentContent(filename);
CREATE INDEX idx_documents_org_id ON Documents(org_id);
CREATE INDEX idx_documents_document_type ON Documents(document_type);
CREATE INDEX idx_documents_status ON Documents(status);
CREATE INDEX idx_contentchunks_org_id ON ContentChunks(org_id);
CREATE INDEX idx_contentchunks_source_id ON ContentChunks(source_id);
CREATE INDEX idx_chatsessions_org_id ON ChatSessions(org_id);
CREATE INDEX idx_chatmessages_session_id ON ChatMessages(session_id);

-- Create vector indexes for similarity search
CREATE INDEX contentchunks_embedding_idx ON ContentChunks USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX contentlibrary_embedding_idx ON OrgContentLibrary USING ivfflat (embedding vector_cosine_ops);

-- Enable Row Level Security
ALTER TABLE Organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE OrgContacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE OrgUsers ENABLE ROW LEVEL SECURITY;
ALTER TABLE OrgContentSources ENABLE ROW LEVEL SECURITY;
ALTER TABLE OrgContentLibrary ENABLE ROW LEVEL SECURITY;
ALTER TABLE ContentChunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE ExtractionJobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE MarkdownExtractionJobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE MarkdownContent ENABLE ROW LEVEL SECURITY;
ALTER TABLE ExtractedLinks ENABLE ROW LEVEL SECURITY;
ALTER TABLE DocumentConversionJobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE DocumentContent ENABLE ROW LEVEL SECURITY;
ALTER TABLE Documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE ChatSessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ChatMessages ENABLE ROW LEVEL SECURITY;

-- Create basic RLS policies for organization-based isolation
CREATE POLICY "Organizations belong to users in the org" ON Organizations
    USING (id IN (
        SELECT org_id FROM OrgUsers WHERE user_id = auth.uid()
    ));

-- Apply similar policies to all other tables
CREATE POLICY "Org content sources are org-specific" ON OrgContentSources
    USING (org_id IN (
        SELECT org_id FROM OrgUsers WHERE user_id = auth.uid()
    ));

-- Additional policies would follow the same pattern for other tables
