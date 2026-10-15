window.VisuospatialApp = window.VisuospatialApp || {};

window.VisuospatialApp.state = {
  cleanup: () => {},
  results: [],
  authenticated: false,
  pendingSessions: [],
  invitationToken: new URLSearchParams(location.search).get('invite')
};

window.VisuospatialApp.symbols = {
  circle: '<span class="shape circle"></span>',
  triangle: '<span class="shape triangle"></span>',
  up: '<span class="shape">↑</span>',
  right: '<span class="shape">→</span>',
  square: '<span class="shape square"></span>',
  plus: '<span class="shape">+</span>'
};

window.VisuospatialApp.main = document.querySelector("main");

window.VisuospatialApp.button = function (label, route, secondary = false) {
  return `<a class="button ${secondary ? "secondary" : ""}" href="#${route}">${label}</a>`;
};

window.VisuospatialApp.eyebrow = function (label) {
  return `<div class="eyebrow">${label}</div>`;
};

window.VisuospatialApp.sample = function (shape) {
  return `<div class="sample-card" aria-hidden="true">${window.VisuospatialApp.symbols[shape]}</div>`;
};

window.VisuospatialApp.go = function (route) {
  location.hash = route;
};

window.VisuospatialApp.escapeHTML = function (value) {
  return String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
};

window.VisuospatialApp.api = async function (path, data) {
  const csrf = document.cookie.split('; ').find(cookie => cookie.startsWith('csrftoken='));
  const response = await fetch(path, {
    method: data === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: {
      'Accept': 'application/json',
      ...(data === undefined ? {} : {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf ? decodeURIComponent(csrf.slice(10)) : ''
      })
    },
    ...(data === undefined ? {} : {body: JSON.stringify(data)})
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || (response.status === 403
      ? 'Your session could not be verified. Refresh the page and try again.'
      : 'Unable to complete the request. Please try again.'));
    error.status = response.status;
    throw error;
  }
  return payload;
};
