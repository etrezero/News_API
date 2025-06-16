import os
import base64
import requests
import yaml
import openai
import re
from pathlib import Path
from dash import Dash, html, dcc, Input, Output, State
from urllib.parse import quote
from google.cloud import texttospeech
import dash_bootstrap_components as dbc
from PIL import Image
from datetime import datetime
from flask import send_from_directory

# ---------------- 설정 ----------------
BASE_DIR = Path("D:/code")
CONFIG_PATH = BASE_DIR / "config.yaml"
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

openai.api_key = config["openai_api_key"]
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(config["google_service_account"])
NEWSAPI_KEY = config["newsapi_key"]

# GPT 클라이언트
from openai import OpenAI
client = OpenAI(api_key=config["openai_api_key"])

# ---------------- 뉴스 요약 및 음성 생성 ----------------
def fetch_news_headlines():
    url = "https://newsapi.org/v2/top-headlines"
    params = {'category': 'business', 'language': 'en', 'pageSize': 30, 'apiKey': NEWSAPI_KEY}
    r = requests.get(url, params=params)
    articles = r.json().get('articles', [])
    return [{'label': a['title'], 'value': a['description'], 'title': a['title']} for a in articles if a.get('description')]

def is_english(text):
    return len(re.findall(r'[a-zA-Z]', text)) > len(re.findall(r'[가-힣]', text))

def summarize_with_gpt(text):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "뉴스의 핵심 내용, 배경 맥락, 요점을 3문장으로 한국어로 요약해줘."},
                  {"role": "user", "content": text}]
    )
    return response.choices[0].message.content.strip()

def summarize_and_translate_if_needed(news_option):
    title = news_option.get('title', '제목 없음')
    description = news_option.get('value', '')
    translated_title = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Translate this English news headline into natural Korean."},
                  {"role": "user", "content": title}]
    ).choices[0].message.content.strip()
    full_text = f"{title}\n{description}"
    summary = summarize_with_gpt(full_text)
    return f"#{translated_title}\n{summary}"

def summarize_selected_news(news_list):
    summaries = []
    for news in news_list:
        try:
            summary = summarize_and_translate_if_needed(news)
            summaries.append(summary)
        except Exception as e:
            summaries.append(f"❌ 요약 실패: {e}")
    return "커버넌트 뉴스\n\n" + "\n\n".join(summaries)

def generate_voice(text, output_path, voice_name, speaking_rate):
    client_tts = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="ko-KR", name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=speaking_rate)
    response = client_tts.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    with open(output_path, "wb") as out:
        out.write(response.audio_content)

def today():
    return datetime.now().strftime("%Y-%m-%d %H")

# ---------------- Dash 앱 구성 ----------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "뉴스 요약 음성 앱"

app.layout = html.Div([
    html.H2("📰 GPT 뉴스 요약 + 음성 미리듣기"),

    html.H4("1️⃣ 뉴스 제목 선택"),
    dcc.Dropdown(id="news-dropdown", options=[], multi=True, placeholder="뉴스 제목 선택"),
    html.Button("📰 뉴스 새로고침", id="refresh-news", n_clicks=0, style={"marginBottom": "10px"}),
    html.Button("🧠 GPT로 뉴스 요약 반영", id="summarize-news", n_clicks=0, style={"marginBottom": "20px"}),

    html.H4("2️⃣ 텍스트 입력"),
    dcc.Textarea(id='text-input', style={'width': '100%', 'height': 200}),

    html.H4("3️⃣ 음성 설정"),
    dcc.Dropdown(id='voice-selector', options=[
        {"label": "Standard 남성", "value": "ko-KR-Standard-D"},
        {"label": "Neural2 여성", "value": "ko-KR-Neural2-B"}
    ], value="ko-KR-Standard-D", style={"width": "50%"}),
    dcc.Slider(id='speed-slider', min=0.5, max=1.5, step=0.05, value=1.2, marks={0.5: "느림", 1.0: "보통", 1.5: "빠름"}),

    html.H4("🔊 GPT 요약 음성 미리듣기"),
    html.Div(id='audio-preview', style={"marginBottom": "20px"})
], style={"width": "70%", "margin": "auto"})

@app.server.route("/output/<path:filename>")
def serve_output_file(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.callback(
    Output("news-dropdown", "options"),
    Input("refresh-news", "n_clicks")
)
def refresh_news(n_clicks):
    return fetch_news_headlines()

@app.callback(
    Output('text-input', 'value'),
    Output('audio-preview', 'children'),
    Input('summarize-news', 'n_clicks'),
    State('news-dropdown', 'value'),
    State('news-dropdown', 'options'),
    State('voice-selector', 'value'),
    State('speed-slider', 'value')
)
def update_text_from_news(n, selected_values, all_options, voice_name, speed):
    if not selected_values:
        return "커버넌트 뉴스\n", "뉴스를 먼저 선택해주세요."
    news_objs = [opt for opt in all_options if opt['value'] in selected_values]
    summary = summarize_selected_news(news_objs)

    voice_path = OUTPUT_DIR / "gpt_summary_voice.mp3"
    try:
        generate_voice(summary, voice_path, voice_name, speed)
        encoded = quote(voice_path.name)
        audio_player = html.Audio(src=f"/output/{encoded}", controls=True, autoPlay=True)
    except Exception as e:
        audio_player = f"❌ 음성 생성 실패: {e}"

    return summary, audio_player

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8050)
