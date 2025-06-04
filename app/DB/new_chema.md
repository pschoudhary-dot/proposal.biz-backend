# ProposalBiz Database Schema Documentation

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Database Schema Sections](#database-schema-sections)
- [Table Details](#table-details)
- [Relationships](#relationships)
- [Indexes and Performance](#indexes-and-performance)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

---

## Overview

ProposalBiz is a comprehensive business proposal management system with advanced content extraction and AI-powered features. The database schema supports:

- **Multi-tenant Architecture**: Complete data isolation between organizations
- **Content Extraction Pipeline**: Automated extraction from websites and documents
- **RAG (Retrieval-Augmented Generation)**: Vector-based semantic search and AI chat
- **Business Document Management**: Proposals, contracts, and client management
- **Background Job Processing**: Unified system for all async operations

### Key Features
- ✅ Organization-based multi-tenancy
- ✅ Custom authentication system
- ✅ Advanced content processing with vector embeddings
- ✅ Unified job tracking across all operations
- ✅ Performance-optimized with proper indexing
- ✅ Scalable architecture with PostgreSQL + pgvector

---

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Layer    │    │ Organization    │    │  Business Layer │
│                 │    │     Layer       │    │                 │
│ • Users         │◄──►│ • Organizations │◄──►│ • Clients       │
│ • Sessions      │    │ • Org Users     │    │ • Contacts      │
│ • Roles         │    │ • Subscriptions │    │ • Proposals     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲
                                │
                       ┌─────────────────┐
                       │ Content Pipeline│
                       │                 │
                       │ • Job Processing│
                       │ • Content Mgmt  │
                       │ • Vector Search │
                       │ • Chat/RAG      │
                       └─────────────────┘
```

### Data Flow

```
1. Content Ingestion
   ├── Website Extraction → extraction_content
   ├── Document Upload → document_content  
   ├── Markdown Scraping → markdown_content
   └── Manual Entry → org_content_sources

2. Processing Pipeline
   ├── Job Tracking → processing_jobs
   ├── Content Chunking → content_chunks
   ├── Vector Embedding → pgvector
   └── Structured Data → content_library_results

3. Business Operations
   ├── Proposal Creation → proposals
   ├── Client Management → clients/contacts
   └── AI Chat → chat_sessions/chat_messages
```

---

## Database Schema Sections

### 1. User Management System
Handles authentication, authorization, and user sessions.

### 2. Organization Management  
Multi-tenant structure with subscriptions and team management.

### 3. Client & Contact Management
CRM functionality for managing business relationships.

### 4. Proposal System
Core business document creation and management.

### 5. Unified Job Processing
Background task management for all async operations.

### 6. Content Management
Content ingestion, processing, and storage system.

### 7. Endpoint-Specific Results
Dedicated storage for different content extraction types.

### 8. RAG Chat System
AI-powered conversational interface with source attribution.

---

## Table Details

### User Management System

#### `users`
**Purpose**: Core user accounts with authentication and profile information.

| Column | Type | Description |
|--------|------|-------------|
| id | serial | Primary key (auto-increment) |
| email | varchar(255) | Unique email address |
| name | varchar(255) | User's display name |
| profile_image | varchar(500) | Avatar/profile image URL |
| password_hash | varchar(255) | Hashed password for local auth |
| provider | varchar(50) | OAuth provider (google, github, etc.) |
| provider_id | varchar(255) | External provider user ID |
| email_verified | boolean | Email verification status |
| two_factor_enabled | boolean | 2FA activation status |
| onboarding_checklist | json | User onboarding progress tracking |

**Key Features**:
- Supports both local and OAuth authentication
- Built-in 2FA support
- Onboarding progress tracking
- Soft user management

#### `sessions`
**Purpose**: Track active user sessions for security and session management.

| Column | Type | Description |
|--------|------|-------------|
| id | serial | Primary key |
| user_id | integer | Reference to users table |
| token | varchar(255) | Unique session token |
| user_agent | varchar(500) | Browser/client information |
| ip_address | varchar(45) | Client IP address |
| last_active | timestamp | Last activity timestamp |

#### `roles` & `permissions`
**Purpose**: Role-based access control system.

- **roles**: Define user roles (admin, member, viewer, etc.)
- **permissions**: Granular permission definitions
- **role_permissions**: Many-to-many relationship between roles and permissions

### Organization Management

#### `organizations`
**Purpose**: Central entity for multi-tenant architecture.

| Column | Type | Description |
|--------|------|-------------|
| id | serial | Primary key |
| name | varchar(255) | Organization display name |
| domain | varchar(255) | Unique domain identifier |
| custom_domain | varchar(255) | Custom domain for white-labeling |
| website | varchar(500) | Organization website |
| logo | text | Logo image data/URL |
| brand_colors | json | Brand color palette |
| currency | varchar(3) | Default currency (USD, EUR, etc.) |
| industry | varchar(500) | Business industry |
| stripe_customer_id | varchar(255) | Stripe integration |

**Key Features**:
- Custom domain support for white-labeling
- Brand customization (logo, colors)
- Geographic and industry categorization
- Stripe integration for billing

#### `organization_users`
**Purpose**: Define user membership and roles within organizations.

| Column | Type | Description |
|--------|------|-------------|
| org_id | integer | Reference to organizations |
| user_id | integer | Reference to users |
| role_id | integer | User's role in this organization |
| deleted_at | timestamp | Soft deletion timestamp |
| deleted_by | integer | User who performed deletion |

**Key Features**:
- Many-to-many relationship between users and organizations
- Role-based permissions per organization
- Soft deletion for audit trails

### Content Management

#### `processing_jobs`
**Purpose**: Unified tracking system for all background operations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| job_id | text | Human-readable job identifier |
| job_type | text | Type of operation (website_extraction, etc.) |
| status | text | Current status (pending, processing, completed, failed) |
| total_items | integer | Total items to process |
| completed_items | integer | Items completed so far |
| source_url | text | Source URL for web operations |
| source_files | text[] | Array of filenames for document operations |
| source_ids | UUID[] | Array of content source IDs |
| metadata | jsonb | Additional job-specific data |
| error_message | text | Error details if job failed |

**Supported Job Types**:
- `website_extraction`: Extract branding and content from websites
- `markdown_extraction`: Batch markdown extraction from multiple URLs
- `document_conversion`: Convert documents to markdown
- `content_library`: Process content into structured business information
- `vector_processing`: Create embeddings for semantic search

#### `org_content_sources`
**Purpose**: Track all content sources for an organization.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | text | Human-readable source name |
| source_type | text | Type: 'url', 'file', 'manual' |
| source_metadata | jsonb | Source-specific metadata |
| parsed_content | text | Extracted/processed content |
| status | text | Processing status |
| job_id | text | Associated processing job |

#### `content_chunks`
**Purpose**: Semantic text chunks with vector embeddings for RAG.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| source_id | UUID | Reference to content source |
| chunk_index | integer | Order within source document |
| chunk_text | text | Actual text content |
| chunk_metadata | jsonb | Chunk-specific metadata |
| embedding | vector(1536) | OpenAI-compatible vector embedding |

**Key Features**:
- Semantic chunking for optimal RAG performance
- Vector similarity search with pgvector
- Source attribution for AI responses

### Endpoint-Specific Results

#### `extraction_content`
**Purpose**: Store website extraction results with branding and company data.

| Column | Type | Description |
|--------|------|-------------|
| extraction_data | jsonb | Complete WebsiteExtraction schema |
| logo_file_path | text | Stored logo image path |
| favicon_file_path | text | Stored favicon path |
| color_palette | jsonb | Extracted brand colors |

**Sample extraction_data Structure**:
```json
{
  "url": "https://example.com",
  "company": {
    "name": "Acme Inc",
    "description": "Leading software company",
    "industry": "Technology"
  },
  "logo": {
    "url": "https://example.com/logo.png",
    "alt_text": "Acme Inc Logo"
  },
  "social_profiles": {
    "linkedin": "https://linkedin.com/company/acme",
    "twitter": "https://twitter.com/acme"
  },
  "seo_data": {
    "meta_title": "Acme Inc - Leading Software Solutions",
    "meta_description": "We build amazing software..."
  }
}
```

#### `content_library_results`
**Purpose**: Store structured business information extracted from content.

| Column | Type | Description |
|--------|------|-------------|
| business_data | jsonb | Complete BusinessInformationSchema |
| source_count | integer | Number of sources processed |
| processing_metadata | jsonb | Processing statistics and metadata |

**Sample business_data Structure**:
```json
{
  "services": [
    {
      "name": "Web Development",
      "category": "Technology",
      "description": "Custom web applications",
      "key_features": ["React", "Node.js", "Cloud Deployment"],
      "pricing_model": "Project-based"
    }
  ],
  "team": [
    {
      "name": "John Doe",
      "role": "CEO",
      "bio": "15 years of experience...",
      "expertise": ["Leadership", "Strategy"]
    }
  ],
  "case_studies": [...],
  "pricing_packages": [...],
  "technologies": [...]
}
```

#### `markdown_content`
**Purpose**: Store extracted markdown content from websites.

| Column | Type | Description |
|--------|------|-------------|
| url | text | Source URL |
| markdown_text | text | Extracted markdown content |
| metadata | jsonb | Page metadata (title, description, etc.) |
| html | text | Original HTML content |
| screenshot | text | Page screenshot data |

#### `document_content`
**Purpose**: Store converted document content.

| Column | Type | Description |
|--------|------|-------------|
| filename | text | Original document filename |
| markdown_text | text | Converted markdown content |
| metadata | jsonb | Document metadata and conversion info |
| docling_task_id | text | External conversion service task ID |

### RAG Chat System

#### `chat_sessions`
**Purpose**: Organize conversations into sessions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| title | text | Session title/topic |
| created_by | integer | User who started the session |

#### `chat_messages`
**Purpose**: Individual messages within chat sessions.

| Column | Type | Description |
|--------|------|-------------|
| session_id | UUID | Reference to chat session |
| role | text | Message role: 'user', 'assistant', 'system' |
| content | text | Message content |
| sources | jsonb | Array of content chunks used in AI response |

**Sample sources Structure**:
```json
[
  {
    "chunk_id": "uuid-here",
    "chunk_text": "Relevant content excerpt...",
    "source_name": "Company Website",
    "similarity_score": 0.85
  }
]
```

---

## Relationships

### Key Foreign Key Relationships

```
users (1) ←→ (M) organization_users (M) ←→ (1) organizations
organizations (1) ←→ (M) clients (1) ←→ (M) contacts
organizations (1) ←→ (M) proposals
organizations (1) ←→ (M) processing_jobs
processing_jobs (1) ←→ (M) extraction_content
processing_jobs (1) ←→ (M) markdown_content
processing_jobs (1) ←→ (M) document_content
org_content_sources (1) ←→ (M) content_chunks
organizations (1) ←→ (M) chat_sessions (1) ←→ (M) chat_messages
```

### Data Isolation Strategy

- **Organization Level**: All business data is scoped to organizations
- **User Level**: Users can belong to multiple organizations with different roles
- **Content Level**: All content (sources, chunks, results) is organization-specific
- **Job Level**: All background jobs are tracked per organization

---

## Indexes and Performance

### Key Performance Indexes

#### Organization Queries
```sql
-- Fast organization lookup by domain
CREATE INDEX organizations_domain_idx ON organizations(domain);

-- User-organization membership queries
CREATE INDEX organization_users_org_id_idx ON organization_users(org_id);
CREATE INDEX organization_users_user_id_idx ON organization_users(user_id);
```

#### Job Processing
```sql
-- Job status and type filtering
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_job_type ON processing_jobs(job_type);
CREATE INDEX idx_processing_jobs_org_id ON processing_jobs(org_id);
```

#### Vector Search Performance
```sql
-- Vector similarity search optimization
CREATE INDEX content_chunks_embedding_idx ON content_chunks 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX content_library_embedding_idx ON org_content_library 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

#### Content Filtering
```sql
-- Content source filtering by organization and type
CREATE INDEX idx_org_content_sources_org_id ON org_content_sources(org_id);
CREATE INDEX idx_org_content_sources_source_type ON org_content_sources(source_type);
CREATE INDEX idx_org_content_sources_status ON org_content_sources(status);
```

### Performance Considerations

1. **Vector Index Tuning**: Adjust `lists` parameter based on data size
2. **Composite Indexes**: For multi-column queries (org_id + status)
3. **Partial Indexes**: For frequently filtered subsets
4. **Connection Pooling**: Use connection pooling for high-concurrency scenarios

---

## Usage Examples

### 1. User Organization Access

```sql
-- Get all organizations for a user
SELECT o.id, o.name, ou.role_id
FROM organizations o
JOIN organization_users ou ON o.id = ou.org_id
WHERE ou.user_id = 123 AND ou.deleted_at IS NULL;

-- Check if user belongs to organization
SELECT user_belongs_to_org(123, 456);
```

### 2. Content Processing Workflow

```sql
-- Create a new processing job
INSERT INTO processing_jobs (org_id, job_id, job_type, source_url, created_by)
VALUES (456, 'job_789', 'website_extraction', 'https://example.com', 123);

-- Store extraction results
INSERT INTO extraction_content (org_id, job_id, url, extraction_data, status)
VALUES (456, 'job_789', 'https://example.com', '{"company": {...}}', 'completed');

-- Update job progress
UPDATE processing_jobs 
SET status = 'completed', completed_items = 1, updated_at = NOW()
WHERE job_id = 'job_789';
```

### 3. Vector Search for RAG

```sql
-- Find similar content chunks
SELECT 
    id, 
    chunk_text, 
    chunk_metadata,
    1 - (embedding <=> '[0.1,0.2,0.3,...]'::vector) as similarity
FROM content_chunks 
WHERE org_id = 456
ORDER BY embedding <=> '[0.1,0.2,0.3,...]'::vector
LIMIT 5;
```

### 4. Content Library Query

```sql
-- Get structured business information
SELECT 
    clr.business_data,
    pj.created_at,
    pj.metadata
FROM content_library_results clr
JOIN processing_jobs pj ON clr.job_id = pj.job_id
WHERE clr.org_id = 456 AND pj.status = 'completed'
ORDER BY pj.created_at DESC
LIMIT 1;
```

### 5. Chat Session with Sources

```sql
-- Get chat session with source attribution
SELECT 
    cm.role,
    cm.content,
    cm.sources,
    cm.created_at
FROM chat_messages cm
JOIN chat_sessions cs ON cm.session_id = cs.id
WHERE cs.org_id = 456 AND cs.id = 'session_uuid'
ORDER BY cm.created_at;
```

---

## Best Practices

### 1. Data Management

#### Organization Scoping
Always include `org_id` in queries to ensure data isolation:
```sql
-- ✅ Good
SELECT * FROM proposals WHERE org_id = 456 AND status = 'draft';

-- ❌ Bad
SELECT * FROM proposals WHERE status = 'draft';
```

#### Soft Deletion
Use soft deletion for audit trails:
```sql
-- Soft delete user from organization
UPDATE organization_users 
SET deleted_at = NOW(), deleted_by = 123 
WHERE org_id = 456 AND user_id = 789;
```

### 2. Performance Optimization

#### Batch Operations
Use batch operations for bulk content processing:
```sql
-- Batch insert content chunks
INSERT INTO content_chunks (org_id, source_id, chunk_index, chunk_text, embedding)
VALUES 
    (456, 'source1', 0, 'text1', '[...]'),
    (456, 'source1', 1, 'text2', '[...]'),
    (456, 'source1', 2, 'text3', '[...]');
```

#### Query Optimization
Use appropriate indexes and query patterns:
```sql
-- Efficient organization content query
SELECT cs.*, cl.content 
FROM org_content_sources cs
LEFT JOIN org_content_library cl ON cs.id = cl.source_id
WHERE cs.org_id = 456 AND cs.status = 'completed';
```

### 3. Security Considerations

#### Input Validation
Always validate and sanitize inputs, especially for JSONB fields.

#### Access Control
Implement proper access control at the application level to complement database constraints.

#### Data Encryption
Consider encrypting sensitive data like email addresses and personal information.

### 4. Monitoring and Maintenance

#### Job Monitoring
Regularly monitor processing jobs for failures:
```sql
-- Check for failed jobs
SELECT job_id, job_type, error_message, created_at
FROM processing_jobs 
WHERE status = 'failed' AND created_at > NOW() - INTERVAL '24 hours';
```

#### Vector Index Maintenance
Monitor vector index performance and rebuild when necessary:
```sql
-- Check index statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%embedding%';
```

---

## Conclusion

This database schema provides a robust foundation for the ProposalBiz application with:

- **Scalable multi-tenant architecture**
- **Advanced content processing capabilities**
- **AI-powered features with vector search**
- **Comprehensive job tracking and monitoring**
- **Performance-optimized design**

The modular design allows for easy extension and modification as business requirements evolve.