"""
SocialPulse AI - Fast Native Web Server (Flask)
High-performance, zero-lag web application serving the Stitch SaaS interface.
"""
import os
import io
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template

import pandas as pd
import numpy as np

from utils.constants import (
    STD_DATE, STD_POST, STD_REACH, STD_IMPRESSIONS, STD_LIKES,
    STD_COMMENTS, STD_SHARES, STD_SAVES, STD_FOLLOWERS, STD_POST_TYPE,
    STD_ENGAGEMENT_RATE, PRIMARY, SUCCESS, DANGER
)
from utils.formatters import format_number, format_percentage, format_date_range, truncate_text
from utils.helpers import get_date_range

from services.csv_loader import load_csv_from_path, SUPPORTED_ENCODINGS
from services.column_mapper import auto_map_columns, get_mapping_report
from services.data_validator import validate_dataset, get_health_rating, get_health_color
from services.data_cleaner import clean_dataset, calculate_missing_engagement_rate
from services.analytics_engine import (
    calculate_kpis, calculate_daily_metrics, calculate_weekly_metrics,
    calculate_format_performance, get_top_posts, get_engagement_distribution,
    calculate_posting_frequency, get_peak_performance, calculate_save_reach_ratio,
    calculate_comment_like_ratio, calculate_viral_score
)
from services.comparison_engine import compare_periods, get_comparison_summary
from services.ai_insights import generate_ai_insights, is_ai_configured
from services.pdf_generator import generate_pdf_report

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB

# In-memory session store
CURRENT_DATA = {
    "df": None,
    "raw_df": None,
    "platform": "Instagram",
    "mapped_columns": {},
    "unmapped_columns": [],
    "validation": None,
    "filename": "sample_instagram_data.csv",
    "ai_insights": None,
    "comparison_enabled": True
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def init_default_data():
    """Load default Instagram sample dataset on startup."""
    sample_path = os.path.join(BASE_DIR, "data", "sample_instagram_data.csv")
    if os.path.exists(sample_path):
        _load_file_path(sample_path, "sample_instagram_data.csv", "Instagram")

def _load_file_path(path: str, filename: str, platform: str):
    df, err = load_csv_from_path(path)
    if err or df is None:
        return False, err
    
    mapped, unmapped = auto_map_columns(df)
    validation = validate_dataset(df, mapped)
    cleaned = clean_dataset(df, mapped)
    cleaned = calculate_missing_engagement_rate(cleaned, mapped)

    CURRENT_DATA["df"] = cleaned
    CURRENT_DATA["raw_df"] = df
    CURRENT_DATA["platform"] = platform
    CURRENT_DATA["mapped_columns"] = mapped
    CURRENT_DATA["unmapped_columns"] = unmapped
    CURRENT_DATA["validation"] = validation
    CURRENT_DATA["filename"] = filename
    CURRENT_DATA["ai_insights"] = None
    return True, None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    df = CURRENT_DATA["df"]
    has_data = df is not None and not df.empty
    date_range_str = "No dates available"
    date_start, date_end = None, None

    if has_data:
        date_start, date_end = get_date_range(df, CURRENT_DATA["mapped_columns"].get(STD_DATE, ""))
        if date_start and date_end:
            date_range_str = format_date_range(date_start, date_end)

    return jsonify({
        "has_data": has_data,
        "platform": CURRENT_DATA["platform"],
        "filename": CURRENT_DATA["filename"],
        "total_rows": len(df) if has_data else 0,
        "date_range": date_range_str,
        "comparison_enabled": CURRENT_DATA["comparison_enabled"],
        "ai_configured": is_ai_configured()
    })


@app.route("/api/set-platform", methods=["POST"])
def set_platform():
    data = request.json or {}
    platform = data.get("platform", "Instagram")
    CURRENT_DATA["platform"] = platform
    return jsonify({"success": True, "platform": platform})


@app.route("/api/load-sample", methods=["POST"])
def load_sample():
    data = request.json or {}
    sample_type = data.get("type", "instagram")
    
    if sample_type == "instagram":
        path = os.path.join(BASE_DIR, "data", "sample_instagram_data.csv")
        platform = "Instagram"
        filename = "sample_instagram_data.csv"
    else:
        path = os.path.join(BASE_DIR, "data", "sample_linkedin_data.csv")
        platform = "LinkedIn"
        filename = "sample_linkedin_data.csv"

    success, err = _load_file_path(path, filename, platform)
    if not success:
        return jsonify({"success": False, "error": err}), 400
    
    return jsonify({"success": True, "filename": filename, "rows": len(CURRENT_DATA["df"])})


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    platform = request.form.get("platform", CURRENT_DATA["platform"])
    
    content = file.read()
    df = None
    for encoding in SUPPORTED_ENCODINGS:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=encoding)
            df.columns = [str(col).strip() for col in df.columns]
            break
        except Exception:
            continue

    if df is None or df.empty:
        return jsonify({"success": False, "error": "Unable to parse CSV. Ensure it is valid CSV encoding."}), 400

    mapped, unmapped = auto_map_columns(df)
    validation = validate_dataset(df, mapped)
    cleaned = clean_dataset(df, mapped)
    cleaned = calculate_missing_engagement_rate(cleaned, mapped)

    CURRENT_DATA["df"] = cleaned
    CURRENT_DATA["raw_df"] = df
    CURRENT_DATA["platform"] = platform
    CURRENT_DATA["mapped_columns"] = mapped
    CURRENT_DATA["unmapped_columns"] = unmapped
    CURRENT_DATA["validation"] = validation
    CURRENT_DATA["filename"] = file.filename
    CURRENT_DATA["ai_insights"] = None

    return jsonify({
        "success": True,
        "filename": file.filename,
        "rows": len(cleaned),
        "health_score": validation.get("health_score", 0),
        "health_rating": get_health_rating(validation.get("health_score", 0)),
        "mapped_count": len(mapped)
    })


@app.route("/api/overview", methods=["GET"])
def get_overview():
    df = CURRENT_DATA["df"]
    if df is None or df.empty:
        return jsonify({"has_data": False})

    mapped = CURRENT_DATA["mapped_columns"]
    platform = CURRENT_DATA["platform"]

    kpis = calculate_kpis(df, mapped)
    comparison = compare_periods(df, mapped) if CURRENT_DATA["comparison_enabled"] else {}
    comp_summary = get_comparison_summary(comparison) if comparison else {}

    # Format trends for chart
    daily_df = calculate_daily_metrics(df, mapped)
    daily_chart = []
    if daily_df is not None and not daily_df.empty:
        for _, row in daily_df.iterrows():
            daily_chart.append({
                "date": str(row.get("Date", "")),
                "reach": float(row.get("Reach", 0)),
                "impressions": float(row.get("Impressions", 0)),
                "engagements": float(row.get("Engagements", 0))
            })

    # Weekly chart
    weekly_df = calculate_weekly_metrics(df, mapped)
    weekly_chart = []
    if weekly_df is not None and not weekly_df.empty:
        for _, row in weekly_df.iterrows():
            weekly_chart.append({
                "date": str(row.get("Date", ""))[:10],
                "reach": float(row.get("Reach", 0)),
                "impressions": float(row.get("Impressions", 0)),
                "engagements": float(row.get("Engagements", 0))
            })

    # Format breakdown
    fmt_df = calculate_format_performance(df, mapped)
    formats = []
    if fmt_df is not None and not fmt_df.empty:
        for idx, row in fmt_df.iterrows():
            formats.append({
                "format": str(idx),
                "count": int(row.get("post_count", 0)),
                "share": float(row.get("pct_contribution", 0)),
                "eng_rate": float(row.get("eng_rate_by_reach", 0))
            })

    # Top 3 posts
    top_3 = get_top_posts(df, mapped, sort_by="engagements", n=3)
    top_posts_data = []
    post_col = mapped.get(STD_POST, "")
    type_col = mapped.get(STD_POST_TYPE, "")
    date_col = mapped.get(STD_DATE, "")
    er_col = mapped.get(STD_ENGAGEMENT_RATE, "")
    reach_col = mapped.get(STD_REACH, "")
    likes_col = mapped.get(STD_LIKES, "")
    comm_col = mapped.get(STD_COMMENTS, "")
    shares_col = mapped.get(STD_SHARES, "")

    for _, row in top_3.iterrows():
        top_posts_data.append({
            "caption": truncate_text(str(row.get(post_col, "Untitled Post")), 65),
            "type": str(row.get(type_col, "Post")),
            "date": str(row.get(date_col, ""))[:10],
            "er": f"{float(row.get(er_col, 0)):.2f}%" if er_col and pd.notna(row.get(er_col)) else "N/A",
            "reach": format_number(row.get(reach_col)),
            "likes": format_number(row.get(likes_col)),
            "comments": format_number(row.get(comm_col)),
            "shares": format_number(row.get(shares_col))
        })

    # Peak performance stats
    peak = get_peak_performance(df, mapped)
    save_ratio = calculate_save_reach_ratio(df, mapped)
    comm_ratio = calculate_comment_like_ratio(df, mapped)

    # Date range string
    date_start, date_end = get_date_range(df, mapped.get(STD_DATE, ""))
    dr_str = format_date_range(date_start, date_end) if date_start and date_end else "N/A"

    return jsonify({
        "has_data": True,
        "platform": platform,
        "filename": CURRENT_DATA["filename"],
        "date_range_str": dr_str,
        "kpis": kpis,
        "comparison": comparison,
        "comp_summary": comp_summary,
        "daily_chart": daily_chart,
        "weekly_chart": weekly_chart,
        "formats": formats,
        "top_posts": top_posts_data,
        "peak": peak,
        "save_ratio": save_ratio,
        "comm_ratio": comm_ratio
    })


@app.route("/api/deep-analytics", methods=["GET"])
def get_deep_analytics():
    df = CURRENT_DATA["df"]
    if df is None or df.empty:
        return jsonify({"has_data": False})

    mapped = CURRENT_DATA["mapped_columns"]
    post_type_filter = request.args.get("post_type", "All")
    
    filtered_df = df.copy()
    type_col = mapped.get(STD_POST_TYPE)
    if post_type_filter != "All" and type_col and type_col in filtered_df.columns:
        filtered_df = filtered_df[filtered_df[type_col] == post_type_filter]

    kpis = calculate_kpis(filtered_df, mapped)
    comparison = compare_periods(filtered_df, mapped)
    engagement_dist = get_engagement_distribution(filtered_df, mapped)
    
    fmt_df = calculate_format_performance(filtered_df, mapped)
    fmt_matrix = []
    if fmt_df is not None and not fmt_df.empty:
        for idx, row in fmt_df.iterrows():
            fmt_matrix.append({
                "format": str(idx),
                "count": int(row.get("post_count", 0)),
                "reach": format_number(row.get(f"{mapped.get(STD_REACH, '')}_sum")),
                "impressions": format_number(row.get(f"{mapped.get(STD_IMPRESSIONS, '')}_sum")),
                "likes": format_number(row.get(f"{mapped.get(STD_LIKES, '')}_sum")),
                "comments": format_number(row.get(f"{mapped.get(STD_COMMENTS, '')}_sum")),
                "shares": format_number(row.get(f"{mapped.get(STD_SHARES, '')}_sum")),
                "eng_rate": f"{float(row.get('eng_rate_by_reach', 0)):.2f}%",
                "share": f"{float(row.get('pct_contribution', 0)):.1f}%"
            })

    # Follower growth line
    date_col = mapped.get(STD_DATE)
    fol_col = mapped.get(STD_FOLLOWERS)
    follower_curve = []
    if date_col and fol_col and date_col in filtered_df.columns and fol_col in filtered_df.columns:
        f_df = filtered_df[[date_col, fol_col]].dropna().sort_values(date_col)
        for _, r in f_df.iterrows():
            follower_curve.append({
                "date": str(r[date_col])[:10],
                "followers": float(r[fol_col])
            })

    return jsonify({
        "has_data": True,
        "kpis": kpis,
        "comparison": comparison,
        "engagement_dist": engagement_dist,
        "format_matrix": fmt_matrix,
        "follower_curve": follower_curve
    })


@app.route("/api/top-posts", methods=["GET"])
def get_all_top_posts():
    df = CURRENT_DATA["df"]
    if df is None or df.empty:
        return jsonify({"has_data": False, "posts": []})

    mapped = CURRENT_DATA["mapped_columns"]
    sort_by = request.args.get("sort_by", "engagements")
    limit = int(request.args.get("limit", 25))
    search = request.args.get("search", None)
    post_type = request.args.get("post_type", "All")

    top_df = get_top_posts(df, mapped, sort_by=sort_by, n=limit, post_type_filter=post_type, search_query=search)

    # Gather stats for viral score
    df_stats = {}
    for std in [STD_REACH, STD_ENGAGEMENT_RATE, STD_SHARES]:
        col = mapped.get(std)
        if col and col in df.columns:
            df_stats[col] = {"min": df[col].min(), "max": df[col].max()}
    if "_total_engagements" in top_df.columns:
        df_stats["_total_engagements"] = {"min": top_df["_total_engagements"].min(), "max": top_df["_total_engagements"].max()}

    post_col = mapped.get(STD_POST, "")
    type_col = mapped.get(STD_POST_TYPE, "")
    date_col = mapped.get(STD_DATE, "")
    er_col = mapped.get(STD_ENGAGEMENT_RATE, "")
    reach_col = mapped.get(STD_REACH, "")
    imp_col = mapped.get(STD_IMPRESSIONS, "")
    likes_col = mapped.get(STD_LIKES, "")
    comm_col = mapped.get(STD_COMMENTS, "")
    shares_col = mapped.get(STD_SHARES, "")
    saves_col = mapped.get(STD_SAVES, "")

    posts = []
    for rank, (_, row) in enumerate(top_df.iterrows(), 1):
        v_score = calculate_viral_score(row, mapped, df_stats)
        posts.append({
            "rank": rank,
            "caption": str(row.get(post_col, "Untitled Post")),
            "short_caption": truncate_text(str(row.get(post_col, "Untitled Post")), 55),
            "type": str(row.get(type_col, "Post")),
            "date": str(row.get(date_col, ""))[:10],
            "reach": format_number(row.get(reach_col)),
            "impressions": format_number(row.get(imp_col)),
            "likes": format_number(row.get(likes_col)),
            "comments": format_number(row.get(comm_col)),
            "shares": format_number(row.get(shares_col)),
            "saves": format_number(row.get(saves_col)),
            "er": f"{float(row.get(er_col, 0)):.2f}%" if er_col and pd.notna(row.get(er_col)) else "N/A",
            "viral_score": int(v_score)
        })

    return jsonify({"has_data": True, "total_posts": len(df), "posts": posts})


@app.route("/api/ai-insights", methods=["GET"])
def get_insights():
    df = CURRENT_DATA["df"]
    if df is None or df.empty:
        return jsonify({"has_data": False})

    if CURRENT_DATA["ai_insights"] is not None and not request.args.get("refresh"):
        return jsonify(CURRENT_DATA["ai_insights"])

    mapped = CURRENT_DATA["mapped_columns"]
    platform = CURRENT_DATA["platform"]
    kpis = calculate_kpis(df, mapped)
    comparison = compare_periods(df, mapped)
    fmt = calculate_format_performance(df, mapped)
    posting_freq = calculate_posting_frequency(df, mapped)
    peak = get_peak_performance(df, mapped)

    insights = generate_ai_insights(kpis, comparison, fmt, posting_freq, peak, platform)
    CURRENT_DATA["ai_insights"] = insights
    return jsonify(insights)


@app.route("/api/validation-info", methods=["GET"])
def get_validation_info():
    val = CURRENT_DATA["validation"]
    df = CURRENT_DATA["df"]
    if val is None or df is None:
        return jsonify({"has_data": False})

    mapped = CURRENT_DATA["mapped_columns"]
    preview_cols = list(df.columns[:8])
    preview_rows = df[preview_cols].head(5).to_dict(orient="records")

    return jsonify({
        "has_data": True,
        "filename": CURRENT_DATA["filename"],
        "total_records": val.get("total_records", 0),
        "valid_records": val.get("valid_records", 0),
        "health_score": val.get("health_score", 0),
        "health_rating": get_health_rating(val.get("health_score", 0)),
        "health_color": get_health_color(val.get("health_score", 0)),
        "corrupted": val.get("corrupted_records", 0),
        "duplicates": val.get("duplicate_records", 0),
        "mapped_columns": mapped,
        "unmapped_columns": CURRENT_DATA["unmapped_columns"],
        "preview_cols": preview_cols,
        "preview_rows": preview_rows
    })


@app.route("/api/export-pdf", methods=["GET"])
def export_pdf():
    df = CURRENT_DATA["df"]
    if df is None or df.empty:
        return "No data loaded", 400

    mapped = CURRENT_DATA["mapped_columns"]
    platform = CURRENT_DATA["platform"]

    kpis = calculate_kpis(df, mapped)
    comparison = compare_periods(df, mapped)
    fmt = calculate_format_performance(df, mapped)
    top = get_top_posts(df, mapped, sort_by="engagements", n=10)

    insights = CURRENT_DATA["ai_insights"]
    if not insights:
        posting_freq = calculate_posting_frequency(df, mapped)
        peak = get_peak_performance(df, mapped)
        insights = generate_ai_insights(kpis, comparison, fmt, posting_freq, peak, platform)

    date_start, date_end = get_date_range(df, mapped.get(STD_DATE, ""))
    dr = (date_start, date_end) if date_start and date_end else None

    pdf_bytes = generate_pdf_report(
        kpis=kpis,
        comparison=comparison,
        format_performance=fmt,
        top_posts=top,
        ai_insights=insights,
        mapped_columns=mapped,
        platform=platform,
        date_range=dr,
        dataset_info={
            "total_rows": len(df),
            "platform": platform,
            "source_file": CURRENT_DATA["filename"]
        }
    )

    filename = f"SocialPulse_AI_Report_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


init_default_data()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
