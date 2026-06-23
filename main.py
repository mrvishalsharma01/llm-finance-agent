import json
from datetime import datetime, timedelta
from utils import Agent

def main():
    with open('config.json', 'r', encoding="utf-8") as file:
        config = json.load(file)
    agent = Agent(config)
    
    # NewsAPI free tier only allows articles from the last 30 days.
    # We choose a recent range (e.g., from 10 days ago to 5 days ago) to stay within limits.
    end_date = datetime.now() - timedelta(days=5)
    start_date = end_date - timedelta(days=5)
    
    agent.backtesting(start_date, end_date, verbose=True)

if __name__ == '__main__':
    main()
