FROM python:3.9
WORKDIR /app

COPY requirements/requirements.txt /app
RUN pip3 install -r requirements.txt

COPY . /app

CMD ["uvicorn", "app.main:app", "--workers", "2", "--host=0.0.0.0", "--port", "80"]
