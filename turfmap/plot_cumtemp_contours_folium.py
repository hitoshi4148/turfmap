import folium
import pandas as pd
import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import os
import matplotlib.font_manager as fm
import datetime
import json

# 日本語フォントを明示的に指定
plt.rcParams['font.family'] = 'Meiryo'  # Windowsの場合
# plt.rcParams['font.family'] = 'Hiragino Sans'  # Macの場合

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

def generate_map(pest):
    """害虫ごとの地図を生成"""
    pest_id = pest['id']
    pest_name = pest['name']
    thresholds = pest['thresholds']
    
    # 閾値・ラベル・色をpests.jsonから取得し、valueで昇順ソート＆重複除去
    seen = set()
    thresholds_sorted = []
    for t in sorted(thresholds, key=lambda t: t['value']):
        if t['value'] not in seen:
            thresholds_sorted.append(t)
            seen.add(t['value'])
    levels = [t['value'] for t in thresholds_sorted]
    labels = [t['label'] for t in thresholds_sorted]
    colors = [t['color'] for t in thresholds_sorted]
    
    # データ読み込み
    df = pd.read_csv("data/cumtemps.csv")

    # 緯度・経度・積算温度
    lat = df["lat"]
    lon = df["lon"]
    temp = df["cum_gdd"]

    # グリッド生成と補間
    grid_lat, grid_lon = np.mgrid[min(lat):max(lat):200j, min(lon):max(lon):200j]
    grid_temp = griddata((lat, lon), temp, (grid_lat, grid_lon), method="cubic")

    # 等値線描画用のレベルを調整（最低2つのレベルが必要）
    if len(levels) == 1:
        levels = [0, levels[0]]
        labels = ['低リスク', labels[0]]
        colors = ['#CCCCCC', colors[0]]
    elif len(levels) == 0:
        levels = [0, 1000]
        labels = ['低リスク', '高リスク']
        colors = ['#CCCCCC', '#FF0000']

    # 画像保存（透明背景）
    fig, ax = plt.subplots(figsize=(8, 6))
    # カラー指定でcontourf
    cs = ax.contourf(grid_lon, grid_lat, grid_temp, levels=levels, colors=colors, alpha=0.7)

    # ラベル（線の上にテキスト）
    lines = plt.contour(grid_lon, grid_lat, grid_temp, levels=levels, colors='black', linewidths=0.5)
    plt.clabel(lines, inline=True, fontsize=8, fmt="%.0f")

    ax.axis('off')
    plt.savefig(f"data/{pest_id}_contours.png", bbox_inches="tight", pad_inches=0, transparent=True)
    plt.close()

    # 凡例を別の画像として保存
    fig_legend = plt.figure(figsize=(10, 6))
    ax_legend = fig_legend.add_subplot(111)
    ax_legend.axis('off')
    
    # 凡例の要素を作成
    legend_elements = []
    for color, label in zip(colors, labels):
        rect = plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor='black')
        legend_elements.append((rect, label))

    # 凡例を表示
    ax_legend.legend(
        [element[0] for element in legend_elements],
        [element[1] for element in legend_elements],
        loc='center',
        frameon=False,
        fontsize=18
    )
    
    # 画像を保存
    plt.savefig(f"output/{pest_id}_legend.png", bbox_inches="tight", pad_inches=0.3, transparent=True, dpi=300)
    plt.close()

    # Foliumマップ作成
    # マップの初期表示範囲を日本全体に固定
    m = folium.Map(
        location=[35.0, 137.0],  # 日本の中心付近
        zoom_start=5,
        min_zoom=4,
        max_zoom=12
    )

    # 等高線画像を日本全体に重ねる
    image_overlay = folium.raster_layers.ImageOverlay(
        name=f"{pest_name} 積算温度 等高線",
        image=f"data/{pest_id}_contours.png",
        bounds=[[24.0, 122.0], [46.0, 146.0]],  # 日本全体
        opacity=0.6,
    )
    image_overlay.add_to(m)
    folium.LayerControl().add_to(m)

    # 出力
    m.save(f"output/{pest_id}_map.html")
    print(f"✅ {pest_name}の地図を output/{pest_id}_map.html に保存しました。")

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
        generate_map(pest)
    
    print("\n🎉 すべての害虫地図の生成が完了しました！")

if __name__ == "__main__":
    main()
