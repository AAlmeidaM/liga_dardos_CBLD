from datetime import datetime, date
from zoneinfo import ZoneInfo
from config import Config

TZ = ZoneInfo(Config.TIMEZONE)


def today_local():
    return datetime.now(TZ).date()


def now_local_iso():
    return datetime.now(TZ).isoformat(timespec="seconds")


def parse_date(s: str):
    return date.fromisoformat(s)


def compute_standings(conn, no_show_win_points: int):
    teams = {row["id"]: {
        "team_id": row["id"],
        "team_name": row["name"],
        "played": 0,
        "wins": 0,
        "losses": 0,
        "no_shows": 0,
        "points": 0,
        "gf": 0,
        "ga": 0,
        "gd": 0,
    } for row in conn.execute("SELECT id, name FROM teams WHERE is_active=1 ORDER BY name").fetchall()}

    matches = conn.execute("SELECT * FROM matches WHERE status='completed'").fetchall()

    for m in matches:
        home = m["home_team_id"]; away = m["away_team_id"]
        hs = m["home_score"]; as_ = m["away_score"]
        winner_one = bool(m["winner_one_player"])  # si el ganador jugó con uno
        no_show = m["no_show_team_id"]

        for t in (home, away):
            teams[t]["played"] += 1

        if no_show:
            loser = no_show
            winner = home if away == loser else away
            teams[loser]["no_shows"] += 1
            teams[winner]["wins"] += 1
            teams[loser]["losses"] += 1
            teams[winner]["points"] += no_show_win_points
            # goles a favor/contra no cuentan en incomparecencia; dejar 0
            continue

        # Validación suave: si faltan marcadores, saltar
        if hs is None or as_ is None or hs == as_:
            # empates no válidos; ignorar en el cómputo de puntos
            continue

        # goles / legs a favor/contra
        teams[home]["gf"] += hs; teams[home]["ga"] += as_
        teams[away]["gf"] += as_; teams[away]["ga"] += hs
        teams[home]["gd"] = teams[home]["gf"] - teams[home]["ga"]
        teams[away]["gd"] = teams[away]["gf"] - teams[away]["ga"]

        if hs > as_:
            winner = home; loser = away
        else:
            winner = away; loser = home

        teams[winner]["wins"] += 1
        teams[loser]["losses"] += 1
        teams[winner]["points"] += (2 if winner_one else 3)
        teams[loser]["points"] += 1

    # Ordenar por puntos, luego diferencia y GF
    table = list(teams.values())
    table.sort(key=lambda r: (r["points"], r["gd"], r["gf"]), reverse=True)
    # Añadir posición
    for i, row in enumerate(table, start=1):
        row["pos"] = i
    return table


def round_robin_pairings(team_ids):
    """
    Algoritmo círculo. Devuelve lista de rondas; cada ronda es lista de (home, away).
    Si número impar, inserta BYE (None); los emparejamientos con BYE se omiten.
    """
    teams = list(team_ids)
    bye = None
    if len(teams) % 2 == 1:
        teams.append(bye)
    n = len(teams)
    rounds = []
    for r in range(n - 1):
        pairs = []
        for i in range(n // 2):
            a = teams[i]
            b = teams[n - 1 - i]
            if a is not None and b is not None:
                # alternar local/visitante por ronda
                if r % 2 == 0:
                    pairs.append((a, b))
                else:
                    pairs.append((b, a))
        # rotación
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        rounds.append(pairs)
    return rounds
