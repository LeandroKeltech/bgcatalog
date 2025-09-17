FROM kivy/buildozer:latest

WORKDIR /app
COPY . /app

RUN buildozer android debug
