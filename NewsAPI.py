import pandas as pd
import requests
from datetime import datetime, timedelta
import yaml
from pathlib import Path
import urllib3

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -----------------------------
# 뉴스 API 함수
# -----------------------------
def fetch_news_articles(start_date, end_date, keyword="경제", language="ko", page_size=10):

    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("NEWS_API_KEY")  # 환경변수에서 API 키를 읽음

    today = datetime.today()
    start = max(datetime.strptime(start_date, "%Y-%m-%d"), today - timedelta(days=29))
    end = min(datetime.strptime(end_date, "%Y-%m-%d"), today)

    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={keyword}"
        f"&from={start.strftime('%Y-%m-%d')}"
        f"&to={end.strftime('%Y-%m-%d')}"
        f"&sortBy=publishedAt"
        f"&language={language}"
        f"&pageSize={page_size}"
        f"&apiKey={api_key}"
    )

    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"❌ 오류 발생: {e}"

    articles = response.json().get('articles', [])
    news_data = []
    for article in articles:
        title = article.get('title')
        link = article.get('url')
        if title and link:
            news_data.append({"title": title, "url": link})
    return news_data


# -----------------------------
# 앱 초기화 및 테마 설정
# -----------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "📄 뉴스 요약 대시보드"

language_options = [
    {"label": "🇰🇷 한국어", "value": "ko"},
    {"label": "🇺🇸 영어", "value": "en"},
    {"label": "🇯🇵 일본어", "value": "ja"},
    {"label": "🇨🇳 중국어", "value": "zh"},
    {"label": "🇩🇪 독일어", "value": "de"},
]

# -----------------------------
# 레이아웃
# -----------------------------
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H2("📰 뉴스 검색 대시보드", className="text-center my-4"), width=12)
    ]),
    
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("🔍 검색어"),
                    dcc.Input(id="input-keyword", type="text", value="관세", className="form-control", placeholder="예: 반도체, 금리")
                ], md=6),

                dbc.Col([
                    dbc.Label("🌐 언어"),
                    dcc.Dropdown(id="language-select", options=language_options, value="ko", className="form-control")
                ], md=3),

                dbc.Col([
                    dbc.Label("📄 기사 수"),
                    dcc.Input(id="page-size", type="number", min=1, max=100, value=10, step=1, className="form-control")
                ], md=3)
            ], className="mb-3"),

            dbc.Row([
                dbc.Col(dbc.Button("검색", id="search-button", color="primary", className="w-100"), md=3),
            ], justify="end")
        ])
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.Div(id="news-output")
        ])
    ])
], fluid=True)


# -----------------------------
# 콜백
# -----------------------------
@app.callback(
    Output("news-output", "children"),
    Input("search-button", "n_clicks"),
    State("input-keyword", "value"),
    State("language-select", "value"),
    State("page-size", "value"),
)
def update_news(n_clicks, keyword, language, page_size):
    if not keyword:
        return dbc.Alert("❌ 검색어를 입력해주세요.", color="danger")

    today = datetime.today()
    start_date = (today - timedelta(14)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    news_data = fetch_news_articles(start_date, end_date, keyword, language, page_size)

    if isinstance(news_data, str):
        return dbc.Alert(news_data, color="danger")

    if news_data:
        return dbc.ListGroup([
            dbc.ListGroupItem([
                html.H5(item['title'], className="mb-1"),
                html.A("📎 자세히 보기", href=item['url'], target="_blank", className="text-primary")
            ]) for item in news_data
        ])
    else:
        return dbc.Alert("❌ 관련 뉴스가 없습니다.", color="warning")


# -----------------------------
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)