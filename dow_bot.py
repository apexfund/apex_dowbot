# -*- coding: utf-8 -*-

import requests
import slack
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from IPython.core.pylabtools import figsize
from datetime import datetime
import base64

# Theese variables help us connect this Python file to the Slack workspace.
SLACK_TOKEN = "SLACK_TOKEN"
SLACK_WEBHOOK_URL = 'SLACK_WEBHOOK_URL'
client = slack.WebClient(token=SLACK_TOKEN)

'''
Written by Siddharth Cherukupalli
'''

# This function creates the graphs for the input ticker.

def plotStockPriceGraph(ticker, shortMA, mediumMA, longMA):
  stock = yf.Ticker(ticker)
  df = stock.history(period="1y")

  # Substring to index 10 is required because otherwise the df includes the timestamp as well, but we only want the date.
  firstDate = str(df.index[0])[:10]
  lastDate = str(df.index[-1])[:10]

  # Establishes a size for the graph, because otherwise the size was too small in Slack.
  plt.figure(figsize=(12, 8))
  plt.grid(True)

  # Graphs the different lines. Current price, and the three moving average lines.
  plt.plot(df.index, df['Close'], label=ticker + ' Current Price', color='teal')
  plt.plot(df.index, df['Close'].loc[firstDate : lastDate].rolling(window=shortMA).mean(), label=str(shortMA) + ' Day Mov Avg.', color='red')
  plt.plot(df.index, df['Close'].loc[firstDate : lastDate].rolling(window=mediumMA).mean(), label=str(mediumMA) + ' Day Mov Avg.', color='orange')
  plt.plot(df.index, df['Close'].loc[firstDate : lastDate].rolling(window=longMA).mean(), label=str(longMA) + ' Day Mov Avg.', color='green')

  plt.xlabel("Date")
  plt.ylabel("Price ($)")
  plt.title(ticker + " Stock Price")
  plt.plot()
  plt.legend()

  # This is needed so that it saves the matplotlib as a .jpg. This is needed because Slack's API needs a .jpg file format to send the graph.
  FILE_NAME = ticker + "_Graph.jpg"
  plt.savefig('/tmp/' + FILE_NAME)

  return FILE_NAME

# This function is for returning the moving average over the last x number of days deciding on user input.

def findMovingAverage(ticker, amountOfDays):
  df = yf.Ticker(ticker).history(period="1y")

  # Reverses the data frame.
  df.iloc[::-1]

  firstDay = str(df.index[0])[:10]
  finalDay = str(df.index[amountOfDays -1])[:10]

  movingAverage = df['Close'].loc[firstDay : finalDay].mean()
  return movingAverage

# This function is for identifying how the average lines are doing currently compared to the current price.
def findTrends(ticker, amountOfDays):
  # Retrieve the current price of the equity of interest.
  price = yf.Ticker(ticker).info['regularMarketPrice']

  movingAverage = findMovingAverage(ticker, amountOfDays)

  if (price > movingAverage):
    trend = "UPTREND"
  elif (price < movingAverage):
    trend = "DOWNTREND"
  elif (price == movingAverage):
    trend = "EQUAL"

  trendsString = str(ticker) + " is on a " + str(trend) + " relative to the " + str(amountOfDays) + " day moving average."
  return trendsString

# This function is for looking at how moving averages are doing relative to the other moving averages.
# If the short-term moving average is above the medium-term moving average, we return that it is a bullish sign. Inversely, it is bearish.

def findMACrossoverTrends(ticker, shortTermMA, longTermMA):
  shortMA = findMovingAverage(ticker, shortTermMA)
  longMA = findMovingAverage(ticker, longTermMA)

  if (shortMA < longMA):
    trend = "BEARISH"
    identifier = "LOWER"
  elif (longMA < shortMA):
    trend = "BULLISH"
    identifier = "HIGHER"

  movingAvgTrendsString = str(ticker) + " is " + str(trend) + " because the " + str(shortTermMA) + " day moving average is " 
  movingAvgTrendsString += str(identifier) + " than the " + str(longTermMA) + " day moving average."
  return movingAvgTrendsString

# This sends the message about the trends using the Webhook
def run_lambda(event, context):

  # THESE LINES ARE COMMENTED OUT BECAUSE THEY RELY ON THE INPUT FROM THE AWS LAMBDA CALL. THESE LINES ARE UNCOMMENTED WHEN THIS CODE IS PUT
  # INTO AWS LAMBDA.

  # # This is what is necessary to decode AWS Lambda's event parameter.
  body = event['body'].encode('ascii')
  body_decode = base64.b64decode(body)
  origInput = body_decode.decode('ascii')

  # # This substrings and gets the ticker and that passes that ticker into the function.
  searchStr = "text="
  index = origInput.index(searchStr)
  input = origInput[index:]
  endingIndex = input.index("&")
  ticker = input[len(searchStr): endingIndex]

  # For parsing the username.
  userStr = "user_name="
  usernameIndex = origInput.index(userStr)
  usernameInput = origInput[usernameIndex:]
  userEndingIndex = usernameInput.index("&")
  username = usernameInput[len(userStr) : userEndingIndex]

  # For parsing the channel
  channelStr = "channel_id="
  channelIndex = origInput.index(channelStr)
  channelInput = origInput[channelIndex:]
  channelEndingIndex = channelInput.index("&")
  channel = channelInput[len(channelStr) : channelEndingIndex]

  shortTimeframe = 12
  mediumTimeframe = 30
  longTimeframe = 60

  message = "<@" + username + ">"
  message += "\n" + findTrends(ticker, shortTimeframe)
  message += "\n" + findTrends(ticker, mediumTimeframe)
  message += "\n" + findTrends(ticker, longTimeframe)
  message += "\n" + findMACrossoverTrends(ticker, shortTimeframe, mediumTimeframe)

  message += "\n These are the graphs for %s over the last year." % (ticker)

  slack_parameter = '{"text": "%s"}' % (message)
  requests.post(SLACK_WEBHOOK_URL, data = slack_parameter)

  # This uploads the graphs to the Slack channel
  FILE_TITLE = ticker + " Graphs"
  FILE_PATH = '/tmp/' + plotStockPriceGraph(ticker, shortTimeframe, mediumTimeframe, longTimeframe)
  client.files_upload(file=FILE_PATH, channels=[channel], title=FILE_TITLE)

  return {}

