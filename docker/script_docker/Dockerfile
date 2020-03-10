FROM python:3.7.4-slim

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

EXPOSE 8990

ENTRYPOINT ["python", "-m", "app.hello"]
