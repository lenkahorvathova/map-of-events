CREATE TABLE IF NOT EXISTS event_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  type TEXT,
  keywords TEXT,
  location TEXT,
  gps_latitude TEXT NOT NULL,
  gps_longitude TEXT NOT NULL,
  start datetime,
  end datetime,
  parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  event_raw_id INTEGER, FOREIGN KEY (event_raw_id) REFERENCES events_raw(id)
);

CREATE TABLE IF NOT EXISTS event_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL UNIQUE,
  html_file_path TEXT NOT NULL,
  is_parsed INTEGER DEFAULT 0,
  downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS website (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  html_file_path TEXT NOT NULL,
  is_parsed INTEGER DEFAULT 0,
  downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
