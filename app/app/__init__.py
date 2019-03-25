"""
Stocks application package. Performs initial application configuration and initialization.
"""

import flask
import flask_sqlalchemy as fs

from app import config
from app import encoder


app = flask.Flask(__name__)
app.config.from_object(config.ProdConfig)
app.json_encoder = encoder.CustomJSONEncoder

blueprint = flask.Blueprint('common', __name__)
db = fs.SQLAlchemy(app)

from app import handlers

app.register_blueprint(blueprint)
app.register_blueprint(blueprint, url_prefix='/api')
