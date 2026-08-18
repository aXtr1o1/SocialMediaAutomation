# SocialMediaAutomation

## Content workflow

The backend workflow ends at processed content. Run the additive migration in
`backend/sql/20260818_content_workflow_extension.sql` in Supabase, install
`backend/requirements.txt`, and set `WORKFLOW_DOMAIN_ID` plus the Supabase and
Gemini credentials in `backend/.env`.

With a Supabase bearer token, start the workflow with:

```text
POST /processing/run
```

The endpoint reads the configured fixed domain, selects existing subdomains,
resolves sources only through `source_subdomain_mapping`, applies keyword /
fuzzy / Gemini matching only after crawling and KPI validation, crawls every
mapped source URL, and stores cleaned content only for passed and relevant
articles. It does not generate or
publish social-media posts.
