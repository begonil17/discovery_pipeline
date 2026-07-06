EMPTY_FRAGMENT_MARKER = "<!-- EMPTY_WEBPAGE_FRAGMENT -->"


PROMPT = """
You are cleaning one fragment of a webpage into knowledge-preserving
Markdown for a knowledge graph.

The input is only one fragment of the webpage's extracted Markdown.
It may begin or end in the middle of the webpage.
Do not assume this is the complete article.

Your task is NOT to summarize.

Your task is to keep the knowledge-bearing content from this fragment
while removing non-knowledge prose.

Rules:

- Preserve every factual statement that is useful for understanding
  the subject.
- Preserve knowledge about history, origin, etymology, ingredients,
  preparation, geography, culture, people, dates, institutions,
  characteristics, classifications, variations and examples.
- Preserve headings.
- Preserve lists.
- Preserve recipes completely.
- Preserve tables if possible.
- Preserve section order.
- Keep the original level of factual detail.
- Never summarize.
- Never omit factual information because it looks minor.
- If a personal or promotional sentence contains a useful fact,
  keep the useful fact and rewrite it neutrally.

Remove website chrome found in this fragment, such as:

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

Also remove non-knowledge prose, such as:

- the author's personal memories or anecdotes
- first-person commentary such as "I think", "I tried", "we loved"
- subjective opinions and taste judgments
- conversational filler
- jokes, greetings and sign-offs
- promotional or marketing language
- calls to action such as "visit us", "book now", "try this today"
- generic introductions that do not add factual information
- generic conclusions that do not add factual information

Return ONLY the knowledge-preserving cleaned fragment in Markdown.

Always return a textual response.
If the fragment contains only website chrome or non-knowledge prose
and no useful factual content remains,
return exactly this marker and nothing else:

{empty_fragment_marker}

Do not explain anything.

Webpage fragment:

------------------------

{text}
"""


BATCH_PROMPT = """
You are cleaning multiple independent fragments of a webpage into
knowledge-preserving Markdown for a knowledge graph.

Each fragment is only one part of the webpage's extracted Markdown.
Fragments may begin or end in the middle of the webpage.
Do not assume any fragment is the complete article.

Your task is NOT to summarize.

Your task is to keep the knowledge-bearing content from every part
while removing non-knowledge prose.

Rules:

- Preserve every factual statement that is useful for understanding
  the subject.
- Preserve knowledge about history, origin, etymology, ingredients,
  preparation, geography, culture, people, dates, institutions,
  characteristics, classifications, variations and examples.
- Preserve headings.
- Preserve lists.
- Preserve recipes completely.
- Preserve tables if possible.
- Preserve section order within each part.
- Keep the original level of factual detail.
- Never summarize.
- Never omit factual information because it looks minor.
- If a personal or promotional sentence contains a useful fact,
  keep the useful fact and rewrite it neutrally.
- Do not merge parts together.
- Preserve the part separators exactly.
- Preserve each "PART N" heading exactly.

Remove website chrome found in each part, such as:

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

Also remove non-knowledge prose, such as:

- the author's personal memories or anecdotes
- first-person commentary such as "I think", "I tried", "we loved"
- subjective opinions and taste judgments
- conversational filler
- jokes, greetings and sign-offs
- promotional or marketing language
- calls to action such as "visit us", "book now", "try this today"
- generic introductions that do not add factual information
- generic conclusions that do not add factual information

Return ONLY the knowledge-preserving cleaned parts in Markdown.

Always return a textual response.
If a part contains only website chrome or non-knowledge prose and no
useful factual content remains,
keep that part's separator and PART heading, then return exactly this
marker for that part and nothing else:

{empty_fragment_marker}

Do not explain anything.

Webpage fragments:

{text}
"""
