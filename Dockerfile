# Dockerfile
FROM python:3.10
COPY requirements.txt /
RUN pip3 install -r /requirements.txt
COPY . .
CMD ["gunicorn"  , "-b", "0.0.0.0:2611", "ibc:app"]; ["python", "execution/execution_service.py"]
