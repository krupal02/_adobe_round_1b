FROM python:3.9-slim-buster

WORKDIR /app

COPY . /app


RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p input_pdfs output

CMD ["python", "main.py"]