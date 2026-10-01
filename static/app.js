window.VisuospatialApp = window.VisuospatialApp || {};
window.VisuospatialApp.init = function () {
  if (window.VisuospatialApp.views && window.VisuospatialApp.views.route) {
    window.VisuospatialApp.views.route();
    window.addEventListener("hashchange", window.VisuospatialApp.views.route);
  }
};

window.VisuospatialApp.init();

