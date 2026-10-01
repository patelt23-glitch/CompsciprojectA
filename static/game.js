(function () {
  const app = window.VisuospatialApp;

  if (!app) {
    return;
  }

  function game(practice) {
    const main = app.main;
    const state = app.state;
    const symbols = app.symbols;

    let alive = true;
    let timers = [];
    let first = null;
    let locked = true;
    let matched = 0;
    let mistakes = 0;
    let attempts = 0;
    let last = 0;
    let times = [];

    state.cleanup = () => {
      alive = false;
      timers.forEach(clearTimeout);
    };

    const delay = (fn, ms) => {
      timers.push(
        setTimeout(() => {
          if (alive) fn();
        }, ms)
      );
    };

    const shapes = practice ? ["circle", "triangle", "square"] : ["up", "right", "triangle"];
    const deck = [...shapes, ...shapes];

    for (let i = deck.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }

    main.innerHTML = `
      <section class="test">
        <div class="test-top">
          ${app.eyebrow(practice ? "Practice round" : "Patient test")}
          <span class="pill timer" id="timer">5 sec</span>
        </div>

        <h1 id="phase">Study the cards</h1>
        <p id="instruction">Remember each shape and where it appears.</p>

        <div class="board" aria-label="Matching cards"></div>

        <div class="test-bottom">
          <span id="progress">0 of 3 pairs matched</span>
          <span>${practice ? "Practice · Not scored" : "Assessment"}</span>
        </div>

        <div class="status" id="status" role="status" aria-live="polite">
          The cards will turn over in five seconds.
        </div>
      </section>
    `;

    const board = document.querySelector(".board");
    const cards = deck.map((shape, index) => {
      const card = document.createElement("button");
      card.className = "card revealed";
      card.innerHTML = symbols[shape];
      card.disabled = true;
      card.setAttribute("aria-label", `Card ${index + 1}: ${shape}`);
      board.append(card);
      return card;
    });

    function hide(index) {
      cards[index].className = "card";
      cards[index].textContent = "?";
      cards[index].setAttribute("aria-label", `Card ${index + 1}: hidden`);
    }

    function reveal(index) {
      cards[index].className = "card revealed";
      cards[index].innerHTML = symbols[deck[index]];
      cards[index].setAttribute("aria-label", `Card ${index + 1}: ${deck[index]}`);
    }

    for (let s = 1; s <= 5; s++) {
      delay(() => {
        document.querySelector("#timer").textContent = `${5 - s} sec`;

        if (s === 5) {
          cards.forEach((card, cardIndex) => {
            hide(cardIndex);
            card.disabled = false;
          });

          locked = false;
          last = performance.now();

          document.querySelector("#timer").textContent = "Find 3 pairs";
          document.querySelector("#timer").classList.remove("timer");
          document.querySelector("#phase").textContent = "Match the cards";
          document.querySelector("#instruction").textContent =
            "Choose two cards that match in shape and direction.";
          document.querySelector("#status").textContent = "Select your first card.";
        }
      }, s * 1000);
    }

    cards.forEach((card, index) => {
      card.onclick = () => {
        if (locked || card.disabled || first === index) {
          return;
        }

        reveal(index);

        if (first === null) {
          first = index;
          document.querySelector("#status").textContent = "Now choose a matching card.";
          return;
        }

        locked = true;
        attempts += 1;
        times.push((performance.now() - last) / 1000);

        const previous = first;
        first = null;

        if (deck[previous] === deck[index]) {
          matched += 1;

          [previous, index].forEach((cardIndex) => {
            cards[cardIndex].classList.add("matched");
            cards[cardIndex].disabled = true;
            cards[cardIndex].setAttribute(
              "aria-label",
              `Card ${cardIndex + 1}: ${deck[cardIndex]}, matched`
            );
          });

          document.querySelector("#progress").textContent = `${matched} of 3 pairs matched`;
          document.querySelector("#status").textContent = "A match. Nicely done!";
          locked = false;
          last = performance.now();

          if (matched === 3) {
            locked = true;
            delay(() => {
              if (practice) {
                app.go("practice-complete");
              } else {
                state.results.push({
                  date: new Date(),
                  matches: matched,
                  mistakes,
                  attempts,
                  accuracy: Math.round((matched / attempts) * 100),
                  average: times.reduce((sum, value) => sum + value, 0) / times.length
                });
                app.go("complete");
              }
            }, 700);
          }
        } else {
          mistakes += 1;
          document.querySelector("#status").textContent =
            "Different shapes or directions. Try another pair.";

          delay(() => {
            hide(previous);
            hide(index);
            locked = false;
            last = performance.now();
          }, 1000);
        }
      };
    });
  }

  app.game = game;
})();
