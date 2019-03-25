"""
Stocks web application.
"""

import os
from app import app


if __name__ == "__main__":
    # ==================================#
    #        DEVELOPER MODE ONLY        #
    #      DON'T USE IN PRODUCTION      #
    # ==================================#
    app.run(port=os.getenv('PORT', 8080))
