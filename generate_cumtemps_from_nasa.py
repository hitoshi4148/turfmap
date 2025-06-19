import pandas as pd
import requests
import time
import os

# 📁 データフォルダの作成
os.makedirs("data", exist_ok=True)

def fetch_nasa_temp_data(lat, lon, start_date, end_date):
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M"
        f"&start={start_date}"
        f"&end={end_date}"
        f"&latitude={lat}"
        f"&longitude={lon}"
        f"&format=JSON"
        f"&community=AG" # ←　これを追加！
    )
    response = requests.get(url)
    if response.status_code != 200:
        raise requests.HTTPError(f"{response.status_code} Client Error: {url}")
    data = response.json()
    temps = data["properties"]["parameter"]["T2M"]
    df = pd.DataFrame(temps.items(), columns=["date", "temp"])
    df["temp"] = pd.to_numeric(df["temp"], errors="coerce")
    return df

def calculate_cumtemp(df, base_temp=10.0):
    df["gdd"] = df["temp"].apply(lambda t: max(t - base_temp, 0))
    df["cum_gdd"] = df["gdd"].cumsum()
    return df

# 📥 入力CSVから地点情報を取得
grid_df = pd.read_csv("data/grid_points.csv")

start_date = "20240101"
# 📅 積算対象の終了日（ここは固定 or 自由に設定可）
end_date = "20240601"

results = []

print(f"🌍 {len(grid_df)} 地点に対してデータを取得します...")

for i, row in grid_df.iterrows():
    lat, lon = row["lat"], row["lon"]
    start_date = str(row["start_date"])

   # 👇 この行を追加！
    print(f"🔄 {i+1}/{len(grid_df)}: ({lat}, {lon}) 取得中...")

    try:
        df = fetch_nasa_temp_data(lat, lon, start_date, end_date)
        df = calculate_cumtemp(df)
        final_cum_gdd = df["cum_gdd"].iloc[-1]
        results.append({"lat": lat, "lon": lon, "cum_gdd": final_cum_gdd})
    except Exception as e:
        print(f"⚠️ エラー（{lat},{lon}）：{e}")
        results.append({"lat": lat, "lon": lon, "cum_gdd": None})
    
    time.sleep(1.2)  # 🌐 NASA API負荷対策（1.2秒待機）

# 💾 出力CSV保存
output_df = pd.DataFrame(results)
output_df.to_csv("data/cumtemps.csv", index=False, encoding="utf-8")
print("✅ cumtemps.csv を保存しました。")
