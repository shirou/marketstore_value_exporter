#!/usr/bin/env python3

import argparse
import datetime
import logging
import os
import signal
import sys
import time

import pandas as pd
import pymarketstore as pymkts
from prometheus_client import Gauge, start_http_server
import trading_calendars as tc

logging.basicConfig(
    level=logging.ERROR,
    format='{"level": "%(levelname)s", "time": "%(asctime)s", "msg": "%(message)s"}',
)
logger = logging.getLogger(__name__)


ERROR_VALUE_OF_LATENCY = 9999  # return this value if can not find in the lookback time


def is_symbol_does_not_exist_error(e: Exception) -> bool:
    msgs = [
        "Symbol not in catalog",
        "AttributeGroup not in catalog",
        "Timeframe not in catalog",
    ]
    return any([msg in str(e) for msg in msgs])


def get_value(client, query: str, column: str, start_dt: datetime, end_dt: datetime):
    symbol, timeframe, attribute = query.split("/")
    try:
        params = pymkts.Params(
            symbol, timeframe, attribute, limit=1, start=start_dt, end=end_dt
        )
        df = client.query(params).first().df()
        if df is None or df.empty:  # there are no result
            return (0, ERROR_VALUE_OF_LATENCY)
        value = df.tail(1).get(column)
        if value is None:
            logger.error("column %s does not exists", column)
            return (0, 0)
        latency = end_dt - df.index[-1]
        return (value, latency.total_seconds())
    except ConnectionError as e:
        logger.error("connection error")
    except Exception as e:
        if is_symbol_does_not_exist_error(e):
            logger.error("symbol does not exists: %s", query)
        else:
            logger.error(e)

    return (0, 0)


def run(args: argparse.Namespace):
    gauges_value = {}
    gauges_latency = {}
    gauge_avg = Gauge(f"{args.prefix}_avg_latency", "avg latency")
    for query in args.queries:
        # USDJPY/1Sec/TICK -> usdjpy_1sec_tick
        key = query.replace("/", "_").replace("-", "_").lower()
        gauges_value[query] = Gauge(
            f"{args.prefix}_{key}_value", "value of {}".format(query)
        )
        gauges_latency[query] = Gauge(
            f"{args.prefix}_{key}_latency", "latency of {}".format(query)
        )

    url = f"http://{args.marketstore_host}:{args.marketstore_port}/rpc"
    delta = datetime.timedelta(seconds=args.lookback)

    cal = None
    if args.market:
        cal = tc.get_calendar("XNYS")

    while True:
        client = pymkts.Client(url)

        end_dt = pd.Timestamp.utcnow()
        start_dt = end_dt - delta

        holiday = False
        if cal and cal.is_session(end_dt) is False:
            holiday = True

        total = 0
        for query in args.queries:
            if holiday:
                value, latency = (0, 0)
            else:
                (value, latency) = get_value(
                    client, query, args.column, start_dt, end_dt
                )
            gauges_value[query].set(value)
            gauges_latency[query].set(latency)
            total += latency

        gauge_avg.set(total / len(args.queries))
        time.sleep(args.interval)


def exit_handler(signum, frame) -> None:
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="marketstore_value_exporter")
    parser.add_argument(
        "--port", type=int, default=os.environ.get("PORT", 8000), help="prometheus port"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=os.environ.get("INTERVAL", 60),
        help="get value interval seconds",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=os.environ.get("LOOKBACK", 3600),
        help="lookback window size(seconds) to search result",
    )
    parser.add_argument(
        "--marketstore-host",
        type=str,
        default=os.environ.get("MARKETSTORE_HOST", "localhost"),
        help="marketstore host",
    )
    parser.add_argument(
        "--marketstore-port",
        type=int,
        default=os.environ.get("MARKETSTORE_PORT", 5993),
        help="marketstore port",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=os.environ.get("PREFIX", "marketstore"),
        help="prometheus key prefix",
    )
    parser.add_argument(
        "--column",
        type=str,
        default=os.environ.get("COLUMN", "price"),
        help="column name to get",
    )
    parser.add_argument(
        "--market",
        type=str,
        default=os.environ.get("MARKET", ""),
        help="market to set holidays",
    )

    parser.add_argument(
        "queries",
        metavar="USDJPY/1Sec/TICK",
        type=str,
        nargs="+",
        help="list of marketstore query",
    )

    args = parser.parse_args()
    signal.signal(signal.SIGTERM, exit_handler)

    start_http_server(8000)

    run(args)
