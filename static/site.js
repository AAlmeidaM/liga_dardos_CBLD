const DATE_FORMAT = new Intl.DateTimeFormat('es-ES', {
  day: '2-digit',
  month: 'short',
  year: 'numeric'
});

async function fetchJSON(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${path}: ${response.status}`);
  }
  return response.json();
}

function formatDate(dateString) {
  if (!dateString) return 'Sin fecha';
  const parsed = new Date(dateString);
  if (Number.isNaN(parsed.getTime())) {
    return dateString;
  }
  return DATE_FORMAT.format(parsed);
}

function renderStandings(tableElement, data) {
  const tbody = tableElement.querySelector('tbody');
  tbody.innerHTML = '';
  data.forEach((row) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${row.pos}</td>
      <td>${row.team_name}</td>
      <td>${row.played}</td>
      <td>${row.wins}</td>
      <td>${row.losses}</td>
      <td>${row.gf}</td>
      <td>${row.ga}</td>
      <td>${row.gd >= 0 ? '+' : ''}${row.gd}</td>
      <td><strong>${row.points}</strong></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderUpcoming(container, data) {
  container.innerHTML = '';
  if (!data.length) {
    container.innerHTML = '<div class="small">No hay próximos partidos.</div>';
    return;
  }
  data.forEach((match) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex';
    wrapper.style.justifyContent = 'space-between';
    wrapper.innerHTML = `
      <div>
        <span class="badge">Jornada ${match.jornada_id}</span>
        <strong>${match.home_name}</strong> vs <strong>${match.away_name}</strong>
      </div>
      <div class="small">${formatDate(match.date)}</div>
    `;
    container.appendChild(wrapper);
    container.appendChild(document.createElement('hr'));
  });
  container.lastChild?.remove();
}

function renderRecent(container, data) {
  container.innerHTML = '';
  if (!data.length) {
    container.innerHTML = '<div class="small">Sin resultados aún.</div>';
    return;
  }
  data.forEach((match) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex';
    wrapper.style.justifyContent = 'space-between';
    const score = match.status === 'completed' && !match.no_show_team_id
      ? `${match.home_score} - ${match.away_score}`
      : 'vs';
    const badges = [];
    if (match.no_show_team_id) {
      badges.push('<span class="small">(incomparecencia)</span>');
    }
    if (match.winner_one_player) {
      badges.push('<span class="small">(victoria con 1 jugador)</span>');
    }
    wrapper.innerHTML = `
      <div>
        <span class="badge">Jornada ${match.jornada_id}</span>
        <strong>${match.home_name}</strong> ${score} <strong>${match.away_name}</strong>
        ${badges.join(' ')}
      </div>
      <div class="small">${formatDate(match.date)}</div>
    `;
    container.appendChild(wrapper);
    container.appendChild(document.createElement('hr'));
  });
  container.lastChild?.remove();
}

function renderJornadas(container, data) {
  container.innerHTML = '';
  if (!data.length) {
    container.innerHTML = '<div class="small">No hay jornadas registradas todavía.</div>';
    return;
  }
  data.forEach((entry) => {
    const section = document.createElement('section');
    section.className = 'card';
    const jornada = entry.jornada;
    const header = document.createElement('div');
    header.className = 'flex';
    header.style.justifyContent = 'space-between';
    header.innerHTML = `
      <h2>Jornada ${jornada.number}</h2>
      <div class="small">${formatDate(jornada.date)}</div>
    `;
    section.appendChild(header);

    if (!entry.matches.length) {
      const empty = document.createElement('div');
      empty.className = 'small';
      empty.textContent = 'Sin partidos programados.';
      section.appendChild(empty);
    } else {
      const table = document.createElement('table');
      table.className = 'table';
      table.innerHTML = `
        <thead>
          <tr>
            <th>#</th>
            <th>Local</th>
            <th>Visitante</th>
            <th>Estado</th>
            <th>Resultado</th>
          </tr>
        </thead>
        <tbody></tbody>
      `;
      const tbody = table.querySelector('tbody');
      entry.matches.forEach((match) => {
        const tr = document.createElement('tr');
        const score = match.status === 'completed' && !match.no_show_team_id
          ? `${match.home_score} - ${match.away_score}`
          : 'Pendiente';
        tr.innerHTML = `
          <td>${match.id}</td>
          <td>${match.home_name}</td>
          <td>${match.away_name}</td>
          <td>${match.status === 'completed' ? 'Completado' : 'Programado'}</td>
          <td>${score}</td>
        `;
        tbody.appendChild(tr);
      });
      section.appendChild(table);
    }
    container.appendChild(section);
  });
}

function renderMatches(tableElement, data) {
  const tbody = tableElement.querySelector('tbody');
  tbody.innerHTML = '';
  data.forEach((match) => {
    const tr = document.createElement('tr');
    const score = match.status === 'completed' && !match.no_show_team_id
      ? `${match.home_score} - ${match.away_score}`
      : 'Pendiente';
    const tags = [];
    if (match.no_show_team_id) {
      tags.push('Incomparecencia');
    }
    if (match.winner_one_player) {
      tags.push('1 jugador');
    }
    tr.innerHTML = `
      <td>${match.jornada_number}</td>
      <td>${formatDate(match.date)}</td>
      <td>${match.home_name}</td>
      <td>${match.away_name}</td>
      <td>${score}</td>
      <td>${tags.join(', ') || '-'}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderError(target, error) {
  target.innerHTML = `
    <div class="alert danger">
      <strong>Ups.</strong> ${error.message || error}
    </div>
  `;
}

window.renderLandingPage = async function renderLandingPage() {
  const standingsTable = document.querySelector('#standings-table');
  const upcomingContainer = document.querySelector('#upcoming');
  const recentContainer = document.querySelector('#recent');
  try {
    const [standings, upcoming, recent] = await Promise.all([
      fetchJSON('data/standings.json'),
      fetchJSON('data/upcoming.json'),
      fetchJSON('data/recent.json')
    ]);
    renderStandings(standingsTable, standings);
    renderUpcoming(upcomingContainer, upcoming);
    renderRecent(recentContainer, recent);
  } catch (error) {
    renderError(document.querySelector('main'), error);
  }
};

window.renderStandingsPage = async function renderStandingsPage() {
  const standingsTable = document.querySelector('#standings-table');
  try {
    const standings = await fetchJSON('data/standings.json');
    renderStandings(standingsTable, standings);
  } catch (error) {
    renderError(document.querySelector('main'), error);
  }
};

window.renderJornadasPage = async function renderJornadasPage() {
  const container = document.querySelector('#jornadas');
  try {
    const jornadas = await fetchJSON('data/jornadas.json');
    renderJornadas(container, jornadas);
  } catch (error) {
    renderError(container, error);
  }
};

window.renderMatchesPage = async function renderMatchesPage() {
  const table = document.querySelector('#matches-table');
  try {
    const matches = await fetchJSON('data/matches.json');
    renderMatches(table, matches);
  } catch (error) {
    renderError(document.querySelector('main'), error);
  }
};

window.renderStandaloneMessage = function renderStandaloneMessage() {
  const target = document.querySelector('#standalone-message');
  if (!target) return;
  target.innerHTML = `
    <div class="alert info">
      Esta versión publicada en GitHub Pages es solo de lectura. Para registrar resultados usa la aplicación desplegada con Flask.
    </div>
  `;
};
