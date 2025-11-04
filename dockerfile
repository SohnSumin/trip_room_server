FROM python:3.11-slim

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flask만 실행 (test.py는 따로 관리 권장)
CMD ["python", "app.py"]

ENV MONGO_URI="mongodb+srv://somsumun_db_user:c16Mv5bXC8JxQpQ4@cluster0.3liugev.mongodb.net/trip_room_db?retryWrites=true&w=majority"
