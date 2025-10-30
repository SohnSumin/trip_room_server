FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "app.py", "test.py"]
ENV MONGO_URI="mongodb+srv://somsumun_db_user:c16Mv5bXC8JxQpQ4@cluster0.3liugev.mongodb.net/trip_room_db?retryWrites=true&w=majority"