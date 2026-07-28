FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# dev lockfile on purpose: the same image runs the server and the test suite
# (docker-compose.tests.yml); split into stages if a lean prod image is needed
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements-dev.txt

COPY alembic.ini pytest.ini mypy.ini ./
COPY migrations ./migrations
COPY source ./source
COPY tests ./tests

RUN useradd --create-home app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m source.server"]
