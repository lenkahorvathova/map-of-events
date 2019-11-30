CREATE TABLE IF NOT EXISTS events_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  type TEXT,
  keywords TEXT,
  location TEXT,
  gps_latitude TEXT NOT NULL,
  gps_longitude TEXT NOT NULL,
  start datetime,
  end datetime,
  parsed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  raw_id INTEGER, FOREIGN KEY (raw_id) REFERENCES events_raw(id)
);

CREATE TABLE IF NOT EXISTS events_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE,
  html_file_path TEXT,
  downloaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

CREATE TABLE IF NOT EXISTS websites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT UNIQUE,
  html_file_path TEXT,
  downloaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
