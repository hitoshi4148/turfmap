import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

# CSV読み込み
df = pd.read_csv("data/cumtemps.csv")
lats = df["lat"].values
lons = df["lon"].values
temps = df["cum_gdd"].values

# グリッド作成
grid_lat = np.linspace(min(lats), max(lats), 100)
grid_lon = np.linspace(min(lons), max(lons), 100)
xi, yi = np.meshgrid(grid_lon, grid_lat)

# 積算温度をグリッド化
zi = griddata((lons, lats), temps, (xi, yi), method='cubic')

# 等高線レベル
levels = np.arange(0, 600, 50)

# プロット
plt.figure(figsize=(10, 8))
cs = plt.contourf(xi, yi, zi, levels=levels, cmap='YlOrRd')  # 塗りつぶし
cbar = plt.colorbar(cs)
cbar.set_label('積算温度 (℃)')

# オプション：黒線で輪郭も表示
lines = plt.contour(xi, yi, zi, levels=levels, colors='black', linewidths=0.5)
plt.clabel(lines, inline=True, fontsize=8, fmt="%.0f")

plt.title("積算温度の等値線マップ")
plt.xlabel("経度")
plt.ylabel("緯度")
plt.savefig("cumtemp_map_filled.png", dpi=300)
plt.show()
