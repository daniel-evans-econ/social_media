"""Browser checks of actual bot-rendered pages; Chromium uses a synthetic camera."""
from pathlib import Path
from urllib.parse import urlparse, unquote
import mimetypes
import sys
import otree
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
fixtures = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT / 'qa_oct20/html'
shots = ROOT / 'qa_oct20/screenshots'
shots.mkdir(exist_ok=True)

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=['--use-fake-device-for-media-stream',
                                                     '--use-fake-ui-for-media-stream'])
    context = browser.new_context(viewport={'width':1200,'height':900}, permissions=['camera'])
    roots = [ROOT/'_static',ROOT/'social_media/static',Path(otree.__file__).parent/'static']
    def serve(route):
        path = unquote(urlparse(route.request.url).path)
        candidates = [fixtures/path.removeprefix('/qa/')] if path.startswith('/qa/') else [
            root/path.removeprefix('/static/') for root in roots] if path.startswith('/static/') else []
        for candidate in candidates:
            if candidate.is_file():
                content_type = mimetypes.guess_type(candidate)[0] or 'application/octet-stream'
                if candidate.suffix in ('.html','.css','.js'):
                    content_type += '; charset=utf-8'
                route.fulfill(body=candidate.read_bytes(),content_type=content_type)
                return
        route.fulfill(status=404,body='Outside QA fixtures')
    context.route('**/*',serve)
    page = context.new_page()
    errors=[]
    page.on('pageerror',lambda error: errors.append(str(error)))
    def load(name):
        page.goto('https://survey.test/qa/'+name+'.html',wait_until='load')
    if (fixtures/'Consent.html').exists():
        load('Consent')
        page.evaluate('() => { window.sent=[]; window.liveSend=data=>window.sent.push(data); }')
        next_button = page.locator('.otree-btn-next')
        assert next_button.is_disabled()
        page.locator('[name=consent]').check()
        page.locator('[name=llm_rule_confirm]').check()
        assert next_button.is_disabled()
        selfie_box = page.locator('[name=selfie_consent]')
        assert selfie_box.get_attribute('required') is not None
        selfie_box.check()
        assert next_button.is_disabled(), 'Must wait for the saved consent acknowledgement'
        page.evaluate('liveRecv({selfie_consent_saved:true,request_id:1})')
        assert next_button.is_enabled()
        selfie_box.uncheck()
        assert next_button.is_disabled()
        page.evaluate('liveRecv({selfie_consent_saved:true,request_id:1})')
        assert next_button.is_disabled(), 'Ignore stale acknowledgements'
        page.evaluate('liveRecv({selfie_consent_saved:false,request_id:2})')
        selfie_box.check()
        page.evaluate('liveRecv({selfie_consent_saved:true,request_id:3})')
        assert next_button.is_enabled()
        for phrase in ('upload a selfie','blurred version'):
            emphasis = page.locator('strong').filter(has_text=phrase)
            assert emphasis.count()==1
            assert emphasis.evaluate("el=>getComputedStyle(el).color")=='rgb(139, 0, 0)'
        page.screenshot(path=str(shots/'selfie-consent-checkbox.png'),full_page=True)
    load('SelfieCapture')
    assert page.locator('input[type=file]').count()==0
    page.evaluate("() => { window.sent=[]; window.liveSend=data=>window.sent.push(data); }")
    page.locator('#selfie-open').click()
    page.wait_for_function("document.getElementById('selfie-camera').videoWidth>0")
    page.evaluate("window.testTrack=document.getElementById('selfie-camera').srcObject.getVideoTracks()[0]")
    page.locator('#selfie-take').click()
    assert page.evaluate("window.testTrack.readyState")=='ended'
    assert page.evaluate("window.sent.filter(x=>x && x.action==='confirm').length")==0, page.evaluate("window.sent.map(x=>Object.keys(x))")
    photo=page.locator('#selfie-result').get_attribute('src')
    assert photo.startswith('data:image/jpeg;base64,')
    assert page.locator('#selfie-preview').is_visible()
    assert page.locator('#selfie-result').bounding_box()['width'] == 36
    assert page.locator('#selfie-result').bounding_box()['height'] == 36
    page.screenshot(path=str(shots/'selfie-confirm.png'))
    page.locator('#selfie-retake').click()
    assert page.locator('#selfie-preview').is_hidden()
    page.wait_for_function("document.getElementById('selfie-camera').videoWidth>0")
    page.locator('#selfie-take').click()
    page.locator('#selfie-confirm').click()
    assert page.evaluate("window.sent.filter(x=>x && x.action==='confirm').length")==1
    assert page.evaluate("window.sent.find(x=>x && x.action==='confirm').image===document.getElementById('selfie-result').src")
    load('SelfieCapture')
    page.evaluate("() => { navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Denied')}; }")
    page.locator('#selfie-open').click()
    assert 'unavailable' in page.locator('#selfie-status').inner_text()
    assert page.locator('#selfie-open').is_enabled()
    load('IntroImage_avatar')
    page.evaluate("() => { window.liveSend=data=>window.liveRecv(data); }")
    page.locator('#id_display_name').fill('Preview user')
    page.locator('.avatar-trigger').hover()
    assert page.locator('[name=avatar_picker]').count()==10
    page.get_by_label('Avatar 1',exact=True).check()
    assert 'feminine-v2-1.svg' in page.locator('#identity-preview-image').get_attribute('src')
    assert page.locator('#identity-preview-name').inner_text()=='Preview user'
    page.locator('.avatar-trigger').hover()
    page.screenshot(path=str(shots/'avatar-options.png'))
    for width in (1200,390):
        page.set_viewport_size({'width':width,'height':900})
        for name in ('IntroImage_avatar','IntroImage_selfie','IntroImage_avatar_reactions','IntroImage_selfie_reactions','SelfieCapture',
                     'AverageBeliefs_quantitative_social','AverageBeliefs_qualitative_social',
                     'AverageTruth_quantitative_social','AverageTruth_qualitative_social',
                     'AverageOutcomes','EndOfPeriodSurvey','MessageReactionFeedback'):
            if not (fixtures/(name+'.html')).exists():
                raise AssertionError('Missing actual rendered fixture '+name)
            load(name)
            assert 'Debug info' not in page.locator('body').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1'),(width,name)
            if name in ('IntroImage_avatar_reactions','IntroImage_selfie_reactions'):
                icon = page.locator('.care-icon')
                assert icon.count()==1
                bounds = icon.bounding_box()
                assert 10 < bounds['width'] < 40 and 10 < bounds['height'] < 40,(name,bounds)
            if name=='IntroImage_selfie':
                assert page.locator('.avatar-picker').count()==0
                assert page.locator('#identity-preview-image').get_attribute('src').startswith('data:image/jpeg;base64,')
            if name.startswith('AverageBeliefs'):
                page.evaluate("() => { window.sent=[];window.liveSend=data=>window.sent.push(data); }")
                for answer in page.locator('[data-answer]').all(): answer.fill('5')
                page.locator('.otree-btn-next').click()
                assert len(page.evaluate('window.sent'))==1
            if name.startswith('Average'):
                assert page.locator('.average-page-title').evaluate("el => Number(getComputedStyle(el).fontWeight) >= 700")
                page.screenshot(path=str(shots/f'{name}_{width}.png'),full_page=True)
            if name=='AverageOutcomes':
                page.evaluate("""() => {
                    window.sent=[];window.liveSend=data=>window.sent.push(data);
                    document.querySelector('form').requestSubmit=()=>{window.resubmitted=true;};
                }""")
                for fieldset in page.locator('fieldset').all():
                    options=fieldset.locator('label')
                    bounds=[option.bounding_box() for option in options.all()]
                    if width == 1200:
                        assert all(abs(b['y']-bounds[0]['y']) < 1 for b in bounds)
                    fieldset.locator('input').first.check()
                page.locator('.otree-btn-next').click()
                sent=page.evaluate('window.sent')
                assert len(sent)==1 and sent[0]['mood']=='1' and len(sent[0])==page.locator('fieldset').count()
                page.evaluate('liveRecv({saved:true})')
                assert page.evaluate('window.resubmitted')
            if name=='EndOfPeriodSurvey':
                assert page.locator('fieldset [name=task_difficulty_response]').count()==5
                page.evaluate("""() => {
                    window.sent=[];window.liveSend=data=>window.sent.push(data);
                    const names=new Set();
                    document.querySelectorAll('input[type=radio]').forEach(el=>{
                        if (!names.has(el.name)) { el.checked=true; names.add(el.name); }
                    });
                    document.querySelector('form').requestSubmit=()=>{window.resubmitted=true;};
                }""")
                page.locator('.otree-btn-next').click()
                assert page.evaluate('window.sent')==[{'difficulty':1}]
                page.evaluate('liveRecv({difficulty_saved:1})')
                assert page.evaluate('window.resubmitted')
            if name in ('AverageTruth_qualitative_social','IntroImage_selfie','EndOfPeriodSurvey'):
                page.screenshot(path=str(shots/f'{name}_{width}.png'),full_page=True)
    assert not errors,errors
    browser.close()
print('Passed: camera capture/retake/denial/confirmation, stopped streams, no upload option, image previews, avatar selection, live-answer payloads, and desktop/mobile layouts.')
