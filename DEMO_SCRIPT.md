# Demo recording script (about 2 minutes 30 seconds)

Before recording: `streamlit run app.py`, browser at 100% zoom, a Groq or OpenAI key in `.env`, and the LinkedIn-style sample ready.

0:00 - 0:15  Overview page. "This is the AI Social Media Performance Analyzer. It turns a raw analytics CSV into metrics, comparisons, AI insights and a PDF report."

0:15 - 0:50  Upload data. Click "Use LinkedIn-style sample". Point at the file info and the raw preview. "The column names here are LinkedIn's, like Reactions and Reposts. The app mapped them to its standard fields automatically." Open the mapping form, change one dropdown, apply, and show the validation message. Mention duplicates, bad dates and missing values are counted, not hidden.

0:50 - 1:30  Analytics. Pick "Last 30 days of data" in the sidebar. KPI cards with change versus the previous period. Say the engagement rate formula out loud: engagement divided by reach. Trends tab: switch to Weekly. Comparison tab: current vs previous table and the day-by-day overlay. Top posts tab: show the three rankings and read the ranking note.

1:30 - 2:00  AI insights. Click Generate. Read the summary and one recommendation. Open "Data sent to the AI service" and say only aggregates leave the app. Mention the fallback if there is no key.

2:00 - 2:25  PDF report. Build it, download it, scroll through the pages: KPIs, comparison, charts, top posts, insights, limitations.

2:25 - 2:30  "Code is on GitHub, with tests and a README. Thanks."

Optional 10 seconds if time allows: upload a CSV with no Date column to show the readable error.
