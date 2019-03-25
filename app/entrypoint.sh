#!/bin/sh

while true; do
    python initdb.py
    if [ $? -eq 0 ]; then
        echo 'Database successfully initialized'
        break
    fi

    echo 'Database initialization failed, retrying in 5 seconds...'
    sleep 5
done


echo 'Fetching data from https://www.nasdaq.com'
python data_fetcher.py --threads ${FETCHER_WORKERS} --max-pages ${MAX_PAGES:-10} -t './tickers.txt' --loglevel info
if [ $? -ne 0 ]; then
    echo 'Nasdaq data fetching failed'
    exit 1
fi
echo 'Nasdaq data successfully fetched'

exec "$@"