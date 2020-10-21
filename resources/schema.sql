CREATE TABLE IF NOT EXISTS calendar
(
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    url                 TEXT NOT NULL,
    html_file_path      TEXT NOT NULL,
    is_parsed           INTEGER   DEFAULT 0,
    all_event_url_count INTEGER   DEFAULT 0,
    new_event_url_count INTEGER   DEFAULT 0,
    downloaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_url
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT NOT NULL,
    parsed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    calendar_id INTEGER,
    FOREIGN KEY (calendar_id) REFERENCES calendar (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_event_url ON event_url (url);

CREATE TABLE IF NOT EXISTS event_html
(
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    html_file_path TEXT,
    is_parsed      INTEGER   DEFAULT 0,
    downloaded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_url_id   INTEGER,
    FOREIGN KEY (event_url_id) REFERENCES event_url (id)
);

CREATE TABLE IF NOT EXISTS event_data
(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    perex         TEXT,
    datetime      TEXT NOT NULL,
    location      TEXT,
    gps           TEXT,
    organizer     TEXT,
    types         TEXT,
    parsed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_html_id INTEGER,
    FOREIGN KEY (event_html_id) REFERENCES event_html (id),
    UNIQUE (event_html_id)
);

CREATE TABLE IF NOT EXISTS event_data_datetime
(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    start_date    TEXT,
    start_time    TEXT,
    end_date      TEXT,
    end_time      TEXT,
    event_data_id INTEGER,
    FOREIGN KEY (event_data_id) REFERENCES event_data (id),
    UNIQUE (start_date, start_time, end_date, end_time, event_data_id)
);

CREATE TABLE IF NOT EXISTS event_data_gps
(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    online        INTEGER,
    has_default   INTEGER,
    gps           TEXT,
    location      TEXT,
    municipality  TEXT,
    district      TEXT,
    event_data_id INTEGER,
    FOREIGN KEY (event_data_id) REFERENCES event_data (id)
);

CREATE TABLE IF NOT EXISTS event_data_types
(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    type          TEXT,
    event_data_id INTEGER,
    FOREIGN KEY (event_data_id) REFERENCES event_data (id)
);

DROP VIEW IF EXISTS event_data_view;
CREATE VIEW event_data_view AS
    SELECT c.id              AS calendar__id,
           c.url             AS calendar__url,
           c.html_file_path  AS calendar__html_file_path,
           c.downloaded_at   AS calendar__downloaded_at,
           eu.id             AS event_url__id,
           eu.url            AS event_url__url,
           eh.id             AS event_html__id,
           eh.html_file_path AS event_html__html_file_path,
           ed.id             AS event_data__id,
           ed.title          AS event_data__title,
           ed.perex          AS event_data__perex,
           ed.datetime       AS event_data__datetime,
           ed.location       AS event_data__location,
           ed.gps            AS event_data__gps,
           ed.organizer      AS event_data__organizer,
           ed.types          AS event_data__types,
           edd.id            AS event_data_datetime__id,
           edd.start_date    AS event_data_datetime__start_date,
           edd.start_time    AS event_data_datetime__start_time,
           edd.end_date      AS event_data_datetime__end_date,
           edd.end_time      AS event_data_datetime__end_time,
           edg.id            AS event_data_gps__id,
           edg.online        AS event_data_gps__online,
           edg.has_default   AS event_data_gps__has_default,
           edg.gps           AS event_data_gps__gps,
           edg.location      AS event_data_gps__location,
           edg.municipality  AS event_data_gps__municipality,
           edg.district      AS event_data_gps__district
    FROM calendar c
         LEFT OUTER JOIN event_url eu ON eu.calendar_id = c.id
         LEFT OUTER JOIN event_html eh ON eh.event_url_id = eu.id
         LEFT OUTER JOIN event_data ed ON ed.event_html_id = eh.id
         LEFT OUTER JOIN event_data_datetime edd ON edd.event_data_id = ed.id
         LEFT OUTER JOIN event_data_gps edg ON edg.event_data_id = ed.id;
