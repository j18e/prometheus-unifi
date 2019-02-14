FROM python:3.7-alpine

RUN pip install --upgrade docopt prometheus_client requests

ADD main.py main.py

ENTRYPOINT ["python3", "-u", "main.py"]
