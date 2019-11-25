CREATE TABLE IF NOT EXISTS akce (
    id PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT,
    keywords TEXT,
    gps TEXT NOT NULL, # aspon okres...
    location TEXT,
    beg datetime,
    end datetime,
    url TEXT UNIQUE,
    t TIMESTAMP DEFAULT CURRENT_TIMESTAMP, # when was added
    UNIQUE (beg, title, location)
);
