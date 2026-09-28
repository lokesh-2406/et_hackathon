import sqlite3
try:
    conn = sqlite3.connect('data/market.db')
    for table in ['nav_master', 'nav_history', 'ter', 'tri', 'holdings', 'peer_stats']:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count}")
        except Exception as e:
            print(f"{table}: ERROR - {e}")
except Exception as e:
    print(f"DB Error: {e}")
