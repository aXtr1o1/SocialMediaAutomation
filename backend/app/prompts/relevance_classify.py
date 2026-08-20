RELEVANCE_CLASSIFY_PROMPT = """You are a strict relevance judge for a content pipeline.

Decide if this article is about one of the SELECTED subdomains. This runs only after KPI quality checks passed.
Do not browse. Use only the supplied text. Do not invent quotes.

SELECTED DOMAIN
<<DOMAIN_NAME>>

SELECTED SUBDOMAINS (the only valid targets)
<<SUBDOMAINS>>

ARTICLE
TITLE: <<TITLE>>
DESCRIPTION: <<DESCRIPTION>>
HEADINGS: <<HEADINGS>>
CONTENT:
<<CONTENT>>

LEXICAL SIGNALS (evidence only — do not rubber-stamp them)
KEYWORD_SCORE: <<KEYWORD_SCORE>>
FUZZY_SCORE: <<FUZZY_SCORE>>
MATCHED_TERMS: <<MATCHED_TERMS>>

RULES
- relevant=true only if the article's MAIN SUBJECT is clearly one selected subdomain, not a sibling topic and not a generic "AI" page.
- relevant=true REQUIRES at least one evidence quote copied verbatim from TITLE, HEADINGS, or CONTENT, and primary_subdomain MUST be one of the selected subdomain names.
- A footer, tag list, nav item, or a single mention of "AI" / "machine learning" is not enough. relevant=false.
- If keyword/fuzzy are high but the substance is off-topic, score <= 40 and relevant=false.
- If names barely match but the substance is clearly a selected subdomain, score high, still with evidence.
- If you cannot quote evidence, relevant=false and score <= 40.

Return strict JSON only:
{
  "score": 0,
  "relevant": false,
  "primary_subdomain": "",
  "evidence": ["string"],
  "reason": "string"
}
"""
