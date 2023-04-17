FROM python:3.9

WORKDIR /app

RUN mkdir /app/logs
RUN touch /app/logs/errors.txt
RUN touch /app/logs/logs.txt

COPY requirements.txt /app
RUN pip3 install -r requirements.txt

COPY . /app

CMD ["uvicorn", "main:app", "--workers", "4", "--host=0.0.0.0", "--port", "80"]
