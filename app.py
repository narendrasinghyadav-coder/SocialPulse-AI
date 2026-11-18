"""AI Social Media Performance Analyzer: Streamlit entry point.

Run with:  streamlit run app.py
All calculations live in modules/; this file only handles layout and session state.
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from modules import visualizations as viz
from modules.ai_insights import (PROVIDERS, SECTION_TITLES, build_payload, fallback_insights,
                                 generate_insights, get_provider_settings)
from modules.comparisons import COMPARED, build_analysis
from modules.data_loader import STANDARD_FIELDS, DataLoadError, apply_mapping, read_csv, suggest_mapping
from modules.data_validator import validate_and_clean
from modules.metrics import add_post_metrics, daily_series, top_posts
from modules.pdf_report import build_pdf
from modules.utils import fmt_int, fmt_pct, fmt_signed, fmt_signed_pct

load_dotenv()
ROOT = Path(__file__).parent
LOGO = ROOT / "assets" / "logo.png"
SAMPLES = {
    "Instagram-style sample": ROOT / "sample_data" / "sample_social_media_data.csv",
    "LinkedIn-style sample": ROOT / "sample_data" / "sample_linkedin_export.csv",
}
PAGES = ["Overview", "Upload data", "Analytics", "AI insights", "PDF report", "About"]
NOT_MAPPED = "(not mapped)"

st.set_page_config(page_title="Social Media Performance Analyzer", page_icon=str(LOGO) if LOGO.exists() else "📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
.block-container { padding-top: 2rem; max-width: 1250px; }
h1, h2, h3 { letter-spacing: -0.01em; }
.kpi { background:#fff; border:1px solid #E2E8F0; border-radius:14px; padding:16px 18px; height:100%;
       box-shadow:0 1px 2px rgba(15,23,42,.04); }
.kpi-label { font-size:12px; color:#64748B; font-weight:500; text-transform:uppercase; letter-spacing:.04em; }
.kpi-value { font-size:28px; font-weight:700; color:#0F172A; margin-top:4px; line-height:1.15; }
.kpi-delta { font-size:13px; font-weight:600; margin-top:6px; }
.kpi-sub { font-size:12px; color:#94A3B8; margin-top:2px; }
.pos { color:#059669; } .neg { color:#DC2626; } .neu { color:#64748B; }
.card { background:#fff; border:1px solid #E2E8F0; border-radius:14px; padding:18px 20px; margin-bottom:12px; }
.card h4 { margin:0 0 6px 0; font-size:14px; color:#4F46E5; }
.card p, .card li { font-size:14.5px; color:#1E293B; line-height:1.55; }
.hero { background:linear-gradient(135deg,#4F46E5 0%,#6366F1 55%,#0D9488 120%); color:#fff; border-radius:18px;
        padding:26px 30px; margin-bottom:18px; }
.hero h2 { color:#fff; margin:0 0 4px 0; } .hero p { margin:0; opacity:.9; }
.pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }
.pill-ai { background:#EEF2FF; color:#4338CA; } .pill-fb { background:#FEF3C7; color:#92400E; }
section[data-testid="stSidebar"] { background:#0F172A; }
section[data-testid="stSidebar"] * { color:#E2E8F0; }
section[data-testid="stSidebar"] [data-baseweb="select"] * { color:#0F172A; }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers

def show_chart(fig, key: str):
    if fig is None:
        st.info("This chart needs data that is not available in the uploaded file.")
        return
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except TypeError:  # older Streamlit releases
        st.plotly_chart(fig, use_container_width=True, key=key)


def show_df(df: pd.DataFrame):
    try:
        st.dataframe(df, hide_index=True, width="stretch")
    except TypeError:
        st.dataframe(df, hide_index=True, use_container_width=True)


def kpi(label: str, value: str, delta: str | None = None, tone: str = "neu", sub: str | None = None) -> str:
    d = f'<div class="kpi-delta {tone}">{html.escape(delta)}</div>' if delta else ""
    s = f'<div class="kpi-sub">{html.escape(sub)}</div>' if sub else ""
    return (f'<div class="kpi"><div class="kpi-label">{html.escape(label)}</div>'
            f'<div class="kpi-value">{html.escape(value)}</div>{d}{s}</div>')


def delta_for(analysis: dict, key: str):
    """(text, tone) for the comparison line under a KPI card."""
    c = analysis["changes"].get(key) if analysis["prev_available"] else None
    if not c or c.get("abs") is None:
        return None, "neu"
    arrow = "▲" if c["direction"] == "up" else "▼" if c["direction"] == "down" else "■"
    tone = "pos" if c["direction"] == "up" else "neg" if c["direction"] == "down" else "neu"
    if key == "engagement_rate":
        return f"{arrow} {c['abs']:+.2f} pp vs previous", tone
    if c.get("pct") is None:
        return f"{arrow} {fmt_signed(c['abs'])} vs previous", tone
    return f"{arrow} {c['pct']:+.1f}% vs previous", tone


def kpi_row(analysis: dict, keys: list[tuple[str, str]]):
    cur = analysis["cur_metrics"]
    cols = st.columns(len(keys))
    for col, (key, label) in zip(cols, keys):
        value = cur.get(key)
        if key == "engagement_rate":
            text = fmt_pct(value)
            basis = cur.get("engagement_rate_basis")
            sub = f"of {basis.lower()}" if basis else "unavailable"
        elif key == "follower_growth":
            text, sub = fmt_signed(value), (f"{fmt_int(cur.get('followers_start'))} to {fmt_int(cur.get('followers_end'))}"
                                            if value is not None else "needs a Followers column")
        else:
            text, sub = fmt_int(value), ("not in file" if value is None else None)
        delta, tone = delta_for(analysis, key)
        col.markdown(kpi(label, text, delta, tone, sub), unsafe_allow_html=True)


def display_posts(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    d = df.copy()
    d["Date"] = d["Date"].dt.strftime("%Y-%m-%d")
    if "EngagementRate" in d:
        d["EngagementRate"] = d["EngagementRate"].round(2)
    return d.rename(columns={"EngagementRate": "Engagement rate (%)"})


def go_to(page: str):
    st.session_state["nav"] = page


def ingest(raw: bytes, name: str, signature: tuple):
    """Read a new file, store it, and validate it with the suggested column mapping."""
    for key in ("clean_df", "report", "insights", "insights_sig", "pdf_bytes", "pdf_name"):
        st.session_state.pop(key, None)
    try:
        df = read_csv(raw)
    except DataLoadError as exc:
        st.session_state["raw_df"] = None
        st.session_state["load_error"] = str(exc)
        return
    st.session_state.update(raw_df=df, file_name=name, file_sig=signature, load_error=None, file_size=len(raw),
                            mapping=suggest_mapping(list(df.columns)))
    run_validation(st.session_state["mapping"])


def run_validation(mapping: dict):
    st.session_state["mapping"] = mapping
    for key in ("insights", "insights_sig", "pdf_bytes"):
        st.session_state.pop(key, None)
    try:
        mapped = apply_mapping(st.session_state["raw_df"], mapping)
        clean, report = validate_and_clean(mapped)
    except DataLoadError as exc:
        st.session_state["clean_df"] = None
        st.session_state["report"] = None
        st.session_state["load_error"] = str(exc)
        return
    st.session_state["load_error"] = None
    st.session_state["report"] = report
    st.session_state["clean_df"] = add_post_metrics(clean) if report.ok else None


def load_sample(label: str):
    path = SAMPLES[label]
    raw = path.read_bytes()
    ingest(raw, path.name, ("sample", path.name))
    st.session_state["nav"] = "Analytics" if st.session_state.get("clean_df") is not None else "Upload data"


def has_data() -> bool:
    return st.session_state.get("clean_df") is not None


def empty_state(page_name: str):
    st.markdown(
        '<div class="card" style="text-align:center;padding:40px 20px">'
        '<h3 style="margin:0">No data yet</h3>'
        f'<p style="color:#64748B;margin:8px 0 0 0">{html.escape(page_name)} needs an analytics file. '
        'Upload an Instagram or LinkedIn CSV, or try a sample dataset.</p></div>', unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 2])
    c1.button("Go to upload", on_click=go_to, args=("Upload data",), key=f"es_up_{page_name}")
    c2.button("Load sample data", on_click=load_sample, args=("Instagram-style sample",), key=f"es_sm_{page_name}")


def period_controls(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    dmin, dmax = df["Date"].min().normalize(), df["Date"].max().normalize()
    st.sidebar.markdown("### Reporting period")
    presets = {"Last 30 days of data": 30, "Last 14 days of data": 14, "Last 7 days of data": 7,
               "Last 90 days of data": 90, "Full date range": None, "Custom range": "custom"}
    choice = st.sidebar.selectbox("Period", list(presets), key="period_preset", label_visibility="collapsed")
    n = presets[choice]
    if n == "custom":
        picked = st.sidebar.date_input("Start and end", value=(max(dmin, dmax - pd.Timedelta(days=29)).date(), dmax.date()),
                                       min_value=dmin.date(), max_value=dmax.date(), key="period_custom")
        if not isinstance(picked, (tuple, list)) or len(picked) != 2:
            st.sidebar.warning("Pick both a start and an end date.")
            return None
        start, end = pd.Timestamp(picked[0]), pd.Timestamp(picked[1])
    elif n is None:
        start, end = dmin, dmax
    else:
        end = dmax
        start = max(dmin, dmax - pd.Timedelta(days=n - 1))
    st.sidebar.caption(f"{start:%d %b %Y} to {end:%d %b %Y}  \nData spans {dmin:%d %b %Y} to {dmax:%d %b %Y}")
    return start, end


def current_analysis():
    """Build the analysis for the selected period. Returns None if no usable period."""
    df = st.session_state["clean_df"]
    period = period_controls(df)
    if period is None:
        return None
    start, end = period
    report = st.session_state.get("report")
    analysis = build_analysis(df, start, end, report.warnings if report else [])
    if analysis["cur_df"].empty:
        return analysis
    analysis["daily"] = daily_series(analysis["cur_df"], "D")
    return analysis


def signature(analysis: dict) -> str:
    return f"{st.session_state.get('file_sig')}|{analysis['start']:%Y%m%d}|{analysis['end']:%Y%m%d}|{st.session_state.get('mapping')}"


# ------------------------------------------------------------------ sidebar

if "nav" not in st.session_state:
    st.session_state["nav"] = "Overview"

with st.sidebar:
    if LOGO.exists():
        st.image(str(LOGO), width=54)
    st.markdown("## Performance Analyzer")
    st.caption("Instagram and LinkedIn analytics, explained.")
    st.radio("Navigation", PAGES, key="nav", label_visibility="collapsed")
    st.divider()
    if has_data():
        st.caption(f"File: {st.session_state.get('file_name')}")

analysis = None
if has_data():
    analysis = current_analysis()

page = st.session_state["nav"]

# ------------------------------------------------------------------ pages

def page_overview():
    st.markdown('<div class="hero"><h2>Social media performance, in plain numbers</h2>'
                '<p>Upload a CSV, pick a period, and get metrics, comparisons, top posts, AI insights and a client-ready PDF.</p></div>',
                unsafe_allow_html=True)
    if not has_data():
        empty_state("The overview")
        st.markdown("#### How it works")
        c = st.columns(4)
        for col, (n, t, d) in zip(c, [("1", "Upload", "Instagram or LinkedIn CSV export"), ("2", "Map columns", "Auto-detected, editable"),
                                      ("3", "Explore", "Metrics, trends, comparisons"), ("4", "Export", "Insights and PDF report")]):
            col.markdown(f'<div class="card"><h4>Step {n}</h4><p><b>{t}</b><br>{d}</p></div>', unsafe_allow_html=True)
        return
    if analysis is None:
        return
    if analysis["cur_df"].empty:
        st.warning("There are no posts in the selected period. Choose a different period in the sidebar.")
        return
    st.subheader(f"{analysis['start']:%d %b %Y} to {analysis['end']:%d %b %Y}")
    kpi_row(analysis, [("total_reach", "Total reach"), ("total_engagement", "Total engagement"),
                       ("engagement_rate", "Engagement rate"), ("follower_growth", "Follower growth")])
    if analysis["comparison_note"]:
        st.warning(analysis["comparison_note"])
    elif analysis["prev_available"]:
        st.caption(f"Changes compare with {analysis['prev_start']:%d %b} to {analysis['prev_end']:%d %b %Y}.")
    left, right = st.columns([3, 2])
    with left:
        show_chart(viz.line_chart(analysis["daily"], ["Reach", "Engagement"], "Reach and engagement over time"), "ov_trend")
    with right:
        st.markdown("##### Top 3 posts by engagement")
        t = display_posts(analysis["tops"]["engagement"].head(3))
        if t.empty:
            st.info("Engagement needs Likes, Comments or Shares columns.")
        else:
            show_df(t[[c for c in ("Date", "Post", "Engagement", "Engagement rate (%)") if c in t]])
    rep = st.session_state.get("report")
    if rep:
        st.caption(f"Data health: {rep.info.get('rows_out', 0)} posts used, {rep.info.get('duplicates_removed', 0)} duplicates removed, "
                   f"{rep.info.get('invalid_dates_dropped', 0)} rows dropped for unreadable dates.")


def page_upload():
    st.title("Upload data")
    st.caption("CSV exports from Instagram, LinkedIn or a scheduling tool. Column names do not have to match.")
    up = st.file_uploader("Choose a CSV file", type=["csv"])
    if up is not None:
        sig = (up.name, up.size)
        if st.session_state.get("last_uploader_sig") != sig:
            st.session_state["last_uploader_sig"] = sig
            with st.spinner("Reading and validating the file..."):
                ingest(up.getvalue(), up.name, sig)
    c1, c2, _ = st.columns([1, 1, 2])
    for col, label in zip((c1, c2), SAMPLES):
        col.button(f"Use {label}", on_click=load_sample, args=(label,), key=f"s_{label}")

    if st.session_state.get("load_error"):
        st.error(st.session_state["load_error"])
    raw = st.session_state.get("raw_df")
    if raw is None:
        st.markdown('<div class="card"><h4>Expected columns</h4><p>At minimum a <b>date</b> and one metric such as reach, impressions, '
                    'likes, comments, shares or followers. A post title is recommended. See the About page for the full format.</p></div>',
                    unsafe_allow_html=True)
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("File", st.session_state.get("file_name", ""))
    m2.metric("Size", f"{st.session_state.get('file_size', 0) / 1024:.1f} KB")
    m3.metric("Rows", f"{len(raw):,}")
    m4.metric("Columns", len(raw.columns))
    st.markdown("#### Raw data preview")
    show_df(raw.head(10))

    st.markdown("#### Column mapping")
    st.caption("Each standard field can come from one column of your file. Leave a field unmapped if the file does not have it.")
    mapping = st.session_state.get("mapping", {})
    options = [NOT_MAPPED] + list(raw.columns)
    sig = st.session_state.get("file_sig")
    with st.form("mapping_form"):
        cols = st.columns(4)
        chosen = {}
        for i, field in enumerate(STANDARD_FIELDS):
            current = mapping.get(field)
            idx = options.index(current) if current in options else 0
            label = field + (" (required)" if field == "Date" else "")
            chosen[field] = cols[i % 4].selectbox(label, options, index=idx, key=f"map_{field}_{sig}")
        submitted = st.form_submit_button("Apply mapping and validate", type="primary")
    if submitted:
        with st.spinner("Validating..."):
            run_validation({k: (None if v == NOT_MAPPED else v) for k, v in chosen.items()})
        st.rerun()

    report = st.session_state.get("report")
    if report is None:
        return
    st.markdown("#### Validation result")
    for e in report.errors:
        st.error(e)
    if report.ok:
        st.success(f"File accepted: {report.info['rows_out']} of {report.info['rows_in']} rows are usable "
                   f"({report.info['date_min']:%d %b %Y} to {report.info['date_max']:%d %b %Y}).")
    for w in report.warnings:
        st.warning(w)
    if report.ok:
        from modules.metrics import describe_availability
        unavailable, notes = describe_availability(st.session_state["clean_df"])
        for n in notes:
            st.info(n)
        if unavailable:
            st.markdown("**Metrics that cannot be calculated with this mapping**")
            for k, v in unavailable.items():
                st.markdown(f"- {k}: {v}")
        else:
            st.info("All core metrics can be calculated with this mapping.")
        with st.expander("Cleaned data preview"):
            show_df(display_posts(st.session_state["clean_df"].head(15)))
        st.button("Continue to analytics", on_click=go_to, args=("Analytics",), type="primary")


def page_analytics():
    st.title("Analytics")
    if not has_data():
        return empty_state("Analytics")
    if analysis is None:
        return
    if analysis["cur_df"].empty:
        return st.warning("There are no posts in the selected period. Choose a different period in the sidebar.")
    st.caption(f"{analysis['start']:%d %b %Y} to {analysis['end']:%d %b %Y} | {analysis['cur_metrics']['posts']} posts")
    tabs = st.tabs(["Key metrics", "Trends", "Period comparison", "Top posts", "Distribution"])

    with tabs[0]:
        kpi_row(analysis, [("total_reach", "Total reach"), ("total_impressions", "Total impressions"),
                           ("total_engagement", "Total engagement"), ("engagement_rate", "Engagement rate")])
        st.write("")
        kpi_row(analysis, [("total_likes", "Likes"), ("total_comments", "Comments"),
                           ("total_shares", "Shares"), ("follower_growth", "Follower growth")])
        cur = analysis["cur_metrics"]
        basis = cur.get("engagement_rate_basis")
        st.caption("Engagement = " + (" + ".join(cur["engagement_components"]) or "n/a")
                   + ". Engagement rate = engagement / total " + (basis.lower() if basis else "reach") + " x 100"
                   + (" (impressions-based because reach is not available)." if basis == "Impressions" else "."))
        for n in analysis["notes"]:
            st.info(n)
        if analysis["unavailable"]:
            with st.expander("Metrics that could not be calculated", expanded=True):
                for k, v in analysis["unavailable"].items():
                    st.markdown(f"- **{k}**: {v}")
        if analysis["comparison_note"]:
            st.warning(analysis["comparison_note"])

    with tabs[1]:
        c1, c2 = st.columns([1, 1])
        gran = c1.radio("Granularity", ["Daily", "Weekly"], horizontal=True, key="gran")
        smooth = c2.toggle("Show 3-point moving average", key="smooth")
        series = daily_series(analysis["cur_df"], "D" if gran == "Daily" else "W")
        if gran == "Weekly":
            st.caption("Weekly view sums all posts in each calendar week (weeks end on Sunday).")
        a, b = st.columns(2)
        with a:
            show_chart(viz.line_chart(series, ["Reach"], "Reach over time", 3 if smooth else 0), "t_reach")
            show_chart(viz.line_chart(series, ["Engagement"], "Engagement over time", 3 if smooth else 0), "t_eng")
        with b:
            show_chart(viz.line_chart(series, ["Impressions"], "Impressions over time", 3 if smooth else 0), "t_imp")
            show_chart(viz.follower_chart(series), "t_fol")

    with tabs[2]:
        if not analysis["prev_available"]:
            st.warning(analysis["comparison_note"])
        else:
            if analysis["comparison_note"]:
                st.warning(analysis["comparison_note"])
            st.caption(f"Current {analysis['start']:%d %b} to {analysis['end']:%d %b %Y}  vs  previous "
                       f"{analysis['prev_start']:%d %b} to {analysis['prev_end']:%d %b %Y}")
            rows = []
            for key, label in COMPARED:
                c, p, ch = analysis["cur_metrics"].get(key), analysis["prev_metrics"].get(key), analysis["changes"].get(key, {})
                if c is None and p is None:
                    continue
                rate = key == "engagement_rate"
                f = fmt_pct if rate else fmt_int
                rows.append({"Metric": label, "Current": f(c), "Previous": f(p),
                             "Change": (f"{ch['abs']:+.2f} pp" if rate and ch.get("abs") is not None else fmt_signed(ch.get("abs"))),
                             "% change": fmt_signed_pct(ch.get("pct")),
                             "Trend": {"up": "▲ up", "down": "▼ down", "flat": "■ flat"}.get(ch.get("direction"), "n/a")})
            show_df(pd.DataFrame(rows))
            st.caption("For engagement rate the change is in percentage points (pp); the % change is the relative change of the rate.")
            a, b = st.columns(2)
            with a:
                show_chart(viz.comparison_chart(analysis["cur_metrics"], analysis["prev_metrics"]), "cmp_bar")
            with b:
                options = [c for c in ("Reach", "Impressions", "Engagement") if c in analysis["cur_df"].columns]
                if options:
                    metric = st.selectbox("Metric for day-by-day overlay", options, key="overlay_metric")
                    show_chart(viz.period_overlay(analysis["cur_df"], analysis["prev_df"], analysis["start"],
                                                  analysis["prev_start"], metric), "cmp_overlay")

    with tabs[3]:
        term = st.text_input("Filter posts by title (optional)", key="post_filter", placeholder="e.g. carousel")
        pool = analysis["cur_df"]
        if term:
            pool = pool[pool["Post"].str.contains(term, case=False, regex=False)]
            st.caption(f"{len(pool)} post(s) match. Rankings below are computed within the matches.")
        st.caption("Ranking criteria: each list sorts individual posts by that column, highest first. Engagement = likes + comments + "
                   "shares. Engagement rate = post engagement / post reach x 100 (impressions if reach is missing). Ties keep the earlier post first.")
        for key, title, col in (("engagement", "Top 5 by engagement", "Engagement"), ("reach", "Top 5 by reach", "Reach"),
                                ("impressions", "Top 5 by impressions", "Impressions")):
            top = top_posts(pool, col)
            st.markdown(f"##### {title}")
            if top.empty:
                st.info(f"No posts with {col.lower()} data" + (" match the filter." if term else " in this file."))
                continue
            left, right = st.columns([3, 2])
            with left:
                show_df(display_posts(top))
            with right:
                show_chart(viz.top_posts_chart(top, col, title), f"top_{key}")

    with tabs[4]:
        show_chart(viz.engagement_distribution(analysis["cur_df"]), "dist")
        mix = analysis["mix"]
        if mix:
            st.markdown("**Interaction mix**  \n" + "  |  ".join(f"{k.replace('_pct', '').title()} {v:.1f}%" for k, v in mix.items()))
        if analysis["trend"] and analysis["trend"]["change_pct"] is not None:
            t = analysis["trend"]
            st.caption(f"Average engagement per post: first half {t['first_half_avg_engagement']:.0f}, second half "
                       f"{t['second_half_avg_engagement']:.0f} ({t['change_pct']:+.1f}%).")


def page_ai():
    st.title("AI insights")
    if not has_data():
        return empty_state("AI insights")
    if analysis is None:
        return
    if analysis["cur_df"].empty:
        return st.warning("There are no posts in the selected period.")
    payload = build_payload(analysis)
    provider, key, model = get_provider_settings()
    c1, c2 = st.columns([2, 3])
    with c1:
        if provider:
            st.success(f"AI provider ready: {provider} ({model})")
        else:
            st.info("No API key found. Insights will be written by rule-based Python logic. Set GROQ_API_KEY or OPENAI_API_KEY in .env to use an LLM.")
    with c2:
        st.caption("Only aggregated figures and a few post titles are sent to the AI service, never the raw file. "
                   "The model is told not to invent statistics or audience details.")
    if st.button("Generate insights", type="primary"):
        with st.spinner("Analysing your data..."):
            st.session_state["insights"] = generate_insights(payload)
            st.session_state["insights_sig"] = signature(analysis)
            st.session_state.pop("pdf_bytes", None)
    res = st.session_state.get("insights")
    if res is None:
        st.markdown('<div class="card"><h4>Nothing generated yet</h4><p>Click "Generate insights" to create a summary and recommendations for the selected period.</p></div>',
                    unsafe_allow_html=True)
    else:
        if st.session_state.get("insights_sig") != signature(analysis):
            st.warning("These insights were generated for a different period or mapping. Generate again to refresh them.")
        pill = (f'<span class="pill pill-ai">AI model: {html.escape(res.provider or "")} / {html.escape(res.model or "")}</span>'
                if res.source == "llm" else '<span class="pill pill-fb">Rule-based summary (no AI call)</span>')
        st.markdown(pill, unsafe_allow_html=True)
        for w in res.warnings:
            st.warning(w)
        for k in ("summary", "best_content", "weak_content", "engagement_trends", "audience_observations", "improvement_areas"):
            st.markdown(f'<div class="card"><h4>{SECTION_TITLES[k]}</h4><p>{html.escape(res.sections[k])}</p></div>', unsafe_allow_html=True)
        for k in ("recommendations", "next_steps"):
            items = "".join(f"<li>{html.escape(i)}</li>" for i in res.sections[k])
            st.markdown(f'<div class="card"><h4>{SECTION_TITLES[k]}</h4><ul>{items}</ul></div>', unsafe_allow_html=True)
    with st.expander("Data sent to the AI service (aggregated)"):
        st.json(payload)


def page_pdf():
    st.title("PDF report")
    if not has_data():
        return empty_state("The PDF report")
    if analysis is None:
        return
    if analysis["cur_df"].empty:
        return st.warning("There are no posts in the selected period.")
    st.markdown("The report includes the reporting period, KPIs, comparison, charts, top posts, insights, recommendations and a methodology and limitations section.")
    res = st.session_state.get("insights")
    fresh = res is not None and st.session_state.get("insights_sig") == signature(analysis)
    if fresh:
        st.success("The report will use the AI insights you generated for this period.")
    else:
        st.info("No up-to-date AI insights for this period. The report will use the rule-based summary. "
                "Generate insights on the AI insights page first if you want the AI version.")
    if st.button("Build PDF report", type="primary"):
        with st.spinner("Building the report..."):
            try:
                sections = res.sections if fresh else fallback_insights(build_payload(analysis))
                source = res.source if fresh else "fallback"
                pdf = build_pdf(analysis, sections, source, st.session_state.get("file_name", "uploaded.csv"), LOGO)
            except Exception as exc:  # show a readable message instead of a stack trace
                st.error(f"The PDF could not be created ({type(exc).__name__}). Check the data and try again.")
                return
            name = f"performance_report_{analysis['start']:%Y%m%d}_{analysis['end']:%Y%m%d}.pdf"
            try:
                out_dir = ROOT / "generated_reports"
                out_dir.mkdir(exist_ok=True)
                (out_dir / name).write_bytes(pdf)
            except OSError:
                pass  # read-only hosting: the in-memory download below still works
            st.session_state["pdf_bytes"], st.session_state["pdf_name"] = pdf, name
    if st.session_state.get("pdf_bytes"):
        st.success("Report ready.")
        st.download_button("Download PDF", st.session_state["pdf_bytes"], file_name=st.session_state["pdf_name"],
                           mime="application/pdf", type="primary")


def page_about():
    st.title("About this project")
    st.markdown("""
This app turns an Instagram or LinkedIn analytics CSV into metrics, comparisons, charts, AI-written insights and a PDF report.
Built as the AIBOOTSTRAPPER AI Engineering Internship assignment.

**Formulas**
- Total engagement = likes + comments + shares (only the components present in the file)
- Engagement rate = total engagement / total reach x 100. If reach is missing, impressions are used and the label says so.
- Follower growth = last followers value minus first followers value in the period
- Previous period = the window of equal length that ends the day before the selected period starts

**CSV format.** One row per post. Date is required. Everything else is optional, but metrics that need a missing column are reported as unavailable, never guessed.

| Field | Example column names that are auto-detected |
|---|---|
| Date | Date, Post date, Created date |
| Post | Post, Post title, Caption |
| Reach | Reach, Accounts reached, Unique impressions |
| Impressions | Impressions, Views |
| Likes | Likes, Reactions |
| Comments | Comments |
| Shares | Shares, Reposts |
| Followers | Followers, Total followers |

**Known limitations**
- Total reach and impressions are sums of per-post values, so they are not unique audience counts.
- Follower growth is measured from the first to the last followers value inside the period.
- Rankings and weekday patterns come from small samples and are not proof of cause.
- The PDF uses standard fonts, so emoji and some symbols in post titles are dropped.

**Future improvements**
- Direct Instagram and LinkedIn API integration
- Automated daily tracking and scheduled PDF reports
- Multiple account management
- Content performance forecasting
- Competitor analysis
- AI-powered content suggestions
""")


{"Overview": page_overview, "Upload data": page_upload, "Analytics": page_analytics,
 "AI insights": page_ai, "PDF report": page_pdf, "About": page_about}[page]()
