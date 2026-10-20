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
    page.screenshot(path=str(shots/'selfie-confirm.png'))
    page.locator('#selfie-retake').click()
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
    page.get_by_label('White female',exact=True).check()
    assert 'feminine-v2-1.svg' in page.locator('#identity-preview-image').get_attribute('src')
    assert page.locator('#identity-preview-name').inner_text()=='Preview user'
    page.locator('.avatar-trigger').hover()
    page.screenshot(path=str(shots/'avatar-options.png'))
    for width in (1200,390):
        page.set_viewport_size({'width':width,'height':900})
        for name in ('IntroImage_avatar','IntroImage_selfie','SelfieCapture',
                     'AverageBeliefs_quantitative_social','AverageBeliefs_qualitative_social',
                     'AverageTruth_quantitative_social','AverageTruth_qualitative_social',
                     'AverageOutcomes','EndOfPeriodSurvey','MessageReactionFeedback'):
            if not (fixtures/(name+'.html')).exists():
                raise AssertionError('Missing actual rendered fixture '+name)
            load(name)
            assert 'Debug info' not in page.locator('body').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth+1'),(width,name)
            if name=='IntroImage_selfie':
                assert page.locator('.avatar-picker').count()==0
                assert page.locator('#identity-preview-image').get_attribute('src').startswith('data:image/jpeg;base64,')
            if name.startswith('AverageBeliefs'):
                page.evaluate("() => { window.sent=[];window.liveSend=data=>window.sent.push(data); }")
                for answer in page.locator('[data-answer]').all(): answer.fill('5')
                page.locator('.otree-btn-next').click()
                assert len(page.evaluate('window.sent'))==1
            if name in ('AverageTruth_qualitative_social','IntroImage_selfie','EndOfPeriodSurvey'):
                page.screenshot(path=str(shots/f'{name}_{width}.png'),full_page=True)
    assert not errors,errors
    browser.close()
print('Passed: camera capture/retake/denial/confirmation, stopped streams, no upload option, image previews, avatar selection, live-answer payloads, and desktop/mobile layouts.')
