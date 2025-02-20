FROM ubuntu:20.04

COPY . /analyticks

WORKDIR /analyticks



RUN apt update && apt upgrade -y
RUN add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && apt-cache search python3.1

RUN apt-get install python3.10 -y && apt-get install python3-pip -y

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python3","main.py" ]