FROM python:3.11-slim

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flask 내장 개발 서버를 직접 실행합니다. (프로덕션 환경에는 권장되지 않음)
CMD ["python", "app.py"]
