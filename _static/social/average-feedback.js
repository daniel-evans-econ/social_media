(() => {
  'use strict';
  const form = document.querySelector('form');
  const button = document.getElementById('average-submit');
  const outcomes = document.getElementById('average-outcomes');
  const status = document.getElementById('answer-status');
  let submitted = button.dataset.submitted === '1', pending = false, finished = false;
  let waitingForCorrection = false, revealTimer = null;
  const understood = document.getElementById('average-understood');
  const estimateStage = document.getElementById('average-estimate-stage');
  let readingIntroduction = !!understood;
  if (understood) {
    const storageKey = 'average-introduction-understood:' + window.location.pathname;
    let acknowledged = false;
    try { acknowledged = sessionStorage.getItem(storageKey) === '1'; } catch (_) {}
    function showEstimate() {
      readingIntroduction = false;
      understood.hidden = true;
      estimateStage.disabled = false;
      estimateStage.hidden = false;
    }
    if (acknowledged) {
      showEstimate();
    } else {
      const readyAt = performance.now() + 20000;
      function updateReadingTime() {
        const remaining = Math.max(0, Math.ceil((readyAt - performance.now()) / 1000));
        understood.textContent = remaining ? 'Understood (' + remaining + ')' : 'Understood';
        understood.disabled = remaining > 0;
        if (!remaining) clearInterval(readingTimer);
      }
      const readingTimer = setInterval(updateReadingTime, 250);
      updateReadingTime();
      understood.addEventListener('click', () => {
        if (performance.now() < readyAt) return;
        clearInterval(readingTimer);
        try { sessionStorage.setItem(storageKey, '1'); } catch (_) {}
        showEstimate();
      });
    }
  }
  function showOutcomes() {
    waitingForCorrection = false;
    outcomes.disabled = false; outcomes.hidden = false;
    button.disabled = false; button.hidden = false; button.textContent = 'Next';
  }
  function revealOutcomes() {
    clearTimeout(revealTimer);
    const hasCorrection = Array.from(form.querySelectorAll('[data-correction]')).some(
      row => !row.hidden && row.querySelector('[data-actual]').textContent.trim() !== ''
    );
    if (!hasCorrection) { showOutcomes(); return; }
    waitingForCorrection = true;
    outcomes.disabled = true; outcomes.hidden = true;
    button.disabled = true; button.hidden = true;
    revealTimer = setTimeout(showOutcomes, 3000);
  }
  // Also delay on direct-entry/reloaded correction pages; keep the questions
  // hidden in the initial HTML so they cannot flash before this script runs.
  if (submitted) revealOutcomes();
  form.addEventListener('submit', event => {
    if (finished) return;
    event.preventDefault();
    // This stage saves through liveSend, not a page submission. Do not let
    // oTree's submit debounce restore our temporary disabled state later.
    event.stopImmediatePropagation();
    if (readingIntroduction || pending || waitingForCorrection || !form.reportValidity()) return;
    const answers = {};
    const inputs = submitted ? outcomes.querySelectorAll('[data-answer]')
                            : form.querySelectorAll('.average-section [data-answer]');
    inputs.forEach(input => {
      if (input.type !== 'radio' || input.checked) answers[input.dataset.answer] = input.value;
    });
    pending = true; button.disabled = true; status.textContent = 'Saving…';
    liveSend({action: submitted ? 'outcomes' : 'belief', answers});
  });
  window.liveRecv = data => {
    pending = false; button.disabled = false;
    if (!data.saved) { status.textContent = data.error || 'Please try again.'; return; }
    if (data.stage === 'belief') {
      submitted = true;
      form.querySelectorAll('.average-section [data-answer]').forEach(input => {
        input.value = data.beliefs[input.dataset.answer]; input.readOnly = true;
      });
      (data.corrections || []).forEach(row => {
        const target = form.querySelector('[data-correction="' + row.period + '"]');
        if (target) { target.querySelector('[data-actual]').textContent = row.value; target.hidden = false; }
      });
      status.textContent = '';
      revealOutcomes();
    } else {
      finished = true; form.requestSubmit();
    }
  };
})();
