PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS teams (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jornadas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  number INTEGER NOT NULL,
  date TEXT NOT NULL -- YYYY-MM-DD
);

CREATE TABLE IF NOT EXISTS matches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  jornada_id INTEGER NOT NULL,
  home_team_id INTEGER NOT NULL,
  away_team_id INTEGER NOT NULL,
  scheduled_at TEXT, -- ISO datetime opcional
  status TEXT NOT NULL DEFAULT 'scheduled', -- scheduled|completed
  home_score INTEGER,
  away_score INTEGER,
  winner_one_player INTEGER NOT NULL DEFAULT 0, -- 1 si el equipo ganador jugó con un solo jugador
  no_show_team_id INTEGER, -- equipo que no se presentó (NULL si no aplica)
  submitted_by_team_id INTEGER, -- quién registró el resultado
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jornada_id) REFERENCES jornadas(id) ON DELETE CASCADE,
  FOREIGN KEY (home_team_id) REFERENCES teams(id) ON DELETE CASCADE,
  FOREIGN KEY (away_team_id) REFERENCES teams(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_matches_jornada ON matches(jornada_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
