"""
アニメーション用の週次積算温度データを生成する。
前年1月1日～前年12月31日 (前年基準でゼロから積算) と
今年1月1日～昨日 (今年基準でゼロから積算) を1週間間隔でサンプリングし、
output/animation_data.json に出力する。
さらに、各害虫×各フレームの等値線PNG画像を生成する。
"""

import json
import os
import logging
import numpy as np
import matplotlib
matplotlib.use('Agg')  # GUIバックエンド不要
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from datetime import datetime, timedelta, date
from database import get_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


def get_weekly_accumulated_temps(conn, start_date, end_date):
    """
    指定期間の積算温度を週次でサンプリングして返す。
    start_date からゼロスタートで積算する。
    各地点ごとに直近の既知値をキャリーフォワードし、データ欠損を補完する。
    戻り値: (frame_dates, all_point_coords, frame_data_list)
      - frame_dates: [date, ...]
      - all_point_coords: [(lat, lon), ...]
      - frame_data_list: [[temp_for_point0, temp_for_point1, ...], ...]  per frame
    """
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    logging.info(f"  期間: {start_str} ~ {end_str}")

    with conn.cursor() as cur:
        # 各地点の積算温度を計算
        # GREATEST(0, temperature) でマイナス気温を0に切り上げ → 単調増加を保証
        cur.execute('''
            WITH daily_cumsum AS (
                SELECT
                    date::date as d,
                    latitude::numeric as lat,
                    longitude::numeric as lon,
                    SUM(GREATEST(0, temperature::numeric)) OVER (
                        PARTITION BY latitude, longitude
                        ORDER BY date
                        ROWS UNBOUNDED PRECEDING
                    ) as cum_temp
                FROM temperature_data
                WHERE date::date >= %s::date AND date::date <= %s::date
            )
            SELECT d, lat, lon, cum_temp
            FROM daily_cumsum
            ORDER BY lat, lon, d
        ''', (start_str, end_str))

        # 地点ごとの時系列を構築
        point_timeseries = {}  # (lat, lon) -> [(date, cum_temp), ...]
        for row in cur:
            d = row['d']
            if isinstance(d, str):
                d = datetime.strptime(d, '%Y-%m-%d').date()
            key = (float(row['lat']), float(row['lon']))
            if key not in point_timeseries:
                point_timeseries[key] = []
            point_timeseries[key].append((d, float(row['cum_temp'])))

    if not point_timeseries:
        logging.warning(f"  データがありません")
        return [], [], []

    # 期間の最初の2週間以内にデータがある地点のみ使用（途中参加の地点を除外）
    # これによりフレーム間で地点数が急変するのを防ぐ
    early_cutoff = start_date + timedelta(days=14)
    consistent_points = {}
    excluded = 0
    for key, ts in point_timeseries.items():
        first_date = ts[0][0]  # 時系列は日付順
        if first_date <= early_cutoff:
            consistent_points[key] = ts
        else:
            excluded += 1
    point_timeseries = consistent_points
    if excluded > 0:
        logging.info(f"  途中参加の{excluded}地点を除外（最初の2週間以内にデータなし）")

    all_point_coords = sorted(point_timeseries.keys())
    logging.info(f"  使用地点数: {len(all_point_coords)}")

    # 週次サンプリング日を決定
    frame_dates = []
    sample_date = start_date + timedelta(days=6)
    while sample_date <= end_date:
        frame_dates.append(sample_date)
        sample_date += timedelta(days=7)
    # 最終日を追加（最後のフレームと重複しなければ）
    if not frame_dates or frame_dates[-1] != end_date:
        frame_dates.append(end_date)

    # 各フレーム×各地点のデータを構築（キャリーフォワード方式）
    frame_data_list = []
    for fd in frame_dates:
        frame_temps = []
        for (lat, lon) in all_point_coords:
            ts = point_timeseries[(lat, lon)]
            # fd 以下の最新データを二分探索で取得
            val = None
            lo, hi = 0, len(ts) - 1
            while lo <= hi:
                mid = (lo + hi) // 2
                if ts[mid][0] <= fd:
                    val = ts[mid][1]
                    lo = mid + 1
                else:
                    hi = mid - 1
            frame_temps.append(val)
        frame_data_list.append(frame_temps)

    # 統計ログ
    for i, fd in enumerate(frame_dates):
        valid = sum(1 for t in frame_data_list[i] if t is not None)
        total = len(all_point_coords)
        if valid < total:
            logging.info(f"  {fd}: {valid}/{total} 地点にデータあり")

    logging.info(f"  フレーム数: {len(frame_dates)}")
    return frame_dates, all_point_coords, frame_data_list


def load_pests_from_json():
    """pests.jsonから害虫データを読み込み"""
    pests_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'pests.json')
    if os.path.exists(pests_file):
        with open(pests_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data['pests']
    else:
        logging.error(f"{pests_file} が見つかりません")
        return []


def generate_contour_frame(lat_arr, lon_arr, temp_arr, levels, colors, output_path):
    """
    1フレーム分の等値線PNG画像を生成する。
    不均一グリッドに対応するため、linear補間 → nearest補間でNaN穴埋め。
    """
    # グリッド生成と補間（200x200で高解像度）
    grid_lat, grid_lon = np.mgrid[
        min(lat_arr):max(lat_arr):200j,
        min(lon_arr):max(lon_arr):200j
    ]

    # 1) linear補間（滑らかだがデータ外縁でNaNになりやすい）
    grid_temp = griddata(
        (lat_arr, lon_arr), temp_arr,
        (grid_lat, grid_lon), method="linear"
    )
    # 2) NaN部分をnearest補間で穴埋め（データ外縁を補完）
    nan_mask = np.isnan(grid_temp)
    if np.any(nan_mask):
        grid_nearest = griddata(
            (lat_arr, lon_arr), temp_arr,
            (grid_lat, grid_lon), method="nearest"
        )
        grid_temp[nan_mask] = grid_nearest[nan_mask]

    # 3) ガウシアンスムージングで等値線を滑らかにする
    #    sigma=4: 気象データ可視化の標準的な平滑化レベル
    grid_temp = gaussian_filter(grid_temp, sigma=4)

    # 等値線画像を描画
    fig, ax = plt.subplots(figsize=(8, 6))
    try:
        # colorsの数をlevelsの数-1に揃える
        fill_colors = list(colors)
        if len(fill_colors) > len(levels) - 1:
            fill_colors = fill_colors[:len(levels) - 1]
        elif len(fill_colors) < len(levels) - 1:
            fill_colors += [fill_colors[-1]] * (len(levels) - 1 - len(fill_colors))

        ax.contourf(grid_lon, grid_lat, grid_temp,
                     levels=levels, colors=fill_colors, alpha=0.7, extend='both')
        lines = ax.contour(grid_lon, grid_lat, grid_temp,
                            levels=levels, colors='black', linewidths=0.5)
        ax.clabel(lines, inline=True, fontsize=8, fmt="%.0f")
    except Exception as e:
        # データ範囲が閾値をカバーしていない場合はベタ塗り
        ax.contourf(grid_lon, grid_lat, grid_temp,
                     levels=50, cmap='RdYlGn_r', alpha=0.7)

    ax.axis('off')
    plt.savefig(output_path, bbox_inches="tight", pad_inches=0,
                transparent=True, dpi=72)
    plt.close(fig)


def generate_animation_data():
    """アニメーションデータを生成してJSONファイルと等値線画像を出力する"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    prev_year = today.year - 1
    curr_year = today.year

    prev_start = date(prev_year, 1, 1)
    prev_end = date(prev_year, 12, 31)
    curr_start = date(curr_year, 1, 1)
    curr_end = yesterday

    logging.info("=== アニメーションデータ生成開始 ===")

    with get_connection() as conn:
        logging.info(f"前年({prev_year})の積算温度を計算中...")
        prev_dates, prev_coords, prev_data = get_weekly_accumulated_temps(conn, prev_start, prev_end)

        logging.info(f"今年({curr_year})の積算温度を計算中...")
        curr_dates, curr_coords, curr_data = get_weekly_accumulated_temps(conn, curr_start, curr_end)

    if not prev_dates and not curr_dates:
        logging.error("フレームデータがありません")
        return

    # 全地点の統合（前年と今年で地点が異なる可能性に対応）
    all_point_set = set(prev_coords) | set(curr_coords)
    all_point_coords = sorted(all_point_set)
    logging.info(f"統合地点数: {len(all_point_coords)}")

    # 前年・今年のデータを地点インデックスでマッピング
    def remap_data(src_coords, src_data_list, dst_coords):
        """元の地点リストから統合地点リストへのマッピング"""
        idx_map = {coord: i for i, coord in enumerate(src_coords)}
        remapped = []
        for frame_temps in src_data_list:
            new_temps = []
            for coord in dst_coords:
                src_i = idx_map.get(coord)
                if src_i is not None:
                    new_temps.append(frame_temps[src_i])
                else:
                    new_temps.append(None)
            remapped.append(new_temps)
        return remapped

    prev_remapped = remap_data(prev_coords, prev_data, all_point_coords) if prev_dates else []
    curr_remapped = remap_data(curr_coords, curr_data, all_point_coords) if curr_dates else []

    # フレームを結合
    all_dates = [d.strftime('%Y-%m-%d') for d in prev_dates] + [d.strftime('%Y-%m-%d') for d in curr_dates]
    all_frame_data = prev_remapped + curr_remapped
    year_boundary_index = len(prev_dates)
    total_frames = len(all_dates)

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    os.makedirs(output_dir, exist_ok=True)

    # === 害虫ごとの等値線フレーム画像を生成 ===
    pests = load_pests_from_json()
    if not pests:
        logging.error("害虫データが見つかりません")
        return

    # 全座標配列
    all_lat = np.array([p[0] for p in all_point_coords])
    all_lon = np.array([p[1] for p in all_point_coords])

    # 地理的境界（ImageOverlay用）
    bounds = {
        "south": float(np.min(all_lat)),
        "north": float(np.max(all_lat)),
        "west": float(np.min(all_lon)),
        "east": float(np.max(all_lon))
    }

    pest_ids = []
    for pest in pests:
        pest_id = pest['id']
        pest_ids.append(pest_id)
        thresholds = pest['thresholds']

        # 閾値・色を整理
        seen = set()
        thresholds_sorted = []
        for t in sorted(thresholds, key=lambda t: t['value']):
            if t['value'] not in seen:
                thresholds_sorted.append(t)
                seen.add(t['value'])
        levels = [t['value'] for t in thresholds_sorted]
        colors_list = [t['color'] for t in thresholds_sorted]

        if len(levels) < 2:
            levels = [0, 5000]
            colors_list = ['#CCCCCC', '#FF0000']

        frames_dir = os.path.join(output_dir, 'animation_frames', pest_id)
        os.makedirs(frames_dir, exist_ok=True)

        logging.info(f"害虫 {pest['name']} ({pest_id}) のフレーム画像を生成中... ({total_frames}枚)")

        for i in range(total_frames):
            frame_path = os.path.join(frames_dir, f"frame_{i:03d}.png")
            frame_temps = all_frame_data[i]

            # 有効なデータのみを抽出（None を除外）
            valid_mask = [t is not None for t in frame_temps]
            valid_lat = all_lat[valid_mask]
            valid_lon = all_lon[valid_mask]
            valid_temp = np.array([t for t in frame_temps if t is not None])

            if len(valid_temp) < 10:
                logging.warning(f"  {pest_id}: frame {i} ({all_dates[i]}) 有効地点が{len(valid_temp)}のみ - スキップ")
                # 前のフレームをコピー
                if i > 0:
                    prev_path = os.path.join(frames_dir, f"frame_{i-1:03d}.png")
                    if os.path.exists(prev_path):
                        import shutil
                        shutil.copy2(prev_path, frame_path)
                continue

            generate_contour_frame(valid_lat, valid_lon, valid_temp,
                                    levels, colors_list, frame_path)

            if (i + 1) % 10 == 0:
                logging.info(f"  {pest_id}: {i + 1}/{total_frames} フレーム完了")

        logging.info(f"  {pest_id}: 全 {total_frames} フレーム完了")

    # JSON出力用: 地点ごとの温度配列（None → 0 に変換）
    point_temps_json = []
    for j, (lat, lon) in enumerate(all_point_coords):
        temps = []
        for i in range(total_frames):
            val = all_frame_data[i][j]
            temps.append(round(val, 1) if val is not None else 0)
        point_temps_json.append([lat, lon, temps])

    output = {
        "dates": all_dates,
        "year_boundary_index": year_boundary_index,
        "bounds": bounds,
        "pest_ids": pest_ids,
        "total_frames": total_frames,
        "points": point_temps_json
    }

    output_path = os.path.join(output_dir, 'animation_data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f)

    file_size = os.path.getsize(output_path)
    logging.info(f"JSON出力: {output_path} ({file_size / 1024:.0f} KB)")
    logging.info(f"フレーム総数: {total_frames}, 地点数: {len(all_point_coords)}")
    logging.info(f"害虫数: {len(pest_ids)}, フレーム画像総数: {len(pest_ids) * total_frames}")
    logging.info("=== アニメーションデータ生成完了 ===")


if __name__ == "__main__":
    generate_animation_data()
