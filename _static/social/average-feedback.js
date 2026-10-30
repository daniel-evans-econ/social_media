(() => {
  'use strict';
  const form = document.querySelector('form');
  const button = document.getElementById('average-submit');
  const outcomes = document.getElementById('average-outcomes');
  const status = document.getElementById('answer-status');
  let submitted = button.dataset.submitted === '1', pending = false, finished = false;
  form.addEventListener('submit', event => {
    if (finished) return;
    event.preventDefault();
    if (pending || !form.reportValidity()) return;
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
      outcomes.disabled = false; outcomes.hidden = false;
      button.textContent = 'Next'; status.textContent = '';
    } else {
      finished = true; form.requestSubmit();
    }
  };
})();
