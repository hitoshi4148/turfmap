import folium
import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

def load_pests_from_json():
    """pests.jsonから害虫データを読み込み"""
    pests_file = os.path.join('data', 'pests.json')
    if os.path.exists(pests_file):
        with open(pests_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['pests']
    else:
        print(f"Error: {pests_file} not found")
        return []

def create_legend(pest_name, thresholds, output_path):
    """凡例画像を作成"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # 閾値の色リストをpests.jsonから取得
    colors = [t['color'] for t in thresholds]
    
    # カラーマップを作成（閾値の色を使う）
    cmap = LinearSegmentedColormap.from_list('risk_colors', colors, N=100)
    
    # 閾値の範囲でカラーバーを作成
    min_val = 0
    max_val = max([t['value'] for t in thresholds]) * 1.2
    
    norm = plt.Normalize(min_val, max_val)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    
    # カラーバーを追加
    cbar = plt.colorbar(sm, ax=ax, orientation='horizontal', pad=0.1)
    cbar.set_label('積算温度 (℃日)', fontsize=12)
    
    # 閾値ラインを追加
    for threshold in thresholds:
        color = threshold['color']
        value = threshold['value']
        label = threshold['label']
        
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

def generate_pest_map(pest):
    """害虫ごとの地図を生成"""
    # 仮の地点データ（ここに実際の積算温度データを入れてください）
    locations = [
        {"name": "札幌", "lat": 43.06, "lon": 141.35, "cumtemp": 200},
        {"name": "仙台", "lat": 38.26, "lon": 140.87, "cumtemp": 300},
        {"name": "東京", "lat": 35.68, "lon": 139.76, "cumtemp": 400},
        {"name": "大阪", "lat": 34.69, "lon": 135.50, "cumtemp": 500},
        {"name": "福岡", "lat": 33.59, "lon": 130.40, "cumtemp": 550},
    ]
    
    pest_name = pest['name']
    thresholds = pest['thresholds']
    
    # 地図初期化（東京中心）
    m = folium.Map(location=[36.0, 138.0], zoom_start=5)
    
    for loc in locations:
        cumtemp = loc["cumtemp"]
        risks = []
        
        # 閾値チェック
        for threshold in thresholds:
            if cumtemp >= threshold['value']:
                risks.append(f"<li>{threshold['label']}：リスクあり</li>")
        
        if risks:
            color = "red"
            risk_html = "<ul>" + "".join(risks) + "</ul>"
        else:
            color = "blue"
            risk_html = "リスクなし"
        
        # HTML形式でポップアップ作成 + 横幅指定
        popup_html = f"""
        <div style="font-size:14px;">
        <b>{loc['name']}</b><br>
        積算温度：{cumtemp:.1f}℃日<br>
        {risk_html}
        </div>
        """
        popup = folium.Popup(popup_html, max_width=350)
        
        # マーカー追加
        folium.CircleMarker(
            location=[loc["lat"], loc["lon"]],
            radius=10,
            color=color,
            fill=True,
            fill_opacity=0.8,
            popup=popup,
        ).add_to(m)
    
    # ファイル名を生成（IDを使用）
    pest_id = pest['id']
    output_map = f"output/{pest_id}_map.html"
    output_legend = f"output/{pest_id}_legend.png"
    
    # 地図を保存
    m.save(output_map)
    print(f"✅ {output_map} を作成しました。")
    
    # 凡例を作成
    create_legend(pest_name, thresholds, output_legend)
    print(f"✅ {output_legend} を作成しました。")

def main():
    """メイン処理"""
    # pests.jsonから害虫データを読み込み
    pests = load_pests_from_json()
    
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
