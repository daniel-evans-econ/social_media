"""Regression: oTree's five-second debounce must not disable live-stage Next."""
from pathlib import Path
import otree
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
feedback = (ROOT / '_static/social/average-feedback.js').read_text(encoding='utf-8')
common = (Path(otree.__file__).parent / 'static/otree/js/common_user_facing.js').read_text()
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    for truth in (False, True):
        page = browser.new_page()
        corrections = '[{period:1,value:"7.2"}]' if truth else '[]'
        page.set_content('''<html><body><form id="form">
          <section class="average-section"><input data-answer="1" value="8" required></section>
          <p data-correction="1" hidden>The actual average was <span data-actual></span>.</p>
          <fieldset id="average-outcomes" hidden disabled>
            <input type="radio" name="human_nature" data-answer="human_nature" value="3" required>
          </fieldset>
          <button type="submit" class="otree-btn-next" id="average-submit" data-submitted="0">Submit estimate</button>
          <p id="answer-status"></p>
        </form><script>
          let saved = [];
          window.liveSend = data => {
            saved.push(data);
            setTimeout(() => window.liveRecv(data.action === 'belief'
              ? {saved:true,stage:'belief',beliefs:{1:8},corrections:CORRECTIONS}
              : {saved:true}), 20);
          };
        </script><script>FEEDBACK</script><script>COMMON</script><script>
          document.querySelector('form').addEventListener('submit', event => {
            event.preventDefault(); window.completed = true;
          });
        </script></body></html>'''.replace('CORRECTIONS', corrections).replace('FEEDBACK', feedback).replace('COMMON', common))
        page.locator('#average-submit').click()
        page.locator('#average-outcomes').wait_for(state='visible')
        # The regression occurs five seconds after submission, after the
        # three-second correction reveal has already enabled the button.
        page.wait_for_timeout(5200)
        assert page.locator('#average-submit').is_enabled()
        assert page.locator('[data-correction]').is_visible() == truth
        page.locator('input[name=human_nature]').check()
        page.locator('#average-submit').click()
        page.wait_for_function('window.completed === true')
        assert page.evaluate('saved.map(x=>x.action)') == ['belief', 'outcomes']
        page.close()
    browser.close()
print('Passed with real oTree submit handler: control/correction Next remains enabled after five seconds and outcomes submit once.')
