import folium
import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from database import Database, get_connection
from datetime import datetime

def load_pests_from_database():
    """データベースから害虫データを読み込み"""
    try:
        db = Database()
        pests = db.get_pests()
        return pests
    except Exception as e:
        print(f"Error loading pests from database: {e}")
        return []

def get_risk_color(cumtemp):
    """積算温度に基づいてリスク色を決定"""
    if cumtemp < 100:
        return 'green'
    elif cumtemp < 300:
        return 'yellow'
    elif cumtemp < 500:
        return 'orange'
    else:
        return 'red'

def get_risk_level(cumtemp):
    """積算温度に基づいてリスクレベルを決定"""
    if cumtemp < 100:
        return '低リスク'
    elif cumtemp < 300:
        return '中リスク'
    elif cumtemp < 500:
        return '高リスク'
    else:
        return '極高リスク'

def generate_pest_map(pest):
    """害虫ごとの地図を生成"""
    db = Database()
    
    # 最新の積算温度データを取得
    try:
        # 最新の日付を取得
        latest_date = datetime.now().strftime('%Y-%m-%d')
        
        # 積算温度データを取得（最新日付のみ）
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT latitude, longitude, accumulated_temp
                    FROM accumulated_temperature
                    WHERE date = %s
                    ORDER BY latitude, longitude
                ''', (latest_date,))
                data = cur.fetchall()
    except Exception as e:
        print(f"Error fetching accumulated temperature data: {e}")
        return
    
    pest_name = pest['name']
    
    # 地図初期化（日本中心）
    m = folium.Map(location=[36.0, 138.0], zoom_start=5)
    
    for row in data:
        lat, lon, cumtemp = row['latitude'], row['longitude'], row['accumulated_temp']
        
        if cumtemp is None:
            continue
            
        risk_level = get_risk_level(cumtemp)
        color = get_risk_color(cumtemp)
        
        # HTML形式でポップアップ作成
        popup_html = f"""
        <div style="font-size:14px;">
        <b>緯度: {lat:.2f}, 経度: {lon:.2f}</b><br>
        積算温度：{cumtemp:.1f}℃日<br>
        リスクレベル：{risk_level}
        </div>
        """
        popup = folium.Popup(popup_html, max_width=350)
        
        # マーカー追加
        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=popup,
        ).add_to(m)
    
    # 害虫名からローマ字IDへのマッピング（index.htmlと一致させる）
    pest_id_map = {
        'シバツトガ': 'shibatuga',
        'スジキリヨトウ': 'sujikiri',
        'マメコガネ': 'mamekogane',
        'タマナヤガ': 'tamanayaga',
        'ダラースポット': 'dollerspot',
        'スズメノカタビラ': 'katabira',
    }
    
    # ファイル名を生成（ローマ字IDを使用、見つからない場合は日本語名をそのまま使用）
    pest_id = pest_id_map.get(pest_name.strip(), pest_name.replace(' ', '_').replace('/', '_'))
    
    # 出力先ディレクトリ
    output_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    os.makedirs(output_base, exist_ok=True)
    
    output_map = os.path.join(output_base, f"{pest_id}_map.html")

    # 地図を保存
    m.save(output_map)
    print(f"[OK] {output_map}")
    
    # 凡例は plot_cumtemp_contours_folium.py で生成するため、ここでは作成しない

def main():
    """メイン処理"""
    # データベースから害虫データを読み込み
    pests = load_pests_from_database()
    
    if not pests:
        print("害虫データが見つかりません。")
        return
    
    print(f"読み込んだ害虫数: {len(pests)}")
    
    # 各害虫の地図を生成
    for pest in pests:
        print(f"\n{pest['name']}の地図を生成中...")
        generate_pest_map(pest)
    
    print("\n[完了] すべての害虫地図の生成が完了しました！")

if __name__ == "__main__":
    main()
