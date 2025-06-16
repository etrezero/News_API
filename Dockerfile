# ✅ Python 3.10 기반 경량 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 전체 복사
COPY . .

# Dash 앱이 사용하는 포트 열기
EXPOSE 8050

# 앱 실행 명령 (NewsAPI.py를 app.py로 썼다면 여기서 수정 가능)
CMD ["python", "NewsAPI.py"]
