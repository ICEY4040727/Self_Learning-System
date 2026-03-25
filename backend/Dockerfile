FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install uv && uv pip install --no-cache-dir --system -r requirements.txt

COPY . ./backend/
COPY entrypoint.sh /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]
