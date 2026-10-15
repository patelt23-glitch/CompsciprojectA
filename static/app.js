window.VisuospatialApp = window.VisuospatialApp || {};
window.VisuospatialApp.init = async function () {
  if (window.VisuospatialApp.views && window.VisuospatialApp.views.route) {
    try {
      const {user} = await window.VisuospatialApp.api('/api/session/');
      window.VisuospatialApp.state.authenticated = Boolean(user);
      if (user) window.VisuospatialApp.state.clinician = user;
      window.addEventListener("hashchange", window.VisuospatialApp.views.route);
      window.VisuospatialApp.views.route();
    } catch (error) {
      window.VisuospatialApp.main.textContent = error.message;
    }
  }
};

window.VisuospatialApp.init();

