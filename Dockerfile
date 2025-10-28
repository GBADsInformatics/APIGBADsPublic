FROM python:3.11

WORKDIR /app

# Copy requirements and nationality file first for better caching
COPY requirements/requirements.txt /app/requirements/
COPY requirements/nationality.csv /app/requirements/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r /app/requirements/requirements.txt

# Download GloVe embeddings and extract only the 50d file into requirements/
RUN apt-get update && apt-get install -y curl unzip && \
    curl -L -o /app/requirements/glove.6B.zip https://nlp.stanford.edu/data/glove.6B.zip && \
    unzip -j /app/requirements/glove.6B.zip "glove.6B.50d.txt" -d /app/requirements/ && \
    rm /app/requirements/glove.6B.zip && \
    apt-get remove -y curl unzip && apt-get autoremove -y

# Copy the rest of the app
COPY . /app

# Add a healthcheck that uses BASE_URL
ENV BASE_URL=
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f -L http://localhost:80$BASE_URL || exit 1

CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port", "80"]
