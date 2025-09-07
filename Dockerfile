FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r django && useradd -r -g django djangouser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=djangouser:django . .

USER djangouser

EXPOSE 8000

ENTRYPOINT [ "/app/entrypoint.sh" ]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
