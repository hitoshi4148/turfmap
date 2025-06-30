#!/usr/bin/env python3
"""
cron用スクリプト: 最新日付の翌日の気温データを取得し、積算温度計算と害虫マップ生成を自動実行
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from database import Database
import subprocess
import time

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cron_fetch_update.log'),
        logging.StreamHandler()
    ]
)

def main():
    """メイン処理"""
    try:
        logging.info("=== cron fetch_and_update 開始 ===")
        
        # データベース接続
        db = Database()
        logging.info("データベース接続完了")
        
        # 最新の気温データ日付を取得
        latest_date = db.get_latest_temperature_date()
        logging.info(f"最新の気温データ日付: {latest_date}")
        
        if latest_date:
            # latest_dateがstr型ならdatetime型に変換
            if isinstance(latest_date, str):
                latest_date = datetime.strptime(latest_date[:10], '%Y-%m-%d')
            next_date = latest_date + timedelta(days=1)
            next_date_str = next_date.strftime('%Y%m%d')
            logging.info(f"取得対象日: {next_date_str}")
        else:
            # データがなければ2025-01-01から
            next_date_str = '20250101'
            logging.info(f"初回実行: {next_date_str}から開始")
        
        # 今日の日付を取得
        today = datetime.now().date()
        next_date_obj = datetime.strptime(next_date_str, '%Y%m%d').date()
        
        # 今日より未来の日付は取得できない
        if next_date_obj > today:
            logging.info(f"本日({today})分のデータはまだ取得できません。次回実行を待ちます。")
            return
        
        # 1. 気温データ取得
        logging.info("=== 気温データ取得開始 ===")
        try:
            logging.info("fetch_temperature_data.py 実行直前")
            result = subprocess.run([
                'python', 'fetch_temperature_data.py', 
                '--start', next_date_str, 
                '--end', next_date_str
            ], 
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            check=True,
            timeout=18000  # 5時間でタイムアウト（GitHub Actionsの制限を考慮）
            )
            logging.info("気温データ取得完了")
            logging.info(f"気温データ取得 標準出力: {result.stdout}")
            if result.stderr:
                logging.warning(f"気温データ取得 標準エラー: {result.stderr}")
        except subprocess.TimeoutExpired as e:
            logging.error(f"気温データ取得タイムアウト: {e}")
            logging.error("プロセスを強制終了します")
            if e.stdout:
                logging.info(f"タイムアウト時の標準出力: {e.stdout}")
            if e.stderr:
                logging.error(f"タイムアウト時の標準エラー: {e.stderr}")
            raise
        except subprocess.CalledProcessError as e:
            logging.error(f"気温データ取得エラー: {e}")
            logging.error(f"エラー出力: {e.stderr}")
            if e.stdout:
                logging.info(f"エラー時の標準出力: {e.stdout}")
            raise
        
        # 2. 積算温度計算
        try:
            logging.info("calculate_accumulated_temperature_optimized.py 実行直前")
            result = subprocess.run([
                'python', 'calculate_accumulated_temperature_optimized.py'
            ], 
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            check=True,
            timeout=1800  # 30分でタイムアウト（データベース内計算により高速化）
            )
            logging.info("積算温度計算完了")
            logging.info(f"積算温度計算 標準出力: {result.stdout}")
            if result.stderr:
                logging.warning(f"積算温度計算 標準エラー: {result.stderr}")
        except subprocess.TimeoutExpired as e:
            logging.error(f"積算温度計算タイムアウト: {e}")
            if e.stdout:
                logging.info(f"タイムアウト時の標準出力: {e.stdout}")
            if e.stderr:
                logging.error(f"タイムアウト時の標準エラー: {e.stderr}")
            raise
        except subprocess.CalledProcessError as e:
            logging.error(f"積算温度計算エラー: {e}")
            logging.error(f"エラー出力: {e.stderr}")
            if e.stdout:
                logging.info(f"エラー時の標準出力: {e.stdout}")
            raise

        # 3. 害虫マップ生成
        try:
            logging.info("map_pest_risk_updated.py 実行直前")
            result = subprocess.run([
                'python', 'map_pest_risk_updated.py'
            ], 
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            check=True,
            timeout=3600  # 1時間でタイムアウト
            )
            logging.info("害虫マップ生成完了")
            logging.info(f"害虫マップ生成 標準出力: {result.stdout}")
            if result.stderr:
                logging.warning(f"害虫マップ生成 標準エラー: {result.stderr}")
        except subprocess.TimeoutExpired as e:
            logging.error(f"害虫マップ生成タイムアウト: {e}")
            if e.stdout:
                logging.info(f"タイムアウト時の標準出力: {e.stdout}")
            if e.stderr:
                logging.error(f"タイムアウト時の標準エラー: {e.stderr}")
            raise
        except subprocess.CalledProcessError as e:
            logging.error(f"害虫マップ生成エラー: {e}")
            logging.error(f"エラー出力: {e.stderr}")
            if e.stdout:
                logging.info(f"エラー時の標準出力: {e.stdout}")
            raise
        
        logging.info("=== cron fetch_and_update 正常完了 ===")
        
    except Exception as e:
        logging.error(f"=== cron fetch_and_update エラー ===")
        logging.error(f"エラー内容: {str(e)}")
        import traceback
        logging.error(f"トレースバック: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main() 
