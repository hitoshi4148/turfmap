import pandas as pd
from datetime import datetime
import logging
from pathlib import Path
from database import Database, get_connection
import os
from dotenv import load_dotenv
import psycopg2.extras

# 環境変数の読み込み
load_dotenv()

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('temperature_calculation.log'),
        logging.StreamHandler()
    ]
)

def calculate_accumulated_temperature_optimized():
    """最適化された積算温度計算（データベース内で直接計算）"""
    db = Database()
    try:
        logging.info("積算温度計算を開始します")
        
        # 最新の積算温度データの日付を取得
        latest_accumulated_date = db.get_latest_accumulated_temperature_date()
        logging.info(f"最新の積算温度データ日付: {latest_accumulated_date}")
        
        # 最新の気温データの日付を取得
        latest_temp_date = db.get_latest_temperature_date()
        logging.info(f"最新の気温データ日付: {latest_temp_date}")
        
        if not latest_temp_date:
            logging.warning("気温データが見つかりません")
            return
        
        # データベース内で直接積算温度を計算
        logging.info("データベース内で積算温度を計算中...")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 既存の積算温度データをクリア（最新日付以降）
                if latest_accumulated_date:
                    cur.execute('''
                        DELETE FROM accumulated_temperature 
                        WHERE date > %s::date
                    ''', (latest_accumulated_date,))
                    logging.info(f"最新の積算温度データ以降（{latest_accumulated_date}）のデータをクリアしました")
                
                # データベース内で積算温度を計算して挿入
                # 開始日付を設定（最新の積算温度データ日付またはデフォルト日付）
                start_date = latest_accumulated_date if latest_accumulated_date else '2025-01-01'
                
                cur.execute('''
                    INSERT INTO accumulated_temperature (date, latitude, longitude, accumulated_temp, created_at)
                    WITH temp_ordered AS (
                        SELECT 
                            date::date,
                            latitude::numeric,
                            longitude::numeric,
                            temperature::numeric,
                            ROW_NUMBER() OVER (
                                PARTITION BY latitude, longitude 
                                ORDER BY date
                            ) as rn
                        FROM temperature_data
                        WHERE date >= %s::date
                        ORDER BY latitude, longitude, date
                    ),
                    temp_cumsum AS (
                        SELECT 
                            date,
                            latitude,
                            longitude,
                            temperature,
                            SUM(temperature) OVER (
                                PARTITION BY latitude, longitude 
                                ORDER BY date 
                                ROWS UNBOUNDED PRECEDING
                            ) as accumulated_temp
                        FROM temp_ordered
                    )
                    SELECT 
                        date,
                        latitude,
                        longitude,
                        accumulated_temp::numeric,
                        NOW() as created_at
                    FROM temp_cumsum
                    ON CONFLICT (date, latitude, longitude) DO UPDATE SET
                        accumulated_temp = EXCLUDED.accumulated_temp,
                        created_at = EXCLUDED.created_at
                ''', (start_date,))
                
                # 挿入されたレコード数を取得
                inserted_count = cur.rowcount
                conn.commit()
                
                logging.info(f"積算温度計算完了: {inserted_count} レコードを処理しました")
        
        logging.info("積算温度計算が完了しました")
        
    except Exception as e:
        logging.error(f"積算温度の計算中にエラーが発生しました: {str(e)}")
        import traceback
        logging.error(f"トレースバック: {traceback.format_exc()}")
        raise

def main():
    """メイン処理"""
    logging.info("最適化された積算温度の計算を開始します")
    calculate_accumulated_temperature_optimized()
    logging.info("最適化された積算温度の計算が完了しました")

if __name__ == "__main__":
    main() 