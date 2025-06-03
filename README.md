# Proposal Biz

A FastAPI service that extracts comprehensive business data from websites to help generate business proposals. The application now supports multi-organization structure with proper data isolation.

## Project Overview

Proposal Biz receives a website URL from the user and extracts comprehensive data (business info, visuals, tech stack, etc.) using Hyperbrowser and other tools, ultimately to help generate business proposals.

## Features

- Extract business information from websites
- Analyze website color schemes and visual elements
- Identify tech stack used by the business
- Generate structured data for business proposals
- Multi-organization support with data isolation
- Row-level security for organization-specific data

## Project Structure

```plaintext
proposal-biz/
├── app/                        # Main application directory
│   ├── api/                    # API routers
│   │   ├── deps.py             # API dependencies for auth and org access
│   │   ├── v1/                 # API version 1
│   │   │   ├── endpoints/      # Endpoint files
│   │   │   │   ├── extraction.py  # Extraction endpoint
│   │   │   │   ├── doc_to_markdown.py  # Document conversion endpoint
│   │   │   │   └── master_data.py  # Master data endpoint
│   │   │   └── api.py          # API router for v1
│   ├── core/                   # Core configuration
│   │   ├── config.py           # Settings and configuration
│   │   ├── database.py         # Database functions (original)
│   │   ├── database_new.py     # Database functions (org-based)
│   │   └── logging.py          # Logging configuration
│   ├── DB/                     # Database schema files
│   │   ├── newschema.sql       # New organization-based schema
│   │   └── doc_to_markdown_schema.sql  # Document conversion schema
│   ├── schemas/                # Pydantic models
│   │   ├── extraction.py       # Extraction request/response models
│   │   ├── doc_to_markdown.py  # Document conversion models
│   │   └── markdown_extraction.py  # Markdown extraction models
│   └── utils/                  # Utility functions
│       ├── jwt_handler.py      # JWT token handling
│       ├── markdown_extraction.py  # Markdown extraction utilities
│       └── doc_to_markdown.py  # Document conversion utilities
├── logs/                       # Log files directory (created at runtime)
├── scripts/                    # Utility scripts
├── main.py                     # Main application entry point
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Project dependencies
├── .env                        # Environment variables (not in git)
└── .gitignore                  # Git ignore file
```

## Database Schema

### Organization-Based Structure

The application has been refactored to use an organization-based database schema that provides proper data isolation and security. Key features include:

- **Organizations Table**: Central table for managing organizations
- **Organization Users**: Maps users to organizations they belong to
- **Row-Level Security**: PostgreSQL RLS policies ensure users can only access data from their organizations
- **Organization Content Sources**: Tracks content sources by organization
- **Organization Content Library**: Stores content by organization

### Key Tables

- `Organizations`: Stores organization details
- `OrgUsers`: Maps users to organizations
- `OrgContacts`: Stores contacts by organization
- `OrgContentSources`: Tracks content sources by organization
- `ExtractionJobs`: Stores extraction jobs with organization context
- `MarkdownExtractionJobs`: Stores markdown extraction jobs with organization context
- `DocumentConversionJobs`: Stores document conversion jobs with organization context

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd proposal-biz
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with the following content:
   ```
   # API Configuration
   PROJECT_NAME=Proposal Biz

   # Security
   JWT_SECRET_KEY=your_super_secret_key_here
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # External APIs
   HYPERBROWSER_API_KEY=your_hyperbrowser_api_key_here
   ```

## Running the Application

Start the development server:

```bash
python -m uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

- API documentation: `http://127.0.0.1:8000/docs`
- Alternative API documentation: `http://127.0.0.1:8000/redoc`

## Logging

The application uses a comprehensive logging system that:

1. Logs to both console (with colored output) and files
2. Creates timestamped log files in the `logs/` directory
3. Logs all requests, responses, and errors
4. Includes detailed information for debugging

Log levels:

- INFO: Normal application operation (default for console)
- DEBUG: Detailed information for debugging (included in log files)
- WARNING: Potential issues that don't prevent operation
- ERROR: Errors that prevent specific operations
- CRITICAL: Critical errors that may crash the application

## Managing `__pycache__` Directories

Python creates `__pycache__` directories containing compiled bytecode files (`.pyc`) to improve performance. These files can sometimes cause issues during development.

The project includes several features to manage these files:

1. **Prevention**: The application sets `PYTHONDONTWRITEBYTECODE=1` to prevent creation of `__pycache__` directories.

2. **Cleanup Scripts**: Use the following scripts to clean up existing `__pycache__` directories:

   - Windows:

     ```bash
     scripts\clean_pycache.bat
     ```

   - Unix/Linux/Mac:

     ```bash
     chmod +x scripts/clean_pycache.sh
     ./scripts/clean_pycache.sh
     ```

   - Direct Python execution:

     ```bash
     python scripts/clean_pycache.py
     ```

3. **Git Ignore**: The `.gitignore` file is configured to exclude `__pycache__` directories from version control.

## API Endpoints

### Extract Website Data

```http
POST /api/v1/extract
```

Extracts data from a website URL.

**Request Body:**

```json
{
  "url": "https://example.com"
}
```

### Extract Markdown Content

```http
POST /api/v1/markdown/getmd
```

Extracts markdown content from multiple URLs using Hyperbrowser API.

**Request Body:**

```json
{
  "urls": [
    "https://example.com",
    "https://another-site.com"
  ]
}
```

**Response:**

```json
{
  "job_id": "962372c4-a140-400b-8c26-4ffe21d9fb9c",
  "status": "pending",
  "message": "Markdown extraction job started successfully",
  "total_urls": 2
}
```

### Check Markdown Extraction Status

```http
GET /api/v1/markdown/getmd/{job_id}/status
```

Checks the status of a markdown extraction job.

**Response:**

```json
{
  "job_id": "962372c4-a140-400b-8c26-4ffe21d9fb9c",
  "status": "completed",
  "total_urls": 2,
  "completed_urls": 2,
  "message": "Job status: completed"
}
```

### Get Markdown Extraction Results

```http
GET /api/v1/markdown/getmd/{job_id}
```

Returns the markdown content and extracted links for each URL.

**Response:**

```json
{
  "job_id": "962372c4-a140-400b-8c26-4ffe21d9fb9c",
  "status": "completed",
  "total_urls": 2,
  "completed_urls": 2,
  "results": [
    {
      "url": "https://example.com",
      "status": "completed",
      "markdown_text": "# Example Page\nThis is content...",
      "metadata": {
        "title": "Example Page",
        "description": "A sample webpage"
      },
      "links": [
        "https://example.com/about",
        "https://example.com/contact"
      ]
    },
    {
      "url": "https://another-site.com",
      "status": "completed",
      "markdown_text": "# Another Site\nMore content...",
      "metadata": {
        "title": "Another Site",
        "description": "Another sample webpage"
      },
      "links": [
        "https://another-site.com/products",
        "https://another-site.com/services"
      ]
    }
  ]
}
```

**Response:**

```json
{
  "company_name": "Acme Inc.",
  "address": "123 Main St, Anytown, USA",
  "contact_info": {
    "email": "info@acme.com",
    "phone": "+1 (555) 123-4567"
  },
  "about_us": "Acme Inc. is a leading provider of...",
  "why_us": "We have 20 years of experience...",
  "services_offered": ["Web Development", "Mobile Apps", "UI/UX Design"],
  "team_members": [
    {
      "name": "John Doe",
      "role": "CEO",
      "bio": "John has 15 years of experience...",
      "image_url": "https://example.com/john.jpg"
    }
  ],
  "tech_stack": ["React", "Node.js", "Python"],
  "projects": [
    {
      "name": "Project Alpha",
      "description": "A web application for...",
      "image_url": "https://example.com/alpha.jpg",
      "url": "https://example.com/projects/alpha"
    }
  ],
  "social_links": [
    "https://twitter.com/acme",
    "https://linkedin.com/company/acme"
  ],
  "logo_url": "https://example.com/logo.png",
  "color_palette": ["#1a2b3c", "#4d5e6f", "#7g8h9i"],
  "header_info": "Navigation includes Home, Services, About, Contact",
  "footer_info": "Copyright 2023 Acme Inc. All rights reserved."
}
```

## Future Implementation

The current implementation includes placeholders for the following functionality:

- Call Hyperbrowser to extract structured data (Name, Address, About, Services, Team, Tech, Projects, Socials)
- Use Hyperbrowser/other tool to get data for Logo/Color analysis (e.g., screenshot, HTML)
- Extract Logo URL from HTML/Data
- Use Pylette to extract color palette from screenshot/image data
- Attempt to identify Header/Footer base URLs or content
- Combine all extracted data into the response schema

## Authentication

The project includes JWT utilities for authentication, but the current endpoints are not protected. To implement authentication:

1. Create a login endpoint that returns a JWT token
2. Use the `get_current_user` dependency from `app/utils/jwt_handler.py` to protect endpoints

## Development

### Adding New Endpoints

1. Create a new file in `app/api/v1/endpoints/`
2. Define your router and endpoints
3. Include the router in `app/api/v1/api.py`

### Adding New Models

1. Create or update files in `app/schemas/`
2. Define your Pydantic models
3. Use the models in your endpoints

## Dependencies

- FastAPI: Web framework
- Uvicorn: ASGI server
- Pydantic: Data validation
- Python-jose: JWT handling
- Hyperbrowser: Website data extraction
- Pylette: Color palette extraction


POST /api/v1/extract
Body: { "url": "https://example.com" }

Check job status:
GET /api/v1/extract/{job_id}/status

Get extraction results:
GET /api/v1/extract/{job_id}
