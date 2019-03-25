"""
Application web form classes.
"""

import flask_wtf as wtf
import wtforms
from wtforms import validators as wtfv

from app import models


class AnalyticForm(wtf.FlaskForm):
    """
    Analytics request web form.
    """

    ticker = wtforms.StringField(validators=[wtfv.DataRequired()])
    date_from = wtforms.DateField(validators=[wtfv.DataRequired()])
    date_to = wtforms.DateField(validators=[wtfv.DataRequired()])
    submit = wtforms.SubmitField()

    def validate_ticker(self, ticker):
        stock = models.Stock.query.filter_by(ticker=ticker.data).first()
        if stock is None:
            raise wtfv.ValidationError("Акция не найдена")


class DeltaForm(wtf.FlaskForm):
    """
    Delta request web form.
    """

    ticker = wtforms.StringField(validators=[wtfv.DataRequired()])
    value = wtforms.FloatField(validators=[wtfv.DataRequired()])
    type = wtforms.SelectField(choices=[(item, item) for item in map(str, models.PriceType)])
    submit = wtforms.SubmitField()

    def validate_value(self, value):
        if value.data < 0:
            raise wtfv.ValidationError("Значение должно быть положительным")

    def validate_ticker(self, ticker):
        stock = models.Stock.query.filter_by(ticker=ticker.data).first()
        if stock is None:
            raise wtfv.ValidationError("Акция не найдена")
