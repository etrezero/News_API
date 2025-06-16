
import requests
from datetime import datetime, timedelta
import yaml
from pathlib import Path
import urllib3

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

import os

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





import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

def summarize_news_with_gpt(news_items):
    if not news_items:
        return "뉴스가 없습니다."

    prompt_text = "\n".join(f"- {item['title']}" for item in news_items)


    system_prompt = (
        "너는 숙련된 뉴스 편집자야.\n"
        "아래에 제시된 여러 뉴스 기사 제목들과 URL에 포함된 텍스트를 활용하지만, 단순히 나열하지 말고, "
        "전체적인 배경, 흐름, 인과관계, 시사점을 중심으로 하나의 줄거리처럼 연결해서 요약해줘.\n\n"
        "- 기사 간 주제 흐름이나 시점 변화가 자연스럽게 이어지게 구성하고,\n"
        "- 요약 분량은 1500자 이내로 제한하며,\n"
        "- 날짜, 출처, 숫자 인용은 생략해도 좋고 흐름을 해치지 않게 서술해.\n"
        "- 마치 저널리스트가 하나의 기사로 작성하듯 자연스럽게 정리해줘.\n\n"
        "형식은 간결하고 연결된 문장 중심으로, 핵심 흐름을 독자가 한 번에 파악할 수 있도록 작성해."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ 요약 중 오류 발생: {e}"



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
    
    # 🔹 제목
    dbc.Row([
        dbc.Col(html.H2("📰 뉴스 검색 대시보드", className="text-center my-4"), width=12)
    ]),

    # 🔹 검색 조건 입력 카드
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("🔍 검색어"),
                    dcc.Input(
                        id="input-keyword",
                        type="text",
                        value="관세",
                        className="form-control",
                        placeholder="예: 반도체, 금리"
                    )
                ], md=6),

                dbc.Col([
                    dbc.Label("🌐 언어"),
                    dcc.Dropdown(
                        id="language-select",
                        options=[
                            {"label": "🇰🇷 한국어", "value": "ko"},
                            {"label": "🇺🇸 영어", "value": "en"},
                            {"label": "🇯🇵 일본어", "value": "ja"},
                            {"label": "🇨🇳 중국어", "value": "zh"},
                            {"label": "🇩🇪 독일어", "value": "de"},
                        ],
                        value="ko",
                        className="form-control"
                    )
                ], md=3),

                dbc.Col([
                    dbc.Label("📄 기사 수"),
                    dcc.Input(
                        id="page-size",
                        type="number",
                        min=1,
                        max=100,
                        value=10,
                        step=1,
                        className="form-control"
                    )
                ], md=3)
            ], className="mb-3"),

            dbc.Row([
                dbc.Col(
                    dbc.Button("검색", id="search-button", color="primary", className="w-100"),
                    md=3
                ),
            ], justify="end")
        ])
    ], className="mb-4"),

    
    # 🔹 결과 영역 (전체 검색뉴스 요약 + 뉴스 리스트가 이 영역에 출력됨)
    dbc.Row([
        dbc.Col([
           dcc.Loading(
            id="loading",
            type="circle",
            color="#0d6efd",
            children=html.Div(
                id="news-output",
                children="📰 기사 요약중...",  # ✅ 로딩 중 기본 텍스트
                style={"marginTop": "20px", "fontStyle": "italic", "color": "#888"}
            )
        )

        ], width=12)
    ])

], fluid=True)  # ✅ 닫는 괄호가 이 위치에 필요합니다


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

    # 뉴스 데이터 가져오기
    news_data = fetch_news_articles(start_date, end_date, keyword, language, page_size)

    if isinstance(news_data, str):
        return dbc.Alert(news_data, color="danger")

    if news_data:
        # ✅ GPT 요약 생성
        gpt_summary = summarize_news_with_gpt(news_data)

        return html.Div([
            # 🔷 GPT 요약 박스
            dbc.Card([
                dbc.CardBody([
                    html.H5("📝 GPT 줄거리 요약", className="card-title"),
                    html.P(gpt_summary, style={"whiteSpace": "pre-wrap", "fontSize": "1rem"})
                ])
            ], className="mb-4"),

            # 🔷 뉴스 리스트 유지
            dbc.ListGroup([
                dbc.ListGroupItem([
                    html.H5(item['title'], className="mb-1"),
                    html.A("📎 자세히 보기", href=item['url'], target="_blank", className="text-primary")
                ]) for item in news_data
            ])
        ])
    
    else:
        return dbc.Alert("❌ 관련 뉴스가 없습니다.", color="warning")




# -----------------------------
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
