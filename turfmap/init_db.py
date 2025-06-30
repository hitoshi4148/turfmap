import sqlite3
import os
import json
import logging

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def init_db():
    # データベースファイルが存在する場合は削除
    if os.path.exists('temperature.db'):
        os.remove('temperature.db')
    
    # データベース接続
    conn = sqlite3.connect('temperature.db')
    cursor = conn.cursor()
    
    # 害虫データテーブルの作成（新しいスキーマ）
    cursor.execute('''
    CREATE TABLE pests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        threshold_temp REAL NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 温度データテーブルの作成
    cursor.execute('''
    CREATE TABLE temperature_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        temperature REAL NOT NULL,
        date TEXT NOT NULL
    )
    ''')
    
    # インデックスの作成
    cursor.execute('CREATE INDEX idx_lat_lon ON temperature_data (latitude, longitude)')
    
    # pests.jsonから害虫データを読み込み
    try:
        with open('data/pests.json', 'r', encoding='utf-8') as f:
            pests_data = json.load(f)
        
        pests_list = pests_data["pests"]
        logger.info(f"pests.jsonから{len(pests_list)}件の害虫データを読み込みました。")
        
        for pest in pests_list:
            cursor.execute('''
            INSERT INTO pests (name, threshold_temp, description)
            VALUES (?, ?, ?)
            ''', (pest['name'], pest['base_temp'], pest['description']))
            
    except FileNotFoundError:
        logger.error("data/pests.jsonファイルが見つかりません。")
        return
    except json.JSONDecodeError as e:
        logger.error(f"data/pests.jsonのJSON形式が正しくありません: {e}")
        return
    except KeyError as e:
        logger.error(f"data/pests.jsonの構造が正しくありません: {e}")
        return
    
    # サンプル温度データの挿入（日本列島の範囲でグリッドポイントを作成）
    # 緯度: 24-46度、経度: 122-146度の範囲で1度間隔のグリッド
    for lat in range(24, 47, 1):
        for lon in range(122, 147, 1):
            # 各グリッドポイントに温度データを挿入
            cursor.execute('''
            INSERT INTO temperature_data (latitude, longitude, temperature, date)
            VALUES (?, ?, ?, ?)
            ''', (lat, lon, 20.0, '2024-03-20'))  # サンプル温度: 20℃
    
    # 変更を保存
    conn.commit()
    conn.close()
    logger.info("データベースの初期化が完了しました。")

if __name__ == '__main__':
    init_db() 