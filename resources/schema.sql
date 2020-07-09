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
  datetime TEXT NOT NULL,
  location TEXT,
  gps TEXT,
  organizer TEXT,
  types TEXT,
  parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  event_html_id INTEGER, FOREIGN KEY (event_html_id) REFERENCES event_html(id)
);

CREATE TABLE IF NOT EXISTS event_data_datetime (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  start_date TEXT,
  start_time TEXT,
  end_date TEXT,
  end_time TEXT,
  event_data_id INTEGER, FOREIGN KEY (event_data_id) REFERENCES event_data(id),
  UNIQUE(start_date, start_time, end_date, end_time, event_data_id)
);

CREATE TABLE IF NOT EXISTS event_data_location (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  municipality TEXT,
  gps TEXT,
  online INTEGER,
  has_default INTEGER,
  event_data_id INTEGER, FOREIGN KEY (event_data_id) REFERENCES event_data(id)
)