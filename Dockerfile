FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copy project first
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements/base.txt
RUN pip install gunicorn

# Create static and media directories and ensure they're writable
RUN mkdir -p staticfiles media && chmod -R 777 staticfiles media

EXPOSE 8000

# Use a startup script instead of running collectstatic during build
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]