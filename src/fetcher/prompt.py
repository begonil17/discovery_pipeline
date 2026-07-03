EMPTY_FRAGMENT_MARKER = "<!-- EMPTY_WEBPAGE_FRAGMENT -->"


PROMPT = """
You are cleaning one fragment of a webpage.

The input is only one fragment of the webpage's extracted Markdown.
It may begin or end in the middle of the webpage.
Do not assume this is the complete article.

Your task is NOT to summarize.

Your task is to clean this fragment while preserving its content.

Rules:

- Preserve every fact and all factual information.
- Preserve headings.
- Preserve lists.
- Preserve recipes completely.
- Preserve tables if possible.
- Preserve section order.
- Never shorten the fragment.
- Never summarize.
- Never omit any information because it looks unimportant.

Remove ONLY website chrome found in this fragment, such as:

- advertisements
- cookie notices
- navigation menus
- sidebars
- "related articles"
- "you may also like"
- comments
- repeated page titles
- login buttons
- newsletter prompts
- page footer
- page header

Return ONLY the cleaned fragment in Markdown.

Always return a textual response.
If the fragment contains only website chrome and no article content remains,
return exactly this marker and nothing else:

{empty_fragment_marker}

Do not explain anything.

Webpage fragment:

------------------------

{text}
"""
