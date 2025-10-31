# Liga de Dardos (Flask)

Aplicación web para gestionar una liga de dardos con autenticación por equipos, configuración de jornadas y fechas, registro de resultados y clasificación automática.

## Reglas de puntuación
- **3 puntos** por victoria normal (jugaron dos personas por equipo).
- **2 puntos** por victoria si **el equipo ganador jugó con un solo jugador**.
- **1 punto** por derrota.
- **0 puntos** por **incomparecencia** (no presentación). Por defecto, el equipo presente recibe **3 puntos** (configurable con `NO_SHOW_WIN_POINTS`).

> **Nota**: Los empates no están permitidos.

## Requisitos
- Python 3.11+
- (Opcional) Docker

## Puesta en marcha local
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # edite SECRET_KEY y ADMIN_PASSWORD
python app.py
# Abra http://localhost:5000
```

## Flujo de configuración

1. **Entrar como admin** (`/login`) con usuario/clave de `.env`.
2. **Crear equipos** en **Admin → Gestionar equipos**.
3. **Definir jornadas y fechas** en **Admin → Configurar jornadas**.
4. **Generar calendario** (round-robin). Si hay más jornadas que rondas, se crea segunda vuelta invirtiendo localía.
5. Entregue a cada equipo su **usuario** y **contraseña**.
6. Cada equipo entra en **Mi equipo** y registra sus **resultados** (incluye checkbox de incomparecencia y opción de *victoria con 1 jugador*).

## Despliegue en Render

1. Suba este repositorio a GitHub.
2. En Render, cree un **New Web Service** desde el repositorio.
3. Render leerá `render.yaml` y creará el servicio. Ajuste variables si lo desea.

## Despliegue con Docker

```bash
docker build -t dardos-league .
docker run -p 5000:5000 --env-file .env dardos-league
```

## Estructura de la base de datos

* `teams(id, name, username, password_hash, is_active)`
* `jornadas(id, number, date)`
* `matches(id, jornada_id, home_team_id, away_team_id, status, home_score, away_score, winner_one_player, no_show_team_id, submitted_by_team_id)`

## Seguridad

* Las contraseñas se almacenan con **hash** (Werkzeug).
* Sesiones basadas en cookie (`SECRET_KEY`).

## Personalización

* Zona horaria: `TIMEZONE` (por defecto `Europe/Madrid`).
* Puntos por incomparecencia: `NO_SHOW_WIN_POINTS`.
* Hora por defecto de los partidos: en generación se establece `22:30:00`. Modifique en `admin_generate_fixtures` si desea otra.

## Limitaciones iniciales (MVP)

* Un resultado lo puede introducir cualquiera de los dos equipos implicados. El administrador puede reabrir o eliminar un partido si hay errores.
* No hay confirmación del rival ni sanciones automáticas.
* Los empates no están permitidos.

Con estos archivos, puede publicar el repositorio en GitHub y desplegar la app de forma inmediata.
