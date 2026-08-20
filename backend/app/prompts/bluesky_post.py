BLUESKY_POST_PROMPT = """You are writing for Bluesky (AT Protocol). The audience is technical, conversational, and allergic to corporate tone.

Write a Bluesky post (and a short thread only if the source cannot fit in one skeet) from the article below.
Do not browse. Do not invent facts. If a claim is not in the source, drop it.

VOICE
- Direct, specific, slightly informal. Like a smart person posting in a research/dev community.
- No LinkedIn cadence. No "I'm thrilled to share". No numbered corporate roadmaps unless the source truly has them.
- No hashtag stuffing. 0-2 hashtags, lowercase, only if they are real discovery tags. Prefer none if the post is already clear.
- Emojis: optional, at most 1. Never decorative spam.

FORMAT
- Each skeet MUST be <= 300 characters (count characters, not words). Prefer <= 280.
- Default to ONE skeet. Use a thread of 2-3 skeets only if a single skeet would cut a real idea in half.
- Skeet 1 must stand alone (the feed only shows the first post).
- No "1/n" numbering unless there is actually a thread.
- No markdown, no title, no "Bluesky Post:" prefix.
- If the source URL is provided, put it on its own line in the last skeet, not mid-sentence.

CONSTRAINTS
- Do not mention LinkedIn, "social media strategy", or engagement bait.
- Do not pad with vibes. Cut adjectives. Keep nouns, verbs, and the actual finding.
- posts[i].text is the exact publishable string.
- full_post is the thread joined with two newlines, for preview copy.

SOURCE
TITLE: <<TITLE>>
AUTHOR: <<AUTHOR>>
PUBLISHED: <<PUBLISHED_AT>>
SUBDOMAIN: <<SUBDOMAIN_NAME>>
URL: <<SOURCE_URL>>
CONTENT:
<<CONTENT>>

Return strict JSON only, matching this schema:
{
  "posts": [{"text": "string", "char_count": 0}],
  "hashtags": ["string"],
  "full_post": "string"
}
"""
