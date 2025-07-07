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

def create_legend(pest_name, thresholds, output_path):
    """凡例画像を作成"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # 閾値の色リスト
    colors = ['green', 'yellow', 'orange', 'red']
    
    # カラーマップを作成
    cmap = LinearSegmentedColormap.from_list('risk_colors', colors, N=100)
    
    # 閾値の範囲でカラーバーを作成
    min_val = 0
    max_val = 1000  # 最大値を1000℃日に設定
    
    norm = plt.Normalize(min_val, max_val)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    
    # カラーバーを追加
    cbar = plt.colorbar(sm, ax=ax, orientation='horizontal', pad=0.1)
    cbar.set_label('積算温度 (℃日)', fontsize=12)
    
    # 閾値ラインを追加
    threshold_values = [100, 300, 500, 700]  # 例として設定
    threshold_labels = ['低リスク', '中リスク', '高リスク', '極高リスク']
    
    for i, (value, label) in enumerate(zip(threshold_values, threshold_labels)):
        color = colors[i] if i < len(colors) else 'red'
        ax.axvline(x=value, color=color, linestyle='--', linewidth=2, 
                  label=f'{label} ({value}℃日)')
    
    ax.set_xlim(min_val, max_val)
    ax.set_ylim(0, 1)
    ax.set_title(f'{pest_name} 発生リスク凡例', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', bbox_to_anchor=(0, 1))
    ax.set_xticks(np.linspace(min_val, max_val, 6))
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

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
    
    # ファイル名を生成
    pest_name_safe = pest_name.replace(' ', '_').replace('/', '_')
    output_map = f"output/{pest_name_safe}_map.html"
    output_legend = f"output/{pest_name_safe}_legend.png"
    
    # 出力先ディレクトリを取得
    output_dir = os.path.dirname(output_map)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 地図を保存
    m.save(output_map)
    print(f"✅ {output_map} を作成しました。")
    
    # 凡例を作成
    create_legend(pest_name, [], output_legend)
    print(f"✅ {output_legend} を作成しました。")

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
    
    print("\n🎉 すべての害虫地図の生成が完了しました！")

if __name__ == "__main__":
    main() 