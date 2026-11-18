# AI Social Media Performance Analyzer

A Streamlit dashboard that takes an Instagram or LinkedIn analytics CSV and turns it into metrics, period comparisons, top-post rankings, charts, AI-written insights and a PDF report. Built for the AIBOOTSTRAPPER AI Engineering Internship assignment by Narendra Yadav.

Deployment status: not deployed. Run it locally with the steps below, or deploy to Streamlit Community Cloud using the section further down.

## The problem

Social media exports are rows of numbers. A client or manager wants to know whether the account is doing better than last month, which posts worked, and what to do next. This app answers those three questions from the uploaded file only, and says so when the file cannot support an answer.

## What it does

- Reads a CSV (comma, semicolon or tab separated), shows file info and a preview, and suggests a mapping from your column names to eight standard fields: Date, Post, Reach, Impressions, Likes, Comments, Shares, Followers. You can change the mapping before validating.
- Validates and cleans: unreadable dates drop the row, non-numeric or negative values become blank, exact duplicates are removed, missing values stay missing. Every change is counted and shown.
- Calculates reach, impressions, likes, comments, shares, total engagement, engagement rate and follower growth, and lists any metric it cannot calculate and why.
- Compares the selected period with the previous period of the same length, with absolute change, percentage change and an up/down marker.
- Ranks the top 5 posts by engagement, reach and impressions and explains the ranking.
- Draws Plotly charts: reach, impressions, engagement and followers over time (daily or weekly, optional moving average), engagement distribution, top posts, current vs previous period, and a day-by-day overlay of both periods.
- Generates insights with Groq or OpenAI, or with a Python fallback when no key is set or the call fails.
- Exports a PDF with branding, period, KPIs, comparison, charts, top posts, insights, recommendations, methodology and limitations.

## Formulas

Total engagement = likes + comments + shares. If one of these columns is missing, the total uses the ones that exist and the app says which.

Engagement rate = total engagement / total reach x 100. This is a ratio of sums, not an average of per-post rates, so large posts count for more. If the file has no reach column, impressions are used instead and every label says "of impressions". The two definitions are never mixed in one report. Posts with missing or zero reach are left out of the rate.

Follower growth = last Followers value minus first Followers value inside the selected period (ordered by date). It needs at least two values.

Previous period = the window with the same number of days that ends the day before the selected period starts. If the data covers less than 60% of that window the app warns that the comparison may be misleading, and if there are no posts in it, no comparison is made.

Per-post engagement rate in the top-post tables = post engagement / post reach x 100 (impressions if reach is missing).

## CSV format

One row per post. Only Date is required, plus at least one metric column. Example:

```
Date,Post,Reach,Impressions,Likes,Comments,Shares,Followers
2026-10-01,Product launch,1200,1800,95,12,8,2500
2026-10-03,Behind scenes,950,1400,80,9,6,2515
```

Column names do not have to match. The loader recognises common aliases (for example "Reactions" for Likes, "Reposts" for Shares, "Unique impressions" for Reach, "Created date" for Date) and the mapping form lets you pick columns by hand. Dates can be ISO, month-first or day-first. Values like `1,200` and `1.2K` are read as numbers.

Two sample files are included: `sample_data/sample_social_media_data.csv` and `sample_data/sample_linkedin_export.csv` (same data with different column names, to show the mapping). Both are generated random data from `scripts/generate_sample_data.py`, not a real account.

## Tech stack

Python 3.10+, Streamlit, Pandas, NumPy, Plotly (dashboard charts), Matplotlib (charts inside the PDF), ReportLab (PDF), Requests (LLM calls), python-dotenv. Groq or OpenAI for insights.

Two choices worth explaining. The LLM call uses plain `requests` against the OpenAI-compatible `/chat/completions` endpoint, which both Groq and OpenAI offer, so there is one code path and no vendor SDK. The PDF charts use Matplotlib because exporting Plotly figures to images needs Kaleido and a browser engine, which often fails on free hosting.

## Architecture

```
app.py                  Streamlit pages, session state, layout
modules/
  data_loader.py        CSV reading, encoding and separator detection, column mapping
  data_validator.py     Date and number cleaning, duplicates, validation report
  metrics.py            All formulas, rankings, weekday and trend summaries
  comparisons.py        Period selection, previous-period comparison, build_analysis()
  visualizations.py     Plotly figures
  ai_insights.py        Payload builder, LLM client, JSON validation, grounding check, fallback
  pdf_report.py         ReportLab report and Matplotlib charts
  utils.py              Number formatting and percentage change
tests/test_pipeline.py  20 unit tests
sample_data/            Demo CSVs
scripts/                Sample data and logo generator
generated_reports/      PDFs saved here when built
```

Data flow: upload -> `read_csv` -> `suggest_mapping` / `apply_mapping` -> `validate_and_clean` -> `add_post_metrics` -> `build_analysis(period)` -> dashboard, AI payload and PDF all read the same analysis dictionary. That way the screen, the AI and the PDF cannot disagree on a number.

## Run it locally

```
git clone <your-repo-url>
cd ai-social-media-analyzer
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env               # then add a key, optional
streamlit run app.py
```

Open http://localhost:8501, click "Use Instagram-style sample" on the Upload page, and go through Analytics, AI insights and PDF report.

Run the tests with `python -m pytest -q` (install pytest first) or `python -m unittest discover -s tests`.

## AI insights

The app sends the model a small JSON object: the period, metric definitions, current and previous totals, the changes, three top posts by engagement and by reach, three lowest posts by engagement rate, the like/comment/share mix, a first-half vs second-half comparison, weekday averages (only with enough posts), the list of unavailable metrics and the data limitations. Raw rows are not sent. The Insights page shows the exact payload in an expander.

The system prompt tells the model to use only numbers from the JSON, to claim nothing about demographics or behaviour, to say when information is missing and to return a fixed JSON shape. After the call the code checks the shape, then scans the text for numbers that do not appear in the payload (within rounding) and warns the user about any it finds. This check is a heuristic and will miss some cases. Anything that fails, including a missing key, a rejected key, a timeout or malformed JSON, falls back to a rule-based summary written from the same payload, and the page labels which of the two you are looking at.

Set the key in `.env` locally. On Streamlit Community Cloud, put it in the app's Secrets (`GROQ_API_KEY = "..."`). Keys are read on the server and never sent to the browser.

## PDF export

Go to PDF report and click Build. If you generated AI insights for the current period, the PDF uses them; otherwise it uses the rule-based summary and says so. The file downloads from the page and a copy is saved in `generated_reports/` when the filesystem allows it. The PDF uses built-in fonts, so emoji and some symbols in post titles are dropped.

## Deploy to Streamlit Community Cloud

1. Push this folder to a public or private GitHub repository (the `.gitignore` keeps `.env` out).
2. On share.streamlit.io choose New app, pick the repo, branch and `app.py`.
3. In Advanced settings, add the secret `GROQ_API_KEY` (or `OPENAI_API_KEY`).
4. Deploy, then test the sample dataset flow on the live URL before putting the link in your submission.

## Known limitations

- Total reach and impressions add up per-post values, so they are not unique audience size.
- Follower growth starts at the first followers value inside the period, so growth between the last post of one period and the first of the next is not counted.
- Rankings, weekday patterns and trends come from small samples. The insights describe correlations and do not prove cause.
- No demographic or content-format analysis, because the CSV does not carry that data.
- Saves, clicks and video views are ignored, because the assignment defines engagement as likes + comments + shares.
- Uploaded data lives in the session only. Nothing is stored on a server.
- The Streamlit UI was checked by running the page code against a stubbed Streamlit and by the unit tests, not in a live browser session, so visual layout still needs a look on first run.

## Next steps

Direct Instagram and LinkedIn API connections, daily tracking with scheduled PDF reports, multiple accounts, forecasting, competitor comparison, AI content suggestions, and a custom previous-period picker.
