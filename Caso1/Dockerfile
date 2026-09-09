# Dockerfile basico - una sola etapa, imagen completa de Python
FROM python:3.12

WORKDIR /app

COPY . .

RUN apt-get update
RUN apt-get install -y ffmpeg
RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
