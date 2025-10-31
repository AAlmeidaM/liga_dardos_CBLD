"""Exporta datos públicos desde la base de datos SQLite a ficheros JSON.

Ejecuta este script después de actualizar resultados en la app Flask para
mantener sincronizada la versión estática publicada en GitHub Pages.
"""

from __future__ import annotations

import json
from pathlib import Path

from config import Config
from db import DB_PATH, get_connection, init_db
from utils import compute_standings, today_local

DATA_DIR = Path(__file__).resolve().parent / "data"


def ensure_database() -> None:
    if not DB_PATH.exists():
        init_db()


def export_standings(conn) -> list[dict]:
    table = compute_standings(conn, Config.NO_SHOW_WIN_POINTS)
    return [
        {
            "pos": row["pos"],
            "team_name": row["team_name"],
            "played": row["played"],
            "wins": row["wins"],
            "losses": row["losses"],
            "gf": row["gf"],
            "ga": row["ga"],
            "gd": row["gd"],
            "points": row["points"],
        }
        for row in table
    ]


def export_upcoming(conn) -> list[dict]:
    today = today_local().isoformat()
    rows = conn.execute(
        """
        SELECT m.jornada_id, j.date, th.name AS home_name, ta.name AS away_name
        FROM matches m
        JOIN jornadas j ON j.id = m.jornada_id
        JOIN teams th ON th.id = m.home_team_id
        JOIN teams ta ON ta.id = m.away_team_id
        WHERE m.status = 'scheduled' AND j.date >= ?
        ORDER BY j.date ASC
        LIMIT 10
        """,
        (today,),
    ).fetchall()
    return [dict(row) for row in rows]


def export_recent(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT m.jornada_id, j.date, th.name AS home_name, ta.name AS away_name,
               m.status, m.home_score, m.away_score, m.winner_one_player,
               m.no_show_team_id
        FROM matches m
        JOIN jornadas j ON j.id = m.jornada_id
        JOIN teams th ON th.id = m.home_team_id
        JOIN teams ta ON ta.id = m.away_team_id
        WHERE m.status = 'completed'
        ORDER BY j.date DESC, m.updated_at DESC
        LIMIT 10
        """
    ).fetchall()
    return [dict(row) for row in rows]


def export_jornadas(conn) -> list[dict]:
    jornadas = conn.execute(
        "SELECT id, number, date FROM jornadas ORDER BY number"
    ).fetchall()
    result: list[dict] = []
    for jornada in jornadas:
        matches = conn.execute(
            """
            SELECT m.id, m.status, m.home_score, m.away_score, m.no_show_team_id,
                   th.name AS home_name, ta.name AS away_name
            FROM matches m
            JOIN teams th ON th.id = m.home_team_id
            JOIN teams ta ON ta.id = m.away_team_id
            WHERE m.jornada_id = ?
            ORDER BY m.id
            """,
            (jornada["id"],),
        ).fetchall()
        result.append(
            {
                "jornada": {
                    "id": jornada["id"],
                    "number": jornada["number"],
                    "date": jornada["date"],
                },
                "matches": [dict(match) for match in matches],
            }
        )
    return result


def export_matches(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT j.number AS jornada_number, j.date,
               th.name AS home_name, ta.name AS away_name,
               m.status, m.home_score, m.away_score,
               m.winner_one_player, m.no_show_team_id
        FROM matches m
        JOIN jornadas j ON j.id = m.jornada_id
        JOIN teams th ON th.id = m.home_team_id
        JOIN teams ta ON ta.id = m.away_team_id
        ORDER BY j.number, m.id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def write_json(filename: str, payload) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Exportado {filename} ({len(payload)} registros)")


def main() -> None:
    ensure_database()
    with get_connection() as conn:
        write_json("standings.json", export_standings(conn))
        write_json("upcoming.json", export_upcoming(conn))
        write_json("recent.json", export_recent(conn))
        write_json("jornadas.json", export_jornadas(conn))
        write_json("matches.json", export_matches(conn))


if __name__ == "__main__":
    main()
