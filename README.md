# etf-trend-algo Summary
This algorithm leverages the trend of the S&P 500 with two stop conditions and updates on a monthly frequency. The first condition triggers when the price falls below the 200-day moving average, signaling a potential long-term trend reversal. The second condition monitors consumer demand (RRSFS), comparing the current year’s demand to the previous year’s. If the current demand is lower, this condition prevents frequent stop-and-start signals, or "whipsaws," where the stop and continuation conditions are triggered in quick succession. The 200-day moving average captures long-term trends, while consumer demand data refines short-term decision-making and reduces noise in the algorithm’s signals.

The algorithm was backtested using the Quantopian Zipline backtester, covering the period from January 1, 2007, to December 31, 2018. Over this time, the algorithm achieved a return of 11.3%, with a maximum drawdown of 19.3%. Detailed results can be viewed [here](https://github.com/mosesmc52/etf-trend-algo/blob/main/download.png).

### System dependencies
 * Install docker
 * Install docker-compose

### App dependencies
 * [Alpaca](https://app.alpaca.markets/paper/dashboard/overview)
 * [AWS SES](https://aws.amazon.com/ses/)
 * [FRED](https://fred.stlouisfed.org/)

### Setup using docker-compose
__**Step 1: Copy the env file from the backend folder**__
```
    cd backend
    cp .env.docker.example .env
```

__**Step 2: Insert environmental variable data**__

__**Step 3:  To build the application type the command in the console**__
```
docker-compose -f docker-compose.yml build
```

__**Step 4: To launch the application type the command in the console**__
```
docker-compose -f docker-compose.yml up
```

...or launch as a daemon:
```
docker-compose -f docker-compose.yml up -d
```
