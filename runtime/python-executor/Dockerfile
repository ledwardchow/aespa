FROM python:3.12-slim

RUN useradd --uid 65532 --create-home --shell /usr/sbin/nologin sandbox
COPY aespa_runtime /usr/local/lib/python3.12/site-packages/aespa_runtime
COPY aespa_harness.py /opt/aespa_harness.py
COPY aespa_child.py /opt/aespa_child.py
RUN chmod 0555 /opt/aespa_harness.py /opt/aespa_child.py \
    && chmod -R a=rX /usr/local/lib/python3.12/site-packages/aespa_runtime

USER 65532:65532
WORKDIR /work
ENTRYPOINT ["python", "-I", "/opt/aespa_harness.py"]

