import math
from datetime import datetime, timedelta

import models
import pandas as pd
import sqlalchemy
from alpaca_trade_api.rest import TimeFrame
from dateutil import parser as time_parser
from log import log


def str2bool(value):
    valid = {
        "true": True,
        "t": True,
        "1": True,
        "on": True,
        "false": False,
        "f": False,
        "0": False,
    }

    if isinstance(value, bool):
        return value

    lower_value = value.lower()
    if lower_value in valid:
        return valid[lower_value]
    else:
        raise ValueError('invalid literal for boolean: "%s"' % value)


def yoy(current_yr, previous_yr):
    return current_yr - previous_yr


def price_history(api, ticker, start_date, end_date, print_test=False):
    try:
        return api.get_bars(
            ticker,
            TimeFrame.Day,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
        )
    except TypeError as te:
        log("{}\n".format(te), "error")

    return []


def ingest_security(alpaca_api, db_session, ticker, name="", type="stock", days=730):
    now = datetime.now()
    end_date = now - timedelta(hours=48)

    log("\n{0}".format(ticker), "success")
    # insert security in database if doesn't exist
    security = (
        db_session.query(models.Security)
        .filter(models.Security.ticker == ticker)
        .first()
    )
    if not security:
        security = models.Security(ticker=ticker, name=name, type=type)

        db_session.add(security)
        db_session.commit()
        start_date = now - timedelta(days=days)
    else:
        # retrieve latest price data from sql database
        last_price = (
            db_session.query(models.Price)
            .filter(models.Price.security_id == security.id)
            .order_by(sqlalchemy.desc("date"))
            .first()
        )
        if not last_price:
            start_date = now - timedelta(days=days)
        else:
            start_date = last_price.date + timedelta(days=1)
            if start_date > now:
                return True

    # retrieve price history since latest price
    if start_date > end_date:
        log("0 day prices inserted", "info")
        return True

    hist = price_history(alpaca_api, ticker, start_date, end_date)

    for price in hist:
        object = models.Price(
            close=price.c,  # retrieve close price
            date=time_parser.parse(str(price.t)),
            security_id=security.id,
        )
        db_session.add(object)
        db_session.commit()

    log("{0} day prices inserted".format(len(hist)))

    return True


def history(db_session, tickers, days):
    # build sqlite queries
    security_query = db_session.query(models.Security).filter(
        models.Security.ticker.in_(tuple(tickers))
    )

    security_ids = []
    for security in security_query.all():
        security_ids.append(security.id)

    past = datetime.now() - timedelta(days=int(days))
    price_query = db_session.query(models.Price).filter(
        models.Price.security_id.in_(tuple(security_ids)), models.Price.date >= past
    )

    # build pandas dataframe

    security_df = pd.read_sql(security_query.statement, db_session.bind)

    price_df = pd.read_sql(price_query.statement, db_session.bind)

    # merge both dataframes
    df = security_df.merge(price_df, left_on="id", right_on="security_id")

    # remove unnessary columns
    df = df.drop(["security_id", "id_x", "id_y"], axis=1)

    # convert date to datetime object
    df["date"] = pd.to_datetime(df["date"])

    # set date to index
    df = df.set_index(["date"])

    return df


def share_quantity(price, weight, portfolio_value):
    return math.floor((portfolio_value * weight) / price)
