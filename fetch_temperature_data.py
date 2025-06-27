import logging
import pandas as pd
from datetime import datetime, timedelta
from database import Database
from generate_cumtemp import fetch_nasa_temp_data
import time
import sqlite3
import argparse

# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_temperature_data(start_date_str=None, end_date_str=None):
    """NASA POWER APIから気温データを取得し、データベースに保存する"""
    print("fetch_temperature_data.py: スクリプト開始")
    try:
        db = Database()
        logging.info("Database connection established")

        # グリッドポイントの読み込み
        grid_df = pd.read_csv("data/grid_points.csv")
        grid_points = [(row["lat"], row["lon"]) for _, row in grid_df.iterrows()]
        logging.info(f"Loaded {len(grid_points)} grid points from CSV")
        print(f"Loaded {len(grid_points)} grid points from CSV")

        # グリッドポイントをデータベースに登録
        for lat, lon in grid_points:
            try:
                db.insert_grid_point(lat, lon)
                logging.debug(f"Registered grid point: {lat}, {lon}")
            except Exception as e:
                logging.error(f"Error registering grid point {lat}, {lon}: {str(e)}")

        # データ取得期間の設定
        if start_date_str is None or end_date_str is None:
            start_date = datetime(2023, 1, 1)  # 2023年1月1日から
            end_date = datetime.now() - timedelta(days=1)  # 昨日まで
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')
        logging.info(f"Fetching data from {start_date_str} to {end_date_str}")
        print(f"Fetching data from {start_date_str} to {end_date_str}")

        # 各グリッドポイントのデータを取得
        for i, (lat, lon) in enumerate(grid_points):
            logging.info(f"Fetching data for lat={lat}, lon={lon} ({i+1}/{len(grid_points)})")
            print(f"Fetching data for lat={lat}, lon={lon} ({i+1}/{len(grid_points)})")
            try:
                print(f"Calling fetch_nasa_temp_data for lat={lat}, lon={lon}")
                df = fetch_nasa_temp_data(lat, lon, start_date_str, end_date_str, timeout=15)
                print(f"fetch_nasa_temp_data returned for lat={lat}, lon={lon}")
            except Exception as e:
                logging.error(f"fetch_nasa_temp_data error for {lat}, {lon}: {str(e)}")
                print(f"fetch_nasa_temp_data error for {lat}, {lon}: {str(e)}")
                continue
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    try:
                        date = row['date']
                        temp = row['temp']
                        if temp != -999.0:
                            print(f"Saving data: {date}, {lat}, {lon}, {temp}")
                            db.insert_temperature_data(date, lat, lon, temp, 'nasa_power')
                            print(f"Saved data: {date}, {lat}, {lon}, {temp}")
                    except Exception as e:
                        logging.error(f"Error saving data for {lat}, {lon} on {row['date']}: {str(e)}")
                        print(f"Error saving data for {lat}, {lon} on {row['date']}: {str(e)}")
            else:
                logging.warning(f"No data for lat={lat}, lon={lon}")
                print(f"No data for lat={lat}, lon={lon}")
            time.sleep(1.2)  # API負荷対策

        logging.info("Temperature data fetch completed successfully")
        print("Temperature data fetch completed successfully")

    except Exception as e:
        logging.error(f"Error in fetch_temperature_data: {str(e)}")
        print(f"Error in fetch_temperature_data: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str, help='Start date in YYYYMMDD')
    parser.add_argument('--end', type=str, help='End date in YYYYMMDD')
    args = parser.parse_args()
    fetch_temperature_data(args.start, args.end)

conn = sqlite3.connect('temperature.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(temperature_data);")
columns = cur.fetchall()
for col in columns:
    print(col)
conn.close() 