# Dockerfile
FROM python:3.10
COPY requirements.txt /
RUN pip3 install -r /requirements.txt
COPY . .
ENV REDIS_GATEWAY 172.19.0.2
ENV MONGODB_GATEWAY 172.19.0.4
ENV MY_ADDRESS http://localhost:8000/
CMD ./run.sh
