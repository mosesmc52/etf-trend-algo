import configparser
import os
from datetime import datetime, timedelta

import alpaca_trade_api as tradeapi
import pandas as pd
import sentry_sdk
import sqlalchemy
from dotenv import find_dotenv, load_dotenv
from fredapi import Fred
from helper import history, share_quantity, str2bool, yoy
from log import log
from SES import AmazonSES

sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))

load_dotenv(find_dotenv())


LIVE_TRADE = str2bool(os.getenv("LIVE_TRADE", False))

# retreive configuration parameters
config = configparser.ConfigParser()
config.read(f'{os.getenv("CONFIG_FILE_ABSOLUTE_PATH")}/settings.cfg')

fred = Fred(api_key=os.getenv("FRED_API_KEY"))

now = datetime.now()
extra_parameters = {
    "observation_start": (now - timedelta(days=600)).strftime("%Y-%m-%d"),
    "observation_end": now.strftime("%Y-%m-%d"),
}

MACRO = fred.get_series("RRSFS", **extra_parameters)
MACRO.name = "MACRO"

df = pd.concat([MACRO], axis=1)
full_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D")
df = df.reindex(full_range)
df.ffill(inplace=True)

# initialize Alpaca Trader
api = tradeapi.REST(
    os.getenv("ALPACA_KEY_ID"),
    os.getenv("ALPACA_SECRET_KEY"),
    base_url=os.getenv("ALPACA_BASE_URL"),
)  # or use ENV Vars shown below

account = api.get_account()
portfolio_value = round(float(account.equity), 3)


# open sqllite db
engine = sqlalchemy.create_engine("sqlite:///securities.db")
db_session = sqlalchemy.orm.Session(bind=engine)


market_history = history(
    db_session=db_session,
    tickers=[config["model"]["market"]],
    days=config["model"]["tailing_window"],
)


is_bull_market = (
    market_history["close"].tail(1).iloc[0] > market_history["close"].mean()
)


MACRO_YOY = yoy(
    df["MACRO"].tail(1).iloc[0],
    df.loc[df["MACRO"].tail(1).index - pd.DateOffset(years=1)]["MACRO"][0],
)

updated_positions = []

if MACRO_YOY > 0.0 or is_bull_market:

    qty = share_quantity(
        price=market_history["close"].tail(1).iloc[0],
        weight=1.0,
        portfolio_value=portfolio_value,
    )

    updated_positions.append(
        {
            "security": config["model"]["market"],
            "action": "buy",
            "qty": qty,
        }
    )

    if LIVE_TRADE:
        # remove all cash
        for position in api.list_positions():
            if position.symbol == config["model"]["cash"]:
                api.submit_order(
                    symbol=position.symbol,
                    time_in_force="day",
                    side="sell",
                    type="market",
                    qty=position.qty,
                )

                updated_positions.append(
                    {
                        "security": position.symbol,
                        "action": "sell",
                        "qty": position.qty,
                    }
                )

        api.submit_order(
            symbol=config["model"]["market"],
            time_in_force="day",
            side="buy",
            type="market",
            qty=qty,
        )

else:

    cash_history = history(
        db_session=db_session,
        tickers=[config["model"]["cash"]],
        days=config["model"]["tailing_window"],
    )

    qty = share_quantity(
        price=cash_history["close"].tail(1).iloc[0],
        weight=1.0,
        portfolio_value=portfolio_value,
    )

    updated_positions.append(
        {
            "security": config["model"]["cash"],
            "action": "buy",
            "qty": qty,
        }
    )

    if LIVE_TRADE:
        # remove all equity if exist
        for position in api.list_positions():
            if position.symbol == config["model"]["market"]:
                api.submit_order(
                    symbol=position.symbol,
                    time_in_force="day",
                    side="sell",
                    type="market",
                    qty=position.qty,
                )

                updated_positions.append(
                    {
                        "security": position.symbol,
                        "action": "sell",
                        "qty": position.qty,
                    }
                )

        api.submit_order(
            symbol=config["model"]["cash"],
            time_in_force="day",
            side="day",
            type="market",
            qty=qty,
        )


# Email Positions
EMAIL_POSITIONS = str2bool(os.getenv("EMAIL_POSITIONS", False))

message_body_html = f"Portfolio Value: {portfolio_value}<br>"
message_body_plain = f"Portfolio Value: {portfolio_value}\n"

# too lazy to write better
message_body_html += "Market Condition: {0}<br>".format(
    "Bull" if is_bull_market else "Bear"
)

message_body_plain += "Market Condition: {0}\n".format(
    "Bull" if is_bull_market else "Bear"
)

message_body_html += (
    f'{now.strftime("%B")} YoY Retail and Food Services Sales Change: {MACRO_YOY}<br>'
)
message_body_plain += (
    f'{now.strftime("%B")} YoY Retail and Food Services Sales Change: {MACRO_YOY}\n'
)

for position in updated_positions:
    message_body_html += f'<a clicktracking=off href="https://finviz.com/quote.ashx?t={position["security"]}">{position["security"]}</a>: {position["qty"]} ({position["action"]})<br>'
    message_body_plain += (
        f'{position["security"]}: {position["qty"]} ({position["action"]})\n'
    )

if EMAIL_POSITIONS:
    TO_ADDRESSES = os.getenv("TO_ADDRESSES", "").split(",")
    FROM_ADDRESS = os.getenv("FROM_ADDRESS", "")
    ses = AmazonSES(
        region=os.environ.get("AWS_SES_REGION_NAME"),
        access_key=os.environ.get("AWS_SES_ACCESS_KEY_ID"),
        secret_key=os.environ.get("AWS_SES_SECRET_ACCESS_KEY"),
        from_address=os.environ.get("FROM_ADDRESS"),
    )
    if LIVE_TRADE:
        status = "Live"
    else:
        status = "Test"

    subject = "Monthly Trend Algo Report - {}".format(status)

    for to_address in TO_ADDRESSES:
        ses.send_html_email(
            to_address=to_address, subject=subject, content=message_body_html
        )

print("---------------------------------------------------\n")
print(message_body_plain)
