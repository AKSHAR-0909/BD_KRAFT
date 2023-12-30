FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3 python3-pip
RUN apt-get update && apt-get install -y netcat

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY . /code/
