from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
import sqlite3

from config import Config
from db import get_connection, init_db, DB_PATH
from utils import today_local, now_local_iso, compute_standings, round_robin_pairings

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY


# --------- Helpers de sesión ---------

def is_admin():
    return session.get("role") == "admin"


def current_team_id():
    return session.get("team_id")


# --------- Inicialización DB ---------

@app.before_request
def ensure_db():
    if not DB_PATH.exists():
        init_db()


# --------- Rutas públicas ---------

@app.get("/")
def index():
    with get_connection() as conn:
        standings = compute_standings(conn, app.config["NO_SHOW_WIN_POINTS"])
        today = today_local().isoformat()
        # Próximos 10 partidos
        upcoming = conn.execute(
            """
            SELECT m.*, j.date, th.name as home_name, ta.name as away_name
            FROM matches m
            JOIN jornadas j ON j.id=m.jornada_id
            JOIN teams th ON th.id=m.home_team_id
            JOIN teams ta ON ta.id=m.away_team_id
            WHERE m.status='scheduled' AND j.date >= ?
            ORDER BY j.date ASC
            LIMIT 10
            """,
            (today,),
        ).fetchall()
        # Últimos resultados (10)
        recent = conn.execute(
            """
            SELECT m.*, j.date, th.name as home_name, ta.name as away_name
            FROM matches m
            JOIN jornadas j ON j.id=m.jornada_id
            JOIN teams th ON th.id=m.home_team_id
            JOIN teams ta ON ta.id=m.away_team_id
            WHERE m.status='completed'
            ORDER BY j.date DESC, m.updated_at DESC
            LIMIT 10
            """,
        ).fetchall()
    return render_template("index.html", standings=standings, upcoming=upcoming, recent=recent)


@app.get("/standings")
def standings():
    with get_connection() as conn:
        table = compute_standings(conn, app.config["NO_SHOW_WIN_POINTS"])
    return render_template("standings.html", table=table)


@app.get("/jornadas")
def jornadas():
    with get_connection() as conn:
        rows = conn.execute("SELECT id, number, date FROM jornadas ORDER BY number").fetchall()
        data = []
        for j in rows:
            matches = conn.execute(
                """
                SELECT m.*, th.name as home_name, ta.name as away_name
                FROM matches m
                JOIN teams th ON th.id=m.home_team_id
                JOIN teams ta ON ta.id=m.away_team_id
                WHERE m.jornada_id=?
                ORDER BY m.id
                """,
                (j["id"],),
            ).fetchall()
            data.append({"jornada": j, "matches": matches})
    return render_template("jornadas.html", data=data)


@app.get("/matches")
def matches():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.*, j.date, th.name as home_name, ta.name as away_name
            FROM matches m
            JOIN jornadas j ON j.id=m.jornada_id
            JOIN teams th ON th.id=m.home_team_id
            JOIN teams ta ON ta.id=m.away_team_id
            ORDER BY j.number, m.id
            """
        ).fetchall()
    return render_template("matches.html", matches=rows)


# --------- Autenticación equipos ---------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == app.config["ADMIN_USERNAME"]:
            if password == app.config["ADMIN_PASSWORD"]:
                session.clear()
                session["role"] = "admin"
                flash("Acceso de administrador concedido", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Credenciales incorrectas", "danger")
                return render_template("login.html")

        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, is_active FROM teams WHERE username=?",
                (username,),
            ).fetchone()
        if not row or not row["is_active"]:
            flash("Usuario no encontrado o inactivo", "danger")
            return render_template("login.html")

        if not check_password_hash(row["password_hash"], password):
            flash("Contraseña incorrecta", "danger")
            return render_template("login.html")

        session.clear()
        session["role"] = "team"
        session["team_id"] = row["id"]
        flash("Sesión iniciada", "success")
        return redirect(url_for("team_dashboard"))

    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada", "info")
    return redirect(url_for("index"))


@app.get("/team")
def team_dashboard():
    if current_team_id() is None:
        return redirect(url_for("login"))
    tid = current_team_id()
    with get_connection() as conn:
        team = conn.execute("SELECT * FROM teams WHERE id=?", (tid,)).fetchone()
        upcoming = conn.execute(
            """
            SELECT m.*, j.date, th.name as home_name, ta.name as away_name
            FROM matches m
            JOIN jornadas j ON j.id=m.jornada_id
            JOIN teams th ON th.id=m.home_team_id
            JOIN teams ta ON ta.id=m.away_team_id
            WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status='scheduled'
            ORDER BY j.date ASC
            LIMIT 10
            """,
            (tid, tid),
        ).fetchall()
        pending_to_fill = conn.execute(
            """
            SELECT m.*, j.date, th.name as home_name, ta.name as away_name
            FROM matches m
            JOIN jornadas j ON j.id=m.jornada_id
            JOIN teams th ON th.id=m.home_team_id
            JOIN teams ta ON ta.id=m.away_team_id
            WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status='scheduled' AND j.date <= date('now')
            ORDER BY j.date ASC
            """,
            (tid, tid),
        ).fetchall()
        recent = conn.execute(
            """
            SELECT m.*, j.date, th.name as home_name, ta.name as away_name
            FROM matches m
            JOIN jornadas j ON j.id=m.jornada_id
            JOIN teams th ON th.id=m.home_team_id
            JOIN teams ta ON ta.id=m.away_team_id
            WHERE (m.home_team_id=? OR m.away_team_id=?) AND m.status='completed'
            ORDER BY j.date DESC, m.updated_at DESC
            LIMIT 10
            """,
            (tid, tid),
        ).fetchall()
    return render_template(
        "team_dashboard.html", team=team, upcoming=upcoming, pending=pending_to_fill, recent=recent
    )


@app.route("/team/match/<int:match_id>/enter", methods=["GET", "POST"])
def enter_result(match_id: int):
    if current_team_id() is None:
        return redirect(url_for("login"))
    tid = current_team_id()
    with get_connection() as conn:
        m = conn.execute(
            """
            SELECT m.*, j.date, th.name as home_name, ta.name as away_name
            FROM matches m
            JOIN jornadas j ON j.id=m.jornada_id
            JOIN teams th ON th.id=m.home_team_id
            JOIN teams ta ON ta.id=m.away_team_id
            WHERE m.id=?
            """,
            (match_id,),
        ).fetchone()
        if not m:
            flash("Partido no encontrado", "danger")
            return redirect(url_for("team_dashboard"))
        if tid not in (m["home_team_id"], m["away_team_id"]):
            flash("No puede introducir resultados de un partido ajeno", "danger")
            return redirect(url_for("team_dashboard"))
        if m["status"] == "completed":
            flash("Este partido ya tiene resultado", "info")
            return redirect(url_for("team_dashboard"))

        if request.method == "POST":
            no_show = request.form.get("no_show")
            winner_one_player = 1 if request.form.get("winner_one_player") == "on" else 0
            if no_show == "opponent":
                # El rival no se presentó -> victoria administrativa
                no_show_team_id = m["away_team_id"] if tid == m["home_team_id"] else m["home_team_id"]
                conn.execute(
                    """
                    UPDATE matches SET status='completed', home_score=NULL, away_score=NULL,
                           no_show_team_id=?, winner_one_player=0, submitted_by_team_id=?, updated_at=?
                    WHERE id=?
                    """,
                    (no_show_team_id, tid, now_local_iso(), match_id),
                )
                conn.commit()
                flash("Resultado registrado: incomparecencia del rival", "success")
                return redirect(url_for("team_dashboard"))
            else:
                # Resultado normal
                try:
                    home_score = int(request.form.get("home_score", "").strip())
                    away_score = int(request.form.get("away_score", "").strip())
                except ValueError:
                    flash("Introduzca marcadores válidos (enteros)", "danger")
                    return render_template("enter_result.html", m=m)
                if home_score == away_score:
                    flash("No se permite empate. Ajuste los marcadores.", "danger")
                    return render_template("enter_result.html", m=m)
                conn.execute(
                    """
                    UPDATE matches
                    SET status='completed', home_score=?, away_score=?, winner_one_player=?,
                        no_show_team_id=NULL, submitted_by_team_id=?, updated_at=?
                    WHERE id=?
                    """,
                    (home_score, away_score, winner_one_player, tid, now_local_iso(), match_id),
                )
                conn.commit()
                flash("Resultado registrado correctamente", "success")
                return redirect(url_for("team_dashboard"))

    return render_template("enter_result.html", m=m)


# --------- Administración ---------

@app.get("/admin/login")
def admin_login():
    return render_template("admin_login.html")


@app.get("/admin")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("login"))
    with get_connection() as conn:
        team_count = conn.execute("SELECT COUNT(*) AS c FROM teams").fetchone()["c"]
        jornada_count = conn.execute("SELECT COUNT(*) AS c FROM jornadas").fetchone()["c"]
        match_count = conn.execute("SELECT COUNT(*) AS c FROM matches").fetchone()["c"]
    return render_template(
        "admin_dashboard.html",
        team_count=team_count,
        jornada_count=jornada_count,
        match_count=match_count,
    )


@app.route("/admin/teams", methods=["GET", "POST"])
def admin_teams():
    if not is_admin():
        return redirect(url_for("login"))
    with get_connection() as conn:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            if not name or not username or not password:
                flash("Nombre, usuario y contraseña son obligatorios", "danger")
            else:
                try:
                    conn.execute(
                        "INSERT INTO teams(name, username, password_hash) VALUES(?,?,?)",
                        (name, username, generate_password_hash(password)),
                    )
                    conn.commit()
                    flash("Equipo creado", "success")
                except sqlite3.IntegrityError:
                    flash("Nombre o usuario ya existe", "danger")
        teams = conn.execute("SELECT * FROM teams ORDER BY name").fetchall()
    return render_template("admin_teams.html", teams=teams)


@app.post("/admin/teams/<int:team_id>/toggle")
def admin_team_toggle(team_id: int):
    if not is_admin():
        return redirect(url_for("login"))
    with get_connection() as conn:
        row = conn.execute("SELECT is_active FROM teams WHERE id=?", (team_id,)).fetchone()
        if row:
            new_val = 0 if row["is_active"] else 1
            conn.execute("UPDATE teams SET is_active=? WHERE id=?", (new_val, team_id))
            conn.commit()
            flash("Estado actualizado", "success")
    return redirect(url_for("admin_teams"))


@app.post("/admin/teams/<int:team_id>/reset_password")
def admin_team_reset_pwd(team_id: int):
    if not is_admin():
        return redirect(url_for("login"))
    pwd = request.form.get("new_password", "")
    if not pwd:
        flash("Contraseña no puede estar vacía", "danger")
        return redirect(url_for("admin_teams"))
    with get_connection() as conn:
        conn.execute(
            "UPDATE teams SET password_hash=? WHERE id=?",
            (generate_password_hash(pwd), team_id),
        )
        conn.commit()
    flash("Contraseña actualizada", "success")
    return redirect(url_for("admin_teams"))


@app.route("/admin/jornadas", methods=["GET", "POST"])
def admin_jornadas():
    if not is_admin():
        return redirect(url_for("login"))
    with get_connection() as conn:
        if request.method == "POST":
            try:
                n = int(request.form.get("num_jornadas", "0"))
            except ValueError:
                n = 0
            if n <= 0:
                flash("Introduzca un número de jornadas válido", "danger")
            else:
                # borrar y recrear con fechas
                conn.execute("DELETE FROM jornadas")
                for i in range(1, n + 1):
                    date_str = request.form.get(f"date_{i}", "").strip()
                    if not date_str:
                        flash(f"Falta fecha para jornada {i}", "warning")
                        date_str = today_local().isoformat()
                    conn.execute(
                        "INSERT INTO jornadas(number, date) VALUES(?, ?)", (i, date_str)
                    )
                conn.commit()
                flash("Jornadas guardadas", "success")
        jornadas = conn.execute("SELECT * FROM jornadas ORDER BY number").fetchall()
    return render_template("admin_jornadas.html", jornadas=jornadas)


@app.post("/admin/generate_fixtures")
def admin_generate_fixtures():
    if not is_admin():
        return redirect(url_for("login"))
    reset = request.form.get("reset") == "on"
    with get_connection() as conn:
        team_ids = [row["id"] for row in conn.execute("SELECT id FROM teams WHERE is_active=1 ORDER BY id").fetchall()]
        jornadas = conn.execute("SELECT * FROM jornadas ORDER BY number").fetchall()
        if not team_ids or not jornadas:
            flash("Necesita equipos activos y jornadas definidas", "danger")
            return redirect(url_for("admin_dashboard"))
        if reset:
            conn.execute("DELETE FROM matches")
        rounds = round_robin_pairings(team_ids)  # (n-1) rondas

        # repetir rondas si hay más jornadas que rondas
        pairs_by_round = rounds.copy()
        idx = 0
        for j in jornadas:
            if idx >= len(pairs_by_round):
                # segunda vuelta: invertimos localía
                rev = [[(b, a) for (a, b) in rnd] for rnd in rounds]
                pairs_by_round.extend(rev)
            pairs = pairs_by_round[idx]
            for (home, away) in pairs:
                conn.execute(
                    """
                    INSERT INTO matches(jornada_id, home_team_id, away_team_id, scheduled_at, status)
                    VALUES(?,?,?,?, 'scheduled')
                    """,
                    (j["id"], home, away, j["date"] + " 22:30:00"),  # hora por defecto
                )
            idx += 1
        conn.commit()
        flash("Calendario generado", "success")
    return redirect(url_for("admin_matches"))


@app.get("/admin/matches")
def admin_matches():
    if not is_admin():
        return redirect(url_for("login"))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT m.*, j.number as jn, j.date, th.name as home_name, ta.name as away_name
            FROM matches m
            JOIN jornadas j ON j.id=m.jornada_id
            JOIN teams th ON th.id=m.home_team_id
            JOIN teams ta ON ta.id=m.away_team_id
            ORDER BY j.number, m.id
            """
        ).fetchall()
    return render_template("admin_matches.html", matches=rows)


@app.post("/admin/matches/<int:match_id>/reset")
def admin_match_reset(match_id: int):
    if not is_admin():
        return redirect(url_for("login"))
    with get_connection() as conn:
        conn.execute(
            "UPDATE matches SET status='scheduled', home_score=NULL, away_score=NULL, winner_one_player=0, no_show_team_id=NULL WHERE id=?",
            (match_id,),
        )
        conn.commit()
    flash("Partido reabierto", "success")
    return redirect(url_for("admin_matches"))


@app.post("/admin/matches/<int:match_id>/delete")
def admin_match_delete(match_id: int):
    if not is_admin():
        return redirect(url_for("login"))
    with get_connection() as conn:
        conn.execute("DELETE FROM matches WHERE id=?", (match_id,))
        conn.commit()
    flash("Partido eliminado", "success")
    return redirect(url_for("admin_matches"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=True)
