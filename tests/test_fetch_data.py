import logging
from fetch_temperature_data import fetch_nasa_temp_data, process_and_save_data
from database import Database
import pandas as pd
from datetime import datetime, timedelta
import json

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_fetch.log'),
        logging.StreamHandler()
    ]
)

def test_single_point():
    """単一地点でのデータ取得テスト"""
    logging.info("単一地点でのデータ取得テストを開始します")
    
    # テスト用のデータベース初期化
    db = Database('test_temperature_data.db')
    
    # テスト用の座標（東京）
    lat, lon = 35.6812, 139.7671
    
    # 日付の設定（昨日までのデータを取得）
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=1)
    
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    logging.info(f"テストデータ取得: 緯度{lat}、経度{lon}")
    logging.info(f"期間: {start_date_str}から{end_date_str}")
    
    # APIのURLを構築して表示
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M"
        f"&start={start_date_str}"
        f"&end={end_date_str}"
        f"&latitude={lat}"
        f"&longitude={lon}"
        f"&format=JSON"
        f"&community=AG"
    )
    logging.info(f"API URL: {url}")
    
    # データ取得
    df = fetch_nasa_temp_data(lat, lon, start_date_str, end_date_str)
    
    if df is not None:
        logging.info("データ取得成功")
        logging.info(f"取得したデータ:\n{df}")
        
        # データベースへの保存
        process_and_save_data(df, lat, lon, db)
        
        # 保存したデータの確認
        saved_data = db.get_temperature_data()
        logging.info(f"保存されたデータ数: {len(saved_data)}")
        if saved_data:
            logging.info(f"最初のレコード: {saved_data[0]}")
    else:
        logging.error("データ取得に失敗しました")

def test_multiple_dates():
    """複数日付でのデータ取得テスト"""
    logging.info("複数日付でのデータ取得テストを開始します")
    
    # テスト用の座標（東京）
    lat, lon = 35.6812, 139.7671
    
    # 過去の日付でテスト
    end_date = datetime(2024, 1, 1)  # 2024年1月1日
    start_date = end_date - timedelta(days=2)  # 2日前
    
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    logging.info(f"過去データのテスト: 緯度{lat}、経度{lon}")
    logging.info(f"期間: {start_date_str}から{end_date_str}")
    
    # APIのURLを構築して表示
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M"
        f"&start={start_date_str}"
        f"&end={end_date_str}"
        f"&latitude={lat}"
        f"&longitude={lon}"
        f"&format=JSON"
        f"&community=AG"
    )
    logging.info(f"API URL: {url}")
    
    # データ取得
    df = fetch_nasa_temp_data(lat, lon, start_date_str, end_date_str)
    
    if df is not None:
        logging.info("過去データの取得に成功")
        logging.info(f"取得したデータ:\n{df}")
    else:
        logging.error("過去データの取得に失敗しました")

if __name__ == "__main__":
    test_single_point()
    test_multiple_dates() 