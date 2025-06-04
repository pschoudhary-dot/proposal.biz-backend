-- =============================================
-- COMPLETE DATABASE SCHEMA FOR PROPOSALBIZ
-- =============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================
-- USER MANAGEMENT SYSTEM
-- =============================================

CREATE TABLE "users" (
    "id" serial PRIMARY KEY NOT NULL,
    "email" varchar(255) NOT NULL,
    "name" varchar(255),
    "profile_image" varchar(500),
    "password_hash" varchar(255),
    "provider" varchar(50),
    "provider_id" varchar(255),
    "email_verified" boolean DEFAULT false,
    "two_factor_enabled" boolean DEFAULT false,
    "two_factor_secret" varchar(255),
    "heard_from" varchar(500),
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now(),
    "onboarding_checklist" json DEFAULT '{"welcome-video":false,"update-branding":false,"complete-organization-details":false,"add-team":false,"add-client":false,"create-proposal":false,"send-proposal":false}'::json,
    CONSTRAINT "users_email_unique" UNIQUE("email")
);

CREATE TABLE "verification_tokens" (
    "id" serial PRIMARY KEY NOT NULL,
    "user_id" integer,
    "token" varchar(255) NOT NULL,
    "type" varchar(50) NOT NULL,
    "expires_at" timestamp NOT NULL,
    "created_at" timestamp DEFAULT now(),
    CONSTRAINT "verification_tokens_token_unique" UNIQUE("token")
);

CREATE TABLE "roles" (
    "id" serial PRIMARY KEY NOT NULL,
    "name" varchar(100) NOT NULL,
    "created_at" timestamp DEFAULT now()
);

CREATE TABLE "permissions" (
    "id" serial PRIMARY KEY NOT NULL,
    "name" varchar(100) NOT NULL,
    "description" text,
    "created_at" timestamp DEFAULT now()
);

CREATE TABLE "role_permissions" (
    "role_id" integer,
    "permission_id" integer,
    "created_at" timestamp DEFAULT now(),
    CONSTRAINT "role_permissions_role_id_permission_id_pk" PRIMARY KEY("role_id","permission_id")
);

CREATE TABLE "sessions" (
    "id" serial PRIMARY KEY NOT NULL,
    "user_id" integer NOT NULL,
    "token" varchar(255) NOT NULL,
    "user_agent" varchar(500),
    "ip_address" varchar(45),
    "last_active" timestamp DEFAULT now(),
    "created_at" timestamp DEFAULT now(),
    CONSTRAINT "sessions_token_unique" UNIQUE("token")
);

-- =============================================
-- ORGANIZATION MANAGEMENT
-- =============================================

CREATE TABLE "organizations" (
    "id" serial PRIMARY KEY NOT NULL,
    "name" varchar(255) NOT NULL,
    "domain" varchar(255) NOT NULL,
    "custom_domain" varchar(255),
    "custom_domain_verification_token" varchar(255),
    "custom_domain_verified_at" timestamp,
    "custom_domain_instructions" json,
    "currency" varchar(3),
    "country" varchar(100),
    "country_code" varchar(2),
    "state" varchar(100),
    "state_code" varchar(10),
    "city" varchar(100),
    "zip_code" varchar(100),
    "address" varchar(500),
    "website" varchar(500),
    "logo" text,
    "brand_colors" json,
    "document_type" varchar(50),
    "industry" varchar(500),
    "employee_count" varchar(500),
    "crm" varchar(500),
    "heard_from" varchar(500),
    "use_case" json,
    "stripe_customer_id" varchar(255),
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now(),
    CONSTRAINT "organizations_custom_domain_unique" UNIQUE("custom_domain")
);

CREATE TABLE "organization_users" (
    "id" serial PRIMARY KEY NOT NULL,
    "org_id" integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    "user_id" integer,
    "role_id" integer,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now(),
    "deleted_at" TIMESTAMP WITH TIME ZONE,
    "deleted_by" integer
);

CREATE TABLE "organization_subscriptions" (
    "id" serial PRIMARY KEY NOT NULL,
    "org_id" integer NOT NULL,
    "plan_id" integer NOT NULL,
    "stripe_subscription_id" varchar(255),
    "stripe_customer_id" varchar(255),
    "status" varchar(50) NOT NULL,
    "current_period_start" timestamp,
    "current_period_end" timestamp,
    "cancel_at_period_end" boolean DEFAULT false,
    "canceled_at" timestamp,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now()
);

CREATE TABLE "subscription_plans" (
    "id" serial PRIMARY KEY NOT NULL,
    "name" varchar(100) NOT NULL,
    "description" text,
    "stripe_price_id" varchar(255) NOT NULL,
    "stripe_product_id" varchar(255) NOT NULL,
    "amount" integer NOT NULL,
    "currency" varchar(3) DEFAULT 'usd' NOT NULL,
    "interval" varchar(20) NOT NULL,
    "active" boolean DEFAULT true,
    "default_plan" boolean DEFAULT false,
    "initial_credits" integer DEFAULT 0,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now()
);

CREATE TABLE "subscription_plan_features" (
    "id" serial PRIMARY KEY NOT NULL,
    "plan_id" integer NOT NULL,
    "feature_key" varchar(100) NOT NULL,
    "feature_name" varchar(255) NOT NULL,
    "description" text,
    "value" varchar(255) NOT NULL,
    "value_type" varchar(50) DEFAULT 'string',
    "sort_order" integer DEFAULT 0,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now()
);

CREATE TABLE "invitations" (
    "id" serial PRIMARY KEY NOT NULL,
    "email" varchar(255) NOT NULL,
    "org_id" integer,
    "role_id" integer,
    "token" varchar(255) NOT NULL,
    "expires_at" timestamp NOT NULL,
    "created_at" timestamp DEFAULT now(),
    CONSTRAINT "invitations_token_unique" UNIQUE("token")
);

-- =============================================
-- CLIENT AND CONTACT MANAGEMENT
-- =============================================

CREATE TABLE "clients" (
    "id" serial PRIMARY KEY NOT NULL,
    "name" varchar(255) NOT NULL,
    "website" varchar(255),
    "address" varchar(500),
    "country" varchar(255),
    "state" varchar(255),
    "city" varchar(255),
    "zip_code" varchar(255),
    "org_id" integer NOT NULL,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now()
);

CREATE TABLE "contacts" (
    "id" serial PRIMARY KEY NOT NULL,
    "first_name" varchar(255) NOT NULL,
    "last_name" varchar(255) NOT NULL,
    "email" varchar(500) NOT NULL,
    "phone" varchar(50),
    "job_title" varchar(255),
    "address" varchar(500),
    "status" varchar(50) DEFAULT 'active',
    "client_id" integer,
    "org_id" integer NOT NULL,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now()
);

-- =============================================
-- PROPOSAL SYSTEM
-- =============================================

CREATE TABLE "proposals" (
    "id" serial PRIMARY KEY NOT NULL,
    "title" varchar(255),
    "description" text,
    "slug" varchar(255),
    "status" varchar(50) DEFAULT 'draft' NOT NULL,
    "org_id" integer NOT NULL,
    "user_id" integer NOT NULL,
    "client_id" integer NOT NULL,
    "template_id" integer,
    "document_type" varchar(50),
    "currency" varchar(3),
    "cover_title" varchar(255),
    "cover_description" text,
    "cover_image" varchar(500),
    "content" json,
    "requires_approval" boolean DEFAULT false,
    "from_email" varchar(255),
    "email_subject" varchar(255),
    "email_body" text,
    "sent_to_contact_id" integer,
    "sent_at" timestamp,
    "is_template" boolean DEFAULT false,
    "metadata" json,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now()
);

-- =============================================
-- UNIFIED JOB PROCESSING SYSTEM
-- =============================================

CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL UNIQUE,
    job_type TEXT NOT NULL, -- 'website_extraction', 'markdown_extraction', 'document_conversion', 'content_library', 'vector_processing'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    total_items INTEGER DEFAULT 0,
    completed_items INTEGER DEFAULT 0,
    source_url TEXT, -- For website extraction and markdown scraping
    source_files TEXT[], -- For document conversion (array of filenames)
    source_ids UUID[], -- For content library (array of content source IDs)
    metadata JSONB DEFAULT '{}',
    error_message TEXT,
    created_by integer REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- CONTENT MANAGEMENT
-- =============================================

CREATE TABLE org_content_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'url', 'file', 'manual'
    source_metadata JSONB DEFAULT '{}',
    parsed_content TEXT,
    status TEXT DEFAULT 'pending',
    job_id TEXT REFERENCES processing_jobs(job_id),
    error_message TEXT,
    created_by integer REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE org_content_library (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_id UUID REFERENCES org_content_sources(id) ON DELETE CASCADE,
    content JSONB NOT NULL,
    content_type TEXT NOT NULL, -- 'about_us', 'services', 'testimonial', etc.
    sort_order INTEGER DEFAULT 0,
    is_default BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    embedding vector(1536),
    created_by integer REFERENCES users(id),
    updated_by integer REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE content_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES org_content_sources(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- ENDPOINT-SPECIFIC RESULT TABLES
-- =============================================

-- 1. Website Extraction Results
CREATE TABLE extraction_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES processing_jobs(job_id),
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    extraction_data JSONB, -- Complete WebsiteExtraction schema JSON
    logo_file_path TEXT,
    favicon_file_path TEXT,
    color_palette JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Content Library Processing Results  
CREATE TABLE content_library_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES processing_jobs(job_id),
    business_data JSONB NOT NULL, -- Complete BusinessInformationSchema JSON
    source_count INTEGER DEFAULT 0,
    processing_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Markdown Extraction Results
CREATE TABLE markdown_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES processing_jobs(job_id),
    url TEXT NOT NULL,
    markdown_text TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    html TEXT,
    screenshot TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE extracted_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES processing_jobs(job_id),
    url TEXT NOT NULL,
    link TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Document Conversion Results
CREATE TABLE document_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES processing_jobs(job_id),
    filename TEXT NOT NULL,
    markdown_text TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    docling_task_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- BUSINESS DOCUMENTS
-- =============================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content JSONB,
    sender TEXT,
    receiver TEXT,
    currency TEXT,
    value DECIMAL,
    status TEXT DEFAULT 'draft',
    created_by integer REFERENCES users(id),
    updated_by integer REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- RAG CHAT SYSTEM
-- =============================================

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id integer NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New Chat',
    created_by integer REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- FOREIGN KEY CONSTRAINTS
-- =============================================

-- User Management
ALTER TABLE "verification_tokens" ADD CONSTRAINT "verification_tokens_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "role_permissions" ADD CONSTRAINT "role_permissions_role_id_roles_id_fk" FOREIGN KEY ("role_id") REFERENCES "roles"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "role_permissions" ADD CONSTRAINT "role_permissions_permission_id_permissions_id_fk" FOREIGN KEY ("permission_id") REFERENCES "permissions"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "sessions" ADD CONSTRAINT "sessions_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;

-- Organization Management
ALTER TABLE "organization_users" ADD CONSTRAINT "organization_users_organization_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "organizations"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "organization_users" ADD CONSTRAINT "organization_users_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "organization_users" ADD CONSTRAINT "organization_users_role_id_roles_id_fk" FOREIGN KEY ("role_id") REFERENCES "roles"("id") ON DELETE no action ON UPDATE no action;
ALTER TABLE "organization_subscriptions" ADD CONSTRAINT "organization_subscriptions_organization_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "organizations"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "organization_subscriptions" ADD CONSTRAINT "organization_subscriptions_plan_id_subscription_plans_id_fk" FOREIGN KEY ("plan_id") REFERENCES "subscription_plans"("id") ON DELETE restrict ON UPDATE no action;
ALTER TABLE "subscription_plan_features" ADD CONSTRAINT "subscription_plan_features_plan_id_subscription_plans_id_fk" FOREIGN KEY ("plan_id") REFERENCES "subscription_plans"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "invitations" ADD CONSTRAINT "invitations_organization_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "organizations"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "invitations" ADD CONSTRAINT "invitations_role_id_roles_id_fk" FOREIGN KEY ("role_id") REFERENCES "roles"("id") ON DELETE no action ON UPDATE no action;

-- Client and Contact Management
ALTER TABLE "clients" ADD CONSTRAINT "clients_organization_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "organizations"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "contacts" ADD CONSTRAINT "contacts_client_id_clients_id_fk" FOREIGN KEY ("client_id") REFERENCES "clients"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "contacts" ADD CONSTRAINT "contacts_organization_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "organizations"("id") ON DELETE cascade ON UPDATE no action;

-- Proposal System
ALTER TABLE "proposals" ADD CONSTRAINT "proposals_organization_id_organizations_id_fk" FOREIGN KEY ("org_id") REFERENCES "organizations"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "proposals" ADD CONSTRAINT "proposals_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE cascade ON UPDATE no action;
ALTER TABLE "proposals" ADD CONSTRAINT "proposals_sent_to_contact_id_contacts_id_fk" FOREIGN KEY ("sent_to_contact_id") REFERENCES "contacts"("id") ON DELETE no action ON UPDATE no action;

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

-- User Management
CREATE INDEX "users_provider_provider_id_idx" ON "users" USING btree ("provider","provider_id");
CREATE INDEX "verification_tokens_user_type_idx" ON "verification_tokens" USING btree ("user_id","type");
CREATE INDEX "verification_tokens_expires_at_idx" ON "verification_tokens" USING btree ("expires_at");
CREATE UNIQUE INDEX "permissions_name_idx" ON "permissions" USING btree ("name");
CREATE INDEX "sessions_user_id_idx" ON "sessions" USING btree ("user_id");
CREATE INDEX "sessions_last_active_idx" ON "sessions" USING btree ("last_active");

-- Organization Management
CREATE INDEX "organizations_domain_idx" ON "organizations" USING btree ("domain");
CREATE INDEX "organizations_stripe_customer_id_idx" ON "organizations" USING btree ("stripe_customer_id");
CREATE INDEX "organization_users_org_id_idx" ON "organization_users" USING btree ("org_id");
CREATE INDEX "organization_users_user_id_idx" ON "organization_users" USING btree ("user_id");
CREATE UNIQUE INDEX "org_subscriptions_org_id_idx" ON "organization_subscriptions" USING btree ("org_id");
CREATE UNIQUE INDEX "org_subscriptions_stripe_sub_id_idx" ON "organization_subscriptions" USING btree ("stripe_subscription_id");
CREATE INDEX "org_subscriptions_status_idx" ON "organization_subscriptions" USING btree ("status");
CREATE INDEX "org_subscriptions_period_end_idx" ON "organization_subscriptions" USING btree ("current_period_end");
CREATE INDEX "subscription_plan_features_plan_id_idx" ON "subscription_plan_features" USING btree ("plan_id");
CREATE INDEX "subscription_plan_features_key_idx" ON "subscription_plan_features" USING btree ("feature_key");
CREATE INDEX "subscription_plan_features_plan_sort_idx" ON "subscription_plan_features" USING btree ("plan_id","sort_order");
CREATE INDEX "subscription_plans_active_idx" ON "subscription_plans" USING btree ("active");
CREATE INDEX "subscription_plans_default_plan_idx" ON "subscription_plans" USING btree ("default_plan");
CREATE INDEX "invitations_email_idx" ON "invitations" USING btree ("email");
CREATE INDEX "invitations_org_id_idx" ON "invitations" USING btree ("org_id");
CREATE INDEX "invitations_expires_at_idx" ON "invitations" USING btree ("expires_at");

-- Client and Contact Management
CREATE INDEX "clients_org_id_idx" ON "clients" USING btree ("org_id");
CREATE INDEX "clients_org_name_idx" ON "clients" USING btree ("org_id","name");
CREATE INDEX "contacts_org_id_idx" ON "contacts" USING btree ("org_id");
CREATE INDEX "contacts_client_id_idx" ON "contacts" USING btree ("client_id");
CREATE INDEX "contacts_org_email_idx" ON "contacts" USING btree ("org_id","email");
CREATE INDEX "contacts_org_status_idx" ON "contacts" USING btree ("org_id","status");

-- Processing Jobs
CREATE INDEX idx_processing_jobs_org_id ON processing_jobs(org_id);
CREATE INDEX idx_processing_jobs_job_id ON processing_jobs(job_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_job_type ON processing_jobs(job_type);
CREATE INDEX idx_processing_jobs_source_url ON processing_jobs(source_url);
CREATE INDEX idx_processing_jobs_created_by ON processing_jobs(created_by);

-- Content Sources
CREATE INDEX idx_org_content_sources_org_id ON org_content_sources(org_id);
CREATE INDEX idx_org_content_sources_status ON org_content_sources(status);
CREATE INDEX idx_org_content_sources_job_id ON org_content_sources(job_id);
CREATE INDEX idx_org_content_sources_source_type ON org_content_sources(source_type);
CREATE INDEX idx_org_content_sources_created_by ON org_content_sources(created_by);

-- Content Library
CREATE INDEX idx_org_content_library_org_id ON org_content_library(org_id);
CREATE INDEX idx_org_content_library_source_id ON org_content_library(source_id);
CREATE INDEX idx_org_content_library_content_type ON org_content_library(content_type);
CREATE INDEX idx_org_content_library_created_by ON org_content_library(created_by);

-- Content Chunks
CREATE INDEX idx_content_chunks_org_id ON content_chunks(org_id);
CREATE INDEX idx_content_chunks_source_id ON content_chunks(source_id);

-- Endpoint-Specific Result Tables
CREATE INDEX idx_extraction_content_org_id ON extraction_content(org_id);
CREATE INDEX idx_extraction_content_job_id ON extraction_content(job_id);
CREATE INDEX idx_extraction_content_url ON extraction_content(url);
CREATE INDEX idx_extraction_content_status ON extraction_content(status);

CREATE INDEX idx_content_library_results_org_id ON content_library_results(org_id);
CREATE INDEX idx_content_library_results_job_id ON content_library_results(job_id);

CREATE INDEX idx_markdown_content_org_id ON markdown_content(org_id);
CREATE INDEX idx_markdown_content_job_id ON markdown_content(job_id);
CREATE INDEX idx_markdown_content_url ON markdown_content(url);
CREATE INDEX idx_markdown_content_status ON markdown_content(status);

CREATE INDEX idx_extracted_links_org_id ON extracted_links(org_id);
CREATE INDEX idx_extracted_links_job_id ON extracted_links(job_id);
CREATE INDEX idx_extracted_links_url ON extracted_links(url);

CREATE INDEX idx_document_content_org_id ON document_content(org_id);
CREATE INDEX idx_document_content_job_id ON document_content(job_id);
CREATE INDEX idx_document_content_filename ON document_content(filename);
CREATE INDEX idx_document_content_docling_task_id ON document_content(docling_task_id);

-- Documents
CREATE INDEX idx_documents_org_id ON documents(org_id);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_created_by ON documents(created_by);

-- Chat Sessions
CREATE INDEX idx_chat_sessions_org_id ON chat_sessions(org_id);
CREATE INDEX idx_chat_sessions_created_by ON chat_sessions(created_by);

-- Chat Messages
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_role ON chat_messages(role);

-- Vector Indexes for Similarity Search
CREATE INDEX content_chunks_embedding_idx ON content_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX content_library_embedding_idx ON org_content_library USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================
-- HELPER FUNCTIONS
-- =============================================

-- Function to check if user belongs to organization
CREATE OR REPLACE FUNCTION user_belongs_to_org(user_uuid integer, org_uuid integer)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM organization_users 
        WHERE user_id = user_uuid AND org_id = org_uuid AND deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user's organizations
CREATE OR REPLACE FUNCTION get_user_organizations(user_uuid integer)
RETURNS TABLE(org_id integer, org_name TEXT, user_role_id integer) AS $$
BEGIN
    RETURN QUERY
    SELECT o.id, o.name, ou.role_id
    FROM organizations o
    JOIN organization_users ou ON o.id = ou.org_id
    WHERE ou.user_id = user_uuid AND ou.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================
-- COMMENTS FOR DOCUMENTATION
-- =============================================

COMMENT ON TABLE users IS 'User accounts with authentication and profile information';
COMMENT ON TABLE organizations IS 'Main organization entities with branding and settings';
COMMENT ON TABLE organization_users IS 'User-organization relationships with roles';
COMMENT ON TABLE clients IS 'Client companies associated with organizations';
COMMENT ON TABLE contacts IS 'Individual contacts within client companies';
COMMENT ON TABLE proposals IS 'Business proposals and documents';
COMMENT ON TABLE processing_jobs IS 'Unified job tracking for all background processes';
COMMENT ON TABLE org_content_sources IS 'Content sources (files, URLs, manual entries)';
COMMENT ON TABLE org_content_library IS 'Processed content library items';
COMMENT ON TABLE content_chunks IS 'Semantic chunks for RAG with vector embeddings';
COMMENT ON TABLE extraction_content IS 'Website extraction results (logos, branding, company data)';
COMMENT ON TABLE content_library_results IS 'Structured business information from content processing';
COMMENT ON TABLE markdown_content IS 'Extracted markdown content from websites';
COMMENT ON TABLE extracted_links IS 'Links extracted during website processing';
COMMENT ON TABLE document_content IS 'Converted document content';
COMMENT ON TABLE documents IS 'Business documents (invoices, proposals, etc.)';
COMMENT ON TABLE chat_sessions IS 'RAG chat sessions';
COMMENT ON TABLE chat_messages IS 'Chat messages with source references';