CREATE TABLE limits (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
  photo_bytes INTEGER NOT NULL CHECK(photo_bytes BETWEEN 1 AND 5000000),
  daily_posts INTEGER NOT NULL CHECK(daily_posts >= 0),
  monthly_posts INTEGER NOT NULL CHECK(monthly_posts >= 0),
  storage_bytes INTEGER NOT NULL CHECK(storage_bytes >= 0)
);
INSERT INTO limits VALUES (1, 0, 5000000, 30, 300, 2000000000);
CREATE TABLE observations (
  id TEXT PRIMARY KEY,
  fingerprint TEXT NOT NULL,
  bytes INTEGER NOT NULL CHECK(bytes > 0),
  created_at INTEGER NOT NULL,
  day TEXT NOT NULL,
  month TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('pending','ready','deleted')),
  metadata TEXT
);
CREATE INDEX observations_day ON observations(day);
CREATE INDEX observations_month ON observations(month);
CREATE INDEX observations_expiry ON observations(status, expires_at);
-- Executed atomically with the INSERT. Failed uploads keep their post allowance.
CREATE TRIGGER reserve_quota BEFORE INSERT ON observations BEGIN
  SELECT RAISE(ABORT, 'intake_paused') WHERE NOT EXISTS(SELECT 1 FROM limits WHERE id=1 AND enabled=1);
  SELECT RAISE(ABORT, 'photo_limit') WHERE NEW.bytes > (SELECT photo_bytes FROM limits WHERE id=1);
  SELECT RAISE(ABORT, 'daily_limit') WHERE (SELECT COUNT(*) FROM observations WHERE day=NEW.day) >= (SELECT daily_posts FROM limits WHERE id=1);
  SELECT RAISE(ABORT, 'monthly_limit') WHERE (SELECT COUNT(*) FROM observations WHERE month=NEW.month) >= (SELECT monthly_posts FROM limits WHERE id=1);
  SELECT RAISE(ABORT, 'storage_limit') WHERE NEW.bytes + COALESCE((SELECT SUM(bytes) FROM observations WHERE status!='deleted'),0) > (SELECT storage_bytes FROM limits WHERE id=1);
END;
