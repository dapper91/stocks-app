"""
Flask application configurations. Contains Production and Development configurations.
"""

import os


def get_postgres_connection_string():
    """
    Builds postgres connection string using environment variables.

    :return: postgres connection string
    """

    driver = 'psycopg2'
    db_name = os.environ.get('DB_NAME', 'stocks')
    db_user = os.environ.get('DB_USER', 'root')
    db_pass = os.environ.get('DB_PASS', 'root')
    db_host = os.environ.get('DB_HOST', 'db')

    return f'postgresql+{driver}://{db_user}:{db_pass}@{db_host}/{db_name}'


class BaseConfig:
    """
    Base configuration. All application configurations should inherit it.
    """

    DEBUG = False
    TESTING = False
    JSON_AS_ASCII = False

    SQLALCHEMY_DATABASE_URI = get_postgres_connection_string()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


class ProdConfig(BaseConfig):
    """
    Production configuration.
    """


class DevConfig(BaseConfig):
    """
    Development configuration.
    """

    DEBUG = True
    SQLALCHEMY_ECHO = True
