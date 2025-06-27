from dotenv import load_dotenv
load_dotenv()
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import pandas as pd
import logging
import threading
import json
from urllib.parse import urlparse

# ロガーの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_connection():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        # ローカル開発用
        return psycopg2.connect(
            host="localhost",
            port=5432,
            database="agromap",
            user="postgres",
            password="postgres",
            cursor_factory=RealDictCursor
        )
    
    try:
        # URLをパースして個別のパラメータに分解
        parsed = urlparse(DATABASE_URL)
        
        # 接続パラメータを個別に指定
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],  # 先頭の'/'を除去
            user=parsed.username,
            password=parsed.password,
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        logger.error(f"Error parsing DATABASE_URL: {e}")
        # フォールバック: 直接接続
        return psycopg2.connect(
            host="localhost",
            port=5432,
            database="agromap",
            user="postgres",
            password="postgres",
            cursor_factory=RealDictCursor
        )

class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self._initialize_database()

    def _initialize_database(self):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # temperature_data テーブル
                    cur.execute('''
                    CREATE TABLE IF NOT EXISTS temperature_data (
                        id SERIAL PRIMARY KEY,
                        date TIMESTAMP NOT NULL,
                        latitude DOUBLE PRECISION NOT NULL,
                        longitude DOUBLE PRECISION NOT NULL,
                        temperature DOUBLE PRECISION NOT NULL,
                        source TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(date, latitude, longitude)
                    )
                    ''')
                    # grid_points テーブル
                    cur.execute('''
                    CREATE TABLE IF NOT EXISTS grid_points (
                        id SERIAL PRIMARY KEY,
                        latitude DOUBLE PRECISION NOT NULL,
                        longitude DOUBLE PRECISION NOT NULL,
                        region_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(latitude, longitude)
                    )
                    ''')
                    # pests テーブル
                    cur.execute('''
                    CREATE TABLE IF NOT EXISTS pests (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        threshold_temp DOUBLE PRECISION NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    ''')
                    # accumulated_temperature テーブル
                    cur.execute('''
                    CREATE TABLE IF NOT EXISTS accumulated_temperature (
                        date TIMESTAMP NOT NULL,
                        latitude DOUBLE PRECISION NOT NULL,
                        longitude DOUBLE PRECISION NOT NULL,
                        accumulated_temp DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (date, latitude, longitude)
                    )
                    ''')
                    conn.commit()
            self.initialize_pest_data()
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def insert_temperature_data(self, timestamp, latitude, longitude, temperature, source):
        try:
            logger.debug(f"Inserting temperature data: date={timestamp}, lat={latitude}, lon={longitude}, temp={temperature}, source={source}")
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO temperature_data (date, latitude, longitude, temperature, source)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (date, latitude, longitude) DO NOTHING
                    ''', (timestamp, latitude, longitude, temperature, source))
                    conn.commit()
                    logger.debug(f"Successfully inserted temperature data")
        except Exception as e:
            logger.error(f"Error inserting temperature data: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def insert_grid_point(self, latitude, longitude, region_name=None):
        try:
            logger.debug(f"Inserting grid point: lat={latitude}, lon={longitude}, region={region_name}")
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO grid_points (latitude, longitude, region_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (latitude, longitude) DO NOTHING
                    ''', (latitude, longitude, region_name))
                    conn.commit()
                    logger.debug(f"Successfully inserted grid point")
        except Exception as e:
            logger.error(f"Error inserting grid point: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def initialize_pest_data(self):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 既存のデータをクリア
                    cur.execute('DELETE FROM pests')
                    logger.debug("Cleared existing pest data")
                    # pests.jsonからデータを読み込み
                    pests_file = os.path.join('data', 'pests.json')
                    if os.path.exists(pests_file):
                        with open(pests_file, 'r', encoding='utf-8') as f:
                            pests_data = json.load(f)
                        for pest in pests_data['pests']:
                            cur.execute('''
                                INSERT INTO pests (name, threshold_temp, description)
                                VALUES (%s, %s, %s)
                            ''', (pest['name'], pest['base_temp'], pest['description']))
                            logger.debug(f"Added pest: {pest['name']}")
                    else:
                        logger.warning(f"pests.json not found at {pests_file}, using default data")
                        initial_pests = [
                            ('シバツトガ', 10.0, '芝生の主要な害虫。発育開始温度は10℃。'),
                            ('コガネムシ', 12.0, '芝生の根を食害する害虫。発育開始温度は12℃。'),
                            ('スジキリヨトウ', 11.0, '芝生の葉を食害する害虫。発育開始温度は11℃。')
                        ]
                        for pest in initial_pests:
                            cur.execute('''
                                INSERT INTO pests (name, threshold_temp, description)
                                VALUES (%s, %s, %s)
                            ''', pest)
                            logger.debug(f"Added pest: {pest[0]}")
                    conn.commit()
                    # 登録された害虫の確認
                    cur.execute('SELECT * FROM pests')
                    registered_pests = cur.fetchall()
                    logger.debug(f"Registered pests: {registered_pests}")
        except Exception as e:
            logger.error(f"Error initializing pest data: {str(e)}")
            raise

    def get_pests(self):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM pests ORDER BY name')
                    pests = cur.fetchall()
                    logger.debug(f"Retrieved pests: {pests}")
                    return pests
        except Exception as e:
            logger.error(f"Error fetching pests: {str(e)}")
            raise

    def get_pest_by_name(self, name):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM pests WHERE name = %s', (name,))
                    pest = cur.fetchone()
                    return pest if pest else None
        except Exception as e:
            logger.error(f"Error fetching pest by name: {str(e)}")
            raise

    def get_temperature_data_by_location(self, latitude, longitude, tolerance=0.01):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT date, temperature
                        FROM temperature_data
                        WHERE ABS(latitude - %s) <= %s AND ABS(longitude - %s) <= %s
                        ORDER BY date
                    ''', (latitude, tolerance, longitude, tolerance))
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching temperature data by location: {str(e)}")
            raise

    def get_grid_points(self):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT DISTINCT latitude, longitude
                        FROM grid_points
                        ORDER BY latitude, longitude
                    ''')
                    points = [{'lat': row['latitude'], 'lon': row['longitude']} for row in cur.fetchall()]
                    logging.debug(f"Found {len(points)} grid points")
                    return points
        except Exception as e:
            logging.error(f"Error fetching grid points: {str(e)}")
            raise

    def get_temperature_data(self, start_date=None, end_date=None):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    query = "SELECT * FROM temperature_data"
                    params = []
                    if start_date and end_date:
                        query += " WHERE date BETWEEN %s AND %s"
                        params.extend([start_date, end_date])
                    cur.execute(query, params)
                    data = cur.fetchall()
                    return data
        except Exception as e:
            logger.error(f"Error fetching temperature data: {str(e)}")
            raise

    def add_pest(self, name, threshold_temp, description=""):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO pests (name, threshold_temp, description) VALUES (%s, %s, %s)',
                        (name, threshold_temp, description)
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Error adding pest: {str(e)}")
            raise

    def insert_accumulated_temperature(self, date, latitude, longitude, accumulated_temp, created_at=None):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        INSERT INTO accumulated_temperature (date, latitude, longitude, accumulated_temp, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (date, latitude, longitude) DO UPDATE SET
                            accumulated_temp = EXCLUDED.accumulated_temp,
                            created_at = EXCLUDED.created_at
                    ''', (date, latitude, longitude, accumulated_temp, created_at or datetime.now()))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error inserting accumulated temperature: {str(e)}")
            raise

    def get_latest_temperature_date(self):
        """気温データの最新日付を取得"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT MAX(date) as max_date FROM temperature_data')
                    row = cur.fetchone()
                    return row['max_date'] if row and row['max_date'] else None
        except Exception as e:
            logger.error(f"Error fetching latest temperature date: {str(e)}")
            return None

    def get_latest_accumulated_temperature_date(self):
        """積算温度データの最新日付を取得"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT MAX(date) as max_date FROM accumulated_temperature')
                    row = cur.fetchone()
                    return row['max_date'] if row and row['max_date'] else None
        except Exception as e:
            logger.error(f"Error fetching latest accumulated temperature date: {str(e)}")
            return None

# データベースインスタンスの作成とエクスポート
db = Database() 