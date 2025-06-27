import pandas as pd
from datetime import datetime
import logging
from pathlib import Path
from database import Database
import os
from dotenv import load_dotenv

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
    """最適化された積算温度計算"""
    db = Database()
    try:
        logging.info("積算温度計算を開始します")
        
        # 全温度データを一度に取得
        logging.info("温度データを取得中...")
        temp_data = db.get_temperature_data()
        
        if not temp_data:
            logging.warning("温度データが見つかりません")
            return
        
        # DataFrameに変換
        df = pd.DataFrame(temp_data)
        logging.info(f"取得した温度データ: {len(df)} レコード")
        
        # 日付でソート
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(['latitude', 'longitude', 'date'])
        
        # 積算温度の計算
        logging.info("積算温度を計算中...")
        df['accumulated_temp'] = df.groupby(['latitude', 'longitude'])['temperature'].cumsum()
        
        # 結果をデータベースに保存
        logging.info("積算温度をデータベースに保存中...")
        created_at = datetime.now()
        
        # バッチ処理で保存
        batch_size = 1000
        total_records = len(df)
        
        for i in range(0, total_records, batch_size):
            batch = df.iloc[i:i+batch_size]
            for _, row in batch.iterrows():
                try:
                    db.insert_accumulated_temperature(
                        row['date'], 
                        row['latitude'], 
                        row['longitude'], 
                        row['accumulated_temp'], 
                        created_at
                    )
                except Exception as e:
                    # 重複エラーは無視
                    if "duplicate key" not in str(e).lower():
                        logging.error(f"Error inserting accumulated temperature: {e}")
            
            logging.info(f"進捗: {min(i+batch_size, total_records)}/{total_records} レコード処理済み")
        
        logging.info("積算温度計算が完了しました")
        
    except Exception as e:
        logging.error(f"積算温度の計算中にエラーが発生しました: {str(e)}")
        raise

def main():
    """メイン処理"""
    logging.info("最適化された積算温度の計算を開始します")
    calculate_accumulated_temperature_optimized()
    logging.info("最適化された積算温度の計算が完了しました")

if __name__ == "__main__":
    main() 