(function () {
  const app = window.VisuospatialApp;

  if (!app) {
    return;
  }

  const main = app.main;
  const state = app.state;

  function home() {
    main.innerHTML = `
      <section class="hero">
        <div>
          ${app.eyebrow("Look. Remember. Match.")}
          <h1>Visuospatial<br>Card Matching Test</h1>
          <p>
            A short assessment of visual memory and matching. Take a moment,
            study the shapes, and find their pairs.
          </p>
          <div class="actions">
            ${app.button('Start Test <span aria-hidden="true">→</span>', "instructions")}
            ${app.button("Login", "login", true)}
          </div>
          <p class="small hero-note">
            Simple instructions. A practice round. Your own pace.
          </p>
        </div>
        <div class="art">
          <div class="art-grid">
            ${["circle", "triangle", "square", "plus"].map(app.sample).join("")}
          </div>
          <div class="art-caption">A little focus. A fresh perspective.</div>
        </div>
      </section>

      <section class="features" aria-label="How it works">
        <div>
          <span class="feature-number">01 / STUDY</span>
          <h3>Take a closer look</h3>
          <p>Remember each shape and where it appears.</p>
        </div>
        <div>
          <span class="feature-number">02 / MATCH</span>
          <h3>Find the pairs</h3>
          <p>Choose cards with the same shape and direction.</p>
        </div>
        <div>
          <span class="feature-number">03 / COMPLETE</span>
          <h3>You're all set</h3>
          <p>Your test giver reviews the assessment results.</p>
        </div>
      </section>
    `;
  }

  function login() {
    main.innerHTML = `
      <section class="panel narrow">
        ${app.eyebrow("Test giver")}
        <h1>Welcome back</h1>
        <p>Sign in to manage assessments and review results.</p>

        <div class="notice">
          Frontend preview: authentication is not connected. Use the demo button
          to explore the dashboard.
        </div>

        <label class="label" for="email">Email</label>
        <input id="email" type="email" placeholder="you@example.com" disabled>

        <label class="label" for="password">Password</label>
        <input id="password" type="password" placeholder="Password" disabled>

        <div class="actions">
          <button class="primary full" id="demo-login">
            Explore demo dashboard →
          </button>
        </div>
      </section>
    `;

    document.querySelector("#demo-login").onclick = () => {
      state.previewAccess = true;
      app.go("dashboard");
    };
  }

  function dashboard() {
    if (!state.previewAccess) {
      app.go("login");
      return;
    }

    main.innerHTML = `
      <div class="page-head">
        <div>
          ${app.eyebrow("Test giver workspace")}
          <h1>Dashboard</h1>
          <p>Create a test link and review completed assessments.</p>
        </div>
        <button class="button secondary" id="logout">Leave preview</button>
      </div>

      <div class="notice">
        Demo workspace. Links are local previews, not secure patient invitations.
        Results exist only in this browser tab until it is refreshed.
      </div>

      <div class="dashboard-grid">
        <section class="panel">
          <h2>Patient test link</h2>
          <p>Open the instructions and practice flow with a preview link.</p>
          <button class="primary" id="generate">
            Generate Link <span aria-hidden="true">↗</span>
          </button>

          <div class="link-output hidden" id="link-output">
            <label class="label" for="patient-link">Preview link</label>
            <input id="patient-link" readonly>

            <div class="actions">
              <button class="button secondary" id="copy">Copy link</button>
              ${app.button("Open", "instructions", true)}
            </div>

            <p class="status" id="copy-status" role="status"></p>
          </div>
        </section>

        <section class="panel">
          <h2>Completed tests</h2>
          <p class="small">Assessments completed during this preview session.</p>
          <div id="result-list"></div>
        </section>
      </div>
    `;

    const list = document.querySelector("#result-list");

    if (!state.results.length) {
      list.innerHTML =
        '<div class="empty">No completed tests yet. Open a patient test to try the full flow.</div>';
    }

    state.results.forEach((result, index) => {
      const row = document.createElement("div");
      row.className = "result-row";
      row.innerHTML = `
        <div>
          <strong>Test ${index + 1}</strong>
          <p>
            ${result.date.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit"
            })} · ${result.matches} pairs matched
          </p>
        </div>
        ${app.button("View", `results/${index}`, true)}
      `;
      list.append(row);
    });

    document.querySelector("#logout").onclick = () => {
      state.previewAccess = false;
      app.go("home");
    };

    document.querySelector("#generate").onclick = () => {
      document.querySelector("#link-output").classList.remove("hidden");
      document.querySelector("#patient-link").value =
        location.href.split("#")[0] + "#instructions";
    };

    document.querySelector("#copy").onclick = async () => {
      const field = document.querySelector("#patient-link");

      try {
        await navigator.clipboard.writeText(field.value);
        document.querySelector("#copy-status").textContent = "Preview link copied.";
      } catch {
        field.select();
        document.querySelector("#copy-status").textContent =
          "Select and copy the link above.";
      }
    };
  }

  function instructions() {
    main.innerHTML = `
      <section class="panel narrow">
        ${app.eyebrow("Patient test · Getting started")}
        <h1>A moment to focus</h1>
        <p>Before you begin, here's how the card matching test works.</p>

        <ol class="steps">
          <li>You will see cards for five seconds. Remember each shape and its direction.</li>
          <li>The cards will flip over. Select two cards to reveal them.</li>
          <li>Match identical shapes and directions until all pairs are found.</li>
        </ol>

        <div class="example-pair">${app.sample("circle")}${app.sample("circle")}</div>
        <p class="small" style="text-align:center">
          Same shape. Same direction. A matching pair.
        </p>
        ${app.button("Start Practice →", "practice")}

        <div class="notice">
          Practice first to get comfortable. Practice results are not included in
          the assessment.
        </div>
      </section>
    `;
  }

  function complete(practice) {
    main.innerHTML = `
      <section class="panel narrow completion">
        <div class="check" aria-hidden="true">✓</div>
        ${app.eyebrow(practice ? "Ready for the next step" : "All done")}
        <h1>${practice ? "Practice completed" : "Test completed"}</h1>
        <p>
          ${practice
            ? "You know how it works. When you’re ready, begin the assessment."
            : "Thank you for taking the assessment. Your responses are available in this preview session."}
        </p>
        ${practice ? app.button("Begin Assessment →", "study") : app.button("Done", "home")}
        ${
          practice
            ? `<div class="actions" style="justify-content:center">${app.button("Practice again", "practice", true)}</div>`
            : ""
        }
      </section>
    `;
  }

  function showResult(index) {
    if (!state.previewAccess) {
      app.go("login");
      return;
    }

    const result = state.results[index];

    if (!result) {
      main.innerHTML = `
        <section class="panel narrow">
          <h1>No result available</h1>
          <p>Complete an assessment in this preview session first.</p>
          ${app.button("Back to dashboard", "dashboard")}
        </section>
      `;
      return;
    }

    main.innerHTML = `
      <section class="panel narrow">
        ${app.eyebrow(`Completed assessment · Test ${Number(index) + 1}`)}
        <h1>Assessment results</h1>
        <p>Card matching performance for this session.</p>

        <div class="metrics">
          <div class="result-row">
            <span>Correct matches</span>
            <strong>${result.matches} / 3</strong>
          </div>
          <div class="result-row">
            <span>Mistakes</span>
            <strong>${result.mistakes}</strong>
          </div>
          <div class="result-row">
            <span>Accuracy</span>
            <strong>${result.accuracy}%</strong>
          </div>
          <div class="result-row">
            <span>Average time</span>
            <strong>${result.average.toFixed(1)} sec</strong>
          </div>
        </div>

        <p class="small">
          Accuracy = matching attempts ÷ total attempts. Average time measures each
          pair selection, excluding card reset time.
        </p>

        <div class="actions">
          <button class="primary" id="export">Export CSV ↓</button>
          ${app.button("Dashboard", "dashboard", true)}
        </div>
      </section>
    `;

    document.querySelector("#export").onclick = () => {
      const csv = `test,correct_matches,total_pairs,mistakes,attempts,accuracy_percent,average_seconds\n${
        Number(index) + 1
      },${result.matches},3,${result.mistakes},${result.attempts},${result.accuracy},${result.average.toFixed(
        2
      )}\n`;

      const url = URL.createObjectURL(
        new Blob([csv], { type: "text/csv;charset=utf-8" })
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `assessment-${Number(index) + 1}.csv`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
  }

  function route() {
    state.cleanup();
    state.cleanup = () => {};

    const hash = location.hash.slice(1) || "home";

    document.querySelectorAll("nav a").forEach((anchor) => {
      const active = anchor.hash === `#${hash}`;
      anchor.classList.toggle("active", active);

      if (active) {
        anchor.setAttribute("aria-current", "page");
      } else {
        anchor.removeAttribute("aria-current");
      }
    });

    if (hash === "home") {
      home();
    } else if (hash === "login") {
      login();
    } else if (hash === "dashboard") {
      dashboard();
    } else if (hash === "instructions") {
      instructions();
    } else if (hash === "practice") {
      app.game(true);
    } else if (hash === "study") {
      app.game(false);
    } else if (hash === "practice-complete") {
      complete(true);
    } else if (hash === "complete") {
      complete(false);
    } else if (hash.startsWith("results/")) {
      showResult(hash.split("/")[1]);
    } else if (hash === "about" || hash === "info") {
      main.innerHTML = `
        <section class="panel narrow">
          ${app.eyebrow(hash === "about" ? "About the assessment" : "Before you begin")}
          <h1>${hash === "about" ? "Look, remember, match." : "Before you begin"}</h1>
          <p>
            This short visuospatial task asks you to remember shapes and their
            positions, then find matching pairs.
          </p>
          <p>
            Use a quiet space and a comfortable screen size. Select cards with a
            mouse, touch, or the Tab and Enter keys.
          </p>
          <p>
            There is a five-second study phase followed by an untimed matching
            phase. A practice round helps you learn the interaction.
          </p>
          ${app.button("Start Test", "instructions")}

          <div class="notice">
            This is an interactive frontend prototype, not a validated clinical
            assessment. Authentication, secure invitations, and persistent results
            require backend integration.
          </div>
        </section>
      `;
    } else {
      home();
    }

    main.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  app.views = {
    home,
    login,
    dashboard,
    instructions,
    complete,
    showResult,
    route
  };

  app.init = function () {
    window.addEventListener("hashchange", route);
    route();
  };
})();
