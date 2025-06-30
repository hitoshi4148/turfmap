import sqlite3
import pandas as pd
from datetime import datetime
import logging
from pathlib import Path

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('temperature_calculation.log'),
        logging.StreamHandler()
    ]
)

def create_accumulated_table():
    """積算温度テーブルを作成"""
    conn = sqlite3.connect('data/temperature.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accumulated_temperature (
        date TEXT,
        latitude REAL,
        longitude REAL,
        accumulated_temp REAL,
        created_at TEXT,
        PRIMARY KEY (date, latitude, longitude)
    )
    ''')
    
    conn.commit()
    conn.close()
    logging.info("積算温度テーブルを作成しました")

def calculate_accumulated_temperature():
    """積算温度を計算して保存"""
    try:
        conn = sqlite3.connect('data/temperature.db')
        
        # グリッドポイントの取得
        grid_points = pd.read_sql_query(
            "SELECT DISTINCT latitude, longitude FROM temperature_data",
            conn
        )
        
        # 各グリッドポイントについて積算温度を計算
        for _, point in grid_points.iterrows():
            lat, lon = point['latitude'], point['longitude']
            
            # 温度データの取得（日付順）
            query = """
            SELECT date, temperature
            FROM temperature_data
            WHERE latitude = ? AND longitude = ?
            AND date >= '20240101'
            ORDER BY date
            """
            
            df = pd.read_sql_query(query, conn, params=(lat, lon))
            
            if not df.empty:
                # 積算温度の計算
                df['accumulated_temp'] = df['temperature'].cumsum()
                
                # 結果の保存
                created_at = datetime.now().isoformat()
                for _, row in df.iterrows():
                    cursor = conn.cursor()
                    cursor.execute('''
                    INSERT OR REPLACE INTO accumulated_temperature
                    (date, latitude, longitude, accumulated_temp, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (row['date'], lat, lon, row['accumulated_temp'], created_at))
                
                conn.commit()
                logging.info(f"緯度{lat}、経度{lon}の積算温度を計算・保存しました")
        
        logging.info("全てのグリッドポイントの積算温度計算が完了しました")
        
    except Exception as e:
        logging.error(f"積算温度の計算中にエラーが発生しました: {str(e)}")
    finally:
        conn.close()

def main():
    """メイン処理"""
    logging.info("積算温度の計算を開始します")
    
    # テーブルの作成
    create_accumulated_table()
    
    # 積算温度の計算と保存
    calculate_accumulated_temperature()
    
    logging.info("積算温度の計算が完了しました")

if __name__ == "__main__":
    main() 