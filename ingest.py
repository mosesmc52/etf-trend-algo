import configparser
import os

import alpaca_trade_api as tradeapi
import sqlalchemy
from dotenv import find_dotenv, load_dotenv
from helper import ingest_security

load_dotenv(find_dotenv())


# retreive configuration parameters
config = configparser.ConfigParser()
config.read(f'{os.getenv("CONFIG_FILE_ABSOLUTE_PATH")}/settings.cfg')

alpaca_api = tradeapi.REST(
    os.getenv("ALPACA_KEY_ID"),
    os.getenv("ALPACA_SECRET_KEY"),
    base_url=os.getenv("ALPACA_BASE_URL"),
)

# open sqllite db
engine = sqlalchemy.create_engine("sqlite:///securities.db")
db_session = sqlalchemy.orm.Session(bind=engine)

# Ingest  ETF Data
for ETF in [config["model"]["market"], config["model"]["cash"]]:
    ingest_security(
        alpaca_api=alpaca_api, db_session=db_session, ticker=ETF, name=None, type="etf"
    )
