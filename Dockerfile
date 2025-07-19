FROM python:3.11

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app


# Copy only requirements first for better caching
COPY requirements/requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt


# Copy the rest of the app
COPY . /app

# Set restrictive permissions
RUN chown -R appuser:appuser /app && chmod -R 750 /app

# Switch to non-root user
USER appuser

# Add a healthcheck that uses BASE_URL
ENV BASE_URL=/
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 CMD curl -f -L http://localhost:80$BASE_URL || exit 1

CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port", "80"]
