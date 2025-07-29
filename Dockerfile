FROM linuxserver/python:3.12.7
LABEL maintainer=qs315490

WORKDIR /app

COPY pyproject.toml,uv.lock,*.py,jm_options.yml .

RUN pip install uv
RUN uv sync

VOLUME /app/tmp

CMD ["python", "main.py"]