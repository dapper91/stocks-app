"""
Flask application request handlers.
"""

import textwrap
import urllib

import flask
import psycopg2.extensions
import webargs
from sqlalchemy import orm
from webargs import flaskparser

from app import app
from app import blueprint
from app import db
from app import forms
from app import models
from app import serialization as sz


def is_api_request():
    """
    Checks if the request is handled in api context.

    :rtype: bool
    """

    return flask.request.path.startswith('/api')


def build_response(json_data, template_name, **template_args):
    """
    Builds response (json or html) depending on the context ('/api' or '/').

    :param json_data: json data to be sent in json response
    :param template_name: template name to render the web page
    :param template_args: html template arguments
    :return: json or rendered html page response
    """

    return flask.jsonify(json_data) if is_api_request() else flask.render_template(template_name, **template_args)


@blueprint.route('/', strict_slashes=False)
def get_tickers():
    """
    Returns stocks information for the ticker.

    :return: json or rendered html page response
    """

    stocks = models.Stock.query.all()

    return build_response(
        json_data=sz.StockApiSchema(many=True).dump(stocks).data,
        template_name='stocks.html',
        stocks=stocks
    )


@blueprint.route('/<ticker>', strict_slashes=False)
def get_ticker(ticker):
    """
    Returns quotes information for the ticker.

    :param ticker: ticker name
    :return: json or rendered html page response
    :raises HTTPException with 404 code if the stock not found
    """

    stock = models.Stock.query.filter_by(ticker=ticker).first_or_404()
    quotes = models.Quote.query.filter_by(stock_id=stock.id).all()

    return build_response(
        json_data=sz.QuoteApiSchema(many=True).dump(quotes).data,
        template_name='quotes.html',
        ticker=ticker,
        quotes=quotes
    )


@blueprint.route('/<ticker>/insider', strict_slashes=False)
def get_insiders(ticker):
    """
    Returns trade information for the ticker.

    :param ticker: ticker name
    :return: json or rendered html page response
    :raises HTTPException with 404 code if the stock not found
    """

    stock = models.Stock.query.filter_by(ticker=ticker).first_or_404()
    trades = models.Trade.query.filter_by(stock_id=stock.id).options(orm.joinedload(models.Trade.insider)).all()

    return build_response(
        json_data=sz.TradeApiSchema(many=True).dump(trades).data,
        template_name='insiders.html',
        ticker=ticker,
        trades=trades
    )


@blueprint.route('/<ticker>/insider/<name>', strict_slashes=False)
def get_insider(ticker, name):
    """
    Returns trade information for the ticker made by the particular insider.

    :param ticker: ticker name
    :param name: insider name
    :return: json or rendered html page response
    :raises HTTPException with 404 code if the stock or insider not found
    """

    name = urllib.parse.unquote(name)
    stock = models.Stock.query.filter_by(ticker=ticker).first_or_404()
    insider = models.Insider.query.filter_by(name=name).first_or_404()
    trades = models.Trade.query.filter_by(stock_id=stock.id, insider_id=insider.id).all()

    return build_response(
        json_data=sz.TradeApiSchema(many=True).dump(trades).data,
        template_name='insider.html',
        ticker=ticker,
        name=name,
        trades=trades
    )


analytics_request_schema = {
    'date_from': webargs.fields.Date(required=True),
    'date_to': webargs.fields.Date(required=True),
}


@blueprint.route('/<ticker>/analytics')
@flaskparser.use_args(analytics_request_schema)
def get_analytics(args, ticker):
    """
    Returns 'open', 'high', 'low' and 'close' price difference for all the dates within 'date_from' and 'date_to'.

    :param args: query parameters
    :param ticker: ticker name
    :return: json or rendered html page response
    :raises HTTPException with 404 code if the stock not found
    """

    stock = models.Stock.query.filter_by(ticker=ticker).first_or_404()

    query = textwrap.dedent('''

        WITH pivoted AS (
            SELECT id, stock_id, date, volume, open_price AS price, 'open' AS price_type
            FROM quote
            UNION
            SELECT id, stock_id, date, volume, close_price AS price, 'close' AS price_type
            FROM quote
            UNION
            SELECT id, stock_id, date, volume, high_price AS price, 'high' AS price_type
            FROM quote
            UNION
            SELECT id, stock_id, date, volume, low_price AS price, 'low' AS price_type
            FROM quote
        )
        SELECT p1.date AS start_date,
               p2.date AS end_date,
               p1.price AS start_price,
               p2.price AS end_price,
               p1.price_type,
               abs(p1.price - p2.price) AS price_diff
        FROM pivoted p1 INNER JOIN pivoted p2 ON p1.date < p2.date
        WHERE p1.price_type = p2.price_type
          AND p1.date >= %(date_from)s
          AND p2.date <= %(date_to)s
          AND p2.stock_id = p1.stock_id
          AND p2.stock_id = %(stock_id)s

    ''')

    data_proxy = db.engine.execute(query, stock_id=stock.id, date_from=args['date_from'], date_to=args['date_to'])
    data = list(data_proxy)

    return build_response(
        json_data=[dict(zip(data_proxy.keys(), row)) for row in data],
        template_name='analytics.html',
        ticker=ticker,
        date_from=args['date_from'],
        date_to=args['date_to'],
        data=data
    )


delta_request_schema = {
    'value': webargs.fields.Float(required=True, validate=lambda val: val >= 0),
    'type': webargs.fields.Str(required=True, validate=webargs.validate.OneOf(list(map(str, models.PriceType)))),
}


@blueprint.route('/<ticker>/delta')
@flaskparser.use_args(delta_request_schema)
def get_delta(args, ticker):
    """
    Returns 'open', 'high', 'low' or 'close' price deltas between dates for the ticker
    where the delta is greater or equals to 'value' and the dates interval is minimal.

    :param args: query parameters
    :param ticker: ticker name
    :return: json or rendered html page response
    :raises HTTPException with 404 code if the stock not found
    """

    stock = models.Stock.query.filter_by(ticker=ticker).first_or_404()

    query = textwrap.dedent('''

        WITH diff_subquery AS (
            SELECT q1.date AS start_date,
                   q2.date AS end_date,
                   q1.{price_type} AS start_price,
                   q2.{price_type} AS end_price,
                   q2.date - q1.date as date_diff,
                   abs(q1.{price_type} - q2.{price_type}) AS price_diff
            FROM quote q1 INNER JOIN quote q2 ON q1.date < q2.date
            WHERE abs(q1.{price_type} - q2.{price_type}) >= %(value)s
              AND q2.stock_id = q1.stock_id
              AND q2.stock_id = %(stock_id)s
        )
        SELECT *
        FROM diff_subquery
        WHERE date_diff = (
            SELECT MIN(date_diff)
            FROM diff_subquery
        )

    ''')

    column_name = args['type'] + '_price'
    cursor = db.engine.raw_connection().cursor()

    # to prevent sql injections use quote_ident function of psycopg2
    safe_query = query.format(price_type=psycopg2.extensions.quote_ident(column_name, cursor))
    data_proxy = db.engine.execute(safe_query, stock_id=stock.id, value=args['value'])
    data = list(data_proxy)

    return build_response(
        json_data=[dict(zip(data_proxy.keys(), row)) for row in data],
        template_name='delta.html',
        ticker=ticker,
        value=args['value'],
        price_type=args['type'],
        data=data
    )


@app.route('/analytics/form', methods=['GET', 'POST'])
def analytics_form():
    """
    Returns analytics web form on 'GET' request and redirects to 'get_analytics' on 'POST' request
    using form fields if the form is filled correctly otherwise returns itself.
    """

    form = forms.AnalyticForm()
    if form.validate_on_submit():
        return flask.redirect(
            flask.url_for(
                'common.get_analytics',
                ticker=form.ticker.data,
                date_from=form.date_from.data,
                date_to=form.date_to.data
            )
        )

    return flask.render_template('analytics_form.html', form=form)


@app.route('/delta/form', methods=['GET', 'POST'])
def delta_form():
    """
    Returns delta web form on 'GET' request and redirects to 'get_delta' on 'POST' request
    using form fields if the form is filled correctly otherwise returns itself.
    """

    form = forms.DeltaForm()
    if form.validate_on_submit():
        return flask.redirect(
            flask.url_for(
                'common.get_delta',
                ticker=form.ticker.data,
                value=form.value.data,
                type=form.type.data
            )
        )

    return flask.render_template('delta_form.html', form=form)
