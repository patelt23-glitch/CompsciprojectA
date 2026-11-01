/**
 * Clinician Dashboard Interactive Scripts
 * Handles generating patient links, copy-to-clipboard, custom participant IDs, and live UI updates.
 * Zero em-dashes.
 */

document.addEventListener('DOMContentLoaded', () => {
  const sessionForm = document.getElementById('generate-session-form');
  const modal = document.getElementById('link-modal');
  const modalPatientCode = document.getElementById('modal-patient-code');
  const modalPatientUrl = document.getElementById('modal-patient-url');
  const modalCopyBtn = document.getElementById('modal-copy-btn');
  const modalOpenBtn = document.getElementById('modal-open-btn');
  const modalCloseBtn = document.getElementById('modal-close-btn');

  function getCSRFToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  const difficultySelect = document.getElementById('test-difficulty');
  if (difficultySelect) difficultySelect.addEventListener('change', () => {
    const lastCount = document.getElementById('round-3-count');
    if (lastCount) lastCount.value = difficultySelect.value === 'Advanced' ? '12' : '10';
  });

  if (sessionForm) {
    sessionForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const customParticipantInput = document.getElementById('custom-participant-id');
      const customParticipantId = customParticipantInput ? customParticipantInput.value.trim() : '';
      const language = document.getElementById('test-language').value;
      const audioVoice = document.getElementById('audio-voice').value;
      const dob = document.getElementById('patient-dob')?.value || '';
      const difficulty = document.getElementById('test-difficulty') ? document.getElementById('test-difficulty').value : 'Standard';

      const cardCounts = [1, 2, 3].map(n => parseInt(document.getElementById(`round-${n}-count`).value, 10));
      const palette = document.getElementById('shape-palette').value;
      const types = {
        all: ['arrow','triangle','l_shape','circle','square','plus','star','diamond'],
        angular: ['arrow','triangle','l_shape'],
        geometric: ['triangle','circle','square','star','diamond'],
      };
      const seconds = document.getElementById('study-seconds').value;
      // Omit default controls so backend marks the invitation standardized.
      const presetCounts = difficulty === 'Advanced' ? [6,8,12] : [6,8,10];
      const settings = {};
      if (cardCounts.some((n, i) => n !== presetCounts[i])) settings.card_counts = cardCounts;
      if (palette !== 'all') settings.shape_types = types[palette];
      if (seconds !== 'preset') settings.study_time_ms = Number(seconds) * 1000;

      const submitBtn = sessionForm.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.textContent = 'Generating Link...';
      submitBtn.disabled = true;

      fetch('/api/sessions/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
          participant_id: customParticipantId,
          language: language,
          audio_voice: audioVoice,
          dob: dob,
          difficulty: difficulty,
          ...settings,
        })
      })
      .then(res => {
        if (!res.ok) {
          return res.json().then(errData => {
            throw new Error(errData.error || 'Failed to create session');
          });
        }
        return res.json();
      })
      .then(data => {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;

        // Reset custom input
        if (customParticipantInput) customParticipantInput.value = '';

        // Show Generated Link Modal
        if (modal && modalPatientCode && modalPatientUrl) {
          modalPatientCode.textContent = data.invitation_code;
          modalPatientUrl.value = data.patient_url;
          modalOpenBtn.href = data.patient_url;
          modal.style.display = 'flex';
        }

        // Add to pending sessions list dynamically
        const pendingContainer = document.getElementById('pending-sessions-list');
        if (pendingContainer) {
          const emptyState = document.getElementById('pending-empty-state');
          if (emptyState) emptyState.remove();

          const newRow = document.createElement('div');
          newRow.className = 'item-row';
          const safe = str => String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
          newRow.innerHTML = `
            <div>
              <div style="font-weight: 700; color: var(--text-main); font-size: 0.95rem;">${safe(data.patient_code)}</div>
              <div style="font-size: 0.8rem; color: var(--text-muted);">${safe(data.language)} · Voice: ${safe(data.audio_voice)} · ${safe(data.difficulty)} · Age ${safe(data.age_bracket)}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <span class="badge badge-pending"><span class="badge-dot"></span>Pending</span>
              <a href="${safe(data.patient_url)}" target="_blank" class="btn btn-secondary btn-sm">Open Test</a>
            </div>
          `;
          pendingContainer.insertBefore(newRow, pendingContainer.firstChild);

          // Update pending count in metrics card
          const pendingCountEl = document.getElementById('pending-count-metric');
          if (pendingCountEl) {
            const current = parseInt(pendingCountEl.textContent, 10) || 0;
            pendingCountEl.textContent = (current + 1).toString();
          }
        }
      })
      .catch(err => {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
        alert(err.message || 'Could not generate patient session. Please check your inputs and try again.');
        console.error(err);
      });
    });
  }

  const copyCodeBtn = document.getElementById('modal-copy-code-btn');
  if (copyCodeBtn && modalPatientCode) {
    copyCodeBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(modalPatientCode.textContent);
    });
  }

  // Copy URL to clipboard
  if (modalCopyBtn && modalPatientUrl) {
    modalCopyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(modalPatientUrl.value).then(() => {
        const origText = modalCopyBtn.textContent;
        modalCopyBtn.textContent = 'Copied!';
        modalCopyBtn.style.backgroundColor = 'var(--success)';
        modalCopyBtn.style.color = '#ffffff';
        setTimeout(() => {
          modalCopyBtn.textContent = origText;
          modalCopyBtn.style.backgroundColor = '';
          modalCopyBtn.style.color = '';
        }, 2000);
      });
    });
  }

  // Close modal
  if (modalCloseBtn && modal) {
    modalCloseBtn.addEventListener('click', () => {
      modal.style.display = 'none';
    });
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
      }
    });
  }
});
