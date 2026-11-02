/**
 * Clinician Dashboard Interactive Scripts
 * Handles generating patient links, copy-to-clipboard, custom participant IDs,
 * link cancellation, link regeneration, and live status updates.
 * Zero em-dashes.
 */

document.addEventListener('DOMContentLoaded', () => {
  const sessionForm = document.getElementById('generate-session-form');
  const modal = document.getElementById('link-modal');
  const modalTitle = document.getElementById('modal-title');
  const modalDesc = document.getElementById('modal-desc');
  const modalPatientCode = document.getElementById('modal-patient-code');
  const modalPatientUrl = document.getElementById('modal-patient-url');
  const modalCopyBtn = document.getElementById('modal-copy-btn');
  const modalOpenBtn = document.getElementById('modal-open-btn');
  const modalCloseBtn = document.getElementById('modal-close-btn');

  function getCSRFToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }

  // Bind delegated events for Copy, Cancel, and Regenerate buttons
  document.addEventListener('click', (e) => {
    // 1. Copy Link Button
    const copyBtn = e.target.closest('.copy-link-btn');
    if (copyBtn) {
      e.preventDefault();
      const relativeUrl = copyBtn.getAttribute('data-url');
      const fullUrl = relativeUrl.startsWith('http') ? relativeUrl : (window.location.origin + relativeUrl);
      navigator.clipboard.writeText(fullUrl).then(() => {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        copyBtn.style.backgroundColor = 'var(--success)';
        copyBtn.style.color = '#ffffff';
        setTimeout(() => {
          copyBtn.textContent = originalText;
          copyBtn.style.backgroundColor = '';
          copyBtn.style.color = '';
        }, 1800);
      });
      return;
    }

    // 2. Cancel Link Button (Feature 1)
    const cancelBtn = e.target.closest('.cancel-link-btn');
    if (cancelBtn) {
      e.preventDefault();
      const sessionId = cancelBtn.getAttribute('data-id');
      const patientCode = cancelBtn.getAttribute('data-code') || 'this patient';

      if (!confirm(`Are you sure you want to cancel the assessment link for ${patientCode}? The patient will not be able to start the test.`)) {
        return;
      }

      cancelBtn.disabled = true;
      cancelBtn.textContent = 'Canceling...';

      fetch(`/api/sessions/${sessionId}/cancel/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        }
      })
      .then(res => {
        if (!res.ok) {
          return res.json().then(errData => {
            throw new Error(errData.error || 'Failed to cancel link');
          });
        }
        return res.json();
      })
      .then(data => {
        // Update DOM row
        const row = document.getElementById(`session-row-${sessionId}`);
        if (row) {
          const badgeEl = row.querySelector('.badge');
          if (badgeEl) {
            badgeEl.className = 'badge badge-canceled';
            badgeEl.innerHTML = '<span class="badge-dot"></span>Canceled';
          }
          // Remove Copy and Open buttons, replace Cancel with Regenerate
          const actionsDiv = cancelBtn.parentElement;
          if (actionsDiv) {
            actionsDiv.innerHTML = `
              <button type="button" class="btn btn-secondary btn-sm regenerate-link-btn" data-id="${sessionId}" data-code="${patientCode}" style="color: var(--primary);" title="Regenerate with fresh 7-day token">
                Regenerate
              </button>
            `;
          }
        }
      })
      .catch(err => {
        cancelBtn.disabled = false;
        cancelBtn.textContent = 'Cancel';
        alert(err.message || 'Could not cancel the assessment link.');
      });
      return;
    }

    // 3. Regenerate Link Button (Feature 1)
    const regenBtn = e.target.closest('.regenerate-link-btn');
    if (regenBtn) {
      e.preventDefault();
      const sessionId = regenBtn.getAttribute('data-id');
      const patientCode = regenBtn.getAttribute('data-code') || 'patient';

      regenBtn.disabled = true;
      regenBtn.textContent = 'Regenerating...';

      fetch(`/api/sessions/${sessionId}/regenerate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        }
      })
      .then(res => {
        if (!res.ok) {
          return res.json().then(errData => {
            throw new Error(errData.error || 'Failed to regenerate link');
          });
        }
        return res.json();
      })
      .then(data => {
        regenBtn.disabled = false;
        regenBtn.textContent = 'Regenerate';

        // Update DOM row
        const row = document.getElementById(`session-row-${sessionId}`);
        if (row) {
          const badgeEl = row.querySelector('.badge');
          if (badgeEl) {
            badgeEl.className = 'badge badge-pending';
            badgeEl.innerHTML = '<span class="badge-dot"></span>Pending';
          }
          const actionsDiv = regenBtn.parentElement;
          if (actionsDiv) {
            actionsDiv.innerHTML = `
              <button type="button" class="btn btn-secondary btn-sm copy-link-btn" data-url="${data.patient_url}" title="Copy patient link to clipboard">
                Copy
              </button>
              <a href="${data.patient_url}" target="_blank" class="btn btn-secondary btn-sm">
                Open
              </a>
              <button type="button" class="btn btn-secondary btn-sm cancel-link-btn" data-id="${sessionId}" data-code="${patientCode}" style="color: #dc2626;" title="Cancel this assessment link">
                Cancel
              </button>
            `;
          }
        }

        // Show Modal with new link
        if (modal && modalPatientCode && modalPatientUrl) {
          if (modalTitle) modalTitle.textContent = 'Patient Link Regenerated';
          if (modalDesc) modalDesc.innerHTML = `Fresh invitation created for patient <strong>${patientCode}</strong>. Valid for 7 days.`;
          modalPatientCode.textContent = patientCode;
          modalPatientUrl.value = data.patient_url;
          modalOpenBtn.href = data.patient_url;
          modal.style.display = 'flex';
        }
      })
      .catch(err => {
        regenBtn.disabled = false;
        regenBtn.textContent = 'Regenerate';
        alert(err.message || 'Could not regenerate link.');
      });
      return;
    }
  });

  // Generate New Assessment Link Form
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
          if (modalTitle) modalTitle.textContent = 'Patient Link Created';
          if (modalDesc) modalDesc.innerHTML = `Session created for patient <strong>${data.patient_code}</strong>. Share this expiring link with the patient to start their test.`;
          modalPatientCode.textContent = data.patient_code;
          modalPatientUrl.value = data.patient_url;
          modalOpenBtn.href = data.patient_url;
          modal.style.display = 'flex';
        }

        // Add to active links list dynamically
        const activeContainer = document.getElementById('active-links-list');
        if (activeContainer) {
          const emptyState = document.getElementById('pending-empty-state');
          if (emptyState) emptyState.remove();

          const newRow = document.createElement('div');
          newRow.className = 'item-row';
          newRow.id = `session-row-${data.session_id}`;
          newRow.style.alignItems = 'flex-start';
          newRow.innerHTML = `
            <div style="flex: 1;">
              <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                <span style="font-weight: 700; color: var(--text-main); font-size: 0.95rem;">
                  ${data.patient_code}
                </span>
                ${data.participant_id && data.participant_id !== data.patient_code ? `<span style="font-weight: 400; color: var(--text-muted); font-size: 0.85rem;">(${data.participant_id})</span>` : ''}
                <span class="badge badge-pending"><span class="badge-dot"></span>Pending</span>
              </div>
              <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">
                ${data.difficulty} · ${data.language} · Voice: ${data.audio_voice} · ${data.age_bracket}
              </div>
              <div style="font-size: 0.75rem; color: var(--text-subtle); margin-top: 0.15rem;">
                Created: Today · <span>Expires in ${data.invitation_days || 7} days</span>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; justify-content: flex-end;">
              <button type="button" class="btn btn-secondary btn-sm copy-link-btn" data-url="${data.patient_url}" title="Copy patient link to clipboard">
                Copy
              </button>
              <a href="${data.patient_url}" target="_blank" class="btn btn-secondary btn-sm">
                Open
              </a>
              <button type="button" class="btn btn-secondary btn-sm cancel-link-btn" data-id="${data.session_id}" data-code="${data.patient_code}" style="color: #dc2626;" title="Cancel this assessment link">
                Cancel
              </button>
            </div>
          `;
          activeContainer.insertBefore(newRow, activeContainer.firstChild);

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

  // Copy URL to clipboard from modal
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
