import folium
import pandas as pd

# ✅ 地点と積算温度のサンプルデータ（実際はgenerate_cumtemp.pyなどで作ったCSVを読む）
data = [
    {"name": "札幌", "lat": 43.06, "lon": 141.35, "cumtemp": 250},
    {"name": "仙台", "lat": 38.26, "lon": 140.87, "cumtemp": 320},
    {"name": "東京", "lat": 35.68, "lon": 139.76, "cumtemp": 410},
    {"name": "名古屋", "lat": 35.17, "lon": 136.91, "cumtemp": 450},
    {"name": "大阪", "lat": 34.69, "lon": 135.50, "cumtemp": 480},
    {"name": "福岡", "lat": 33.59, "lon": 130.40, "cumtemp": 520},
]

# ✅ カラースケール（積算温度に応じてマーカーの色を変える）
def get_color(cumtemp):
    if cumtemp < 300:
        return "blue"
    elif cumtemp < 400:
        return "green"
    elif cumtemp < 500:
        return "orange"
    else:
        return "red"

# ✅ 地図を初期化（中心＝東京）
m = folium.Map(location=[36.0, 138.0], zoom_start=5)

# ✅ 各地点にマーカーを追加
for d in data:
    folium.CircleMarker(
        location=[d["lat"], d["lon"]],
        radius=10,
        color=get_color(d["cumtemp"]),
        fill=True,
        fill_opacity=0.7,
        popup=f'{d["name"]}：{d["cumtemp"]:.1f}℃日',
    ).add_to(m)

# ✅ 保存してブラウザで表示
m.save("cumtemp_map.html")
print("✅ 地図を cumtemp_map.html に保存しました。")
