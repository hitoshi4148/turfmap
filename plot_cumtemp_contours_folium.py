import folium
import pandas as pd
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
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

    print(f"{pest_id}: grid_temp min={np.nanmin(temp)}, max={np.nanmax(temp)}, nan count={np.isnan(temp).sum()}, total={temp.size}")

    # グリッド生成と補間（linear + nearest穴埋めで不均一グリッド対応）
    grid_lat, grid_lon = np.mgrid[min(lat):max(lat):200j, min(lon):max(lon):200j]
    grid_temp = griddata((lat, lon), temp, (grid_lat, grid_lon), method="linear")
    # NaN部分をnearest補間で穴埋め
    nan_mask = np.isnan(grid_temp)
    if np.any(nan_mask):
        grid_nearest = griddata((lat, lon), temp, (grid_lat, grid_lon), method="nearest")
        grid_temp[nan_mask] = grid_nearest[nan_mask]
    # ガウシアンスムージングで等値線を滑らかにする
    grid_temp = gaussian_filter(grid_temp, sigma=4)

    print(f"{pest_id}: grid_temp min={np.nanmin(grid_temp)}, max={np.nanmax(grid_temp)}, nan count={np.isnan(grid_temp).sum()}, total={grid_temp.size}")

    # 等値線描画用のレベルを調整（最低2つのレベルが必要）
    if len(levels) == 1:
        levels = [0, levels[0]]
        labels = ['低リスク', labels[0]]
        colors = ['#CCCCCC', colors[0]]
    elif len(levels) == 0:
        levels = [0, 1000]
        labels = ['低リスク', '高リスク']
        colors = ['#CCCCCC', '#FF0000']

    print(f"{pest_id}: levels={levels}")

    # colorsの数をlevelsの数-1に揃える
    if len(colors) > len(levels) - 1:
        colors = colors[:len(levels)-1]
    elif len(colors) < len(levels) - 1:
        # 足りない場合は最後の色で埋める
        colors += [colors[-1]] * (len(levels)-1 - len(colors))

    # 画像保存（透明背景）
    fig, ax = plt.subplots(figsize=(8, 6))
    # カラー指定でcontourf
    try:
        cs = ax.contourf(grid_lon, grid_lat, grid_temp, levels=levels, colors=colors, alpha=0.7)
        lines = plt.contour(grid_lon, grid_lat, grid_temp, levels=levels, colors='black', linewidths=0.5)
        plt.clabel(lines, inline=True, fontsize=8, fmt="%.0f")
    except Exception as e:
        print(f"{pest_id}: contour error: {e}")

    ax.axis('off')
    plt.savefig(f"data/{pest_id}_contours.png", bbox_inches="tight", pad_inches=0, transparent=True)
    plt.close()

    # 凡例を別の画像として保存（コンパクトに生成）
    fig_legend, ax_legend = plt.subplots(figsize=(2.5, 1.5))
    ax_legend.axis('off')
    
    # 凡例の要素を作成
    patches = []
    patch_labels = []
    for color, label in zip(colors, labels):
        patches.append(plt.Rectangle((0, 0), 1, 1, facecolor=color, edgecolor='black', linewidth=0.5))
        patch_labels.append(label)

    # 凡例を左上に配置
    leg = ax_legend.legend(
        patches,
        patch_labels,
        loc='upper left',
        frameon=True,
        framealpha=0.9,
        edgecolor='#ccc',
        fontsize=9,
        handlelength=1.2,
        handletextpad=0.4,
        labelspacing=0.3,
        borderpad=0.4,
    )
    
    # 画像を保存
    plt.savefig(f"output/{pest_id}_legend.png", bbox_inches="tight", pad_inches=0.05, transparent=False, dpi=150, facecolor='#f0f0f0')
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
    print(f"[OK] {pest_name}の地図を output/{pest_id}_map.html に保存しました。")

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
    
    print("\n[完了] すべての害虫地図の生成が完了しました！")

if __name__ == "__main__":
    main()
