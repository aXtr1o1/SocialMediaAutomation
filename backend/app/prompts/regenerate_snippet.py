REGENERATE_SNIPPET_PROMPT = """You are editing ONE excerpt inside an existing social media post.

Your job is to rewrite ONLY the TARGET TEXT below, following the USER INSTRUCTION.
Do not rewrite the rest of the post. Do not return the full post.
Do not invent facts, stats, vendors, or claims that are not already implied by the TARGET TEXT
unless the instruction explicitly asks for a rewrite of wording only.

PLATFORM: <<PLATFORM>>

USER INSTRUCTION
<<INSTRUCTION>>

TARGET TEXT (rewrite this only)
<<TARGET_TEXT>>

OPTIONAL SURROUNDING CONTEXT (for tone/continuity — do not rewrite this)
BEFORE:
<<BEFORE_CONTEXT>>

AFTER:
<<AFTER_CONTEXT>>

RULES
1. Return a replacement for TARGET TEXT only.
2. Keep meaning aligned with the instruction; do not expand into a full new post.
3. Preserve links, @handles, and hashtags that appear inside TARGET TEXT unless the instruction asks to change them.
4. Match the existing voice and formatting style of the TARGET TEXT (paragraph breaks, bullets, emoji density).
5. Do not wrap the result in quotes unless the original TARGET TEXT was quoted.
6. If the instruction is unclear, make the smallest reasonable edit.
7. PLAIN TEXT ONLY — this is a LinkedIn/Bluesky post, not a webpage.
   - Never use HTML or XML tags (no <ul>, <li>, <ol>, <p>, <br>, <div>, etc.).
   - Never use Markdown code fences.
   - For bullet points, use plain lines starting with "• " or "- " (one item per line).
   - For numbered lists, use "1. ", "2. ", "3. " on separate lines.

OUTPUT
Return raw JSON only — no markdown fences, no extra text:

{
  "replacement_text": "string"
}
"""
