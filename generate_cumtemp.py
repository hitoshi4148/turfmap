import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 日本語フォントを明示的に指定（Windows向け例：MS Gothic）
plt.rcParams['font.family'] = 'Meiryo'  # 他に 'Yu Gothic', 'Meiryo' なども可

from datetime import datetime

def fetch_nasa_temp_data(lat, lon, start_date, end_date, timeout=30):
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M"
        f"&start={start_date}"
        f"&end={end_date}"
        f"&latitude={lat}"
        f"&longitude={lon}"
        f"&community=AG"
        f"&format=JSON"
    )
    try:
        print(f"APIリクエスト送信: {url}")
        response = requests.get(url, timeout=timeout)
        print(f"APIレスポンス受信: status={response.status_code}")
        if response.status_code == 404:
            print(f"Error: No data available for the specified parameters")
            print(f"URL: {url}")
            print(f"Response: {response.text}")
            return None
        response.raise_for_status()
        data = response.json()
        records = data['properties']['parameter']['T2M']
        df = pd.DataFrame(records.items(), columns=["date", "temp"])
        df["date"] = pd.to_datetime(df["date"])
        df["temp"] = df["temp"].astype(float)
        print(f"Successfully fetched {len(df)} temperature records for lat={lat}, lon={lon}")
        return df
    except requests.exceptions.Timeout as e:
        print(f"Timeout error fetching data for lat={lat}, lon={lon}: {str(e)}")
        print(f"URL: {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for lat={lat}, lon={lon}: {str(e)}")
        print(f"URL: {url}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching data for lat={lat}, lon={lon}: {str(e)}")
        print(f"URL: {url}")
        return None

def calculate_cumtemp(df, base_temp=10):
    df["active_temp"] = df["temp"] - base_temp
    df["active_temp"] = df["active_temp"].apply(lambda x: x if x > 0 else 0)
    df["cumsum"] = df["active_temp"].cumsum()
    return df

def save_and_plot(df, output_csv="cumtemp.csv", show_plot=True):
    df.to_csv(output_csv, index=False)
    print(f"CSV出力: {output_csv}")

    if show_plot:
        plt.figure(figsize=(10, 5))
        plt.plot(df["date"], df["cumsum"], label="積算温度")
        plt.title("積算温度の推移")
        plt.xlabel("日付")
        plt.ylabel("積算温度 (℃日)")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    # 設定：緯度経度（例：東京）、期間、基準温度
    lat = 35.68
    lon = 139.76
    start_date = "20260101"  # 2026年1月1日から
    end_date = datetime.now().strftime("%Y%m%d")  # 最新の日付まで
    base_temp = 10  # 積算温度の基準値

    df = fetch_nasa_temp_data(lat, lon, start_date, end_date)
    df = calculate_cumtemp(df, base_temp)
    save_and_plot(df, output_csv="cumtemp_tokyo.csv")