# Interview notes

## One-minute pitch
Upload a CSV, map its columns, validate it, pick a period, and every number on screen, in the AI prompt and in the PDF comes from one `build_analysis()` result. The AI only sees aggregates, and if it fails the app falls back to a Python-written summary.

## Architecture in one breath
`data_loader` reads and maps, `data_validator` cleans and reports, `metrics` holds formulas, `comparisons` picks periods and builds the shared analysis, `visualizations` and `pdf_report` draw it, `ai_insights` explains it, `app.py` is only layout and session state.

## Decisions you should be ready to defend
- Engagement rate is a ratio of sums (total engagement / total reach). An average of per-post rates would let a tiny post with a huge rate distort the result. Per-post rates are shown only in the post tables.
- Reach is the default denominator because the brief's sample has it; impressions are used only when reach is absent, and the label changes. Mixing them silently would make two reports incomparable.
- Missing values stay blank. A zero would pull totals and averages down and look like real data. Rows with a missing denominator are left out of the rate.
- Duplicates are exact duplicates across all mapped columns. Same date and title with different numbers is kept and flagged, because it could be two posts.
- Previous period is the same number of days ending the day before the start. Equal length keeps totals comparable. Coverage under 60% triggers a warning.
- Follower growth is last minus first value in the period. It misses growth between periods; this is stated in the limitations.
- `requests` against the OpenAI-compatible endpoint instead of two SDKs: fewer dependencies, one code path, easy to mock in tests.
- Matplotlib for PDF charts, Plotly for the dashboard. Plotly-to-image needs Kaleido and Chrome, which is fragile on free hosting.
- Grounding check: regex pulls numbers from the AI text and compares them to the payload within rounding. It is a heuristic and can miss wrong claims that reuse real numbers.

## Questions likely to come up
- How do you stop the AI making things up? Aggregated input, a strict system prompt, JSON schema check, number check, labelled fallback, and the payload is visible to the user.
- What happens with a bad file? Empty file, one column, no header rows, no Date column and no metric columns each give a specific message (see `tests/test_pipeline.py`).
- What would break at scale? Everything is in memory and recomputed on each rerun, fine for thousands of rows. Past that, cache with `st.cache_data` or move to a database.
- Why Streamlit? Fastest route to an interactive data app in six hours, and Python end to end.
- What is untested? Live browser rendering of the UI, and calls to the real Groq and OpenAI APIs (they were mocked). Say so plainly if asked.

## Numbers to memorise from the assignment's four sample rows
Reach 4,850, impressions 7,200, likes 420, comments 56, shares 42, engagement 518, engagement rate 10.68%, follower growth +42. This is `test_known_values_from_brief`.
