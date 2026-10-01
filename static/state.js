window.VisuospatialApp = window.VisuospatialApp || {};

window.VisuospatialApp.state = {
  cleanup: () => {},
  results: [],
  previewAccess: false
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
