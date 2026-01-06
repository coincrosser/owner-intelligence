CREATE TABLE IF NOT EXISTS owners (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS source_records (
    id TEXT PRIMARY KEY,
    owner_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    address_line1 TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS addresses (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    line1 TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    confidence REAL NOT NULL,
    is_deliverable INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES owners(id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    value TEXT NOT NULL,
    contact_type TEXT NOT NULL,
    phone_type TEXT,
    confidence REAL NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES owners(id)
);

CREATE TABLE IF NOT EXISTS contact_attempts (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES owners(id)
);

CREATE TABLE IF NOT EXISTS suppression (
    owner_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outreach_queue (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    payload TEXT NOT NULL,
    scheduled_for TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES owners(id)
);

CREATE TABLE IF NOT EXISTS inbound_messages (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES owners(id)
);

CREATE TABLE IF NOT EXISTS hot_leads (
    owner_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
