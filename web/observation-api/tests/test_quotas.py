import pathlib
import sqlite3
import unittest

SCHEMA = (pathlib.Path(__file__).parents[1] / 'migrations/0001.sql').read_text()

class Quotas(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript(SCHEMA)

    def insert(self, id, size=10, day='2026-09-07', month='2026-09'):
        self.db.execute('INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)',
                        (id,'hash',size,1,day,month,2,'pending','{}'))

    def enable(self, **values):
        self.db.execute('UPDATE limits SET enabled=1')
        for key, value in values.items():
            self.db.execute(f'UPDATE limits SET {key}=?', (value,))

    def test_closed_by_default_and_missing_config(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError,'intake_paused'): self.insert('a')
        self.db.execute('DELETE FROM limits')
        with self.assertRaisesRegex(sqlite3.IntegrityError,'intake_paused'): self.insert('b')

    def test_daily_and_monthly_boundary(self):
        self.enable(daily_posts=1,monthly_posts=2)
        self.insert('a')
        with self.assertRaisesRegex(sqlite3.IntegrityError,'daily_limit'): self.insert('b')
        self.insert('b',day='2026-09-08')
        with self.assertRaisesRegex(sqlite3.IntegrityError,'monthly_limit'): self.insert('c',day='2026-09-09')
        self.insert('d',day='2026-10-01',month='2026-10')

    def test_pending_reserves_storage_and_deletion_preserves_post_count(self):
        self.enable(storage_bytes=20,daily_posts=2)
        self.insert('a',20)
        with self.assertRaisesRegex(sqlite3.IntegrityError,'storage_limit'): self.insert('b')
        self.db.execute("UPDATE observations SET status='deleted' WHERE id='a'")
        self.insert('b',20)
        with self.assertRaisesRegex(sqlite3.IntegrityError,'daily_limit'): self.insert('c')

    def test_exact_photo_limit_and_duplicate(self):
        self.enable()
        self.insert('a',5000000)
        with self.assertRaisesRegex(sqlite3.IntegrityError,'photo_limit'): self.insert('b',5000001)
        with self.assertRaises(sqlite3.IntegrityError): self.insert('a')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM observations').fetchone()[0],1)

if __name__ == '__main__': unittest.main()
