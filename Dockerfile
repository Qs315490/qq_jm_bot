FROM python:3.12.11-alpine3.22
LABEL maintainer=qs315490

WORKDIR /app

COPY pyproject.toml *.py jm_options.yml ./

RUN /bin/sh -c set -eux; apk add --no-cache uv
RUN /bin/sh -c set -eux; uv sync

ARG PROXY
RUN if [ -n "$PROXY" ];then sed -i "s|proxies: system|proxies: ${PROXY}|g" jm_options.yml;fi

VOLUME /app/tmp

CMD [".venv/bin/python", "main.py"]