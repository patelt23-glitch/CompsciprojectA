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
              !state.previewAccess
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

        <h1>
          Welcome back
        </h1>

        <p>
          Sign in to manage patient sessions
          and review completed results.
        </p>


        <label
          class="label"
          for="email"
        >
          Email address
        </label>

        <input
          id="email"
          type="email"
          placeholder="doctor@clinic.org"
        >


        <label
          class="label"
          for="password"
        >
          Password
        </label>

        <div class="password-wrap">

          <input
            id="password"
            type="password"
            placeholder="Enter your password"
          >

          <button
            type="button"
            id="show-password"
            class="show-password"
          >
            Show
          </button>

        </div>


        <div class="login-row">

          <label class="remember">

            <input type="checkbox">

            Remember me

          </label>


          <button
            type="button"
            id="forgot-password"
            class="text-link"
          >
            Forgot password?
          </button>

        </div>


        <p
          id="login-error"
          class="error-message"
        ></p>


        <button
          id="login-button"
          class="primary full"
        >
          Sign in →
        </button>


        <div class="account-choice">

          New clinician?

          <a href="#signup">
            Create account
          </a>

        </div>

      </section>
    `;


    const password =
      document.querySelector("#password");

    const showButton =
      document.querySelector("#show-password");


    showButton.onclick = () => {

      if (password.type === "password") {

        password.type = "text";

        showButton.textContent =
          "Hide";

      } else {

        password.type =
          "password";

        showButton.textContent =
          "Show";
      }
    };


    document.querySelector(
      "#forgot-password"
    ).onclick = () => {

      alert(
        "Password recovery will be added with the backend."
      );
    };


    document.querySelector(
      "#login-button"
    ).onclick = () => {

      const email =
        document.querySelector("#email")
          .value
          .trim();

      const error =
        document.querySelector(
          "#login-error"
        );


      if (
        !email ||
        password.value.length < 8
      ) {

        error.textContent =
          "Enter a valid email and a password with at least 8 characters.";

        return;
      }


      state.clinician.email =
        email;


      if (!state.clinician.name) {

        state.clinician.name =
          "Clinician";
      }


      state.previewAccess =
        true;


      app.go(
        "dashboard"
      );
    };
  }


  function signup() {
    main.innerHTML = `
      <section class="panel narrow clinician-box">

        ${app.eyebrow("New clinician")}

        <h1>
          Create your account
        </h1>


        <label
          class="label"
          for="full-name"
        >
          Full name
        </label>

        <input
          id="full-name"
          type="text"
          placeholder="Dr. Jane Doe"
        >


        <label
          class="label"
          for="organization"
        >
          Organization
        </label>

        <input
          id="organization"
          type="text"
          placeholder="Clinic or research lab"
        >


        <label
          class="label"
          for="signup-email"
        >
          Work email
        </label>

        <input
          id="signup-email"
          type="email"
          placeholder="you@clinic.org"
        >


        <label
          class="label"
          for="signup-password"
        >
          Password
        </label>

        <input
          id="signup-password"
          type="password"
          placeholder="At least 8 characters"
        >


        <label
          class="label"
          for="confirm-password"
        >
          Confirm password
        </label>

        <input
          id="confirm-password"
          type="password"
          placeholder="Re-enter password"
        >


        <p
          id="signup-error"
          class="error-message"
        ></p>


        <button
          id="create-account"
          class="primary full"
        >
          Create account →
        </button>


        <div class="account-choice">

          Already have an account?

          <a href="#login">
            Sign in
          </a>

        </div>

      </section>
    `;


    document.querySelector(
      "#create-account"
    ).onclick = () => {

      const name =
        document.querySelector(
          "#full-name"
        ).value.trim();

      const organization =
        document.querySelector(
          "#organization"
        ).value.trim();

      const email =
        document.querySelector(
          "#signup-email"
        ).value.trim();

      const password =
        document.querySelector(
          "#signup-password"
        ).value;

      const confirm =
        document.querySelector(
          "#confirm-password"
        ).value;

      const error =
        document.querySelector(
          "#signup-error"
        );


      if (!name || !email) {

        error.textContent =
          "Please complete the required fields.";

        return;
      }


      if (password.length < 8) {

        error.textContent =
          "Password must be at least 8 characters.";

        return;
      }


      if (password !== confirm) {

        error.textContent =
          "Passwords do not match.";

        return;
      }


      state.clinician = {
        name,
        organization,
        email
      };


      state.previewAccess =
        true;


      app.go(
        "dashboard"
      );
    };
  }


 function dashboard() {
  if (!state.previewAccess) {
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
          ${state.pendingSessions.length}
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

          <option>
            Spanish
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
            Female
          </option>

          <option>
            Male
          </option>

          <option>
            No Voice
          </option>

        </select>


        <label
          class="label"
          for="patient-dob"
        >
          Patient Date of Birth
        </label>

        <input
          id="patient-dob"
          type="date"
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


            ${app.button(
              "Open Test",
              "instructions",
              true
            )}

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
                  ${session.id}
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


              <span class="pending-badge">
                ${session.status || "Pending"}
              </span>

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

            return name
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
                result.sessionId ||
                `Test ${index + 1}`
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
            `results/${index}`,
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

    app.go(
      "instructions"
    );

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


  document.querySelector(
    "#logout"
  ).onclick = () => {

    state.previewAccess =
      false;

    app.go(
      "home"
    );

  };


  document.querySelector(
    "#generate"
  ).onclick = () => {

    const language =
      document.querySelector(
        "#test-language"
      ).value;


    const voice =
      document.querySelector(
        "#audio-voice"
      ).value;


    const dob =
      document.querySelector(
        "#patient-dob"
      ).value;


    const number =
      Math.floor(
        1000 +
        Math.random() * 9000
      );


    const sessionId =
      `VSA-${number}`;


    state.pendingSessions.unshift({
      id: sessionId,
      language,
      voice,
      dob,
      created:
        new Date().toISOString(),
      status:
        "Pending"
    });


    document.querySelector(
      "#session-id"
    ).value =
      sessionId;


    document.querySelector(
      "#patient-link"
    ).value =
      location.href.split("#")[0] +
      "#instructions";


    document
      .querySelector(
        "#link-output"
      )
      .classList.remove(
        "hidden"
      );


    document.querySelector(
      "#pending-count"
    ).textContent =
      state.pendingSessions.length;


    renderPending();
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
    if (!state.previewAccess) {

      app.go(
        "login"
      );

      return;
    }


    main.innerHTML = `
      <section class="panel profile-page">

        ${app.eyebrow(
          "Clinician profile"
        )}


        <div class="profile-heading">

          <div class="profile-circle">

            ${
              state.clinician.name
                ? state.clinician.name
                    .charAt(0)
                    .toUpperCase()
                : "C"
            }

          </div>


          <div>

            <h1>
              Profile
            </h1>

            <p>
              Update your basic clinician information.
            </p>

          </div>

        </div>


        <label
          class="label"
          for="profile-name"
        >
          Full name
        </label>

        <input
          id="profile-name"
          type="text"
          value="${state.clinician.name || ""}"
          placeholder="Dr. Jane Doe"
        >


        <label
          class="label"
          for="profile-org"
        >
          Organization
        </label>

        <input
          id="profile-org"
          type="text"
          value="${state.clinician.organization || ""}"
          placeholder="Clinic or research lab"
        >


        <label
          class="label"
          for="profile-email"
        >
          Email address
        </label>

        <input
          id="profile-email"
          type="email"
          value="${state.clinician.email || ""}"
          placeholder="doctor@clinic.org"
        >


        <div class="actions">

          <button
            class="primary"
            id="save-profile"
          >
            Save Changes
          </button>


          ${app.button(
            "Back to Dashboard",
            "dashboard",
            true
          )}

        </div>


        <p
          id="profile-status"
          class="status"
        ></p>

      </section>
    `;


    document.querySelector(
      "#save-profile"
    ).onclick = () => {

      state.clinician.name =
        document.querySelector(
          "#profile-name"
        ).value.trim();


      state.clinician.organization =
        document.querySelector(
          "#profile-org"
        ).value.trim();


      state.clinician.email =
        document.querySelector(
          "#profile-email"
        ).value.trim();


      document.querySelector(
        "#profile-status"
      ).textContent =
        "Profile updated for this session.";
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

        <div class="check">
          ✓
        </div>


        ${app.eyebrow(
          practice
            ? "Ready for the next step"
            : "All done"
        )}


        <h1>

          ${
            practice
              ? "Practice completed"
              : "Test completed"
          }

        </h1>


        <p>

          ${
            practice

              ? "You know how it works. When you're ready, begin the assessment."

              : "Thank you for taking the assessment."
          }

        </p>


        ${
          practice

            ? app.button(
                "Begin Assessment →",
                "study"
              )

            : app.button(
                "Done",
                "home"
              )
        }

      </section>
    `;
  }


  function showResult(index) {
    if (!state.previewAccess) {

      app.go(
        "login"
      );

      return;
    }


    const result =
      state.results[index];


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
          `Completed assessment · Test ${
            Number(index) + 1
          }`
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


    document.querySelector(
      "#export"
    ).onclick = () => {

      const csv =
        `test,correct_matches,mistakes,accuracy_percent,average_seconds\n${
          Number(index) + 1
        },${result.matches},${result.mistakes},${result.accuracy},${result.average.toFixed(
          2
        )}\n`;


      const url =
        URL.createObjectURL(

          new Blob(
            [csv],
            {
              type:
                "text/csv;charset=utf-8"
            }
          )

        );


      const link =
        document.createElement(
          "a"
        );


      link.href =
        url;


      link.download =
        `assessment-${
          Number(index) + 1
        }.csv`;


      link.click();


      setTimeout(
        () =>
          URL.revokeObjectURL(
            url
          ),
        1000
      );
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


    if (state.previewAccess) {

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


  function route() {
    state.cleanup();

    state.cleanup =
      () => {};


    const hash =
      location.hash.slice(1) ||
      "home";


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


  app.init = function () {

    window.addEventListener(
      "hashchange",
      route
    );

    route();
  };

})();