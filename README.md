# SocialPulse AI – Social Media Performance Analyzer

**An AI-powered social media analytics platform that transforms Instagram and LinkedIn CSV data into actionable performance insights.**

## 🚀 Project Overview

SocialPulse AI is an intelligent social media performance analyzer built using Python and Streamlit. It helps users understand, monitor, and improve their social media performance through interactive analytics, AI-generated insights, and downloadable PDF reports.

The application allows users to upload Instagram or LinkedIn analytics CSV files, automatically validate and process the data, calculate important performance metrics, identify top-performing posts, compare reporting periods, and generate actionable recommendations.

It combines data analytics, interactive visualization, and AI-powered analysis in one centralized dashboard.

## 🎯 Problem Statement

Social media platforms generate large amounts of performance data, but understanding this data and converting it into meaningful decisions can be challenging.

Users often struggle to:
- Analyze engagement and reach metrics.
- Identify their best-performing content.
- Understand performance trends.
- Compare current and previous reporting periods.
- Discover opportunities to improve content strategies.
- Generate professional performance reports.

SocialPulse AI addresses these challenges by automating the analytics process and presenting meaningful insights through an intuitive dashboard.

## ✨ Key Features

### 1. Dashboard Overview
- Five dynamic KPI cards.
- Total reach and impressions tracking.
- Engagement and follower growth analysis.
- Interactive performance trend charts.
- Content format performance breakdown.
- Top-performing posts overview.
- AI-generated performance summary.

### 2. CSV Upload & Data Preparation
- Upload Instagram and LinkedIn analytics CSV files.
- Automatic column mapping.
- CSV validation and data cleaning.
- Duplicate record detection.
- Missing value identification.
- Invalid date and metric detection.
- Dataset health report.
- Cleaned dataset preview.
- Manual column mapping support.

### 3. Deep Analytics
- Reach and impressions analysis.
- Engagement distribution.
- Likes, comments, shares, and saves analysis.
- Content-type performance comparison.
- Follower growth tracking.
- Date-based filtering.
- Current vs previous period comparison.
- Interactive Plotly visualizations.

### 4. Top Posts Explorer
- Identify top three performing posts.
- Rank posts by reach.
- Rank posts by engagement.
- Rank posts by engagement rate.
- Sort by likes and shares.
- Search posts by caption.
- Filter by content type and date.
- Detailed searchable posts table.
- Transparent performance scoring where sufficient data is available.

### 5. AI-Powered Insights
- AI-generated executive summary.
- Primary performance takeaway.
- Content strategy recommendations.
- Engagement optimization suggestions.
- Reach improvement recommendations.
- Posting consistency analysis.
- Performance strengths and weaknesses.
- Data-grounded recommendations.

**AI Integration:** Groq API or OpenAI API, configured through environment variables.

A clearly labelled rule-based fallback is available when an AI API key is not configured.

### 6. PDF Report Generation
Generate downloadable professional PDF reports containing:

- Project branding and report details.
- Selected social media platform.
- Reporting period.
- Dataset summary.
- KPI overview.
- Engagement analysis.
- Period comparison.
- Performance charts.
- Top-performing posts.
- AI-generated summary.
- Actionable recommendations.
- Data assumptions and limitations.

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python 3.11+ |
| Frontend / Application | Streamlit |
| Data Processing | Pandas, NumPy |
| Data Visualization | Plotly Express, Plotly Graph Objects |
| AI Integration | Groq API / OpenAI API |
| PDF Generation | ReportLab |
| Environment Management | python-dotenv |
| Image Processing | Pillow |
| Testing | Pytest |
| Version Control | Git, GitHub |

## 🏗️ Project Architecture

SocialPulse AI follows a modular architecture that separates the user interface, data processing, analytics, AI integration, and report generation.

### Application Workflow

1. User uploads an Instagram or LinkedIn CSV file.
2. The CSV loader reads the uploaded dataset.
3. The validation and cleaning modules check data quality.
4. The column mapper identifies and standardizes CSV columns.
5. The analytics engine calculates performance metrics.
6. The comparison engine evaluates reporting periods.
7. Plotly generates interactive visualizations.
8. The AI service generates data-grounded insights and recommendations.
9. The PDF generator creates a downloadable analytics report.

## 📂 Project Folder Structure

```text
SocialPulse_AI/
│
├── app.py
│
├── pages/
│   ├── 1_Dashboard_Overview.py
│   ├── 2_CSV_Upload_and_Prep.py
│   ├── 3_Deep_Analytics.py
│   ├── 4_Top_Posts_Explorer.py
│   ├── 5_AI_Insights.py
│   └── 6_Export_PDF_Reports.py
│
├── components/
│   ├── sidebar.py
│   ├── header.py
│   ├── kpi_cards.py
│   ├── charts.py
│   ├── post_cards.py
│   └── filters.py
│
├── services/
│   ├── csv_loader.py
│   ├── data_validator.py
│   ├── data_cleaner.py
│   ├── column_mapper.py
│   ├── analytics_engine.py
│   ├── comparison_engine.py
│   ├── ai_insights.py
│   └── pdf_generator.py
│
├── utils/
│   ├── constants.py
│   ├── formatters.py
│   ├── helpers.py
│   └── session_manager.py
│
├── assets/
│   ├── logo.png
│   └── custom.css
│
├── data/
│   ├── sample_instagram_data.csv
│   └── sample_linkedin_data.csv
│
├── tests/
│   ├── test_analytics.py
│   ├── test_validation.py
│   └── test_comparison.py
│
├── reports/
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 📊 Performance Metrics & Calculations

SocialPulse AI uses consistent metric definitions to ensure accurate performance analysis.

**1. Total Engagements**

```text
Total Engagements = Likes + Comments + Shares + Saves
```

If saves are unavailable, available interaction metrics are used and the limitation is disclosed.

**2. Engagement Rate by Reach**

```text
Engagement Rate = (Total Engagements / Total Reach) × 100
```

**3. Average Post Engagement Rate**

Calculated as the arithmetic mean of individual post engagement rates.

**4. Follower Growth**

```text
Follower Growth = Latest Followers - Earliest Followers
```

Follower growth is calculated only when valid follower snapshots are available.

**5. Percentage Change**

```text
Percentage Change =
((Current Period - Previous Period) / Previous Period) × 100
```

Division-by-zero cases are handled safely.

**Important:** Reach and impressions are aggregated from post-level records. They should not be interpreted as unique account-level audience counts.

## 📁 Supported CSV Format

The application supports Instagram analytics CSV files, LinkedIn analytics CSV files, and compatible custom datasets.

| Standard Field | Supported Column Examples |
|---|---|
| Date | Date, Published Date, Post Date |
| Post | Post, Caption, Content |
| Reach | Reach, Accounts Reached |
| Impressions | Impressions, Views |
| Likes | Likes, Reactions |
| Comments | Comments |
| Shares | Shares, Reposts |
| Followers | Followers, Followers Count |
| Saves | Saves, Bookmarks |
| Post Type | Post Type, Media Type, Content Type |

Automatic column mapping helps standardize different CSV formats.

Missing metrics are not silently treated as zero. The application communicates unavailable metrics and their impact on calculations.

## 🤖 AI Integration

SocialPulse AI integrates Large Language Models through the Groq API or OpenAI API.

The AI service receives summarized performance metrics and calculated trends rather than unnecessarily sending the entire raw dataset.

AI capabilities include:
- Executive performance summaries.
- Content strategy analysis.
- Engagement optimization.
- Reach improvement suggestions.
- Identification of strengths and weaknesses.
- Actionable recommendations.

API keys are stored securely using environment variables.

If an API key is unavailable, the application provides clearly labelled rule-based insights instead of pretending that the results are AI-generated.

## 📄 PDF Report Generation

The PDF generation module uses ReportLab to create professional reports based on the currently selected dataset and reporting period.

Reports include KPI tables, performance charts, engagement analysis, post rankings, AI insights, recommendations, and data limitations.








⭐ If you find this project useful, consider giving the repository a star!
