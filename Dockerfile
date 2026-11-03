FROM python:3.12-slim

WORKDIR /app
COPY app.py test_app.py ./

# Unit tests run during the build; the live GitHub test is skipped here.
RUN SKIP_LIVE=1 python -m unittest -v test_app

RUN useradd --no-create-home appuser
USER appuser

ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "app.py"]
