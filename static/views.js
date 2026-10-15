(function () {
  const app = window.VisuospatialApp;

  if (!app) {
    return;
  }

  const main = app.main;
  const state = app.state;

  if (!state.pendingSessions) {
    state.pendingSessions = [];
  }

  if (!state.clinician) {
    state.clinician = {
      name: "",
      organization: "",
      email: ""
    };
  }

  function home() {
    main.innerHTML = `
      <section class="hero">

        <div>
          ${app.eyebrow("Look. Remember. Match.")}

          <h1>
            Visuospatial<br>
            Card Matching Test
          </h1>

          <p>
            A short assessment of visual memory and matching.
            Study the shapes, remember their positions,
            and find their pairs.
          </p>

          <div class="actions">

            ${app.button(
              "Start Test →",
              "instructions"
            )}

            ${
              !state.authenticated
                ? app.button(
                    "Clinician Login",
                    "login",
                    true
                  )
                : app.button(
                    "Clinician Dashboard",
                    "dashboard",
                    true
                  )
            }

          </div>

          <p class="small hero-note">
            Simple instructions. A practice round.
            Your own pace.
          </p>
        </div>


        <div class="art">

          <div class="art-grid">

            ${[
              "circle",
              "triangle",
              "square",
              "plus"
            ]
              .map(app.sample)
              .join("")}

          </div>

          <div class="art-caption">
            Look carefully. Remember. Match.
          </div>

        </div>

      </section>


      <section class="features">

        <div>
          <span class="feature-number">
            01 / STUDY
          </span>

          <h3>
            Study the cards
          </h3>

          <p>
            Remember each shape and where it appears.
          </p>
        </div>


        <div>
          <span class="feature-number">
            02 / MATCH
          </span>

          <h3>
            Find the pairs
          </h3>

          <p>
            Choose cards with the same
            shape and direction.
          </p>
        </div>


        <div>
          <span class="feature-number">
            03 / COMPLETE
          </span>

          <h3>
            Complete the test
          </h3>

          <p>
            Your clinician can review
            the assessment results.
          </p>
        </div>

      </section>
    `;
  }


  function login() {
    main.innerHTML = `
      <section class="panel narrow clinician-box">
        ${app.eyebrow("Clinician portal")}
        <h1>Welcome back</h1>
        <p>Sign in to manage participant sessions and review saved results.</p>
        <form id="login-form">
          <label class="label" for="email">Email address</label>
          <input id="email" type="email" autocomplete="username" required maxlength="150">
          <label class="label" for="password">Password</label>
          <div class="password-wrap">
            <input id="password" type="password" autocomplete="current-password" required>
            <button type="button" id="show-password" class="show-password">Show</button>
          </div>
          <label class="remember"><input id="remember" type="checkbox">Remember me</label>
          <p id="login-error" class="error-message" role="alert"></p>
          <button type="submit" id="login-button" class="primary full">Sign in →</button>
        </form>
        <div class="account-choice">New test giver? <a href="#signup">Create account</a></div>
      </section>`;
    document.querySelector('#show-password').onclick = event => {
      const input = document.querySelector('#password');
      input.type = input.type === 'password' ? 'text' : 'password';
      event.target.textContent = input.type === 'password' ? 'Show' : 'Hide';
    };
    document.querySelector('#login-form').onsubmit = async event => {
      event.preventDefault();
      const button = document.querySelector('#login-button');
      const error = document.querySelector('#login-error');
      button.disabled = true;
      error.textContent = '';
      try {
        const {user} = await app.api('/api/login/', {
          email: document.querySelector('#email').value.trim(),
          password: document.querySelector('#password').value,
          remember: document.querySelector('#remember').checked
        });
        state.clinician = user;
        state.authenticated = true;
        app.go('dashboard');
      } catch (failure) {
        error.textContent = failure.message;
      } finally { button.disabled = false; }
    };
  }

  function signup() {
    main.innerHTML = `
      <section class="panel narrow clinician-box">
        ${app.eyebrow('New test giver')}
        <h1>Create your account</h1>
        <form id="signup-form">
          <label class="label" for="full-name">Full name</label>
          <input id="full-name" autocomplete="name" required maxlength="150">
          <label class="label" for="organization">Organization (optional)</label>
          <input id="organization" autocomplete="organization" maxlength="200">
          <label class="label" for="signup-email">Email address</label>
          <input id="signup-email" type="email" autocomplete="username" required maxlength="150">
          <label class="label" for="signup-password">Password</label>
          <input id="signup-password" type="password" autocomplete="new-password" required minlength="8">
          <p class="small">Use at least 8 characters. Avoid common, entirely numeric, or personal passwords.</p>
          <label class="label" for="confirm-password">Confirm password</label>
          <input id="confirm-password" type="password" autocomplete="new-password" required>
          <p id="signup-error" class="error-message" role="alert"></p>
          <button type="submit" id="create-account" class="primary full">Create account →</button>
        </form>
        <div class="account-choice">Already have an account? <a href="#login">Sign in</a></div>
      </section>`;
    document.querySelector('#signup-form').onsubmit = async event => {
      event.preventDefault();
      const error = document.querySelector('#signup-error');
      const button = document.querySelector('#create-account');
      const password = document.querySelector('#signup-password').value;
      if (password !== document.querySelector('#confirm-password').value) {
        error.textContent = 'Passwords do not match.';
        return;
      }
      error.textContent = '';
      button.disabled = true;
      try {
        const {user} = await app.api('/api/signup/', {
          name: document.querySelector('#full-name').value.trim(),
          email: document.querySelector('#signup-email').value.trim(),
          organization: document.querySelector('#organization').value.trim(), password
        });
        state.clinician = user;
        state.authenticated = true;
        app.go('dashboard');
      } catch (failure) { error.textContent = failure.message; }
      finally { button.disabled = false; }
    };
  }

  function dashboard() {
  if (!state.authenticated) {
    app.go("login");
    return;
  }

  const completed = state.results.length;

  const averageAccuracy = completed
    ? Math.round(
        state.results.reduce(
          (total, result) => total + result.accuracy,
          0
        ) / completed
      )
    : 0;

  const averageTime = completed
    ? (
        state.results.reduce(
          (total, result) => total + result.average,
          0
        ) / completed
      ).toFixed(1)
    : "0.0";


  main.innerHTML = `
    <div class="page-head">

      <div>
        ${app.eyebrow("Clinician workspace")}

        <h1>
          Dashboard
        </h1>

        <p>
          Create patient sessions
          and review assessment activity.
        </p>
      </div>


      <div class="dashboard-buttons">

        <a
          class="button secondary"
          href="#profile"
        >
          Profile
        </a>

        <button
          class="button secondary"
          id="logout"
        >
          Sign out
        </button>

      </div>

    </div>


    <section class="summary-grid">

      <div class="summary-card blue-summary">

        <span>
          Completed Tests
        </span>

        <strong>
          ${completed}
        </strong>

        <small>
          Assessment sessions
        </small>

      </div>


      <div class="summary-card purple-summary">

        <span>
          Average Accuracy
        </span>

        <strong>
          ${averageAccuracy}%
        </strong>

        <small>
          Completed tests
        </small>

      </div>


      <div class="summary-card teal-summary">

        <span>
          Average Response
        </span>

        <strong>
          ${averageTime}s
        </strong>

        <small>
          Selection time
        </small>

      </div>


      <div class="summary-card gold-summary">

        <span>
          Pending Sessions
        </span>

        <strong id="pending-count">
          ${state.pendingSessions.filter(session => session.status === "Pending").length}
        </strong>

        <small>
          Waiting for completion
        </small>

      </div>

    </section>


    <section class="panel quick-actions-panel">

      ${app.eyebrow("Shortcuts")}

      <h2>
        Quick Actions
      </h2>

      <p>
        Quickly create a session,
        preview the test,
        or review completed results.
      </p>

      <div class="quick-actions">

        <button
          type="button"
          class="quick-action"
          id="quick-new-session"
        >
          + New Patient Session
        </button>

        <button
          type="button"
          class="quick-action"
          id="quick-preview"
        >
          ▶ Preview Patient Test
        </button>

        <button
          type="button"
          class="quick-action"
          id="quick-results"
        >
          ▦ Review Results
        </button>

      </div>

    </section>


    <div class="dashboard-grid">

      <section
        class="panel"
        id="new-session-panel"
      >

        ${app.eyebrow("New session")}

        <h2>
          Generate Patient Link
        </h2>

        <p>
          Select the test settings
          and generate a patient link.
        </p>


        <label
          class="label"
          for="test-language"
        >
          Test Language
        </label>

        <select id="test-language">

          <option>
            English
          </option>



        </select>


        <label
          class="label"
          for="audio-voice"
        >
          Audio Voice
        </label>

        <select id="audio-voice">



          <option>
            No Voice
          </option>

        </select>


        <label
          class="label"
          for="participant-id"
        >
          Participant ID
        </label>

        <input
          id="participant-id"
          type="text" maxlength="64" placeholder="e.g. P001" required
          pattern="[A-Za-z0-9_-]+"
        >


        <div class="actions">

          <button
            class="primary"
            id="generate"
          >
            Generate Link →
          </button>

        </div>


        <div
          class="link-output hidden"
          id="link-output"
        >

          <label
            class="label"
            for="session-id"
          >
            Session ID
          </label>

          <input
            id="session-id"
            readonly
          >


          <label
            class="label"
            for="patient-link"
          >
            Patient Access Link
          </label>

          <input
            id="patient-link"
            readonly
          >


          <div class="actions">

            <button
              id="copy"
              class="button secondary"
            >
              Copy Link
            </button>


            <a id="open-test" class="button secondary" target="_blank" rel="noopener noreferrer">Open Test</a>

          </div>


          <p
            id="copy-status"
            class="status"
          ></p>

        </div>

      </section>


      <section class="panel">

        ${app.eyebrow("Activity")}

        <h2>
          Pending Sessions
        </h2>

        <p class="small">Links expire after seven days and accept one completed assessment.</p>
        <div id="pending-list"></div>


        <h2 class="results-heading">
          Completed Assessments
        </h2>


        <input
          id="result-search"
          type="search"
          placeholder="Search Test..."
          aria-label="Search completed assessments"
        >


        <a class="button secondary" href="/api/results/export/">Export all results CSV ↓</a>
        <div id="result-list"></div>

      </section>

    </div>
  `;


  const pendingList =
    document.querySelector(
      "#pending-list"
    );

  const resultList =
    document.querySelector(
      "#result-list"
    );


  function renderPending() {
    if (!state.pendingSessions.length) {
      pendingList.innerHTML = `
        <div class="empty">
          No pending sessions yet.
        </div>
      `;

      return;
    }


    pendingList.innerHTML =
      state.pendingSessions
        .map(
          (session) => `

            <div class="simple-session-row">

              <div>

                <strong>
                  ${app.escapeHTML(session.participantId)}
                </strong>

                <p>
                  ${session.language}
                  ·
                  ${session.voice}
                </p>

                <small>
                  ${
                    session.created
                      ? new Date(
                          session.created
                        ).toLocaleString()
                      : ""
                  }
                </small>

              </div>


              <div>
                <span class="pending-badge">${session.status}</span>
                <p class="small">Expires: ${new Date(session.expires).toLocaleString()}</p>
                ${session.status === 'Pending' ? `<a class="button secondary" href="${app.escapeHTML(session.url)}" target="_blank" rel="noopener noreferrer">Open test link</a>` : ''}
              </div>

            </div>

          `
        )
        .join("");
  }


  function renderResults(searchValue = "") {
    const search =
      searchValue
        .trim()
        .toLowerCase();


    const filteredResults =
      state.results
        .map(
          (result, index) => ({
            result,
            index
          })
        )
        .filter(
          ({ result, index }) => {

            const name =
              result.sessionId ||
              `Test ${index + 1}`;

            return (name + ' ' + result.participantId)
              .toLowerCase()
              .includes(search);
          }
        );


    if (!filteredResults.length) {
      resultList.innerHTML = `
        <div class="empty">

          ${
            state.results.length
              ? "No matching assessments found."
              : "No completed assessments yet."
          }

        </div>
      `;

      return;
    }


    resultList.innerHTML = "";


    filteredResults.forEach(
      ({ result, index }) => {

        const row =
          document.createElement(
            "div"
          );


        row.className =
          "result-row";


        row.innerHTML = `

          <div>

            <strong>
              ${
                app.escapeHTML(result.participantId) || `Test ${index + 1}`
              }
            </strong>


            <p>
              Accuracy:
              ${result.accuracy}%

              ·

              ${result.matches}
              pairs matched
            </p>


            <p class="small">
              Mistakes:
              ${result.mistakes}

              ·

              Average response:
              ${Number(result.average).toFixed(1)}s
            </p>

          </div>


          ${app.button(
            "View",
            `results/${result.id}`,
            true
          )}

        `;


        resultList.append(
          row
        );
      }
    );
  }


  renderPending();
  renderResults();


  document.querySelector(
    "#result-search"
  ).addEventListener(
    "input",
    (event) => {

      renderResults(
        event.target.value
      );

    }
  );


  document.querySelector(
    "#quick-new-session"
  ).onclick = () => {

    document.querySelector(
      "#new-session-panel"
    ).scrollIntoView({
      behavior: "smooth"
    });

  };


  document.querySelector(
    "#quick-preview"
  ).onclick = () => {

    window.location.assign('/#instructions');

  };


  document.querySelector(
    "#quick-results"
  ).onclick = () => {

    document.querySelector(
      "#result-search"
    ).scrollIntoView({
      behavior: "smooth"
    });

  };


  document.querySelector('#logout').onclick = async () => {
    try {
      await app.api('/api/logout/', {});
      state.authenticated = false;
      state.clinician = {name: '', email: '', organization: ''};
      state.results = [];
      state.pendingSessions = [];
      app.go('home');
    } catch (error) { window.alert(error.message); }
  };

  const generate = document.querySelector('#generate');
  const generationStatus = document.createElement('p');
  generationStatus.className = 'status';
  generationStatus.setAttribute('role', 'status');
  generate.parentElement.after(generationStatus);
  generate.onclick = async () => {
    const participant = document.querySelector('#participant-id');
    if (!participant.reportValidity()) return;
    generate.disabled = true;
    generationStatus.textContent = '';
    try {
      const invitation = await app.api('/api/invitations/', {
        participantId: participant.value.trim(),
        language: document.querySelector('#test-language').value,
        voice: document.querySelector('#audio-voice').value
      });
      state.pendingSessions.unshift(invitation);
      document.querySelector('#session-id').value = invitation.id;
      document.querySelector('#patient-link').value = invitation.url;
      document.querySelector('#open-test').href = invitation.url;
      document.querySelector('#link-output').classList.remove('hidden');
      document.querySelector('#pending-count').textContent = state.pendingSessions.filter(session => session.status === 'Pending').length;
      generationStatus.textContent = `Link created for ${invitation.participantId}. Expires ${new Date(invitation.expires).toLocaleString()}.`;
      renderPending();
    } catch (error) { generationStatus.textContent = error.message; }
    finally { generate.disabled = false; }
  };

  document.querySelector(
    "#copy"
  ).onclick = async () => {

    const field =
      document.querySelector(
        "#patient-link"
      );


    try {

      await navigator.clipboard.writeText(
        field.value
      );


      document.querySelector(
        "#copy-status"
      ).textContent =
        "Patient link copied.";

    } catch {

      field.select();


      document.querySelector(
        "#copy-status"
      ).textContent =
        "Select and copy the link.";

    }
  };
}

  function profile() {
    if (!state.authenticated) { app.go('login'); return; }
    const clinician = state.clinician;
    main.innerHTML = `
      <section class="panel narrow profile-page">
        ${app.eyebrow('Test giver profile')}
        <h1>Profile</h1>
        <form id="profile-form">
          <label class="label" for="profile-name">Full name</label>
          <input id="profile-name" required maxlength="150" value="${app.escapeHTML(clinician.name)}">
          <label class="label" for="profile-org">Organization</label>
          <input id="profile-org" maxlength="200" value="${app.escapeHTML(clinician.organization)}">
          <label class="label" for="profile-email">Email address</label>
          <input id="profile-email" type="email" required maxlength="150" value="${app.escapeHTML(clinician.email)}">
          <div class="actions">
            <button class="primary" id="save-profile">Save changes</button>
            ${app.button('Dashboard', 'dashboard', true)}
          </div>
          <p id="profile-status" class="status" role="status"></p>
        </form>
      </section>`;
    document.querySelector('#profile-form').onsubmit = async event => {
      event.preventDefault();
      const status = document.querySelector('#profile-status');
      const button = document.querySelector('#save-profile');
      button.disabled = true;
      try {
        const {user} = await app.api('/api/profile/', {
          name: document.querySelector('#profile-name').value.trim(),
          organization: document.querySelector('#profile-org').value.trim(),
          email: document.querySelector('#profile-email').value.trim()
        });
        state.clinician = user;
        status.textContent = 'Profile saved.';
      } catch (error) { status.textContent = error.message; }
      finally { button.disabled = false; }
    };
  }

  function about() {
    main.innerHTML = `
      <section class="about-page">

        <div class="about-intro">

          ${app.eyebrow(
            "About the assessment"
          )}

          <h1>
            Look. Remember. Match.
          </h1>

          <p>
            The Visuospatial Card Matching Test
            is an interactive task designed to
            measure visual memory and matching
            performance.
          </p>

          ${app.button(
            "Start Test →",
            "instructions"
          )}

        </div>


        <div class="about-grid">

          <article class="about-card">

            <span class="about-icon">
              ◉
            </span>

            <h3>
              Visual Memory
            </h3>

            <p>
              Patients briefly study shapes
              and remember where they appear.
            </p>

          </article>


          <article class="about-card">

            <span class="about-icon">
              ◇
            </span>

            <h3>
              Card Matching
            </h3>

            <p>
              Cards are hidden and patients
              identify matching pairs.
            </p>

          </article>


          <article class="about-card">

            <span class="about-icon">
              ✓
            </span>

            <h3>
              Performance Results
            </h3>

            <p>
              The assessment records accuracy,
              mistakes, and response time.
            </p>

          </article>

        </div>


        <section class="panel about-details">

          ${app.eyebrow(
            "How it works"
          )}

          <h2>
            A simple three-step assessment
          </h2>


          <div class="about-steps">

            <div>

              <strong>
                01
              </strong>

              <h3>
                Study
              </h3>

              <p>
                View the cards and remember
                their positions.
              </p>

            </div>


            <div>

              <strong>
                02
              </strong>

              <h3>
                Match
              </h3>

              <p>
                Reveal cards and find
                identical pairs.
              </p>

            </div>


            <div>

              <strong>
                03
              </strong>

              <h3>
                Complete
              </h3>

              <p>
                The clinician can review
                the completed result.
              </p>

            </div>

          </div>

        </section>

      </section>
    `;
  }


  function instructions() {
    main.innerHTML = `
      <section class="panel narrow instructions-page">

        ${app.eyebrow(
          "Patient test · Getting started"
        )}

        <h1>
          A moment to focus
        </h1>

        <p>
          Before you begin, here's how
          the card matching test works.
        </p>


        <ol class="steps">

          <li>
            You will see cards for five seconds.
            Remember each shape and its direction.
          </li>

          <li>
            The cards will flip over.
            Select two cards to reveal them.
          </li>

          <li>
            Match identical shapes and directions
            until all pairs are found.
          </li>

        </ol>


        <div class="example-pair">

          ${app.sample(
            "circle"
          )}

          ${app.sample(
            "circle"
          )}

        </div>


        ${app.button(
          "Start Practice →",
          "practice"
        )}

      </section>
    `;
  }


  function complete(practice) {
    main.innerHTML = `
      <section class="panel narrow completion">
        <div class="check">✓</div>
        ${app.eyebrow(practice ? 'Ready for the next step' : 'All done')}
        <h1>${practice ? 'Practice completed' : 'Test completed'}</h1>
        <p>${practice ? "When you're ready, begin the assessment." : 'Thank you for taking the assessment.'}</p>
        <p id="save-status" role="status"></p>
        <button id="retry-save" class="primary hidden">Retry saving</button>
        ${practice ? app.button('Begin Assessment →', 'study') : app.button('Done', 'home')}
      </section>`;
    if (practice) return;
    const status = document.querySelector('#save-status');
    const retry = document.querySelector('#retry-save');
    const submission = state.pendingSubmission;
    if (!submission) {
      status.textContent = state.lastSaved ? 'Your result has been saved.' : 'Preview only. No result was submitted.';
      return;
    }
    const save = async () => {
      retry.classList.add('hidden');
      status.textContent = 'Saving your result…';
      try {
        await app.api(`/api/invitations/${encodeURIComponent(submission.token)}/complete/`, {selections: submission.selections});
        state.pendingSubmission = null;
        state.lastSaved = true;
        status.textContent = 'Your result has been saved. You may close this page.';
      } catch (error) {
        status.textContent = `Your result has not been saved: ${error.message} Keep this page open and retry.`;
        retry.classList.remove('hidden');
      }
    };
    retry.onclick = save;
    save();
  }

  function showResult(resultId) {
    if (!state.authenticated) {

      app.go(
        "login"
      );

      return;
    }


    const result =
      state.results.find(result => String(result.id) === resultId);


    if (!result) {

      main.innerHTML = `
        <section class="panel narrow">

          <h1>
            No result available
          </h1>

          <p>
            Complete an assessment first.
          </p>

          ${app.button(
            "Back to dashboard",
            "dashboard"
          )}

        </section>
      `;

      return;
    }


    main.innerHTML = `
      <section class="panel narrow">

        ${app.eyebrow(
          `Completed assessment · ${app.escapeHTML(result.participantId)}`
        )}

        <h1>
          Assessment results
        </h1>


        <div class="metrics">

          <div class="result-row">

            <span>
              Correct matches
            </span>

            <strong>
              ${result.matches} / 3
            </strong>

          </div>


          <div class="result-row">

            <span>
              Mistakes
            </span>

            <strong>
              ${result.mistakes}
            </strong>

          </div>


          <div class="result-row">

            <span>
              Accuracy
            </span>

            <strong>
              ${result.accuracy}%
            </strong>

          </div>


          <div class="result-row">

            <span>
              Average time
            </span>

            <strong>
              ${result.average.toFixed(1)} sec
            </strong>

          </div>

        </div>


        <div class="actions">

          <button
            class="primary"
            id="export"
          >
            Export CSV ↓
          </button>


          ${app.button(
            "Dashboard",
            "dashboard",
            true
          )}

        </div>

      </section>
    `;


    document.querySelector('#export').onclick = () => {
      window.location.assign(`/api/results/${result.id}/export/`);
    };
  }

  function updateNavigation() {
    const loginNav =
      document.querySelector(
        "#login-nav"
      );

    const profileNav =
      document.querySelector(
        "#profile-nav"
      );


    if (
      !loginNav ||
      !profileNav
    ) {
      return;
    }


    if (state.authenticated) {

      loginNav.classList.add(
        "hidden"
      );

      profileNav.classList.remove(
        "hidden"
      );

    } else {

      loginNav.classList.remove(
        "hidden"
      );

      profileNav.classList.add(
        "hidden"
      );
    }
  }


  let routeVersion = 0;
  async function route() {
    const version = ++routeVersion;
    state.cleanup();

    state.cleanup =
      () => {};


    const hash =
      location.hash.slice(1) ||
      (location.pathname === '/dashboard/' ? 'dashboard' : state.invitationToken ? 'instructions' : 'home');

    if (['dashboard', 'profile'].includes(hash) || hash.startsWith('results/')) {
      main.textContent = 'Loading your workspace…';
      try {
        const {user} = await app.api('/api/session/');
        if (version !== routeVersion) return;
        state.authenticated = Boolean(user);
        if (!user) { state.results = []; state.pendingSessions = []; app.go('login'); return; }
        state.clinician = user;
        const data = await app.api('/api/dashboard/');
        if (version !== routeVersion) return;
        state.results = data.results;
        state.pendingSessions = data.invitations;
      } catch (error) {
        if (version !== routeVersion) return;
        if (error.status === 401) { state.authenticated = false; app.go('login'); return; }
        main.textContent = error.message;
        return;
      }
    }

    updateNavigation();


    document
      .querySelectorAll(
        "nav a"
      )
      .forEach(
        (anchor) => {

          const active =
            anchor.hash ===
            `#${hash}`;


          anchor.classList.toggle(
            "active",
            active
          );


          if (active) {

            anchor.setAttribute(
              "aria-current",
              "page"
            );

          } else {

            anchor.removeAttribute(
              "aria-current"
            );

          }
        }
      );


    if (hash === "home") {

      home();

    } else if (hash === "about") {

      about();

    } else if (hash === "info") {

      about();

    } else if (hash === "login") {

      login();

    } else if (hash === "signup") {

      signup();

    } else if (hash === "dashboard") {

      dashboard();

    } else if (hash === "profile") {

      profile();

    } else if (hash === "instructions") {

      instructions();

    } else if (hash === "practice") {

      app.game(true);

    } else if (hash === "study") {

      app.game(false);

    } else if (
      hash === "practice-complete"
    ) {

      complete(true);

    } else if (hash === "complete") {

      complete(false);

    } else if (
      hash.startsWith(
        "results/"
      )
    ) {

      showResult(
        hash.split("/")[1]
      );

    } else {

      home();
    }


    updateNavigation();


    main.focus({
      preventScroll: true
    });


    window.scrollTo(
      0,
      0
    );
  }


  app.views = {
    home,
    about,
    login,
    signup,
    dashboard,
    profile,
    instructions,
    complete,
    showResult,
    route
  };

})();
