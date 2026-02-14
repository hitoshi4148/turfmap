from flask import Flask, render_template, jsonify, request, send_from_directory
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
import json
from database import Database

app = Flask(__name__)

@app.route('/output/<path:filename>')
def output_files(filename):
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    print(f"DEBUG: output_dir={output_dir}, filename={filename}")
    return send_from_directory(output_dir, filename)


# 環境変数の読み込み
load_dotenv()

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# データディレクトリの設定
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# データベースの設定
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/agromap')

# データベースインスタンスの作成
db = Database()

def load_weather_data():
    """気象データを読み込む"""
    try:
        # 気象データの読み込み
        weather_file = os.path.join(DATA_DIR, 'weather_data.csv')
        if not os.path.exists(weather_file):
            print(f"Warning: {weather_file} not found")
            # サンプルデータを生成
            return generate_sample_weather_data()
        
        df = pd.read_csv(weather_file)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        print(f"Error loading weather data: {e}")
        return generate_sample_weather_data()

def generate_sample_weather_data():
    """サンプルの気象データを生成"""
    try:
        # グリッドポイントの取得
        grid_points = get_grid_points().get_json()
        
        # 日付の範囲を設定（2026年1月1日から現在まで）
        start_date = datetime(2026, 1, 1)
        end_date = datetime.now()
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # データフレームを作成
        data = []
        for point in grid_points:
            for date in dates:
                # 中心からの距離に応じて温度を変化させる
                distance = np.sqrt(
                    (point['lat'] - 35.6812) ** 2 + 
                    (point['lon'] - 139.7671) ** 2
                )
                
                # より自然な温度分布を生成
                # 1. 標高による温度変化（北に行くほど低くなる）
                lat_effect = -0.5 * (point['lat'] - 35.6812)
                
                # 2. 海からの距離による温度変化（内陸ほど温度差が大きい）
                sea_distance = np.sqrt(
                    (point['lon'] - 139.7671) ** 2
                )
                sea_effect = 0.3 * sea_distance
                
                # 3. 季節による温度変化
                day_of_year = date.timetuple().tm_yday
                seasonal_effect = 10 * np.sin(2 * np.pi * day_of_year / 365)
                
                # 基本温度を計算
                base_temp = 15 + lat_effect + sea_effect + seasonal_effect
                
                # ランダムな変動を加える（より小さく）
                temperature = base_temp + np.random.uniform(-1, 1)
                
                data.append({
                    'grid_id': point['id'],
                    'date': date,
                    'temperature': temperature
                })
        
        df = pd.DataFrame(data)
        print(f"Debug: Generated sample weather data with {len(df)} records")
        return df
    except Exception as e:
        print(f"Error generating sample weather data: {e}")
        return pd.DataFrame()

def calculate_accumulated_temperature(df, pest):
    """積算温度を計算"""
    if df.empty:
        return pd.DataFrame()
    
    try:
        # 基準日から現在までのデータを取得
        base_date = datetime(2026, 1, 1)
        current_date = datetime.now()
        mask = (df['date'] >= base_date) & (df['date'] <= current_date)
        df = df[mask].copy()
        
        # 発育開始温度を取得
        threshold_temp = pest.get('threshold_temp', 10.0)
        
        # 発育開始温度以上の温度のみを積算
        df['effective_temp'] = df['temperature'].apply(lambda x: max(0, x - threshold_temp))
        df['accumulated_temp'] = df.groupby('grid_id')['effective_temp'].cumsum()
        
        print(f"Debug: Calculated accumulated temperature for {len(df['grid_id'].unique())} grid points")
        return df
    except Exception as e:
        print(f"Error in calculate_accumulated_temperature: {str(e)}")
        return pd.DataFrame()

def calculate_cumtemp(temps, base_temp=10):
    """積算温度を計算"""
    return sum(max(0, temp - base_temp) for temp in temps)

# グリッドポイントの生成
def generate_grid_points():
    # 東京周辺の緯度経度範囲
    lat_min, lat_max = 35.2, 36.0
    lon_min, lon_max = 139.2, 140.3
    
    # 0.05度間隔でグリッドポイントを生成
    lats = np.arange(lat_min, lat_max, 0.05)
    lons = np.arange(lon_min, lon_max, 0.05)
    
    points = []
    for lat in lats:
        for lon in lons:
            points.append({
                'lat': round(lat, 4),
                'lon': round(lon, 4)
            })
    
    return points

# 温度データの生成（ダミーデータ）
def generate_temperature_data(lat, lon):
    # 東京周辺の温度分布を模擬
    base_temp = 20.0  # 基準温度
    lat_factor = (lat - 35.5) * 2  # 緯度による温度変化
    lon_factor = (lon - 139.7) * 1  # 経度による温度変化
    
    # ランダムな変動を加える
    random_factor = np.random.normal(0, 1)
    
    temperature = base_temp + lat_factor + lon_factor + random_factor
    return round(temperature, 1)

def load_pests_data():
    """害虫データをJSONファイルから読み込む"""
    try:
        pests_file = os.path.join(DATA_DIR, 'pests.json')
        if not os.path.exists(pests_file):
            logger.error(f"Pests file not found: {pests_file}")
            return []
        
        with open(pests_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('pests', [])
    except Exception as e:
        logger.error(f"Error loading pests data: {e}")
        return []

@app.route('/')
def index():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    return send_from_directory(output_dir, 'index.html')

@app.route('/api/pests')
def get_pests():
    """害虫データをJSONで取得"""
    pests = db.get_pests()
    return jsonify(pests)

@app.route('/api/pest/<pest_name>')
def get_pest_info(pest_name):
    """特定の害虫の情報を取得"""
    pest = db.get_pest_by_name(pest_name)
    if pest:
        return jsonify(pest)
    else:
        return jsonify({'error': 'Pest not found'}), 404

@app.route('/api/grid_points')
def get_grid_points():
    points = generate_grid_points()
    return jsonify(points)

@app.route('/api/temperature/<float:lat>/<float:lon>')
def get_temperature(lat, lon):
    try:
        # 温度データの生成
        temperature = generate_temperature_data(lat, lon)
        return jsonify({
            'temperature': temperature,
            'lat': lat,
            'lon': lon
        })
    except Exception as e:
        print(f"Error generating temperature data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/temperature/<int:pest_id>')
def get_temperature_data(pest_id):
    try:
        # 気象データを読み込む
        df = load_weather_data()
        if df.empty:
            print("Warning: No weather data available")
            return jsonify([])
        
        # 害虫の閾値を取得
        pest = get_pest_info(pest_id).get_json()
        if not pest:
            print(f"Warning: No pest data found for ID {pest_id}")
            return jsonify([])
        
        # 積算温度を計算
        df = calculate_accumulated_temperature(df, pest)
        if df.empty:
            print("Warning: No accumulated temperature data calculated")
            return jsonify([])
        
        # 最新の積算温度データを取得
        latest_data = df.groupby('grid_id').last().reset_index()
        
        # グリッドポイントのデータを取得
        grid_points = get_grid_points().get_json()
        grid_dict = {point['id']: point for point in grid_points}
        
        # 結果を整形
        result = []
        for _, row in latest_data.iterrows():
            grid_id = row['grid_id']
            if grid_id in grid_dict:
                result.append({
                    'lat': grid_dict[grid_id]['lat'],
                    'lon': grid_dict[grid_id]['lon'],
                    'value': float(row['accumulated_temp'])  # 数値型に変換
                })
        
        print(f"Debug: Generated {len(result)} temperature points")
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_temperature_data: {str(e)}")
        return jsonify([])

@app.route('/data/<path:filename>')
def data_files(filename):
    """dataディレクトリのファイルを提供"""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    return send_from_directory(data_dir, filename)

if __name__ == '__main__':
    # データベースの初期化は Database.__init__ 内で実行済みのため、ここでは呼ばない
    
    if os.environ.get('FLASK_ENV') == 'production':
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        app.run(debug=True)
