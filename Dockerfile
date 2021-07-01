FROM python:alpine

COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY ./ ./

CMD uvicorn main:app
