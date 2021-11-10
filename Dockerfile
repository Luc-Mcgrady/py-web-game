FROM python:3.9.8

COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt

COPY . .

EXPOSE 80

CMD ["python", "./server.py"]