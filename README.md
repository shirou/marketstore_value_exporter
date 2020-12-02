# marketstor-value-exporter

`marketstor-value-exporter` is a [promehtheus](https://prometheus.io/) exporter for [marketstore](https://github.com/alpacahq/marketstore). This can fetch values from marketstore and export as prometheus exporter. This also collects latencies from current time and avarage latency time.

You can also configure this to send [DataDog](https://www.datadoghq.com/) from [Kurbernetes](https://kubernetes.io/) by using prometheus integration. And it can be useful for other SaaS.

## Manifest example

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: price-monitor
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
  selector:
    matchLabels:
      app: price-monitor
  template:
    metadata:
      labels:
        app: price-monitor
      annotations:
        ad.datadoghq.com/price-monitor.check_names: |
          ["openmetrics"]
        ad.datadoghq.com/price-monitor.init_configs: |
          [{}]
        ad.datadoghq.com/price-monitor.instances: |
          [
            {
              "prometheus_url": "http://%%host%%:%%port%%/",
              "namespace": "marketstore",
              "metrics": [
                {
                  "marketstore_avg_latency": "avg_latency",
                  "marketstore_usdjpy_1sec_tick_value": "USDJPY.price",
                  "marketstore_eurusd_1sec_tick_value": "EURUSD.price"
                }
              ]
            }
          ]
    spec:
      containers:
        - name: price-monitor
          image: shirou/marketstore_value_exporter:latest
          args: ["USDJPY/1Sec/TICK", "EURUSD/1Sec/TICK"]
          env:
            - name: MARKETSTORE_HOST
              value: marketstore
          ports:
            - name: container-port
              containerPort: 8000
          readinessProbe:
            httpGet:
              path: /
              port: container-port
            initialDelaySeconds: 3
            periodSeconds: 3
          resources:
            requests:
              cpu: 30m
              memory: 100Mi
            limits:
              cpu: 50m
              memory: 100Mi
```

## Metrics

- `<prefix>_<query>_value`: value of the query. if not exists, return 0
- `<prefix>_<query>_latency`: latency(seconds) between current time and last fetched time for the query
- `<prefix>_avg_latency`: average latency for all queries

### example

```
# HELP marketstore_avg_latency avg latency
# TYPE marketstore_avg_latency gauge
marketstore_avg_latency 2.61206
# HELP marketstore_usdjpy_1sec_tick_value value of USDJPY/1Sec/TICK
# TYPE marketstore_usdjpy_1sec_tick_value gauge
marketstore_usdjpy_1sec_tick_value 104.40699768066406
# HELP marketstore_usdjpy_1sec_tick_latency latency of USDJPY/1Sec/TICK
# TYPE marketstore_usdjpy_1sec_tick_latency gauge
marketstore_usdjpy_1sec_tick_latency 2.61206
# HELP marketstore_eurusd_1sec_tick_value value of EURUSD/1Sec/TICK
# TYPE marketstore_eurusd_1sec_tick_value gauge
marketstore_eurusd_1sec_tick_value 1.2075200080871582
# HELP marketstore_eurusd_1sec_tick_latency latency of EURUSD/1Sec/TICK
# TYPE marketstore_eurusd_1sec_tick_latency gauge
marketstore_eurusd_1sec_tick_latency 2.61206
```

# Options

```
usage: main.py [-h] [--port PORT] [--interval INTERVAL] [--lookback LOOKBACK] [--marketstore-host MARKETSTORE_HOST] [--marketstore-port MARKETSTORE_PORT] [--prefix PREFIX] [--column COLUMN] USDJPY/1Sec/TICK [USDJPY/1Sec/TICK ...]

marketstore_value_exporter

positional arguments:
  USDJPY/1Sec/TICK      list of marketstore query

optional arguments:
  -h, --help            show this help message and exit
  --port PORT           prometheus port (default=8000)
  --interval INTERVAL   get value interval seconds (default=60)
  --lookback LOOKBACK   lookback window size(seconds) to search result (default=3600)
  --marketstore-host MARKETSTORE_HOST (default=localhost)
                        marketstore host
  --marketstore-port MARKETSTORE_PORT (default=5993)
                        marketstore port
  --prefix PREFIX       prometheus key prefix (default=marketstore)
  --column COLUMN       column name to get (default=price)
  --market MARKET       market to set holidays (default="")
```

You can specify multiple queris.

`market` is an option to set holiday and opening time. You can specify [ISO-10383 market identifier code](https://www.iso20022.org/market-identifier-codes) like "XTKS" to check the market is open or closed. If market is closed, returns value and latency are both 0. If does not specify market, it means 24/365.

See [quantopian/trading_calendars](https://github.com/quantopian/trading_calendars) more detail.


## Note:

- `column` is used for all queries.
- `latency` is calcurated from `Epoch`.
- If there are no result in the `lookback`, returns value 0, latency 9999.

# License

Apache 2.0
