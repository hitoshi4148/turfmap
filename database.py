import sqlite3
import os
from datetime import datetime, timedelta
import pandas as pd
import logging
import threading
import json

# ロガーの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Database:
    _instance = None
    _lock = threading.Lock()
    _local = threading.local()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.db_path = 'temperature.db'  # 現在のディレクトリのtemperature.dbを使用
            self.conn = None
            self.cursor = None
            self._initialize_database()

    def connect(self):
        """データベースに接続"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            logger.debug("Database connection established")
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise

    def close(self):
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            logger.debug("Database connection closed")

    def _initialize_database(self):
        """データベースの初期化とテーブルの作成"""
        try:
            self.connect()
            
            # temperature_data テーブルの作成
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS temperature_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                temperature REAL NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # grid_points テーブルの作成
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS grid_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                region_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # pests テーブルの作成
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                threshold_temp REAL NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            self.conn.commit()
            self.initialize_pest_data()
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
        finally:
            self.close()

    def insert_temperature_data(self, timestamp, latitude, longitude, temperature, source):
        """温度データを保存"""
        try:
            self.connect()
            # タイムスタンプを文字列に変換
            date_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            with self.conn:
                self.cursor.execute('''
                    INSERT INTO temperature_data (date, latitude, longitude, temperature, source)
                    VALUES (?, ?, ?, ?, ?)
                ''', (date_str, latitude, longitude, temperature, source))
        except Exception as e:
            logger.error(f"Error inserting temperature data: {str(e)}")
            raise

    def insert_grid_point(self, latitude, longitude, region_name=None):
        """グリッドポイントを保存"""
        self.connect()
        with self.conn:
            self.cursor.execute('''
                INSERT INTO grid_points (latitude, longitude, region_name)
                VALUES (?, ?, ?)
            ''', (latitude, longitude, region_name))

    def initialize_pest_data(self):
        """害虫データの初期化"""
        try:
            self.connect()
            
            # 既存のデータをクリア
            self.cursor.execute('DELETE FROM pests')
            logger.debug("Cleared existing pest data")
            
            # pests.jsonからデータを読み込み
            pests_file = os.path.join('data', 'pests.json')
            if os.path.exists(pests_file):
                with open(pests_file, 'r', encoding='utf-8') as f:
                    pests_data = json.load(f)
                
                for pest in pests_data['pests']:
                    self.cursor.execute('''
                    INSERT INTO pests (name, threshold_temp, description)
                    VALUES (?, ?, ?)
                    ''', (pest['name'], pest['base_temp'], pest['description']))
                    logger.debug(f"Added pest: {pest['name']}")
            else:
                logger.warning(f"pests.json not found at {pests_file}, using default data")
                # デフォルトデータの追加
                initial_pests = [
                    ('シバツトガ', 10.0, '芝生の主要な害虫。発育開始温度は10℃。'),
                    ('コガネムシ', 12.0, '芝生の根を食害する害虫。発育開始温度は12℃。'),
                    ('スジキリヨトウ', 11.0, '芝生の葉を食害する害虫。発育開始温度は11℃。')
                ]
                
                for pest in initial_pests:
                    self.cursor.execute('''
                    INSERT INTO pests (name, threshold_temp, description)
                    VALUES (?, ?, ?)
                    ''', pest)
                    logger.debug(f"Added pest: {pest[0]}")
            
            self.conn.commit()
            
            # 登録された害虫の確認
            self.cursor.execute('SELECT * FROM pests')
            registered_pests = [dict(row) for row in self.cursor.fetchall()]
            logger.debug(f"Registered pests: {registered_pests}")
            
        except Exception as e:
            logger.error(f"Error initializing pest data: {str(e)}")
            raise
        finally:
            self.close()

    def get_pests(self):
        """全ての害虫情報を取得"""
        self.connect()
        cursor = self.conn.execute('SELECT * FROM pests ORDER BY name')
        pests = [dict(row) for row in cursor.fetchall()]
        logger.debug(f"Retrieved pests: {pests}")
        return pests

    def get_pest_by_name(self, name):
        """害虫名で検索"""
        self.connect()
        cursor = self.conn.execute('SELECT * FROM pests WHERE name = ?', (name,))
        return dict(cursor.fetchone()) if cursor.fetchone() else None

    def get_temperature_data_by_location(self, latitude, longitude, tolerance=0.01):
        """指定された緯度経度の温度データを取得"""
        self.connect()
        cursor = self.conn.execute('''
            SELECT date, temperature
            FROM temperature_data
            WHERE ABS(latitude - ?) <= ? AND ABS(longitude - ?) <= ?
            ORDER BY date
        ''', (latitude, tolerance, longitude, tolerance))
        return [dict(row) for row in cursor.fetchall()]

    def get_grid_points(self):
        """グリッドポイントの一覧を取得"""
        try:
            logging.debug("Fetching grid points from database")
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT DISTINCT latitude, longitude
                FROM grid_points
                ORDER BY latitude, longitude
            """)
            points = [{'lat': row[0], 'lon': row[1]} for row in cursor.fetchall()]
            logging.debug(f"Found {len(points)} grid points")
            return points
        except Exception as e:
            logging.error(f"Error fetching grid points: {str(e)}")
            raise

    def get_temperature_data(self, start_date=None, end_date=None):
        """指定期間の気温データを取得"""
        self.connect()
        query = "SELECT * FROM temperature_data"
        params = []
        
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        
        cursor = self.conn.execute(query, params)
        data = cursor.fetchall()
        return [dict(row) for row in data]

    def add_pest(self, name, threshold_temp, description=""):
        """害虫情報を追加"""
        self.connect()
        with self.conn:
            self.cursor.execute(
                'INSERT INTO pests (name, threshold_temp, description) VALUES (?, ?, ?)',
                (name, threshold_temp, description)
            )

# データベースインスタンスの作成とエクスポート
db = Database() 