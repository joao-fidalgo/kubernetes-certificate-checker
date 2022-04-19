FROM alpine:3.15

ENV CLUSTER_NAME changeme
ENV DAYS_UNTIL 3
ENV WEBHOOK_URL changeme

RUN apk add gcc musl-dev python3-dev py3-pip libffi-dev openssl-dev && \
    pip install -U pip && \
    pip install pyopenssl pymsteams

COPY ./certificate-checker.py /certificate-checker.py

ENTRYPOINT ["/usr/bin/python3"]
CMD ["/certificate-checker.py"]