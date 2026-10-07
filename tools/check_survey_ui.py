"""Browser QA of real pages captured by oTree bots.

Set SURVEY_QA_HTML_DIR to an empty temporary folder and run the IQ-mode bots,
then run: python tools/check_survey_ui.py <that-folder>
Requires Playwright and its Chromium browser (development only).
"""
from pathlib import Path
import json
import mimetypes
import sys
from urllib.parse import urlparse, unquote

import otree
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    fixtures = Path(sys.argv[1]).resolve()
    screenshots = fixtures / 'screenshots'
    screenshots.mkdir(exist_ok=True)
    static_roots = [ROOT / '_static', ROOT / 'social_media' / 'static', Path(otree.__file__).parent / 'static']
    errors = []
    checked = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})

        def serve(route):
            path = unquote(urlparse(route.request.url).path)
            candidates = ([fixtures / path.removeprefix('/qa/')] if path.startswith('/qa/') else
                          [root / path.removeprefix('/static/') for root in static_roots] if path.startswith('/static/') else [])
            for candidate in candidates:
                if candidate.is_file():
                    content_type = mimetypes.guess_type(candidate)[0] or 'application/octet-stream'
                    if candidate.suffix in ('.html', '.css', '.js'):
                        content_type += '; charset=utf-8'
                    route.fulfill(body=candidate.read_bytes(), content_type=content_type)
                    return
            route.fulfill(status=404, body='Not part of local QA fixtures')

        context.route('**/*', serve)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))

        def load(name):
            page.goto(f'http://127.0.0.1:8765/qa/{name}.html', wait_until='load')

        if '--colours-only' in sys.argv:
            page.set_viewport_size({'width': 390, 'height': 900})
            for name in ('BlockFeedback', 'IQFeedback', 'GlobalIQFeedback'):
                load(name + '_qualitative_social')
                page.locator('.emoji-compose-trigger').wait_for(state='visible')
                assert page.locator('.fb-compose').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(255, 255, 255)'
                assert page.locator('.fb-preview').first.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(247, 250, 255)'
                page.locator('.fb-compose').screenshot(path=str(screenshots / (name + '_blue_message.png')))
            load('MessageReactionFeedback')
            assert page.locator('.rf-own').first.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(247, 250, 255)'
            assert not errors, errors
            browser.close()
            print('Passed: white outer boxes and lighter blue own-message bubbles on all four pages.')
            return

        if '--reactions-only' in sys.argv:
            load('BlockFeedbackReactions')
            field = page.locator('#id_received_reaction')
            trigger = page.locator('.reaction-trigger')
            assert page.get_by_role('button', name='Remove reaction', exact=True).count() == 0
            for value in ('like', 'love', 'care', 'haha', 'wow', 'sad', 'angry'):
                trigger.click()
                page.locator('[data-reaction="' + value + '"]').click()
                assert field.input_value() == value
                trigger.click()
                assert field.input_value() == 'none'
                assert page.locator('[data-reaction][aria-pressed=true]').count() == 0
                assert trigger.locator('svg').count() == 1
            page.reload()
            assert field.input_value() == 'none'
            trigger.click()
            page.locator('[data-reaction="love"]').click()
            trigger.press('ArrowDown')
            page.locator('[data-reaction="love"]').click()
            assert field.input_value() == 'none'
            trigger.click()
            page.locator('[data-reaction="care"]').click()
            trigger.hover()
            page.locator('[data-reaction="wow"]').click()
            assert field.input_value() == 'wow'
            for width in (1280, 390, 320):
                page.set_viewport_size({'width': width, 'height': 900})
                trigger.press('ArrowDown')
                panel = page.locator('#reaction-palette')
                assert panel.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
                box = panel.bounding_box()
                assert box['x'] >= 0 and box['x'] + box['width'] <= width
                page.locator('.fb-received').screenshot(path=str(screenshots / f'reaction_toggle_{width}.png'))
                trigger.press('Escape')
            trigger.press('Enter')
            assert field.input_value() == 'none'
            page.reload()
            assert field.input_value() == 'none'
            for name in ('BlockFeedback', 'IQFeedback', 'GlobalIQFeedback'):
                load(name + '_qualitative_social')
                page.locator('.emoji-compose-trigger').wait_for(state='visible')
                assert page.locator('.fb-compose').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(255, 255, 255)'
                assert page.locator('.fb-preview').first.evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(247, 250, 255)'
                page.locator('.fb-compose').screenshot(path=str(screenshots / (name + '_white_composer.png')))
            assert not errors, errors
            browser.close()
            print('Passed: direct toggle of all seven reactions, same-emoji toggle, hover switching, keyboard removal, refresh persistence, mobile layouts, and white/blue message boxes.')
            return

        if '--avatars-only' in sys.argv:
            # Reproduce the server-rendered checked input for a returning participant.
            saved_html = (fixtures / 'IntroReactions.html').read_text(encoding='utf-8').replace('value="neutral-4"', 'value="neutral-4" checked')
            (fixtures / 'IntroAvatarSaved.html').write_text(saved_html, encoding='utf-8')
            load('IntroReactions')
            emphasis = page.locator('.avatar-picker legend strong')
            assert emphasis.inner_text() == 'avatar'
            assert emphasis.evaluate('(el) => getComputedStyle(el).color') == 'rgb(139, 0, 0)'
            assert int(emphasis.evaluate('(el) => getComputedStyle(el).fontWeight')) >= 600
            prompt_gap = page.locator('#id_display_name').evaluate('(el) => parseFloat(getComputedStyle(el.previousElementSibling).marginTop)')
            avatar_gap = page.locator('.avatar-picker').evaluate('(el) => parseFloat(getComputedStyle(el).marginTop)')
            assert abs(prompt_gap - avatar_gap) < 1
            page.evaluate('window.liveSend = data => window.liveRecv(data)')
            choices = page.locator('[name="avatar_picker"]')
            assert choices.count() == 18
            assert page.locator('.avatar-trigger').inner_text() == '?'
            assert page.locator('.avatar-picker').get_by_text('Feminine', exact=True).count() == 0
            page.locator('.avatar-trigger').hover()
            assert page.locator('.avatar-options:visible').count() == 1
            assert page.locator('[name=avatar_picker]:checked').count() == 0
            page.mouse.move(0, 0)
            assert page.locator('.avatar-options:visible').count() == 0
            for choice in choices.all():
                page.locator('.avatar-trigger').click()
                assert page.locator('.avatar-options:visible').count() == 1
                choice.locator('..').click()
                assert choice.is_checked(), (choice.input_value(), page.locator('[name=avatar_picker]:checked').evaluate_all('(els) => els.map(el => el.value)'), page.locator('#avatar-status').inner_text(), page.locator('.avatar-options').is_visible())
                assert page.locator('#avatar-status').inner_text() == ''
                assert page.locator('.avatar-options:visible').count() == 0
                assert page.locator('.avatar-trigger.selected img').get_attribute('src').endswith('/' + choice.input_value() + '.svg')
            page.locator('.avatar-trigger').focus()
            page.keyboard.press('ArrowDown')
            page.get_by_role('radio', name='Avatar 15', exact=True).focus()
            page.keyboard.press('ArrowRight')
            assert page.locator('[name="avatar_picker"][value="neutral-4"]').is_checked()
            assert page.locator('.avatar-options:visible').count() == 0
            for width in (1280, 390, 320):
                page.set_viewport_size({'width': width, 'height': 900})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
                assert page.locator('.avatar-option img').evaluate_all('(els) => els.every(el => el.complete && el.naturalWidth > 0)')
                assert page.locator('.avatar-picker').bounding_box()['height'] < 180
                page.locator('fieldset').screenshot(path=str(screenshots / f'human_avatars_{width}.png'))
                page.locator('.avatar-trigger').click()
                page.locator('.avatar-options').screenshot(path=str(screenshots / f'human_avatars_expanded_{width}.png'))
                assert page.locator('.avatar-options:visible').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
                popup_box = page.locator('.avatar-options').bounding_box()
                assert popup_box['x'] >= 0 and popup_box['x'] + popup_box['width'] <= width
                page.keyboard.press('Escape')
                assert page.locator('.avatar-options:visible').count() == 0
            load('IntroAvatarSaved')
            assert page.locator('[name="avatar_picker"][value="neutral-4"]').is_checked()
            assert page.locator('.avatar-trigger.selected img').get_attribute('src').endswith('/neutral-4.svg')
            assert page.locator('.avatar-options:visible').count() == 0
            touch_context = browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True)
            touch_context.route('**/*', serve)
            touch_page = touch_context.new_page()
            touch_page.goto('http://127.0.0.1:8765/qa/IntroReactions.html', wait_until='load')
            touch_page.evaluate('window.liveSend = data => window.liveRecv(data)')
            touch_page.locator('.avatar-trigger').tap()
            assert touch_page.locator('.avatar-options').is_visible()
            touch_page.locator('[name=avatar_picker][value="neutral-6"]').locator('..').tap()
            assert touch_page.locator('.avatar-trigger img').get_attribute('src').endswith('/neutral-6.svg')
            assert touch_page.locator('.avatar-options').is_hidden()
            touch_context.close()
            for name in ('BlockFeedback_qualitative_social', 'MessageReactionFeedback'):
                load(name)
                avatars = page.locator('img[src*="/avatars/"]')
                assert avatars.count() > 0
                assert avatars.evaluate_all('(els) => els.every(el => /\\/(feminine|masculine|neutral)-[1-6]\\.svg$/.test(el.src) && el.complete && el.naturalWidth > 0)')
                if name.startswith('BlockFeedback'):
                    assert page.locator('.fb-preview-avatar').first.get_attribute('src').endswith('/neutral-3.svg')
                    assert page.locator('.fb-received img.fb-avatar').count() == 0
                    assert len(page.locator('.fb-received .fb-avatar').inner_text()) == 1
                else:
                    assert page.locator('.rf-post:not(.rf-own) img.rf-avatar').count() == 0
                    assert all(len(value) == 1 for value in page.locator('.rf-post:not(.rf-own) .rf-avatar').all_text_contents())
            assert not errors, errors
            browser.close()
            print(json.dumps({'passed': '18 human avatar selections, keyboard navigation, images at three widths, own and peer message avatars', 'screenshots': str(screenshots)}))
            return

        if (fixtures / 'MessageReactionFeedback.html').exists():
            load('MessageReactionFeedback')
            assert page.locator('.rf-post').count() == 5
            assert page.locator('.rf-own').count() == 2
            assert page.locator('.rf-own .rf-name').all_text_contents() == ['Bot'] * 2
            assert 0 < page.locator('.rf-reaction').count() <= 35
            totals = page.locator('.rf-post').evaluate_all('(els) => els.map(el => Number(el.dataset.total))')
            assert totals == sorted(totals, reverse=True)
            assert all('out of 5' in text for text in page.locator('.rf-text').all_text_contents())
            assert all(key.startswith(('block-', 'received-')) for key in page.locator('.rf-post').evaluate_all('(els) => els.map(el => el.dataset.messageKey)'))
            assert page.locator('.rf-reaction button, .rf-reaction input').count() == 0
            counts = page.locator('.rf-count').all_text_contents()
            page.reload()
            assert page.locator('.rf-count').all_text_contents() == counts
            assert all('Earlier' not in t for t in page.locator('.rf-time').all_text_contents())
            for width, height in [(1280, 900), (390, 844), (320, 740)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.wait_for_timeout(400)
                assert page.locator('.rf-sidebar').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
                for post in page.locator('.rf-post').all():
                    box = post.bounding_box()
                    for reaction in post.locator('.rf-reaction').all():
                        badge = reaction.bounding_box()
                        assert badge['y'] < box['y'] + box['height'] < badge['y'] + badge['height']
                        assert badge['x'] >= box['x'] and badge['x'] + badge['width'] <= box['x'] + box['width']
                        assert reaction.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
                page.screenshot(path=str(screenshots/f'reaction_counts_{width}.png'))
                page.locator('.rf-next').scroll_into_view_if_needed()
                assert page.locator('.rf-next').is_visible()
            load('MessageReactionFeedbackEmpty')
            assert page.locator('.rf-post').count() == 3
            assert page.locator('.rf-own').count() == 0
            assert all(int(x) > 0 for x in page.locator('.rf-count').all_text_contents())
            page.set_viewport_size({'width': 1280, 'height': 900})
            checked.append('synthetic reaction counts, stable refresh, timestamps, mobile borders, empty sent-message state')

        load('IQReferencePoint')
        assert 'IQ compared with 20 other Prolific respondents' in page.locator('body').inner_text()
        assert 'separately drawn comparison group for each component' not in page.locator('body').inner_text()
        assert page.locator('.dist-wrap + #iq-comparison-explanation').count() == 1
        assert 'components of IQ compared with 20 other Prolific respondents' in ' '.join(page.locator('#iq-comparison-explanation').inner_text().split())
        halves = page.locator('strong', has_text='50%')
        assert halves.count() == 2
        for half in halves.all():
            assert half.evaluate('(el) => getComputedStyle(el).color') == 'rgb(139, 0, 0)'
        load('IntroReactions')
        intro = page.locator('body').inner_text()
        assert 'Other participants can also react to any message you send using the same emojis.' in intro
        assert page.locator('img.care-icon').count() == 1
        assert ', and 😡' in ' '.join(intro.split())
        assert 'let you know' in intro
        assert 'follow up with you' not in intro
        assert 'how many of each type of reaction' in intro
        assert 'likes and dislikes' not in intro
        load('IntroNoReactions')
        assert 'You can also react' not in page.locator('body').inner_text()
        assert 'Other participants can also react' not in page.locator('body').inner_text()
        for format in ('quantitative_social', 'qualitative_social'):
            for reactions in (False, True):
                load('Intro_' + format + ('_reactions' if reactions else '_no_reactions'))
                text = ' '.join(page.locator('body').inner_text().split())
                assert ('Other participants can also react' in text) == reactions
                assert 'After each period with social interactions' not in text
                assert 'Your messages will' not in text
                assert page.locator('.avatar-option').count() == 18
                page.evaluate('window.liveSend = data => window.liveRecv(data)')
                page.locator('.avatar-trigger').click()
                page.get_by_role('radio', name='Avatar 15', exact=True).locator('..').click()
                assert page.locator('[name="avatar_picker"][value="neutral-3"]').is_checked()
                assert page.locator('#avatar-status').inner_text() == ''
        for asked in (0, 1):
            for accepted in (0, 1):
                load(f'FinalResults_{asked}_{accepted}')
                text = ' '.join(page.locator('body').inner_text().split())
                maximum = 0.50 + 0.25 * accepted + 0.50 * asked
                assert f'${maximum:.2f}' in text
                assert ('estimates of your IQ and percentile' in text) == bool(asked)
                assert ('We will follow up with you after the data collection is complete' in text) == (not asked)
        checked.append('both 50% highlights, reaction disclosure, and four final-bonus conditions')
        load('Experience_writing')
        assert page.locator('strong', has_text='content').count() == 1
        assert page.locator('strong', has_text='content').evaluate('(el) => getComputedStyle(el).color') == 'rgb(139, 0, 0)'
        assert 'I tried to write messages that would help them feel better about their performance.' in page.locator('body').inner_text()
        assert 'I tended to emphasize that I had performed better than they had.' in page.locator('body').inner_text()
        well_block = page.locator('.motive-block').filter(has_text='When another participant said they did well')
        assert 'I tried to write messages that acknowledged how well they had done.' in well_block.inner_text()
        assert 'I tended to emphasize that I had performed just as well as or better than they had.' in well_block.inner_text()
        assert well_block.locator('input[name="write_peer_well_acknowledge"]').count() == 5
        assert well_block.locator('input[name="write_peer_well_compare"]').count() == 5
        assert page.locator('td.motive-text', has_text='I was more likely to write critically about my own performance.').count() == 2
        checked.append('introduction and writing wording')

        load('BlockFeedbackReactions')
        palette = [('Like', 'like', '👍'), ('Love', 'love', '❤️'), ('Care', 'care', '🤗'), ('Haha', 'haha', '😆'), ('Wow', 'wow', '😮'), ('Sad', 'sad', '😢'), ('Angry', 'angry', '😡')]
        buttons = [page.get_by_role('button', name=name, exact=True) for name, _, _ in palette]
        assert page.locator('[data-reaction]').count() == 7
        assert page.get_by_role('button', name='Dislike', exact=True).count() == 0
        field = page.locator('#id_received_reaction')
        page.evaluate('sessionStorage.clear()')
        page.reload()
        page.locator('.reaction-trigger').hover()
        assert page.locator('#reaction-palette').is_visible()
        assert field.input_value() == 'none'
        page.locator('.reaction-trigger').focus()
        page.keyboard.press('Escape')
        assert page.locator('#reaction-palette').is_hidden()
        page.keyboard.press('ArrowDown')
        assert page.locator('[data-reaction="like"]').evaluate('(el) => el === document.activeElement')
        for button, (_, value, emoji) in zip(buttons, palette):
            page.locator('.reaction-trigger').press('ArrowDown')
            if value == 'care':
                assert button.locator('img.care-icon').count() == 1
            else:
                assert button.inner_text().strip() == emoji
            button.click()
            assert field.input_value() == value
            assert page.locator('[data-reaction][aria-pressed="true"]').count() == 1
            page.reload()
            assert field.input_value() == value
            page.locator('.reaction-trigger').press('ArrowDown')
            button.click()
            assert field.input_value() == 'none'
        page.locator('.reaction-trigger').press('ArrowDown')
        buttons[0].click()
        page.locator('.reaction-trigger').press('ArrowDown')
        buttons[3].click()
        assert field.input_value() == 'haha'
        assert page.locator('[data-reaction="like"]').get_attribute('aria-pressed') == 'false'
        page.locator('.reaction-trigger').press('ArrowDown')
        buttons[3].click()
        for width, height in [(1280, 900), (390, 844), (320, 740)]:
            page.set_viewport_size({'width': width, 'height': height})
            bubble = page.locator('.fb-post.fb-has-reactions').bounding_box()
            edge = bubble['y'] + bubble['height']
            for button in [page.locator('.reaction-trigger')]:
                box = button.bounding_box()
                assert box['y'] < edge < box['y'] + box['height'], (width, box, bubble)
                assert abs(box['y'] + box['height'] / 2 - edge) <= 2
                assert box['x'] >= bubble['x'] and box['x'] + box['width'] <= bubble['x'] + bubble['width']
                assert button.evaluate('(el) => getComputedStyle(el).borderRadius') == '999px'
            page.screenshot(path=str(screenshots/f'reactions_{width}.png'))
        page.set_viewport_size({'width': 1280, 'height': 900})
        page.screenshot(path=str(screenshots/'reactions.png'))
        load('BlockFeedbackNoReactions')
        assert page.locator('[data-reaction]').count() == 0
        assert field.input_value() == 'none'
        checked.append('all seven reactions, switch/remove/refresh, no dislike, and untreated arm')

        load('BlockFeedback_quantitative_social')
        assert page.locator('.fb-emoji').count() == 0
        assert page.locator('input[name="report_number"]').count() == 1
        load('BlockFeedback_qualitative_social')
        choices = page.locator('.fb-emoji input[type="radio"]')
        assert choices.count() == 7
        assert choices.evaluate_all('(els) => els.map(el => el.value)') == [emoji for _, _, emoji in palette]
        for width in (1280, 390, 320):
            page.set_viewport_size({'width': width, 'height': 900})
            for choice in choices.all():
                page.locator('.emoji-compose-trigger').click()
                choice.locator('..').click()
                assert choice.is_checked()
                preview = page.locator('.fb-preview-body').first
                if choice.input_value() == '🤗':
                    assert preview.locator('img.care-icon').count() == 1
                else:
                    assert choice.input_value() in preview.inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            page.screenshot(path=str(screenshots/f'qualitative_composer_{width}.png'))
        page.set_viewport_size({'width': 1280, 'height': 900})
        checked.append('matching qualitative emoji palette; quantitative composition stays number-only')

        for name, field_name in [('IQFeedback', 'iq_report_message'), ('GlobalIQFeedback', 'global_report_message')]:
            load(name + '_qualitative_social')
            page.locator('.emoji-compose-trigger').click()
            page.get_by_role('radio', name='Care', exact=True).locator('..').click()
            assert page.locator('.fb-preview-body').first.locator('img.care-icon').count() == 1
            page.locator('[name="' + field_name + '"]').fill('I felt good about this task.')
            assert 'I felt good about this task.' in page.locator('.fb-preview-body').first.inner_text()
            page.locator('#fb-compose-next').click()
            assert page.locator('#fb-confirm-next').is_visible()
            load(name + '_quantitative_social')
            assert page.locator('.emoji-compose-trigger').count() == 0
        checked.append('task and overall IQ emoji-only preview, text entry, and confirmation')

        load('PerceivedPercentile')
        estimate_text = ' '.join(page.locator('body').inner_text().split())
        assert '0 means you think you did worse than every other participant.' in estimate_text
        assert '10 means you think you did better than half of the other participants, and worse than the other half of participants.' in estimate_text
        assert '20 means you think you did better than every other participant.' in estimate_text
        for phrase in ('worse than every other', 'better than half', 'worse than the other half', 'better than every other'):
            emphasis = page.get_by_text(phrase, exact=True)
            assert emphasis.evaluate('(el) => getComputedStyle(el).color') == 'rgb(139, 0, 0)'
            assert int(emphasis.evaluate('(el) => getComputedStyle(el).fontWeight')) >= 600
        field = page.locator('#perceived_outperformed_count')
        assert field.input_value() == ''
        page.locator('#percentile-track-placeholder').click()
        slider = page.locator('#percentile-slider')
        assert slider.get_attribute('max') == '20'
        slider.focus()
        slider.press('Home')
        assert field.input_value() == '0'
        assert '0%' in page.locator('#slider-value').inner_text()
        for _ in range(10):
            slider.press('ArrowRight')
        assert field.input_value() == '10'
        assert '50%' in page.locator('#slider-value').inner_text()
        slider.press('End')
        assert field.input_value() == '20'
        assert '100%' in page.locator('#slider-value').inner_text()
        page.screenshot(path=str(screenshots/'percentile.png'))
        checked.append('slider endpoints 0/20 and midpoint 10 map to 0%/100%/50%')

        for width, height in [(1280, 900), (390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            for name, selector, phrase in [
                ('BigFiveSurvey1', 'thead', 'I see myself as someone who'),
                ('SelfEsteemSurvey', 'thead', 'Please choose the option that best describes you.'),
                ('WTACompare', '.wta-table thead', 'social interactions'),
            ]:
                load(name)
                header = page.locator(selector).first
                original = header.bounding_box()
                page.evaluate('(y) => window.scrollTo(0, y)', original['y'] + 180)
                page.wait_for_timeout(100)
                box = header.bounding_box()
                # Short batteries may end before their header reaches the top.
                expected_top = max(0, original['y'] - page.evaluate('scrollY'))
                assert abs(box['y'] - expected_top) <= 2, (name, width, box, expected_top)
                assert header.evaluate('(el) => getComputedStyle(el).position') == 'sticky'
                assert phrase in header.inner_text()
                page.screenshot(path=str(screenshots/f'{name}_{width}.png'))
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), (name, width, 'horizontal overflow')
                if name == 'WTACompare':
                    assert 'Payment per correct answer' in header.inner_text()
                    assert 'Your choice' in header.inner_text()
                    next_header = page.locator(selector).nth(1)
                    position = next_header.bounding_box()['y'] + page.evaluate('scrollY')
                    page.evaluate('(y) => window.scrollTo(0, y)', position + 180)
                    page.wait_for_timeout(100)
                    assert abs(next_header.bounding_box()['y']) <= 2
                    assert header.bounding_box()['y'] < 0
                page.screenshot(path=str(screenshots/f'{name}_{width}.png'))
            checked.append(f'sticky headers and block transitions at {width}px')
            load('NarcissismSurvey')
            assert page.locator('.npi-instruction').evaluate('(el) => getComputedStyle(el).position') == 'static'
        checked.append('reaction mini-bubbles straddle message border on desktop/mobile; narcissism instruction is not sticky')
        assert not errors, errors
        browser.close()
    print(json.dumps({'passed':checked, 'screenshots':str(screenshots)},indent=2))


if __name__ == '__main__':
    main()
