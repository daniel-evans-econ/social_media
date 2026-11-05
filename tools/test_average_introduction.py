"""Browser regression for the qualitative reading stage and subsequent flow."""
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
        page.clock.install()
        corrections = '[{period:1,value:"15.0"}]' if truth else '[]'
        html = '''<html><body><form><style>[hidden]{display:none!important}</style>
          <p>For this question we interpret a happy emoji as equivalent to Very much.</p>
          <button type="button" id="average-understood" disabled>Understood</button>
          <fieldset id="average-estimate-stage" hidden disabled>
            <section class="average-section"><input data-answer="1" value="20" required></section>
            <p data-correction="1" hidden>The actual percentage was <span data-actual></span>.</p>
            <fieldset id="average-outcomes" hidden disabled>
              <input type="radio" name="human_nature" data-answer="human_nature" value="3" required>
            </fieldset>
            <button type="submit" class="otree-btn-next" id="average-submit" data-submitted="0">Submit estimate</button>
            <p id="answer-status"></p>
          </fieldset>
        </form><script>
          window.saved=[];
          window.liveSend=data=>{saved.push(data);setTimeout(()=>liveRecv(data.action==='belief'
            ? {saved:true,stage:'belief',beliefs:{1:20},corrections:CORRECTIONS}
            : {saved:true}),20);};
        </script><script>FEEDBACK</script><script>COMMON</script><script>
          document.querySelector('form').addEventListener('submit',event=>{
            event.preventDefault();window.completed=true;
          });
        </script></body></html>'''.replace('CORRECTIONS',corrections).replace('FEEDBACK',feedback).replace('COMMON',common)
        page.route('https://survey.test/**',lambda route:route.fulfill(body=html,content_type='text/html'))
        page.goto('https://survey.test/qualitative')
        assert page.locator('#average-understood').is_disabled()
        assert not page.locator('#average-estimate-stage').is_visible()
        assert page.locator('.average-section input').is_disabled()
        page.evaluate("document.querySelector('form').requestSubmit()")
        assert page.evaluate('saved.length')==0
        page.clock.run_for(19000)
        assert page.locator('#average-understood').is_disabled()
        page.clock.run_for(1100)
        assert page.locator('#average-understood').is_enabled()
        assert not page.locator('#average-estimate-stage').is_visible()
        page.locator('#average-understood').click()
        assert page.locator('#average-estimate-stage').is_visible()
        assert not page.locator('#average-outcomes').is_visible()
        page.reload()
        assert not page.locator('#average-understood').is_visible()
        assert page.locator('.average-section input').is_enabled()
        page.locator('#average-submit').click()
        page.clock.run_for(100)
        assert page.locator('[data-correction]').is_visible()==truth
        assert page.locator('#average-outcomes').is_visible()!=truth
        page.clock.run_for(5200)
        assert page.locator('#average-outcomes').is_visible()
        assert page.locator('#average-submit').is_enabled()
        page.locator('[name=human_nature]').check()
        page.locator('#average-submit').click()
        page.clock.run_for(100)
        assert page.evaluate('window.completed===true')
        assert page.evaluate('saved.map(x=>x.action)')==['belief','outcomes']
        # Different participant URLs do not inherit the acknowledgement.
        page.goto('https://survey.test/another-participant')
        assert page.locator('#average-understood').is_disabled()
        assert not page.locator('#average-estimate-stage').is_visible()
        page.close()
    browser.close()
print('Passed: 20-second gate, acknowledgement, refresh, participant isolation, correction/control and final submission.')
