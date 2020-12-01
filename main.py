#!/usr/bin/env python3

import argparse
import os
import time
import logging
import pandas as pd
import datetime


from prometheus_client import start_http_server, Gauge
import pymarketstore as pymkts

logger = logging.getLogger(__name__)


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
        params = pymkts.Params(symbol, timeframe, attribute, start=start_dt, end=end_dt)
        df = client.query(params).first().df()
        if df.empty:
            return 0
        return df.iloc[-1].get(column, 0)
    except ConnectionError as e:
        logger.error("connection error")
    except Exception as e:
        if is_symbol_does_not_exist_error(e):
            logger.error("symbol does not exists: {}".format(query))
        # ignore other errors

    return 0


def run(args: argparse.Namespace):
    gauges = {}
    for query in args.queries:
        # USDJPY/1S/TICK -> USDJPY_1S_TICK
        key = query.replace("/", "_").replace("-", "_").lower()
        gauges[query] = Gauge(args.prefix + "_" + key, "value of {}".format(query))

    url = f"http://{args.marketstore_host}:{args.marketstore_port}/rpc"
    delta = datetime.timedelta(seconds=args.interval)

    while True:
        client = pymkts.Client(url)

        end_dt = datetime.datetime.utcnow()
        start_dt = end_dt - delta

        for key, g in gauges.items():
            g.set(get_value(client, query, args.column, start_dt, end_dt))
        time.sleep(args.interval)


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
        "--prefix",
        type=str,
        default=os.environ.get("PREFIX", "marketstore"),
        help="prometheus key prefix",
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
        "--column",
        type=str,
        default=os.environ.get("CLOUMN", "price"),
        help="column name to get",
    )

    parser.add_argument(
        "queries",
        metavar="USDJPY/1Sec/TICK",
        type=str,
        nargs="+",
        help="list of marketstore query",
    )

    args = parser.parse_args()
    start_http_server(8000)

    run(args)
