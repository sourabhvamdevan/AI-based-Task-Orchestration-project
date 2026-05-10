
FROM python:3.11-slim


RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY . .

ENV PYTHONUNBUFFERED=1 \
    ALFRED_KB_PATH=/app/data/alfred_kb.json

RUN mkdir -p /app/data && chmod 777 /app/data

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH


EXPOSE 7860


CMD ["python", "app.py"]