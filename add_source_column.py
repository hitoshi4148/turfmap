import sqlite3

conn = sqlite3.connect('temperature.db')
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE temperature_data ADD COLUMN source TEXT;")
    print("カラム 'source' を追加しました。")
except Exception as e:
    print("エラー:", e)
conn.commit()
conn.close() 