CREATE TABLE IF NOT EXISTS calendar (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  html_file_path TEXT NOT NULL,
  is_parsed INTEGER DEFAULT 0,
  downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_url (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url TEXT NOT NULL,
  parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  calendar_id INTEGER, FOREIGN KEY (calendar_id) REFERENCES calendar(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_url ON event_url (url);

CREATE TABLE IF NOT EXISTS event_html (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  html_file_path TEXT,
  is_parsed INTEGER DEFAULT 0,
  downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  event_url_id INTEGER, FOREIGN KEY (event_url_id) REFERENCES event_url(id)
);

CREATE TABLE IF NOT EXISTS event_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  perex TEXT,
  organizer TEXT,
  types TEXT,
  keywords TEXT,
  location TEXT,
  gps_latitude TEXT NOT NULL,
  gps_longitude TEXT NOT NULL,
  start datetime NOT NULL,
  end datetime,
  parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  event_html_id INTEGER, FOREIGN KEY (event_html_id) REFERENCES event_html(id)
);