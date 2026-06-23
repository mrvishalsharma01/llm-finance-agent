import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils import Agent

st.set_page_config(
    page_title="AI Financial Forecasting Agent",
    page_icon="📈",
    layout="wide"
)

st.title("🤖 AI Financial Forecasting Agent & Backtesting Dashboard")
st.markdown("This interactive application fetches historical stock data and recent news headlines, utilizing Large Language Models to forecast future prices.")

# Sidebar for Configuration
st.sidebar.header("⚙️ Configuration")
news_api_key = st.sidebar.text_input("NewsAPI Key", type="password", help="Get a key from newsapi.org")
genai_api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Get a key from Google AI Studio")
model_name = st.sidebar.selectbox("Model Name", ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.5-pro"])
stock_symbol = st.sidebar.text_input("Stock Symbol", value="RELIANCE.NS")
days = st.sidebar.slider("Historical Days for Context", min_value=5, max_value=60, value=30)

# Date inputs for backtesting (limited to 30 days due to NewsAPI free tier)
st.sidebar.subheader("📅 Backtesting Range")
default_end = datetime.now() - timedelta(days=5)
default_start = default_end - timedelta(days=5)
start_date = st.sidebar.date_input("Start Date", value=default_start)
end_date = st.sidebar.date_input("End Date", value=default_end)

if st.sidebar.button("Run Backtesting", type="primary"):
    if not news_api_key or not genai_api_key:
        st.error("Please enter both NewsAPI and Gemini API keys in the sidebar.")
    elif start_date > end_date:
        st.error("Start Date must be before or equal to End Date.")
    elif (datetime.now().date() - start_date).days > 30:
        st.warning("NewsAPI free tier only supports news from the last 30 days. Predictions for older dates may fail or lack news data.")
    
    # Run the backtest
    config = {
        "news_api_key": news_api_key,
        "genai_api_key": genai_api_key,
        "model_name": model_name,
        "stock_symbol": stock_symbol,
        "days": days
    }
    
    with st.spinner("Initializing agent and fetching metadata..."):
        try:
            agent = Agent(config)
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            st.stop()

    st.info(f"Resolved stock target name: **{agent.stock_name}**")
    
    # Run backtest
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        import yfinance as yf
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        import numpy as np
        import plotly.graph_objects as go
        
        # Download data
        df_start = datetime.combine(start_date, datetime.min.time())
        df_end = datetime.combine(end_date, datetime.min.time())
        
        stock_history_data = yf.download(config['stock_symbol'], start=df_start, end=df_end + timedelta(days=1))
        if stock_history_data.empty:
            st.error("No stock price data found for the selected range.")
            st.stop()
            
        if isinstance(stock_history_data.columns, pd.MultiIndex):
            stock_history_data.columns = stock_history_data.columns.droplevel('Ticker')
            
        stock_history_data.reset_index(inplace=True)
        
        results = []
        total_days = len(stock_history_data)
        
        for i, row in stock_history_data.iterrows():
            date = row['Date']
            actual_price = row['Close']
            
            status_text.text(f"Predicting for {date.strftime('%Y-%m-%d')} ({i+1}/{total_days})...")
            progress_bar.progress((i + 1) / total_days)
            
            predicted_price = agent.predict(date, verbose=False)
            
            results.append({
                'Date': date.strftime("%Y-%m-%d"),
                'Predicted Price': predicted_price,
                'Actual Price': actual_price
            })
            
        results_df = pd.DataFrame(results)
        
        # Calculate metrics
        actual_prices = results_df['Actual Price'].dropna().values
        predicted_prices = results_df['Predicted Price'].dropna().values
        
        mse = mean_squared_error(actual_prices, predicted_prices)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(actual_prices, predicted_prices)
        r2 = r2_score(actual_prices, predicted_prices)
        ndei = rmse / np.std(actual_prices)
        
        status_text.success("Backtesting Complete!")
        
        # Display Metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("MSE", f"{mse:.2f}")
        col2.metric("RMSE", f"{rmse:.2f}")
        col3.metric("MAE", f"{mae:.2f}")
        col4.metric("R² Score", f"{r2:.4f}")
        col5.metric("NDEI", f"{ndei:.4f}")
        
        # Interactive Plotly Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=results_df['Date'], y=results_df['Actual Price'], name='Actual Price', mode='lines+markers', line=dict(color='#ff7f0e')))
        fig.add_trace(go.Scatter(x=results_df['Date'], y=results_df['Predicted Price'], name='Predicted Price', mode='lines+markers', line=dict(color='#1f77b4')))
        
        fig.update_layout(
            title=f"Predicted vs Actual Stock Prices for {stock_symbol}",
            xaxis_title="Date",
            yaxis_title="Price (INR)",
            hovermode="x unified",
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Show Detailed Data Frame
        st.subheader("📋 Prediction Logs")
        st.dataframe(results_df, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error during backtesting: {e}")
