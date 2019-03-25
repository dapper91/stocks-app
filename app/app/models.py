"""
Database models.
"""

import enum
from sqlalchemy import orm

from app import db


class OwnerType(enum.Enum):
    """
    Owner type enumeration.
    """

    direct = 1
    indirect = 2

    def __str__(self):
        return self.name


class PriceType(enum.Enum):
    """
    Price type enumeration.
    """

    open = 1
    close = 2
    low = 3
    high = 4

    def __str__(self):
        return self.name


class Stock(db.Model):
    """
    Stock database model.
    """

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(5), unique=True, nullable=False)


class Quote(db.Model):
    """
    Quote database model.
    """

    __table_args__ = (
        db.UniqueConstraint('stock_id', 'date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey(Stock.id, onupdate='cascade'), nullable=False)
    date = db.Column(db.Date, nullable=False)

    open_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)

    volume = db.Column(db.Float, nullable=False)


class Insider(db.Model):
    """
    Insider database model.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    relation = db.Column(db.String(50), nullable=False)

    trades = orm.relationship('Trade', backref='insider')


class Trade(db.Model):
    """
    Trade database model.
    """

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey(Stock.id, onupdate='cascade'), nullable=False)
    insider_id = db.Column(db.Integer, db.ForeignKey(Insider.id, onupdate='cascade'), nullable=False)

    transaction_type = db.Column(db.String(100), nullable=False)
    owner_type = db.Column(db.Enum(OwnerType), nullable=False)

    last_date = db.Column(db.Date, nullable=False)
    shares_traded = db.Column(db.Integer, nullable=False)
    last_price = db.Column(db.Float, nullable=True)
    shares_hold = db.Column(db.Integer, nullable=False)
