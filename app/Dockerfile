FROM python:3.7.2-slim-stretch

WORKDIR /stocks-app

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./entrypoint.sh .
RUN chmod +x ./entrypoint.sh

COPY ./gunicorn.conf.py stocks_app.py ./
COPY ./initdb.py ./data_fetcher.py ./

COPY ./tickers.txt .
COPY ./app ./app

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "-c", "gunicorn.conf.py", "stocks_app:app"]