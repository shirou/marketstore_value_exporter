FROM python:3.7-slim-buster as builder

WORKDIR /opt/app

COPY requirements.lock /opt/app
RUN pip3 install -r requirements.lock

#################################################
FROM gcr.io/distroless/python3-debian10 as runner

COPY --from=builder /usr/local/lib/python3.7/site-packages /root/.local/lib/python3.7/site-packages

COPY main.py /opt/app/main.py

WORKDIR /opt/app/

EXPOSE 8000
ENTRYPOINT ["python3", "main.py"]