"""
Nasdaq data fetching script. Contains classes for parsing nasdaq web page
and saving data to the application database. Should be executed on application startup.
"""

import argparse
import logging
import urllib.parse as url_parser
from concurrent import futures as conc_futures

import bs4
import requests
import sqlalchemy.exc
from dateutil import parser as date_parser

from app import db
from app import models


logger = logging.getLogger('fetcher')


class ParsingError(Exception):
    """
    Base parser error.
    """


class Parser:
    """
    Nasdaq web page parser. Parses 'history' and 'insider-trades' page tables.
    """

    BASE_URL = 'https://www.nasdaq.com'

    @staticmethod
    def parse_page(url, **params):
        """
        Parses the page at the url and returns its DOM

        :param url: page url to parse
        :param params: parameters to be passed to the 'request' method
        :return: parsed page DOM
        """

        resp = requests.get(url, params=params)
        resp.raise_for_status()
        page_dom = bs4.BeautifulSoup(resp.text, 'html.parser')

        return page_dom

    @staticmethod
    def find_tag(dom, **kwargs):
        """
        Finds a tag by kwargs conditions.

        :param dom: page DOM to be used for search
        :param kwargs: arguments to be passed to 'find' method
        :return: the requested tag
        :raises ParsingError is the requested tag not found
        """

        result = dom.find(**kwargs)
        if result is None:
            raise ParsingError(f"Tag {kwargs} not found")

        return result

    @staticmethod
    def parse_table(table_dom):
        """
        Parses table DOM and returns the result in a matrix form.

        :param table_dom: web page table DOM
        :return: list of table rows
        """

        return [[col.get_text().strip() for col in row.find_all('td')]
                for row in table_dom.find_all('tr', recursive=False)]

    @classmethod
    def parse_history(cls, ticker):
        """
        Parses nasdaq 'historical' web page table and returns historical data.

        :param ticker: ticker name
        :return: historical data as a list of dicts
        """

        page_dom = cls.parse_page(f'{cls.BASE_URL}/symbol/{ticker.lower()}/historical')
        div_dom = cls.find_tag(page_dom, name='div', id='quotes_content_left_pnlAJAX')
        table_dom = cls.find_tag(div_dom, name='table').find('tbody')

        table = cls.parse_table(table_dom)
        result = []

        for row in table:
            if len(row) != 6:
                logger.warning(f"Unexpected table row size (expected: 6, actual: {len(row)}): {row}")
                continue

            try:
                result.append(dict(
                    date=date_parser.parse(row[0]).date(),
                    open_price=float(row[1].replace(',', '')),
                    high_price=float(row[2].replace(',', '')),
                    low_price=float(row[3].replace(',', '')),
                    close_price=float(row[4].replace(',', '')),
                    volume=float(row[5].replace(',', '')),
                ))
            except ValueError as e:
                logger.warning(f"Unexpected data format: {ticker} {e}")
                continue

        return result

    @classmethod
    def parse_trades(cls, ticker, page=1):
        """
        Parses nasdaq 'insider-trades' web page table and returns trades data.

        :param ticker: ticker name
        :param page: page number to parse
        :return: historical data as a list of dicts
        """

        page_dom = cls.parse_page(f'{cls.BASE_URL}/symbol/{ticker.lower()}/insider-trades', page=page)
        page_count = cls.parse_trades_page_count(page_dom)

        result = []
        if page <= page_count:
            div_dom = cls.find_tag(page_dom, name='div', class_='genTable')
            table_dom = cls.find_tag(div_dom, name='table')

            table = cls.parse_table(table_dom)

            for row in table:
                if len(row) != 8:
                    logger.warning(f"Unexpected table row size (expected: 8, actual: {len(row)}): {row}")
                    continue

                try:
                    result.append(dict(
                        insider=row[0],
                        relation=row[1],
                        last_date=date_parser.parse(row[2]).date(),
                        transaction_type=row[3],
                        owner_type=row[4],
                        shares_traded=float(row[5].replace(',', '')),
                        last_price=float(row[6]) if row[6] else None,
                        shares_hold=float(row[7].replace(',', '')),
                    ))
                except ValueError as e:
                    logger.warning(f"Unexpected data format: {ticker} {page} {e}")
                    continue

        return result

    @classmethod
    def parse_trades_page_count(cls, page_dom):
        """
        Traverses nasdaq 'insider-trades' page DOM to find the page count.

        :param page_dom: page DOM to traverse
        :return: number of pages
        """

        last_page_dom = cls.find_tag(page_dom, id='quotes_content_left_lb_LastPage')
        last_page_url = url_parser.urlparse(last_page_dom.get('href', ''))

        return int(url_parser.parse_qs(last_page_url.query).get('page', ['1'])[0])


class Fetcher:
    """
    Multi-threaded nasdaq data fetcher.
    """

    @property
    def session(self):
        """
        :return: thread-local db session
        """

        return db.session()

    def __init__(self, max_workers, max_trades_pages=10):
        """
        :param max_workers: number of threads (workers) the tasks to be executed on
        :param max_trades_pages: maximum number of trades pages to parse
        """

        self._max_workers = max_workers
        self._max_trades_pages = max_trades_pages
        self._executor = conc_futures.ThreadPoolExecutor(max_workers)

    def fetch(self, tickers):
        """
        Executes nasdaq data fetching tasks using thread pool executor and waits for the result.

        :param tickers: ticker names to fetch the information about
        """

        logger.info(f"Fetching nasdaq data using {self._max_workers} threads")
        futures = []

        for ticker in tickers:
            futures.append(self._executor.submit(self.fetch_history, ticker))
            for page in range(self._max_trades_pages):
                futures.append(self._executor.submit(self.fetch_trades, ticker, page + 1))

        for future in conc_futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as e:
                logger.error(f"Fetching task failed: {e}")
            else:
                logger.info(f"Fetching task finished: {result}")

        logger.info(f"Data fetching successfully finished")

    def fetch_history(self, ticker):
        """
        Fetches history information about the ticker

        :param ticker: ticker name
        :return: result message
        """

        history = Parser.parse_history(ticker)

        try:
            stock = self.upsert(models.Stock, dict(ticker=ticker), keys=('ticker',))
            for item in history:
                item.update(stock_id=stock.id)
                self.upsert(models.Quote, item, keys=('date', 'stock_id'))

        except Exception:
            self.session.rollback()
            raise

        return f"{len(history)} history items for '{ticker}' has been collected"

    def fetch_trades(self, ticker, page):
        """
        Fetches trade information about the ticker

        :param ticker: ticker name
        :param page: page number to parse
        :return: result message
        """

        trades = Parser.parse_trades(ticker, page)

        try:
            stock = self.upsert(models.Stock, dict(ticker=ticker), keys=('ticker',))
            for trade in trades:
                insider_data = dict(name=trade.pop('insider'), relation=trade.pop('relation'))
                insider = self.upsert(models.Insider, insider_data, keys=('name',))

                self.session.add(models.Trade(stock_id=stock.id, insider_id=insider.id, **trade))
                self.session.commit()

        except Exception:
            self.session.rollback()
            raise

        return f"{len(trades)} trade items for '{ticker}' has been collected (page: {page})"

    def upsert(self, model, data, keys):
        """
        Inserts 'model' object to the database or updates it if it already exists.

        :param model: database model
        :param data: model fields to be updated or used for the creating a new object if it already exists
        :param keys: model fields to be used for identification (primary or unique fields)
        :return: updated or inserted object
        """

        key_fields = {key: data[key] for key in keys}
        instance = model(**data)

        try:
            self.session.add(instance)
            self.session.flush()

        except sqlalchemy.exc.IntegrityError:
            self.session.rollback()
            instance = self.session.query(model).filter_by(**key_fields).first()

            for key, value in data.items():
                setattr(instance, key, value)

        self.session.commit()

        return instance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch data from nasdaq.')
    parser.add_argument('-l', '--loglevel', dest='loglevel', choices=['debug', 'warning', 'info'], default='info', help='logging level')
    parser.add_argument('-n', '--threads', dest='threads', type=int, default=4, help='number of threads the tasks to be executed on')
    parser.add_argument('-p', '--max-pages', dest='pages', type=int, default=1, help='maxinum number of trade pages to parse')
    parser.add_argument('-t', '--tickers', dest='tickers', default='tickers.txt', help='tickers file')

    args = parser.parse_args()

    logger_format = '[%(levelname)-8s] %(asctime)-15s (%(name)s): %(message)s'
    logging.basicConfig(level=getattr(logging, args.loglevel.upper()), format=logger_format)

    with open(args.tickers) as file:
        tickers = [line.strip() for line in file.readlines()]

    fetcher = Fetcher(max_workers=args.threads, max_trades_pages=args.pages)
    fetcher.fetch(tickers)
