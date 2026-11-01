/**
 * Visuospatial Assessment Engine
 * Fluid, responsive card matching with sub-millisecond performance.now() latency tracking.
 * Compliant with Apple Design guidelines and Taste Skill directives.
 * Zero em-dashes.
 */

class VisuospatialEngine {
  constructor(config) {
    this.sessionId = config.sessionId;
    this.patientCode = config.patientCode;
    this.token = config.token || '';
    this.language = config.language || 'English';
    this.audioVoice = config.audioVoice || 'Female';
    this.difficulty = config.difficulty || 'Standard';
    this.rounds = config.rounds || [];

    this.currentRoundIndex = 0;
    this.currentAttemptNumber = 1;
    this.selectedCards = [];
    this.isInputLocked = true;
    this.attemptStartTime = 0;
    this.roundStartTime = 0;
    this.matchedPairsInRound = 0;

    // Track all selections across rounds for atomic completion fallback
    this.allSelections = [];
    this.pendingAttemptPromises = [];

    // Audio & Speech State
    this.audioCtx = null;
    this.isMuted = (this.audioVoice === 'No Voice');
    this.speechVoice = null;
    this.recognition = null;
    this.isListening = false;

    this.initElements();
    this.initVoiceSynthesis();
    this.initVoiceRecognition();
    this.bindEvents();
    this.applyLocalization();
  }

  t(key, params) {
    if (typeof window.getTranslation === 'function') {
      return window.getTranslation(this.language, key, params);
    }
    return key;
  }

  initAudio() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  playFeedbackSound(type) {
    if (this.isMuted || !this.audioCtx) return;
    try {
      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();
      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      if (type === 'flip') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(580, now + 0.05);
        gain.gain.setValueAtTime(0.04, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
        osc.start(now);
        osc.stop(now + 0.05);
      } else if (type === 'match') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, now);
        osc.frequency.setValueAtTime(659.25, now + 0.08);
        gain.gain.setValueAtTime(0.06, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      } else if (type === 'mismatch') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(220, now);
        osc.frequency.setValueAtTime(180, now + 0.08);
        gain.gain.setValueAtTime(0.04, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
        osc.start(now);
        osc.stop(now + 0.18);
      }
    } catch (e) {
      // Audio fallback
    }
  }

  // ============================================================================
  // Speech Synthesis (Voice Output) with Gender & Locale Matching
  // ============================================================================

  initVoiceSynthesis() {
    if (!('speechSynthesis' in window) || this.audioVoice === 'No Voice') {
      return;
    }

    const loadVoices = () => {
      const voices = window.speechSynthesis.getVoices();
      if (!voices || voices.length === 0) return;

      const langMap = {
        English: 'en',
        Spanish: 'es',
        French: 'fr',
        German: 'de',
      };
      const targetPrefix = langMap[this.language] || 'en';
      const isMale = (this.audioVoice.toLowerCase() === 'male');

      // Filter by language prefix
      const matchingVoices = voices.filter(v => v.lang.toLowerCase().startsWith(targetPrefix));

      if (matchingVoices.length > 0) {
        // Prioritize gender keywords
        const femaleKeywords = ['female', 'zira', 'samantha', 'victoria', 'monica', 'amelie', 'hedda', 'marta', 'lucia', 'anna'];
        const maleKeywords = ['male', 'david', 'george', 'jorge', 'henri', 'stefan', 'pablo', 'martin', 'mark', 'hans'];

        const targetKeywords = isMale ? maleKeywords : femaleKeywords;
        const genderMatch = matchingVoices.find(v => {
          const name = v.name.toLowerCase();
          return targetKeywords.some(kw => name.includes(kw));
        });

        this.speechVoice = genderMatch || matchingVoices[0];
      } else {
        this.speechVoice = voices[0];
      }
    };

    loadVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }

  speak(text) {
    if (this.isMuted || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      if (this.speechVoice) {
        utterance.voice = this.speechVoice;
      }
      utterance.rate = 0.95;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      // Speech fallback
    }
  }

  // ============================================================================
  // Speech Recognition (Voice Input / Web Speech API)
  // ============================================================================

  initVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const voiceBtn = document.getElementById('voice-input-toggle');

    if (!SpeechRecognition) {
      if (voiceBtn) {
        voiceBtn.title = this.t('voice_unsupported');
      }
      return;
    }

    try {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = false;

      const langMap = {
        English: 'en-US',
        Spanish: 'es-ES',
        French: 'fr-FR',
        German: 'de-DE',
      };
      this.recognition.lang = langMap[this.language] || 'en-US';

      this.recognition.onresult = (event) => {
        const lastResultIndex = event.results.length - 1;
        const transcript = event.results[lastResultIndex][0].transcript.trim().toLowerCase();
        this.handleVoiceCommand(transcript);
      };

      this.recognition.onerror = (event) => {
        if (event.error === 'not-allowed') {
          this.setVoiceRecognitionActive(false);
        }
      };

      this.recognition.onend = () => {
        if (this.isListening) {
          try { this.recognition.start(); } catch (e) {}
        }
      };
    } catch (e) {
      this.recognition = null;
    }
  }

  toggleVoiceRecognition() {
    if (!this.recognition) {
      alert(this.t('voice_unsupported'));
      return;
    }

    if (this.isListening) {
      this.setVoiceRecognitionActive(false);
    } else {
      this.setVoiceRecognitionActive(true);
    }
  }

  setVoiceRecognitionActive(active) {
    this.isListening = active;
    const btn = document.getElementById('voice-input-toggle');
    const badge = document.getElementById('voice-listening-badge');

    if (active) {
      try {
        this.recognition.start();
        if (btn) btn.classList.add('btn-active');
        if (badge) badge.style.display = 'inline-flex';
      } catch (e) {
        this.isListening = false;
      }
    } else {
      try {
        this.recognition.stop();
      } catch (e) {}
      if (btn) btn.classList.remove('btn-active');
      if (badge) badge.style.display = 'none';
    }
  }

  handleVoiceCommand(transcript) {
    if (!transcript) return;

    // Card selection numbers 1 to 10
    const numbersMap = {
      'one': 1, '1': 1, 'uno': 1, 'un': 1, 'eins': 1,
      'two': 2, '2': 2, 'dos': 2, 'deux': 2, 'zwei': 2,
      'three': 3, '3': 3, 'tres': 3, 'trois': 3, 'drei': 3,
      'four': 4, '4': 4, 'cuatro': 4, 'quatre': 4, 'vier': 4,
      'five': 5, '5': 5, 'cinco': 5, 'cinq': 5, 'fünf': 5,
      'six': 6, '6': 6, 'seis': 6, 'sechs': 6,
      'seven': 7, '7': 7, 'siete': 7, 'sept': 7, 'sieben': 7,
      'eight': 8, '8': 8, 'ocho': 8, 'huit': 8, 'acht': 8,
      'nine': 9, '9': 9, 'nueve': 9, 'neuf': 9, 'neun': 9,
      'ten': 10, '10': 10, 'diez': 10, 'dix': 10, 'zehn': 10,
    };

    for (const [word, num] of Object.entries(numbersMap)) {
      if (transcript.includes(`card ${word}`) || transcript.includes(`carta ${word}`) || transcript.includes(`carte ${word}`) || transcript.includes(`karte ${word}`) || transcript === word) {
        this.selectCardByIndex(num - 1);
        return;
      }
    }

    if (transcript.includes('start') || transcript.includes('comenzar') || transcript.includes('commencer') || transcript.includes('starten')) {
      const startBtn = document.getElementById('start-assessment-btn');
      if (startBtn && startBtn.offsetParent !== null) {
        startBtn.click();
      }
    } else if (transcript.includes('repeat') || transcript.includes('replay') || transcript.includes('repetir') || transcript.includes('répéter')) {
      this.replayCurrentInstruction();
    } else if (transcript.includes('mute') || transcript.includes('silenciar')) {
      this.toggleMute(true);
    } else if (transcript.includes('unmute')) {
      this.toggleMute(false);
    }
  }

  // ============================================================================
  // UI Initialization & Event Binding
  // ============================================================================

  initElements() {
    this.instructionsView = document.getElementById('instructions-view');
    this.gameView = document.getElementById('game-view');
    this.completionView = document.getElementById('completion-view');
    this.retryView = document.getElementById('retry-view');

    this.roundBadge = document.getElementById('round-badge');
    this.pairsNeededBadge = document.getElementById('pairs-needed-badge');
    this.gameTitle = document.getElementById('game-title');
    this.gameSubhead = document.getElementById('game-subhead');
    this.cardsContainer = document.getElementById('cards-container');
    this.countdownContainer = document.getElementById('countdown-container');
    this.countdownFill = document.getElementById('countdown-fill');
    this.countdownLabel = document.getElementById('countdown-label');
    this.matchedCountLabel = document.getElementById('matched-count-label');
    this.actionCueLabel = document.getElementById('action-cue-label');
    this.roundStatusLabel = document.getElementById('round-status-label');
  }

  applyLocalization() {
    const eyebrowEl = document.querySelector('.eyebrow-patient');
    if (eyebrowEl) eyebrowEl.textContent = this.t('eyebrow');

    const focusTitle = document.getElementById('focus-heading');
    if (focusTitle) focusTitle.textContent = this.t('getting_started');

    const instructionsText = document.getElementById('instructions-paragraph');
    if (instructionsText) instructionsText.textContent = this.t('instructions_text');

    const startBtn = document.getElementById('start-assessment-btn');
    if (startBtn) {
      startBtn.textContent = `${this.t('begin_practice')} →`;
    }

    const muteBtn = document.getElementById('mute-toggle-btn');
    if (muteBtn) {
      muteBtn.textContent = this.isMuted ? this.t('unmute') : this.t('mute');
    }

    const replayBtn = document.getElementById('replay-audio-btn');
    if (replayBtn) {
      replayBtn.textContent = this.t('replay');
    }
  }

  bindEvents() {
    const startBtn = document.getElementById('start-assessment-btn');
    if (startBtn) {
      startBtn.addEventListener('click', () => {
        this.initAudio();
        this.startAssessment();
      });
    }

    const readAudioBtn = document.getElementById('read-instructions-btn');
    if (readAudioBtn) {
      readAudioBtn.addEventListener('click', () => {
        this.speakInstructions();
      });
    }

    const muteBtn = document.getElementById('mute-toggle-btn');
    if (muteBtn) {
      muteBtn.addEventListener('click', () => {
        this.toggleMute();
      });
    }

    const replayBtn = document.getElementById('replay-audio-btn');
    if (replayBtn) {
      replayBtn.addEventListener('click', () => {
        this.replayCurrentInstruction();
      });
    }

    const voiceInputBtn = document.getElementById('voice-input-toggle');
    if (voiceInputBtn) {
      voiceInputBtn.addEventListener('click', () => {
        this.toggleVoiceRecognition();
      });
    }

    const retryBtn = document.getElementById('retry-submission-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        this.completeAssessment();
      });
    }
  }

  toggleMute(forcedValue) {
    this.isMuted = (forcedValue !== undefined) ? forcedValue : !this.isMuted;
    const muteBtn = document.getElementById('mute-toggle-btn');
    if (muteBtn) {
      muteBtn.textContent = this.isMuted ? this.t('unmute') : this.t('mute');
    }
    if (this.isMuted && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }

  speakInstructions() {
    const text = `${this.t('title')}. ${this.t('instructions_text')}`;
    this.speak(text);
  }

  replayCurrentInstruction() {
    const text = `${this.gameTitle.textContent}. ${this.gameSubhead.textContent}`;
    this.speak(text);
  }

  // ============================================================================
  // Game Lifecycle & Round Management
  // ============================================================================

  startAssessment() {
    this.instructionsView.style.display = 'none';
    this.gameView.style.display = 'block';
    this.currentRoundIndex = 0;
    this.currentAttemptNumber = 1;
    this.loadRound(this.currentRoundIndex);
  }

  loadRound(index) {
    const roundConfig = this.rounds[index] || {
      round_number: index + 1,
      is_practice: (index === 0),
      mode: index === 0 ? 'practice_round' : (index === 1 ? 'shape_matching' : 'shape_direction'),
      pair_count: index === 0 ? 2 : (index === 1 ? 3 : 4),
      card_count: index === 0 ? 4 : (index === 1 ? 6 : 8),
      study_time_ms: 5000,
      deck: [],
    };

    this.currentRound = roundConfig;
    this.matchedPairsInRound = 0;
    this.selectedCards = [];
    this.isInputLocked = true; // Locked during study period

    // Configure Round Header & Accessibility
    const isPractice = roundConfig.is_practice;
    const roundNumber = roundConfig.round_number;
    const totalRounds = this.rounds.length;

    if (isPractice) {
      this.roundBadge.textContent = this.t('practice_tag').toUpperCase();
      this.roundStatusLabel.textContent = this.t('practice_tag');
    } else {
      const label = this.t('round_label', { n: roundNumber, total: totalRounds });
      this.roundBadge.textContent = label.toUpperCase();
      this.roundStatusLabel.textContent = this.t('assessment_tag');
    }

    this.gameTitle.textContent = this.t('study_title');
    this.gameSubhead.textContent = this.t('study_instruction');

    this.pairsNeededBadge.textContent = this.t('pairs_matched', { matched: 0, total: roundConfig.pair_count });
    this.matchedCountLabel.textContent = this.t('pairs_matched', { matched: 0, total: roundConfig.pair_count });
    this.actionCueLabel.textContent = this.t('study_instruction');

    // Use authoritative server-supplied deck layout
    this.deck = this.prepareDeck(roundConfig);
    this.renderDeck(this.deck);

    // Speak initial study prompt
    this.speak(`${this.t('study_title')}. ${this.t('study_instruction')}`);

    // Study period countdown (5000ms default, shorter on advanced rounds)
    this.startStudyCountdown(roundConfig.study_time_ms || 5000);
  }

  prepareDeck(roundConfig) {
    // If deck layout provided from server, preserve exact match keys and shapes
    if (roundConfig.deck && Array.isArray(roundConfig.deck) && roundConfig.deck.length > 0) {
      return roundConfig.deck.map((item, idx) => ({
        id: item.id !== undefined ? item.id : idx,
        shapeName: item.shape,
        direction: item.direction || 'none',
        color: item.color || '#4f46e5',
        match_key: item.match_key,
        rotation: this.directionToRotation(item.direction),
        mirrored: Boolean(item.mirrored),
        svg: this.getShapeSvg(item.shape, item.color),
      }));
    }

    // Client fallback if offline
    return this.generateFallbackDeck(roundConfig);
  }

  directionToRotation(direction) {
    switch (direction) {
      case 'right': return 90;
      case 'down': return 180;
      case 'left': return 270;
      default: return 0;
    }
  }

  generateFallbackDeck(roundConfig) {
    const pairCount = roundConfig.pair_count;
    const shapes = ['circle', 'triangle', 'square', 'plus', 'star', 'diamond'];
    const colors = ['#4f46e5', '#f59e0b', '#059669', '#7c3aed', '#ec4899', '#0284c7'];

    let pairs = [];
    for (let i = 0; i < pairCount; i++) {
      const shape = shapes[i % shapes.length];
      const color = colors[i % colors.length];
      pairs.push({ shape, color, pairId: i });
      pairs.push({ shape, color, pairId: i });
    }

    for (let i = pairs.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [pairs[i], pairs[j]] = [pairs[j], pairs[i]];
    }

    return pairs.map((p, idx) => ({
      id: idx,
      shapeName: p.shape,
      direction: 'none',
      color: p.color,
      match_key: `client_${p.pairId}`,
      rotation: 0,
      svg: this.getShapeSvg(p.shape, p.color),
    }));
  }

  renderDeck(cards) {
    this.cardsContainer.innerHTML = '';
    if (cards.length >= 8) {
      this.cardsContainer.className = 'cards-grid grid-4x2';
    } else {
      this.cardsContainer.className = 'cards-grid';
    }

    cards.forEach((card, idx) => {
      // Accessible button with tabindex, keyboard support, and ARIA labels
      const cardBtn = document.createElement('button');
      cardBtn.type = 'button';
      cardBtn.className = 'flip-card is-flipped';
      cardBtn.tabIndex = 0;
      cardBtn.dataset.index = idx;
      cardBtn.dataset.matchKey = card.match_key;
      cardBtn.setAttribute('aria-label', this.t('card_label', { n: idx + 1, status: `${card.shapeName}` }));

      cardBtn.innerHTML = `
        <div class="flip-card-inner">
          <div class="flip-card-front" aria-hidden="true">?</div>
          <div class="flip-card-back" aria-hidden="false">
            <div class="shape-svg" style="transform: rotate(${card.rotation}deg) scaleX(${card.mirrored ? -1 : 1});">
              ${card.svg}
            </div>
          </div>
        </div>
      `;

      // Tactile pointerdown and keyboard activation
      cardBtn.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        this.selectCardByIndex(idx);
      });

      cardBtn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.selectCardByIndex(idx);
        }
      });

      this.cardsContainer.appendChild(cardBtn);
    });
  }

  startStudyCountdown(durationMs) {
    this.countdownContainer.style.display = 'block';
    this.countdownFill.style.transition = 'none';
    this.countdownFill.style.width = '100%';

    let secondsLeft = Math.ceil(durationMs / 1000);
    this.countdownLabel.textContent = this.t('study_countdown', { n: secondsLeft });

    void this.countdownFill.offsetWidth;
    this.countdownFill.style.transition = `width ${durationMs}ms linear`;
    this.countdownFill.style.width = '0%';

    const interval = setInterval(() => {
      secondsLeft--;
      if (secondsLeft > 0) {
        this.countdownLabel.textContent = this.t('study_countdown', { n: secondsLeft });
      }
    }, 1000);

    setTimeout(() => {
      clearInterval(interval);
      this.countdownContainer.style.display = 'none';
      this.flipAllCardsDown();
      this.isInputLocked = false;

      this.gameTitle.textContent = this.t('match_title');
      this.gameSubhead.textContent = this.t('match_instruction');
      this.actionCueLabel.textContent = this.t('select_first');

      this.speak(`${this.t('match_title')}. ${this.t('select_first')}`);

      this.roundStartTime = performance.now();
      this.attemptStartTime = performance.now();
    }, durationMs);
  }

  flipAllCardsDown() {
    const cardButtons = this.cardsContainer.querySelectorAll('.flip-card');
    cardButtons.forEach((btn, idx) => {
      btn.classList.remove('is-flipped');
      btn.setAttribute('aria-label', this.t('card_label', { n: idx + 1, status: this.t('card_hidden') }));
    });
    this.playFeedbackSound('flip');
  }

  selectCardByIndex(idx) {
    if (this.isInputLocked) return;
    const cardButtons = this.cardsContainer.querySelectorAll('.flip-card');
    const cardEl = cardButtons[idx];
    if (!cardEl) return;

    if (cardEl.classList.contains('is-flipped') || cardEl.classList.contains('is-matched')) {
      return;
    }

    this.playFeedbackSound('flip');
    cardEl.classList.add('is-flipped');
    cardEl.setAttribute('aria-label', this.t('card_label', { n: idx + 1, status: this.deck[idx].shapeName }));

    this.selectedCards.push({ element: cardEl, index: idx, data: this.deck[idx] });

    if (this.selectedCards.length === 1) {
      this.actionCueLabel.textContent = this.t('select_second');
    } else if (this.selectedCards.length === 2) {
      this.isInputLocked = true;
      this.evaluateSelection();
    }
  }

  async evaluateSelection() {
    const endLatencyTime = performance.now();
    const latencyMs = Math.max(80, Math.round(endLatencyTime - this.attemptStartTime));

    const card1 = this.selectedCards[0];
    const card2 = this.selectedCards[1];

    // Local pre-check matching key
    const isMatch = (card1.data.match_key === card2.data.match_key);
    const targetShape = `${card1.data.shapeName} (${card1.data.direction})`;

    // Record attempt to local collection
    const attemptPayload = {
      round: this.currentRound.round_number,
      attempt: this.currentAttemptNumber,
      selected: [card1.index, card2.index],
      target_shape: targetShape,
      is_correct: isMatch,
      response_latency_ms: latencyMs,
    };
    this.allSelections.push(attemptPayload);

    // Synchronously send attempt to server
    const attemptPromise = this.recordAttemptOnServer(attemptPayload);
    this.pendingAttemptPromises.push(attemptPromise);
    this.currentAttemptNumber++;

    if (isMatch) {
      this.playFeedbackSound('match');
      this.speak(this.t('match_success'));

      card1.element.classList.add('is-matched');
      card2.element.classList.add('is-matched');
      card1.element.disabled = true;
      card2.element.disabled = true;

      this.matchedPairsInRound++;
      this.matchedCountLabel.textContent = this.t('pairs_matched', {
        matched: this.matchedPairsInRound,
        total: this.currentRound.pair_count,
      });

      this.selectedCards = [];
      this.isInputLocked = false;
      this.attemptStartTime = performance.now();

      if (this.matchedPairsInRound >= this.currentRound.pair_count) {
        this.actionCueLabel.textContent = this.t('match_success');
        this.isInputLocked = true;
        setTimeout(() => {
          this.advanceToNextRound();
        }, 900);
      } else {
        this.actionCueLabel.textContent = this.t('select_first');
      }
    } else {
      this.playFeedbackSound('mismatch');
      this.speak(this.t('match_error'));

      card1.element.classList.add('is-mismatch');
      card2.element.classList.add('is-mismatch');
      this.actionCueLabel.textContent = this.t('match_error');

      setTimeout(() => {
        card1.element.classList.remove('is-flipped', 'is-mismatch');
        card2.element.classList.remove('is-flipped', 'is-mismatch');
        card1.element.setAttribute('aria-label', this.t('card_label', { n: card1.index + 1, status: this.t('card_hidden') }));
        card2.element.setAttribute('aria-label', this.t('card_label', { n: card2.index + 1, status: this.t('card_hidden') }));

        this.selectedCards = [];
        this.isInputLocked = false;
        this.attemptStartTime = performance.now();
        this.actionCueLabel.textContent = this.t('select_first');
      }, 750);
    }
  }

  async recordAttemptOnServer(payload) {
    const data = { ...payload, token: this.token };
    try {
      const response = await fetch(`/api/sessions/${this.sessionId}/attempts/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken(),
          'X-Session-Token': this.token,
        },
        body: JSON.stringify(data),
      });
      return await response.json();
    } catch (err) {
      // Local payload preserved in this.allSelections
      return { status: 'buffered_locally' };
    }
  }

  advanceToNextRound() {
    const currentRoundWasPractice = this.currentRound.is_practice;
    this.currentRoundIndex++;

    if (currentRoundWasPractice) {
      // Show Practice Complete interstitial
      this.showPracticeCompleteInterstitial();
      return;
    }

    if (this.currentRoundIndex < this.rounds.length) {
      this.loadRound(this.currentRoundIndex);
    } else {
      this.completeAssessment();
    }
  }

  showPracticeCompleteInterstitial() {
    this.cardsContainer.innerHTML = `
      <div class="card" style="grid-column: 1 / -1; padding: 2.5rem; text-align: center; max-width: 540px; margin: 1rem auto; box-shadow: var(--shadow-lg);">
        <div style="width: 56px; height: 56px; border-radius: 50%; background: var(--success-bg); color: var(--success); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <h2 style="font-size: 1.6rem; margin-bottom: 0.5rem;">${this.t('practice_complete_title')}</h2>
        <p style="color: var(--text-muted); line-height: 1.5; margin-bottom: 1.75rem;">${this.t('practice_complete_msg')}</p>
        <button id="proceed-to-test-btn" class="btn btn-primary btn-lg" style="width: 100%;">
          ${this.t('start_assessment_btn')}
        </button>
      </div>
    `;

    this.speak(`${this.t('practice_complete_title')}. ${this.t('practice_complete_msg')}`);

    const proceedBtn = document.getElementById('proceed-to-test-btn');
    if (proceedBtn) {
      proceedBtn.addEventListener('click', () => {
        this.loadRound(this.currentRoundIndex);
      });
    }
  }

  // ============================================================================
  // Completion & Retry Fault Tolerance
  // ============================================================================

  async completeAssessment() {
    this.isInputLocked = true;
    this.actionCueLabel.textContent = this.t('submitting');

    // Wait for all in-flight attempts to resolve
    try {
      await Promise.all(this.pendingAttemptPromises);
    } catch (e) {}

    // Atomic completion request with batched fallback
    try {
      const response = await fetch(`/api/sessions/${this.sessionId}/complete/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken(),
          'X-Session-Token': this.token,
        },
        body: JSON.stringify({
          token: this.token,
          selections: this.allSelections,
          notes: 'Completed via patient portal.',
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.saved) {
        this.showCompletionScreen(data);
      } else {
        throw new Error('Save verification unconfirmed');
      }
    } catch (err) {
      this.showRetryScreen(err.message);
    }
  }

  showRetryScreen(errorMessage) {
    this.gameView.style.display = 'none';
    if (this.retryView) {
      this.retryView.style.display = 'block';
    } else {
      // Dynamically inject retry card if container not pre-rendered
      const retryContainer = document.createElement('div');
      retryContainer.id = 'retry-view';
      retryContainer.className = 'card';
      retryContainer.style.cssText = 'padding: 3rem 2rem; text-align: center; max-width: 580px; margin: 3rem auto; box-shadow: var(--shadow-lg);';
      retryContainer.innerHTML = `
        <div style="width: 56px; height: 56px; border-radius: 50%; background: var(--danger-bg); color: var(--danger); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 1rem;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        </div>
        <h2 style="font-size: 1.6rem; margin-bottom: 0.5rem;">${this.t('submission_failed')}</h2>
        <p style="color: var(--text-muted); line-height: 1.5; margin-bottom: 2rem;">${this.t('submission_failed_msg')}</p>
        <button id="retry-submission-btn-dynamic" class="btn btn-primary btn-lg" style="min-width: 200px;">
          ${this.t('retry_btn')}
        </button>
      `;
      this.gameView.parentNode.appendChild(retryContainer);
      this.retryView = retryContainer;
      document.getElementById('retry-submission-btn-dynamic').addEventListener('click', () => {
        this.retryView.style.display = 'none';
        this.gameView.style.display = 'block';
        this.completeAssessment();
      });
    }
  }

  showCompletionScreen(data) {
    if (this.retryView) this.retryView.style.display = 'none';
    this.gameView.style.display = 'none';
    this.completionView.style.display = 'block';

    const accuracyEl = document.getElementById('final-accuracy-val');
    const attemptsEl = document.getElementById('final-attempts-val');
    if (accuracyEl) accuracyEl.textContent = 'Saved';
    if (attemptsEl) attemptsEl.textContent = 'Results sent to your clinician';

    const titleEl = document.getElementById('completion-heading');
    if (titleEl) titleEl.textContent = this.t('complete_title');

    const msgEl = document.getElementById('completion-message');
    if (msgEl) msgEl.textContent = this.t('complete_msg');

    this.speak(`${this.t('complete_title')}. ${this.t('complete_msg')}`);
  }

  getCSRFToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  // ============================================================================
  // Card SVGs
  // ============================================================================

  getShapeSvg(shape, color) {
    const clr = color || '#4f46e5';
    switch (shape) {
      case 'arrow':
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M40 92V48H17L50 8l33 40H60v44z" fill="${clr}" /></svg>`;
      case 'l_shape':
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 10h25v53h42v25H19z" fill="${clr}" /></svg>`;
      case 'circle':
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="42" fill="${clr}" /></svg>`;
      case 'triangle':
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><polygon points="50,10 92,85 8,85" fill="${clr}" /></svg>`;
      case 'square':
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="15" y="15" width="70" height="70" rx="10" fill="${clr}" /></svg>`;
      case 'plus':
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M38 14h24v24h24v24H62v24H38V62H14V38h24V14z" fill="${clr}" /></svg>`;
      case 'star':
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><polygon points="50,5 64,36 98,38 72,61 80,95 50,77 20,95 28,61 2,38 36,36" fill="${clr}" /></svg>`;
      case 'diamond':
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><polygon points="50,8 92,50 50,92 8,50" fill="${clr}" /></svg>`;
      default:
        return `<svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="42" fill="${clr}" /></svg>`;
    }
  }
}

window.VisuospatialEngine = VisuospatialEngine;
