import unittest
from database import Database
from datetime import datetime, timedelta
import os

class TestDatabase(unittest.TestCase):
    def setUp(self):
        """テスト前に実行される処理"""
        self.test_db_path = 'test_temperature_data.db'
        self.db = Database(self.test_db_path)

    def tearDown(self):
        """テスト後に実行される処理"""
        self.db.close()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_insert_and_get_temperature_data(self):
        """気温データの挿入と取得のテスト"""
        # テストデータの準備
        timestamp = datetime.now()
        latitude = 35.6812
        longitude = 139.7671
        temperature = 25.5
        source = 'TEST'

        # データの挿入
        self.db.insert_temperature_data(timestamp, latitude, longitude, temperature, source)

        # データの取得
        data = self.db.get_temperature_data()
        
        # 検証
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][2], latitude)  # latitude
        self.assertEqual(data[0][3], longitude)  # longitude
        self.assertEqual(data[0][4], temperature)  # temperature
        self.assertEqual(data[0][5], source)  # source

    def test_insert_and_get_grid_points(self):
        """グリッドポイントの挿入と取得のテスト"""
        # テストデータの準備
        latitude = 35.6812
        longitude = 139.7671
        region_name = 'Tokyo'

        # データの挿入
        self.db.insert_grid_point(latitude, longitude, region_name)

        # データの取得
        points = self.db.get_grid_points()
        
        # 検証
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0][1], latitude)  # latitude
        self.assertEqual(points[0][2], longitude)  # longitude
        self.assertEqual(points[0][3], region_name)  # region_name

    def test_get_temperature_data_with_date_range(self):
        """日付範囲指定での気温データ取得のテスト"""
        # テストデータの準備
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # データの挿入
        self.db.insert_temperature_data(now, 35.6812, 139.7671, 25.5, 'TEST')
        self.db.insert_temperature_data(yesterday, 35.6812, 139.7671, 24.5, 'TEST')
        self.db.insert_temperature_data(tomorrow, 35.6812, 139.7671, 26.5, 'TEST')

        # 日付範囲を指定してデータを取得
        data = self.db.get_temperature_data(yesterday, tomorrow)
        
        # 検証
        self.assertEqual(len(data), 3)  # 3つのデータが取得できることを確認

if __name__ == '__main__':
    unittest.main() 