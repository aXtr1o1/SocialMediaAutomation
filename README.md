# SocialMediaAutomation

SocialMediaAutomation is an AI-powered social media content automation platform that discovers relevant information from trusted web sources, processes the content into clean AI-ready data, generates platform-specific social media posts, and publishes approved content through connected social media accounts.

The platform is designed around a complete content lifecycle:

```text
User
  ↓
Authentication
  ↓
Domain Selection
  ↓
Subdomain Selection
  ↓
Validated Sources
  ↓
Article Discovery
  ↓
Content Processing
  ↓
Article Selection
  ↓
AI Content Generation
  ↓
User Review
  ↓
Partial Regeneration
  ↓
Connected Social Account
  ↓
Publication
  ↓
Publication History
```

The supported social media platforms are:

* LinkedIn
* Bluesky

The current backend content-processing workflow ends at **Processed Content**. Social media generation and publication are downstream stages of the overall application.

---

# Project Overview

Creating high-quality social media content from trusted industry information normally requires several manual steps:

* Finding reliable sources
* Identifying recent articles
* Checking whether the content is relevant
* Extracting useful information
* Cleaning the article content
* Summarizing and adapting the information
* Creating platform-specific social media posts
* Reviewing generated content
* Connecting social media accounts
* Publishing the final content
* Tracking publication results

SocialMediaAutomation is designed to automate these steps while keeping the user involved in the content selection, review, regeneration, and publication process.

The platform uses predefined domains, subdomains, and validated sources to control which websites participate in content discovery.

---

# Main Application Workflow

The complete application workflow is:

```text
                    ┌─────────────────────┐
                    │        User         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Authentication    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Domain / Subdomain  │
                    │     Selection       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Validated Sources   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Article Discovery   │
                    │    and Crawling     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Content Processing  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Article Selection │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   AI Generation     │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
              ┌───────────┐         ┌───────────┐
              │ LinkedIn  │         │  Bluesky  │
              └─────┬─────┘         └─────┬─────┘
                    │                     │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │    User Review      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Partial Regeneration│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Connected Account   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Publish        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Publication History │
                    └─────────────────────┘
```

---

# Current Backend Content Workflow

The current backend workflow starts from the configured domain and processes content until clean, relevant content is stored.

```text
Configured Domain
       ↓
Existing Subdomains
       ↓
source_subdomain_mapping
       ↓
Mapped Sources
       ↓
Source Validation
       ↓
Eligible Sources
       ↓
Crawl Source URLs
       ↓
Article Discovery
       ↓
Relevance Matching
       ↓
Content Cleaning
       ↓
Processed Content
```

The workflow is started using:

```http
POST /processing/run
```

The endpoint:

1. Authenticates the request.
2. Reads the configured workflow domain.
3. Retrieves the existing subdomains.
4. Resolves sources through `source_subdomain_mapping`.
5. Identifies eligible sources.
6. Crawls the mapped source URLs.
7. Discovers available articles.
8. Applies relevance matching after crawling and validation.
9. Cleans and normalizes relevant content.
10. Stores processed content.

The endpoint does **not** generate or publish social media posts.

---

# Core Features

## Authentication

The platform uses authenticated users to associate application data and connected social accounts with the correct user.

The authentication workflow is:

```text
User
  ↓
SSO / Authentication
  ↓
Authenticated Session
  ↓
Application User
```

The application maintains the authenticated user throughout the workflow.

---

## Domain Management

Content is organized using predefined domains.

A domain represents a broad business or technical topic.

Example:

```text
Artificial Intelligence
```

---

## Subdomain Management

Each domain can contain multiple subdomains.

Example:

```text
Artificial Intelligence
│
├── Generative AI
├── AI Agents
├── Machine Learning
└── Deep Learning
```

The user selects a domain and subdomain before starting content discovery.

Only active domains and subdomains are available for normal workflow operations.

---

# Validated Source Management

Sources are predefined and validated before they are used by the normal content workflow.

The system does not dynamically perform complete source validation every time a user starts content discovery.

The source relationship is:

```text
Domain
   ↓
Subdomain
   ↓
source_subdomain_mapping
   ↓
Source
```

A source contains information such as:

```text
Source ID
Source Name
Website URL
Domain Mapping
Subdomain Mapping
Validation Status
Active Status
Last Crawled Timestamp
Created Timestamp
Updated Timestamp
```

Only sources that are both:

```text
Validated
+
Active
```

are eligible for crawling.

Invalid, rejected, or inactive sources are excluded.

---

# Source Selection Flow

The source selection process is:

```text
Configured Domain
        ↓
Existing Subdomains
        ↓
source_subdomain_mapping
        ↓
Mapped Sources
        ↓
Validation Status
        ↓
Active Status
        ↓
Eligible Sources
```

The crawler must not crawl arbitrary websites outside the configured source mapping.

This provides controlled source discovery and prevents unapproved websites from entering the content pipeline.

---

# KPI Validation

Source quality is evaluated through the project's source validation process.

The validation layer can maintain KPI evaluation results and a validation status for each source.

The source validation flow is:

```text
Mapped Source
      ↓
KPI Validation
      ↓
Validation Result
      ↓
Passed / Rejected
      ↓
Eligible for Crawling / Excluded
```

The source validation data is stored separately so that the application can maintain a history of source quality evaluation.

The normal user workflow uses sources that have already been validated.

Dynamic full KPI validation is not performed every time the user selects a domain or subdomain.

---

# Content Discovery and Crawling

The crawler retrieves recent content from eligible sources.

The crawler attempts to identify the latest available articles.

Where available, article extraction includes:

* Article title
* Article URL
* Canonical URL
* Publication date
* Author
* Article body
* Metadata
* Source information

The article lifecycle is:

```text
Validated Source
      ↓
Source URL
      ↓
Crawler
      ↓
Article Discovery
      ↓
Article Extraction
      ↓
Crawled Article
```

---

# Article Identity and Duplicate Handling

The system maintains article identity and freshness information.

This prevents previously discovered articles from unnecessarily triggering duplicate downstream processing.

Article information can include:

```text
Article ID
Source ID
Domain ID
Subdomain ID
Title
URL
Canonical URL
Author
Published At
Raw Content
Processed Content
Content Hash
Crawl Status
Processing Status
Created At
Updated At
```

The separation between article storage and AI-generated content is important because one article can produce multiple AI generations.

The lifecycle is:

```text
One Article
     │
     ├── Generation Session 1
     │      └── Draft Versions
     │
     ├── Generation Session 2
     │      └── Draft Versions
     │
     └── Generation Session 3
            └── Draft Versions
```

---

# Crawl Failure Handling

Crawling is designed to be fault tolerant.

A failure from one source should not terminate the entire multi-source crawl.

Example:

```text
Source A → Success
Source B → Success
Source C → Failed
Source D → Success
Source E → Success
```

The workflow continues with:

```text
Source A
Source B
Source D
Source E
```

while recording the failure for:

```text
Source C
```

This prevents a single website failure from stopping the complete content-discovery process.

---

# Relevance Matching

After crawling and source validation, articles are evaluated for relevance.

The relevance workflow can use:

```text
Keyword Matching
       +
Fuzzy Matching
       +
Gemini Matching
```

The important processing order is:

```text
Source Validation
       ↓
Crawling
       ↓
Article Discovery
       ↓
Relevance Matching
       ↓
Content Processing
```

Relevance matching is not performed against arbitrary URLs before they have passed through the source and crawling workflow.

Only relevant articles continue as usable content.

---

# Content Preprocessing

The content preprocessing layer converts raw scraped content into clean, structured information suitable for AI processing.

The processing pipeline is:

```text
Raw Web Content
      ↓
HTML Extraction
      ↓
Main Article Identification
      ↓
Remove Irrelevant HTML
      ↓
Remove Navigation
      ↓
Remove Footer
      ↓
Remove Advertisements
      ↓
Remove Boilerplate
      ↓
Normalize Text
      ↓
Clean Article Content
      ↓
Processed Content
```

The purpose of preprocessing is to provide the AI generation layer with useful article information instead of raw website HTML.

---

# Processed Content

Processed content is stored separately from raw crawled content.

The relationship is:

```text
Crawled Article
      ↓
Content Processing
      ↓
Processed Content
```

Processed content is the AI-ready representation of the article.

It can contain:

* Article title
* Clean article body
* Author
* Publication date
* Source
* URL
* Processing metadata

Keeping processed content separate from the raw article provides better traceability and allows the same content to be reused for multiple AI generation sessions.

---

# Article Selection

The system does not automatically send every discovered article to the AI model.

The intended workflow is:

```text
Discover
   ↓
Display
   ↓
User Selects Article
   ↓
Process / Retrieve AI-Ready Content
   ↓
Generate
```

This provides user control and avoids unnecessary AI generation.

The user selects the article before generating a social media post.

---

# AI Content Generation

AI generation converts processed source content into social media content.

The AI generation layer considers:

* Processed article content
* Target platform
* Platform audience
* Platform constraints
* Prompt configuration
* Platform-specific generation rules

The system must not simply generate one generic post and copy it to every platform.

Instead:

```text
Processed Article
       ↓
Platform Context
       ↓
Platform-Specific Generation
```

The AI provider and model are configurable rather than being tightly coupled to business logic.

---

# AI Grounding

Generated content should primarily be based on the processed source content.

The AI layer should:

* Use the provided processed content as the primary source.
* Avoid unsupported factual claims.
* Receive the target platform explicitly.
* Use a platform-specific prompt configuration.
* Return a clear failure state when generation fails.

The generation abstraction can conceptually operate as:

```text
generate_initial_post(
    content,
    platform,
    generation_config
)
```

and return structured content:

```text
{
    hookText,
    bodyText,
    hashtags,
    ctaText
}
```

---

# LinkedIn Content Generation

LinkedIn content is generated separately from Bluesky content.

The LinkedIn generation strategy is optimized for a professional audience.

It should support:

* Professional communication
* Clear business or industry context
* Useful insights
* Readable structure
* Appropriate hashtags
* Platform-compatible length

The objective is to create an informative and engaging professional post grounded in the source content.

---

# Bluesky Content Generation

Bluesky uses a separate generation configuration.

The generation strategy considers:

* Shorter communication style
* Concise structure
* Platform character constraints
* Platform audience behavior
* Relevant tags or links where appropriate

The same article can therefore produce:

```text
Article
   ├── LinkedIn Generation
   └── Bluesky Generation
```

The two generations are stored independently.

---

# Generation Sessions

A generation session connects selected processed content with generated drafts.

The relationship is:

```text
Processed Content
      ↓
Generation Session
      ↓
Draft Version 1
      ↓
Draft Version 2
      ↓
Draft Version 3
      ↓
...
```

Generation sessions allow the application to maintain a complete history of the content generation process.

---

# Initial Draft Structure

The initial generated post is divided into four segments:

```text
Hook
Body
Hashtags
CTA
```

Example:

```text
Draft Version 1

Hook:
A new development in AI is changing...

Body:
The article explains...

Hashtags:
#AI #MachineLearning #Technology

CTA:
What do you think about this development?
```

Each segment is stored separately.

---

# Partial Regeneration

The application uses segment-based regeneration.

The user selects exactly one segment to regenerate.

For example:

```text
Current Draft
     ↓
Select Body
     ↓
Provide Instruction
     ↓
Regenerate Body
     ↓
Create New Draft Version
```

Example instruction:

```text
Make the body more concise and professional.
```

Only the selected segment is changed.

The other segments are carried forward unchanged.

---

# Immutable Draft Versions

Previous draft versions are never destructively overwritten.

Example:

```text
Version 1
├── Hook A
├── Body A
├── Hashtags A
└── CTA A
        ↓
Regenerate Body
        ↓
Version 2
├── Hook A
├── Body B
├── Hashtags A
└── CTA A
```

The system maintains the version history so that previous generated content remains traceable.

Every regeneration creates a new draft version.

---

# Social Account Connections

Users can connect supported social media accounts.

Supported platforms:

* LinkedIn
* Bluesky

The connected account belongs to the authenticated application user.

A connected account maintains information required to identify and use the corresponding social platform account.

Typical connection states include:

```text
CONNECTED
DISCONNECTED
EXPIRED
ERROR
```

The application verifies the account connection before publication.

---

# LinkedIn Account Connection

The LinkedIn integration allows the authenticated user to connect a LinkedIn account for publishing.

The general workflow is:

```text
User
  ↓
Connect LinkedIn
  ↓
Platform Authentication
  ↓
Callback
  ↓
Store Connection
  ↓
Connected Account
```

The account must be connected before content can be published through it.

---

# Bluesky Account Connection

Bluesky follows the same overall account lifecycle:

```text
User
  ↓
Connect Bluesky
  ↓
Platform Authentication
  ↓
Store Connection
  ↓
Connected Account
```

The connected account is associated with the authenticated application user.

---

# User Review

Generated content is reviewed before publication.

The review workflow is:

```text
Generated Draft
      ↓
User Review
      ↓
Accept
      │
      ├── Publish
      │
      └── Regenerate Selected Segment
```

The application maintains user control over the final content.

Automatic publishing without user confirmation is not part of the normal workflow.

---

# Publishing

The publishing workflow is:

```text
Approved Draft
      ↓
Select Platform
      ↓
Select Connected Account
      ↓
Verify Account Connection
      ↓
Publish
      ↓
Capture Platform Response
      ↓
Store Publication Result
```

Users publish only through their connected social media accounts.

The selected generated content is published to the selected platform.

---

# Publication Status

Publication status supports at least:

```text
PENDING
PUBLISHED
FAILED
```

The publication record can contain:

```text
Platform
Connected Account
Generation Version
Publication Status
Platform Post ID
Publication Timestamp
Failure Reason
```

A failed social platform API request must never be recorded as a successful publication.

---

# Idempotent Publishing

The publishing layer must protect against duplicate publication.

Repeated clicks or network retries must not accidentally create duplicate social media posts.

The conceptual flow is:

```text
Publish Request
      ↓
Check Existing Publication
      ↓
Already Published?
   ┌──────┴──────┐
  Yes            No
   │              │
   ▼              ▼
Return Existing  Publish
Result             │
                   ▼
             Store Result
```

This ensures that publication is handled safely even when requests are repeated.

---

# Publication History

Publication history maintains the record of completed and failed publication operations.

A publication event can contain:

```text
Publication ID
Platform
Account
Generation Version
Publication Status
Platform Post ID
Publication Timestamp
Failure Reason
```

The history allows the application to trace:

```text
Article
  ↓
Processed Content
  ↓
Generation
  ↓
Draft Version
  ↓
Publication
```

---

# Database Architecture

Supabase/PostgreSQL is used as the persistent database.

The database maintains data required throughout the application lifecycle.

Major entities include:

```text
users
domains
subdomains
connected_accounts
source_subdomain_mapping
sources
source_validations
crawler_jobs
crawled_articles
processed_content
generation_sessions
drafts
published_posts
publication_events
operation_logs
```

---

# Database Relationships

The main content relationship is:

```text
User
  │
  ├── Connected Accounts
  │
  └── Workflow Data
          │
          ▼
       Domain
          │
          ▼
      Subdomain
          │
          ▼
Source/Subdomain Mapping
          │
          ▼
        Source
          │
          ▼
   Source Validation
          │
          ▼
    Crawler Job
          │
          ▼
   Crawled Article
          │
          ▼
 Processed Content
          │
          ▼
 Generation Session
          │
          ▼
       Drafts
          │
          ▼
  Published Posts
          │
          ▼
 Publication Events
```

This separation keeps the different lifecycle stages independent and traceable.

---

# Article and AI Data Separation

Article data and AI-generated content are stored separately.

The architecture follows:

```text
Article
   ↓
Processed Content
   ↓
Generation
   ↓
Draft
   ↓
Publication
```

The system should not store the complete workflow as one single post record.

This allows:

* One article to produce multiple generations.
* One generation session to contain multiple versions.
* Multiple versions to remain immutable.
* Publications to reference the selected generation.
* Article data to remain independent from publication data.

---

# Operational Logging

The application maintains operational logs for important workflow events.

Important events include:

```text
User Login
Domain Selection
Subdomain Selection
Crawl Started
Crawl Completed
Crawl Failed
Article Processing
AI Generation
AI Partial Regeneration
Social Account Connection
Publication Attempt
Publication Success
Publication Rejection
Publication Failure
```

Sensitive credentials must never be included in logs.

The logging layer is intended to support troubleshooting and operational traceability.

---

# Error Handling

The backend uses predictable error states for major workflow failures.

Major error categories include:

```text
Authentication Failure
No Sources Available
Crawler Failure
No Latest Articles Found
Article Extraction Failure
Content Processing Failure
AI Generation Failure
Regeneration Failure
Social Account Not Connected
Social Credential Invalid/Expired
Publishing Failure
```

The API should return structured errors rather than exposing raw backend exceptions.

---

# Reliability

The platform is designed to isolate failures wherever possible.

For example:

```text
Source A
   ↓
Success

Source B
   ↓
Success

Source C
   ↓
Failure

Source D
   ↓
Success
```

The failure of Source C does not stop Sources A, B, and D from being processed.

The same principle applies to external integrations where practical.

---

# Security

The application follows these security principles:

* Protected endpoints require authentication.
* Supabase bearer tokens are used for authenticated operations.
* Credentials are stored in environment variables.
* `.env` files must not be committed.
* Access tokens must not be written to logs.
* Social account connections must be verified before publishing.
* Expired credentials must be handled safely.
* Internal exceptions should not be exposed to clients.
* Publication must occur only through the authenticated user's connected account.

---

# Technology Stack

| Layer                 | Technology             |
| --------------------- | ---------------------- |
| Frontend              | React                  |
| Frontend Styling      | Tailwind CSS           |
| API                   | REST API               |
| Backend               | FastAPI                |
| Validation            | Pydantic               |
| ORM / Database Access | SQLAlchemy             |
| Database              | Supabase / PostgreSQL  |
| Authentication        | SSO / OAuth 2.0        |
| AI                    | Gemini API              |
| Content Sources       | Pre-validated websites |
| Social Platform       | LinkedIn API            |
| Social Platform       | Bluesky API             |

The AI provider is designed to remain configurable rather than being hard-coded throughout the business logic.

---

# Backend Architecture

The backend is separated into logical services.

```text
Authentication Service
        ↓
Domain Service
        ↓
Source Service
        ↓
Crawler Service
        ↓
Content Processing Service
        ↓
AI Generation Service
        ↓
Social Connection Service
        ↓
Publishing Service
        ↓
History Service
```

Each service has a specific responsibility.

---

# Authentication Service

Responsible for:

* SSO authentication
* User identification
* User persistence
* Session management
* Logout

---

# Domain Service

Responsible for:

* Retrieving domains
* Retrieving subdomains
* Returning active domains
* Returning active subdomains

---

# Source Service

Responsible for:

* Retrieving mapped sources
* Source validation state
* Active source filtering
* Source/subdomain mapping

---

# Crawler Service

Responsible for:

* Crawling validated sources
* Discovering latest articles
* Extracting article information
* Detecting duplicate articles
* Recording crawl status
* Isolating crawler failures

---

# Content Processing Service

Responsible for:

* Removing irrelevant HTML
* Removing boilerplate
* Cleaning article content
* Normalizing extracted text
* Preparing AI-ready content

---

# AI Generation Service

Responsible for:

* Initial post generation
* Platform-specific generation
* Segment-based regeneration
* Draft version management
* AI failure handling

---

# Social Connection Service

Responsible for:

* Connecting LinkedIn accounts
* Connecting Bluesky accounts
* Storing connected account information
* Handling platform authentication callbacks
* Disconnecting accounts
* Maintaining account state

---

# Publishing Service

Responsible for:

* Validating the selected social account
* Publishing selected generated content
* Capturing platform responses
* Recording publication status
* Preventing duplicate publication

---

# History Service

Responsible for:

* Publication history
* Operational events
* Workflow traceability
* Troubleshooting information

---

# API

The application follows a REST API architecture.

The main API areas are:

```text
/auth
/domains
/subdomains
/articles
/processed-content
/generation
/social-accounts
/publications
```

---

# Authentication API

Typical authentication operations include:

```http
POST /auth/sso
GET /auth/callback
POST /auth/logout
GET /auth/me
```

These endpoints handle authentication, callback processing, session management, and the current authenticated user.

---

# Domain API

Retrieve active domains:

```http
GET /domains
```

Retrieve subdomains belonging to a domain:

```http
GET /domains/{domain_id}/subdomains
```

---

# Source API

Retrieve validated and active sources mapped to a subdomain:

```http
GET /subdomains/{subdomain_id}/sources
```

---

# Article API

Discover latest articles:

```http
POST /articles/discover
```

Retrieve discovered articles:

```http
GET /articles
```

Retrieve an individual article:

```http
GET /articles/{article_id}
```

---

# Processed Content API

Retrieve AI-ready processed content for an article:

```http
GET /processed-content/{article_id}
```

---

# Processing API

Start the current backend content workflow:

```http
POST /processing/run
```

The endpoint uses:

```env
WORKFLOW_DOMAIN_ID=<domain-id>
```

and resolves the workflow through the configured domain, existing subdomains, and `source_subdomain_mapping`.

---

# Generation API

Create an initial generation session:

```http
POST /generation/generate
```

The initial generation produces the four structured segments:

```text
Hook
Body
Hashtags
CTA
```

---

# Regeneration API

Regenerate one selected segment:

```http
POST /generation/{session_id}/regenerate-segment
```

The request contains:

```json
{
  "draftId": "<draft-id>",
  "segmentKey": "<segment-key>",
  "instruction": "<natural-language-instruction>"
}
```

Only the selected segment is regenerated.

A new draft version is created.

---

# Generation Session API

Retrieve the current generation session:

```http
GET /generation/{session_id}
```

Retrieve all draft versions:

```http
GET /generation/{session_id}/versions
```

---

# Social Account API

Retrieve connected accounts:

```http
GET /social-accounts
```

Connect a platform:

```http
POST /social-accounts/{platform}/connect
```

Handle platform callback:

```http
GET /social-accounts/{platform}/callback
```

Disconnect an account:

```http
DELETE /social-accounts/{account_id}
```

---

# Publication API

Publish selected content:

```http
POST /publications
```

Retrieve publication history:

```http
GET /publications
```

Retrieve publication details:

```http
GET /publications/{publication_id}
```

---

# Environment Configuration

Create:

```text
backend/.env
```

Configure the required environment values.

Example:

```env
WORKFLOW_DOMAIN_ID=<domain-id>

SUPABASE_URL=<supabase-project-url>
SUPABASE_KEY=<supabase-key>

GEMINI_API_KEY=<gemini-api-key>
```

Additional platform credentials should be configured through environment variables or the application's secure configuration mechanism when the corresponding integrations are enabled.

Do not hard-code credentials in Python source files.

---

# Backend Installation

Navigate to the backend:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Database Migration

The content workflow requires the additive database migration:

```text
backend/sql/20260818_content_workflow_extension.sql
```

Run the migration from the Supabase SQL Editor.

Recommended process:

```text
Supabase Dashboard
        ↓
SQL Editor
        ↓
New Query
        ↓
Open 20260818_content_workflow_extension.sql
        ↓
Copy SQL
        ↓
Paste into SQL Editor
        ↓
Run
```

Verify that the migration completes successfully before starting the backend workflow.

---

# Running the Backend

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The backend will normally be available at:

```text
http://127.0.0.1:8000
```

Swagger API documentation:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

# Running the Current Content Workflow

After:

1. Installing dependencies
2. Configuring `.env`
3. Running the Supabase migration
4. Starting the FastAPI server
5. Obtaining a valid Supabase bearer token

start processing with:

```http
POST /processing/run
```

Example:

```bash
curl -X POST http://127.0.0.1:8000/processing/run \
  -H "Authorization: Bearer <SUPABASE_ACCESS_TOKEN>"
```

The processing flow is:

```text
Bearer Token
     ↓
Authenticated User
     ↓
Configured Domain
     ↓
Existing Subdomains
     ↓
source_subdomain_mapping
     ↓
Eligible Sources
     ↓
Crawling
     ↓
Article Discovery
     ↓
Relevance Matching
     ↓
Content Processing
     ↓
Processed Content
```

---

# Development Setup

A typical local development environment is:

```text
Developer Machine
       │
       ├── Python
       │
       ├── FastAPI
       │
       ├── SQLAlchemy
       │
       └── Application Services
                │
                ▼
          Supabase/PostgreSQL
                │
                ├── Users
                ├── Domains
                ├── Sources
                ├── Articles
                ├── Processed Content
                ├── Drafts
                └── Publications
```

External services are integrated through dedicated service layers.

---

# Project Structure

A typical backend structure is:

```text
SocialMediaAutomation/
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── prompts/
│   │   └── main.py
│   │
│   ├── sql/
│   │   └── 20260818_content_workflow_extension.sql
│   │
│   ├── requirements.txt
│   ├── .env
│   └── ...
│
├── README.md
└── ...
```

The internal modules may be extended as additional workflow services are implemented.

---

# Data Flow

The main data flow through the backend is:

```text
User
  ↓
Domain
  ↓
Subdomain
  ↓
Source Mapping
  ↓
Validated Source
  ↓
Crawler Job
  ↓
Crawled Article
  ↓
Processed Content
  ↓
Generation Session
  ↓
Draft Version
  ↓
Published Post
  ↓
Publication Event
```

Each stage has its own persistent representation.

---

# Current Processing Boundary

The currently implemented processing endpoint ends at:

```text
Crawling
   ↓
Article Discovery
   ↓
Relevance Matching
   ↓
Content Cleaning
   ↓
Processed Content
```

It does not automatically execute:

```text
Processed Content
   ↓
AI Generation
   ↓
User Review
   ↓
Partial Regeneration
   ↓
Social Account Selection
   ↓
Publication
```

This separation allows the content-processing pipeline to be tested independently from AI generation and social media publishing.

---

# Complete End-to-End Workflow

Once all application stages are connected, the complete workflow becomes:

```text
1. User Authentication
        ↓
2. Select Domain
        ↓
3. Select Subdomain
        ↓
4. Retrieve Validated Sources
        ↓
5. Discover Latest Articles
        ↓
6. Select Relevant Article
        ↓
7. Process Article
        ↓
8. Generate Platform-Specific Content
        ↓
9. Review Generated Content
        ↓
10. Regenerate Selected Segment if Required
        ↓
11. Create New Draft Version
        ↓
12. Select Connected Social Account
        ↓
13. Verify Connection
        ↓
14. Publish
        ↓
15. Store Publication Result
        ↓
16. Maintain Publication History
```

---

# Design Principles

## Pre-Validated Sources

Only validated and active sources participate in the normal crawling workflow.

---

## User-Controlled Article Selection

The application discovers articles first.

The user selects the content before AI generation.

```text
Discover
   ↓
Display
   ↓
Select
   ↓
Generate
```

This reduces unnecessary AI processing and keeps the user in control.

---

## Platform-Specific Generation

LinkedIn and Bluesky use separate generation configurations.

The application does not use:

```text
Generate Generic Post
        ↓
Copy to LinkedIn
        ↓
Copy to Bluesky
```

Instead:

```text
Article
   ↓
Platform Context
   ├── LinkedIn Generation
   └── Bluesky Generation
```

---

## Segment-Based Regeneration

The application does not regenerate the entire post when the user wants to change one section.

Instead:

```text
Draft
 ├── Hook
 ├── Body
 ├── Hashtags
 └── CTA
      ↓
Select One Segment
      ↓
Regenerate
      ↓
New Version
```

---

## Immutable Version History

Existing draft versions are preserved.

Each regeneration creates a new version.

---

## Separate Lifecycle Data

Article data, generation data, and publication data remain separate.

```text
Article
   ↓
Generation
   ↓
Publication
```

This prevents unrelated lifecycle information from being stored as one record.

---

## Idempotent Publishing

Repeated requests must not unintentionally create duplicate social media posts.

---

## Failure Isolation

One failed source must not stop unrelated sources from being processed.

---

# Error Scenarios

The application handles the following major scenarios:

### Authentication Failure

Returned when the user cannot be authenticated.

### No Sources Available

Returned when no eligible sources are mapped to the selected workflow.

### Crawler Failure

Recorded when an individual source cannot be crawled.

### No Latest Articles Found

Returned when eligible sources do not provide usable latest articles.

### Article Extraction Failure

Recorded when article content cannot be extracted successfully.

### Content Processing Failure

Returned when article content cannot be converted into usable processed content.

### AI Generation Failure

Returned when the AI provider fails to generate content.

### Regeneration Failure

Returned when a selected draft segment cannot be regenerated.

### Social Account Not Connected

Returned when the user attempts to publish without a valid connected account.

### Social Credential Invalid or Expired

Returned when the platform credentials cannot be used.

### Publishing Failure

Recorded when the selected social platform rejects or fails the publication request.

---

# Logging and Monitoring

The system records important operational events.

Example:

```text
Authentication
     ↓
Domain Selection
     ↓
Source Selection
     ↓
Crawl Started
     ↓
Crawl Completed / Failed
     ↓
Article Processing
     ↓
AI Generation
     ↓
Regeneration
     ↓
Publication Attempt
     ↓
Publication Success / Failure
```

Sensitive information such as:

```text
Passwords
API Keys
OAuth Secrets
Access Tokens
```

must never be included in logs.

---

# Performance and Reliability

Crawling and AI generation depend on external systems and can take variable amounts of time.

The application should expose clear processing states where appropriate.

Long-running operations should not make the user assume that the request has failed simply because external processing takes time.

Multi-source crawling should continue even when one source fails.

---

# Maintainability

The backend should remain modular.

Recommended service boundaries are:

```text
Authentication Service
Domain Service
Source Service
Crawler Service
Content Processing Service
AI Generation Service
Social Connection Service
Publishing Service
History Service
```

This separation makes it easier to:

* Replace an external integration.
* Change the AI provider.
* Add a new social platform.
* Modify crawling behavior.
* Change content-processing logic.
* Extend publication tracking.
* Test services independently.

---

# Future Platform Support

The architecture is designed so additional platforms can be introduced later.

Potential future platforms include:

* Facebook
* X
* Instagram

The current supported platforms remain:

* LinkedIn
* Bluesky

Additional platforms should be added through separate platform-specific integrations rather than modifying the existing LinkedIn or Bluesky implementation.

---

# Future Extensions

The architecture can later support:

* Additional domains
* Additional source providers
* Scheduled publishing
* Advanced source administration
* Analytics
* Engagement tracking
* Campaign management
* Additional AI providers
* Additional social media platforms
* Advanced operational dashboards
* More sophisticated access control

These extensions should be added without coupling unrelated workflow stages.

---

# Out of Scope for the Current Workflow

The current `/processing/run` content workflow does not perform:

* AI post generation
* LinkedIn publishing
* Bluesky publishing
* Social account selection
* Draft regeneration
* Publication history creation

These are downstream application stages.

The overall platform can support them as separate services and APIs.

---

# Troubleshooting

## Backend Does Not Start

Check Python:

```bash
python --version
```

Make sure the virtual environment is active.

Then reinstall dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment Variables Are Missing

Verify:

```text
backend/.env
```

contains the required configuration:

```env
WORKFLOW_DOMAIN_ID=<domain-id>
SUPABASE_URL=<supabase-project-url>
SUPABASE_KEY=<supabase-key>
GEMINI_API_KEY=<gemini-api-key>
```

---

## Database Errors

Check:

1. Supabase project availability.
2. Supabase URL.
3. Supabase key.
4. Database migration status.
5. Required tables.
6. Required columns.
7. Database relationships.

Run:

```text
backend/sql/20260818_content_workflow_extension.sql
```

if the content workflow migration has not yet been applied.

---

## Authentication Error

Verify that the request contains:

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
```

The token must belong to a valid authenticated user.

---

## No Sources Are Found

Verify:

```text
Domain
   ↓
Subdomain
   ↓
source_subdomain_mapping
   ↓
Source
```

Then verify that the source is:

```text
Validated
+
Active
```

---

## No Articles Are Found

Check the following workflow:

```text
Source Validation
       ↓
Crawling
       ↓
Article Discovery
       ↓
Article Extraction
       ↓
Relevance Matching
```

A source may produce no stored article if:

* It is not active.
* It is not validated.
* Crawling failed.
* No recent articles were found.
* Article extraction failed.
* The article was not relevant.
* Processing failed.

---

## Gemini Generation Failure

Check:

```text
GEMINI_API_KEY
```

and verify that the configured AI provider/model is available.

Also check application logs for the generation failure without exposing credentials.

---

## Publication Failure

Verify:

1. The user is authenticated.
2. The selected social account is connected.
3. The connection is valid.
4. The selected platform matches the generated content.
5. The platform credentials are valid.
6. The platform API request succeeded.

A failed publication must remain recorded as:

```text
FAILED
```

and must not be marked as:

```text
PUBLISHED
```

---

# Development Commands

Create virtual environment:

```bash
python -m venv .venv
```

Activate on Windows:

```bash
.venv\Scripts\activate
```

Activate on Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start development server:

```bash
uvicorn app.main:app --reload
```

Start production-style server:

```bash
uvicorn app.main:app
```

Open Swagger:

```text
http://127.0.0.1:8000/docs
```

Open ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

# Quick Start

The shortest setup path is:

```bash
git clone <repository-url>
cd SocialMediaAutomation
cd backend
```

Create and activate the virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create:

```text
backend/.env
```

Configure:

```env
WORKFLOW_DOMAIN_ID=<domain-id>
SUPABASE_URL=<supabase-project-url>
SUPABASE_KEY=<supabase-key>
GEMINI_API_KEY=<gemini-api-key>
```

Run the database migration:

```text
backend/sql/20260818_content_workflow_extension.sql
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Then start the content-processing workflow:

```http
POST /processing/run
```

with:

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
```

---

# Current Workflow Summary

The current backend processing pipeline is:

```text
Configured Domain
       ↓
Existing Subdomains
       ↓
Source/Subdomain Mapping
       ↓
Validated + Active Sources
       ↓
Crawl Every Mapped Source URL
       ↓
Article Discovery
       ↓
Article Extraction
       ↓
Keyword Matching
       ↓
Fuzzy Matching
       ↓
Gemini Matching
       ↓
Relevant Articles
       ↓
Content Cleaning
       ↓
Processed Content
```

The current workflow ends at:

```text
PROCESSED CONTENT
```

The next application stage can consume this processed content for platform-specific AI generation.

---

# Complete Platform Summary

SocialMediaAutomation separates the application into clear lifecycle stages:

```text
                    CONTENT LIFECYCLE

Domain
  ↓
Subdomain
  ↓
Validated Source
  ↓
Crawled Article
  ↓
Processed Content
        │
        ▼
   GENERATION
        │
        ▼
Generation Session
        ↓
Draft Version 1
        ↓
Draft Version 2
        ↓
Draft Version N
        │
        ▼
     REVIEW
        │
        ▼
   PUBLICATION
        │
        ├── LinkedIn
        │
        └── Bluesky
        │
        ▼
Publication Event
        ↓
Operation History
```

Each stage is independently stored and traceable.

---

# Project Status

The backend content workflow currently covers:

```text
✓ Configured Domain
✓ Existing Subdomains
✓ Source/Subdomain Mapping
✓ Validated Source Selection
✓ Source Crawling
✓ Article Discovery
✓ Article Extraction
✓ Relevance Matching
✓ Content Cleaning
✓ Processed Content Storage
```

The downstream application architecture includes:

```text
AI Generation
Partial Regeneration
Draft Versioning
LinkedIn Connection
Bluesky Connection
Publication
Publication Tracking
Operational Logging
```

These stages are maintained as separate workflow components.

---