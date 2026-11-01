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

  if (sessionForm) {
    sessionForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const customParticipantInput = document.getElementById('custom-participant-id');
      const customParticipantId = customParticipantInput ? customParticipantInput.value.trim() : '';
      const language = document.getElementById('test-language').value;
      const audioVoice = document.getElementById('audio-voice').value;
      const dob = document.getElementById('patient-dob').value;
      const difficulty = document.getElementById('test-difficulty') ? document.getElementById('test-difficulty').value : 'Standard';

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
          modalPatientCode.textContent = data.patient_code;
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
          newRow.innerHTML = `
            <div>
              <div style="font-weight: 700; color: var(--text-main); font-size: 0.95rem;">${data.patient_code}</div>
              <div style="font-size: 0.8rem; color: var(--text-muted);">${data.language} · Voice: ${data.audio_voice} · ${data.difficulty} · Age ${data.age_bracket}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <span class="badge badge-pending"><span class="badge-dot"></span>Pending</span>
              <a href="${data.patient_url}" target="_blank" class="btn btn-secondary btn-sm">Open Test</a>
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
