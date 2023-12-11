FROM python:3.11-slim
LABEL authors="sawcka"

WORKDIR /app

COPY poetry.lock handlers.py main.py pyproject.toml shedule_parser.py views.py ./

RUN python -m pip install --no-cache-dir poetry && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi \
    && rm -rf $(poetry config cache-dir)/{cache,artifacts}

ENTRYPOINT ["python", "main.py"]