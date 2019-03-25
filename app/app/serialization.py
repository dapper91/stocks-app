"""
Database model serialization schemas.
"""

import marshmallow as mm
import marshmallow_sqlalchemy as ms

from app import models


class StockApiSchema(ms.ModelSchema):
    """
    Stock model api serialization schema.
    """

    class Meta:
        model = models.Stock
        exclude = ('id',)


class QuoteApiSchema(ms.ModelSchema):
    """
    Quote model api serialization schema.
    """

    class Meta:
        model = models.Quote
        exclude = ('id', 'stock_id')


class InsiderApiSchema(ms.ModelSchema):
    """
    Insider model api serialization schema.
    """

    class Meta:
        model = models.Insider
        exclude = ('id', 'trades')


class TradeApiSchema(ms.ModelSchema):
    """
    Trade model api serialization schema.
    """

    class Meta:
        model = models.Trade

    insider = mm.fields.Nested(InsiderApiSchema)
