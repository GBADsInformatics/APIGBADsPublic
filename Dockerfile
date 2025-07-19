FROM python:3.11
WORKDIR /app

COPY requirements/requirements.txt /app
RUN pip3 install -r requirements.txt

COPY . /app

CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port", "80"]
