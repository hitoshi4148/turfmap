import csv
import os

# 日本の範囲（緯度経度）
lat_start = 24.0  # 沖縄県
lat_end = 45.5    # 北海道
lon_start = 122.0 # 最西端
lon_end = 146.0   # 最東端
step = 1.0        # 0.5度間隔

# 保存先ディレクトリを作成
os.makedirs("data", exist_ok=True)

# 小数点ステップ対応 range
def frange(start, stop, step):
    while start <= stop:
        yield round(start, 3)
        start += step

# グリッドポイントを生成
points = []
for lat in frange(lat_start, lat_end, step):
    for lon in frange(lon_start, lon_end, step):
        points.append({
            "lat": lat,
            "lon": lon,
            "start_date": "20240101"  # 積算開始日（固定）
        })

# CSVファイルに保存
with open("data/grid_points.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["lat", "lon", "start_date"])
    writer.writeheader()
    writer.writerows(points)

print(f"✅ {len(points)}個のグリッドポイントを生成しました")
