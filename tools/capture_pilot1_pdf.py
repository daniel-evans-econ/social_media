"""Walk INITIAL (send-only) pilot; screenshot distinctive pages; write PDF.

Skips repeat QuestionPage shots after the first two in each period of 15, so the
PDF stays usable for side-by-side comparison with the IQ pilot.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import builtins

import fitz
from playwright.async_api import async_playwright


def print(*a, **k):  # noqa: A001 — force flush for long runs
    builtins.print(*a, **{**k, "flush": True})

BASE = "http://127.0.0.1:8001"
OUT_DIR = Path(r"C:\Users\Evans\Desktop\research\social_media\pilot_1_analysis\survey_pdf")
OUT_PDF = OUT_DIR / "pilot_1_send_only_walkthrough.pdf"
PAGE_DIR = OUT_DIR / "pages_pdf"


async def create_session() -> str:
    import websockets
    uri = "ws://127.0.0.1:8001/create_demo_session"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"session_config": "cognitive_tasks"}))
        while True:
            data = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
            if data.get("session_url"):
                return data["session_url"]
            if data.get("traceback") or data.get("validation_errors"):
                raise RuntimeError(data)


async def first_participant_url(session_url: str, page) -> str:
    await page.goto(BASE + session_url, wait_until="domcontentloaded")
    return await page.eval_on_selector(
        'a[href*="InitializeParticipant"]', "el => el.href"
    )


async def hide_chrome(page):
    """Strip oTree debug chrome so the printed page matches the live survey look."""
    await page.add_style_tag(content="""
      @media print {
        html, body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      }
      /* Hide oTree debug dump and footer noise */
      #debug, .otree-debug, details { display: none !important; }
    """)
    await page.evaluate("""() => {
      for (const el of document.querySelectorAll('pre, .card, details')) {
        const t = (el.textContent || '');
        if (t.includes('vars_for_template') || t.includes('ID in group') || t.includes('Debug')) {
          el.style.display = 'none';
        }
      }
      for (const el of [...document.querySelectorAll('h2,h3,h4,h5')]) {
        if ((el.textContent || '').trim().toLowerCase().startsWith('debug')) {
          let n = el;
          while (n) { n.style.display = 'none'; n = n.nextElementSibling; }
        }
      }
      // Hide "Powered by oTree" footer if present
      for (const el of document.querySelectorAll('footer, .otree-footer, small')) {
        if (/powered by otree/i.test(el.textContent || '')) el.style.display = 'none';
      }
    }""")


async def save_page_pdf(page, path: Path, label: str):
    await hide_chrome(page)
    # Header banner so pages are identifiable when flipping
    await page.evaluate(
        """(label) => {
          let ban = document.getElementById('pdf-capture-banner');
          if (!ban) {
            ban = document.createElement('div');
            ban.id = 'pdf-capture-banner';
            ban.style.cssText = 'font: 12px/1.3 Helvetica,Arial,sans-serif; color:#333;'
              + 'padding:6px 10px; border-bottom:1px solid #ccc; margin-bottom:8px;';
            const root = document.querySelector('.otree-body, .container, body');
            (root || document.body).insertBefore(ban, (root || document.body).firstChild);
          }
          ban.textContent = 'Pilot 1 (send-only) — ' + label;
        }""",
        label,
    )
    await page.pdf(
        path=str(path),
        format="A4",
        print_background=True,
        margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
    )


async def label_for(page) -> str:
    info = await page.evaluate("""() => {
      const h2 = document.querySelector('h2');
      const prompt = document.querySelector('.q-prompt, .ti-prompt');
      const title = document.title || '';
      return {
        h2: h2 ? h2.innerText.trim() : '',
        prompt: prompt ? prompt.innerText.trim().slice(0, 80) : '',
        title,
        hasQ: !!document.querySelector("input[name='q_answer']"),
        hasReport: !!document.querySelector("input[name='report_shared'], textarea[name='report_message'], input[name='report_number']"),
        hasStroop: !!document.querySelector("input[name='stroop_1'], input[name^='stroop_']"),
      };
    }""")
    if info.get("h2"):
        return info["h2"]
    if info.get("hasReport"):
        return "Block feedback / send decision"
    if info.get("hasQ"):
        return info.get("prompt") or "Question"
    if info.get("hasStroop"):
        return "Stroop / color task"
    title = re.sub(r"^\[[^\]]+\]\s*", "", info.get("title") or "").strip()
    if title and not title.isdigit():
        return title
    return page.url.rstrip("/").split("/")[-1]


async def is_question_page(page) -> bool:
    return await page.locator("input[name='q_answer']").count() > 0


async def ensure_radio(page, name: str, prefer_last: bool = False):
    group = page.locator(f"input[name='{name}']")
    n = await group.count()
    if not n:
        return
    if await page.locator(f"input[name='{name}']:checked").count():
        return
    idx = (n - 1) if prefer_last else min(1, n - 1)
    lab = page.locator(f"label:has(input[name='{name}'])")
    if await lab.count():
        try:
            await lab.nth(min(idx, await lab.count() - 1)).click(force=True, timeout=2000)
            return
        except Exception:
            pass
    await page.evaluate(
        """({name, idx}) => {
          const all = [...document.querySelectorAll(`input[name='${name}']`)];
          const r = all[idx] || all[0];
          if (!r) return;
          r.checked = true;
          r.dispatchEvent(new Event('input', {bubbles:true}));
          r.dispatchEvent(new Event('change', {bubbles:true}));
        }""",
        {"name": name, "idx": idx},
    )


async def handle_block_feedback(page) -> bool:
    """Drive the BlockFeedback multi-step sidebar. Returns True if handled."""
    if not await page.locator("#fb-score-step, #fb-compose-step, #fb-share-step").count():
        return False

    # Control: wait for auto-submit (~5s)
    in_treatment = await page.locator("#fb-compose-step").count() > 0
    if not in_treatment:
        await page.wait_for_timeout(5500)
        return True

    # Wait until compose is visible (auto-advance from score)
    for _ in range(40):
        visible = await page.evaluate(
            """() => {
              const el = document.getElementById('fb-compose-step');
              return el && el.style.display !== 'none';
            }"""
        )
        if visible:
            break
        await page.wait_for_timeout(250)

    # Fill compose
    if await page.locator("input[name='report_number']").count():
        rn = page.locator("input[name='report_number']")
        typ = await rn.first.get_attribute("type")
        if typ == "number":
            await rn.first.fill("4")
        else:
            await ensure_radio(page, "report_number", prefer_last=True)
    if await page.locator("input[name='report_emoji']").count():
        await page.evaluate("""() => {
          const r = document.querySelector("input[name='report_emoji']");
          if (r) { r.checked = true; r.dispatchEvent(new Event('change', {bubbles:true})); }
        }""")
    if await page.locator("textarea[name='report_message']").count():
        await page.fill("textarea[name='report_message']", "Felt fine about that block.")

    if await page.locator("#fb-compose-next").count():
        await page.locator("#fb-compose-next").click(force=True)
        await page.wait_for_timeout(300)

    if await page.locator("#fb-confirm-next").count():
        await page.locator("#fb-confirm-next").click(force=True)
        await page.wait_for_timeout(300)

    # Share decision
    await page.evaluate("""() => {
      const opts = [...document.querySelectorAll("input[name='report_shared']")];
      const yes = opts.find(o => /true|1|yes/i.test(String(o.value)));
      const r = yes || opts[0];
      if (r) { r.checked = true; r.dispatchEvent(new Event('change', {bubbles:true})); }
    }""")
    return True


async def click_next(page):
    for sel in ("#fb-final-submit",
                "#fb-continue-btn",
                "button.otree-btn-next",
                "button[type=submit]"):
        loc = page.locator(sel)
        if await loc.count():
            btn = loc.first
            try:
                if await btn.is_visible():
                    await btn.click(force=True, timeout=8000)
                    return
            except Exception:
                continue
    await page.evaluate("""() => {
      const f = document.querySelector('form');
      if (f) { if (f.requestSubmit) f.requestSubmit(); else f.submit(); }
    }""")


async def handle_task_intro(page) -> bool:
    if not await page.locator("#ti-check, .ti-opt, #ti-count").count():
        return False
    if await page.locator(".ti-opt").count():
        correct = await page.evaluate("""() => {
          const pre = document.body.innerText;
          const m = pre.match(/example_correct['\\\":\\s]+['\"]?([A-H0-9]+)/);
          return m ? m[1] : null;
        }""")
        clicked = False
        if correct:
            loc = page.locator(f'.ti-opt[data-value="{correct}"]')
            if await loc.count():
                await loc.first.click()
                clicked = True
        if not clicked:
            for v in ("G", "A"):
                loc = page.locator(f'.ti-opt[data-value="{v}"]')
                if await loc.count():
                    await loc.first.click()
                    clicked = True
                    break
            if not clicked:
                await page.locator(".ti-opt").first.click()
    if await page.locator("#ti-count").count():
        await page.fill("#ti-count", "3")
    if await page.locator("#ti-check").count():
        await page.locator("#ti-check").click()
        for _ in range(25):
            if not await page.locator(".ti-next-wrap.locked").count():
                break
            await page.wait_for_timeout(150)
    return True


async def fill_and_advance(page):
    prev = page.url
    if await handle_block_feedback(page):
        # Control may already have auto-submitted.
        if page.url != prev:
            return
        await click_next(page)
        return

    await handle_task_intro(page)

    for name in ("consent", "llm_rule_confirm"):
        loc = page.locator(f"input[name='{name}']")
        if await loc.count() and not await page.locator(f"input[name='{name}']:checked").count():
            await loc.first.check(force=True)

    if await page.locator("input[name='prolific_id']").count():
        await page.fill("input[name='prolific_id']", "abcdefghijklmnopqrstuvwx")

    if await page.locator("input[name='iq_reference_score']").count():
        await page.evaluate("""() => {
          const h = document.querySelector("input[name='iq_reference_score']");
          if (h) h.value = '100';
          const s = document.getElementById('percentile-slider');
          if (s) {
            s.value = '100';
            s.dispatchEvent(new Event('input', {bubbles:true}));
            s.dispatchEvent(new Event('change', {bubbles:true}));
          }
        }""")

    if await page.locator("input[name='display_name']").count():
        await page.fill("input[name='display_name']", "Pilot1PDF")

    if await page.locator("input[name='q_answer']").count():
        if await page.locator(".q-options label").count():
            await page.locator(".q-options label").first.click(force=True)
        else:
            ans = page.locator("input[name='q_answer']")
            typ = await ans.first.get_attribute("type")
            if typ == "radio":
                await page.evaluate("""() => {
                  const r = document.querySelector("input[name='q_answer']");
                  if (r) { r.checked = true; r.dispatchEvent(new Event('change', {bubbles:true})); }
                }""")
            else:
                await ans.first.fill("3")
        await page.evaluate("""() => {
          const h = document.getElementById('q-response-time')
                 || document.querySelector("input[name='q_response_time']");
          if (h) h.value = '2.000';
        }""")

    if await page.locator("input[name='report_number']").count():
        rn = page.locator("input[name='report_number']")
        typ = await rn.first.get_attribute("type")
        if typ == "radio":
            await ensure_radio(page, "report_number", prefer_last=True)
        else:
            await rn.first.fill("4")

    await ensure_radio(page, "report_emoji")
    if await page.locator("textarea[name='report_message']").count():
        await page.fill("textarea[name='report_message']", "Felt fine about that block.")
    if await page.locator("input[name='report_shared']").count():
        await page.evaluate("""() => {
          const opts = [...document.querySelectorAll("input[name='report_shared']")];
          const yes = opts.find(o => /true|1|yes/i.test(String(o.value)));
          const r = yes || opts[0];
          if (r) { r.checked = true; r.dispatchEvent(new Event('change', {bubbles:true})); }
        }""")

    for name, val in (
        ("perceived_relative_performance", "50"),
        ("perceived_percentile_confidence", "50"),
    ):
        if await page.locator(f"input[name='{name}']").count():
            await page.evaluate(
                """({name, val}) => {
                  const h = document.querySelector(`input[name='${name}']`);
                  if (h) h.value = val;
                  document.querySelectorAll('input[type=range]').forEach(s => {
                    s.value = val;
                    s.dispatchEvent(new Event('input', {bubbles:true}));
                  });
                }""",
                {"name": name, "val": val},
            )

    for name in ("mood", "performance_satisfaction", "task_enjoyment", "payment_satisfaction"):
        await ensure_radio(page, name)

    for i in range(1, 7):
        if await page.locator(f"input[name='stroop_{i}']").count():
            await ensure_radio(page, f"stroop_{i}")
            await page.evaluate(
                f"""() => {{
                  const h = document.querySelector("input[name='stroop_{i}_response_time']");
                  if (h) h.value = '1.0';
                }}"""
            )

    names = await page.evaluate("""() => {
      const s = new Set();
      document.querySelectorAll('input[type=radio]').forEach(r => {
        if (r.name && !document.querySelector(`input[name="${r.name}"]:checked`)) s.add(r.name);
      });
      return [...s];
    }""")
    for name in names:
        await ensure_radio(page, name)

    for sel, val in (
        ("textarea[name='realism_feedback']", "Send-only pilot walkthrough."),
        ("textarea[name='comments']", "PDF capture."),
        ("input[name='age']", "30"),
        ("input[name='social_media_hours']", "2"),
        ("input[name='survey_reliability']", "7"),
    ):
        if await page.locator(sel).count():
            cur = await page.input_value(sel)
            if not (cur or "").strip():
                await page.fill(sel, val)

    for name, value in (("gender", "woman"), ("education", "bachelor")):
        if await page.locator(f"select[name='{name}']").count():
            await page.select_option(f"select[name='{name}']", value)

    if await page.locator("input[name='sm_instagram']").count():
        await page.locator("input[name='sm_instagram']").check(force=True)

    for name in ("consent", "llm_rule_confirm"):
        loc = page.locator(f"input[name='{name}']")
        if await loc.count():
            typ = await loc.first.get_attribute("type")
            if typ == "checkbox":
                await loc.first.check(force=True)
            else:
                await ensure_radio(page, name)

    await click_next(page)


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    for old in PAGE_DIR.glob("*.pdf"):
        old.unlink()

    print("creating session…")
    session_url = await create_session()
    print("session", session_url)

    pages = []
    q_in_period = 0
    async with async_playwright() as p:
        print("launching browser…")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1100, "height": 1400})
        page = await context.new_page()
        start = await first_participant_url(session_url, page)
        print("start", start)
        await page.goto(start, wait_until="domcontentloaded")

        for step in range(1, 250):
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(150)
            await hide_chrome(page)
            label = await label_for(page)
            is_q = await is_question_page(page)
            if is_q:
                q_in_period += 1
            else:
                if "example task" in label.lower() or "task intro" in label.lower():
                    q_in_period = 0

            take = (not is_q) or (q_in_period <= 2)
            if "performance" in label.lower() or "send" in label.lower() or "message" in label.lower() or "feedback" in label.lower():
                take = True

            if take and await page.locator("#fb-compose-step").count():
                for _ in range(40):
                    visible = await page.evaluate(
                        """() => {
                          const el = document.getElementById('fb-compose-step');
                          return el && el.style.display !== 'none';
                        }"""
                    )
                    if visible:
                        label = "Block feedback — compose message (send-only)"
                        break
                    await page.wait_for_timeout(250)

            if take:
                fname = f"{len(pages)+1:03d}_{re.sub(r'[^A-Za-z0-9._-]+', '_', label)[:55]}.pdf"
                path = PAGE_DIR / fname
                await save_page_pdf(page, path, label)
                pages.append((label, path))
                print(f"PDF {len(pages):03d} step={step} {label}")
            else:
                print(f"skip step={step} q#{q_in_period} {label}")

            if "FinalResults" in page.url or label.lower().startswith("final"):
                break

            prev = page.url
            try:
                await fill_and_advance(page)
            except Exception as e:
                print("advance error:", e)
                try:
                    await click_next(page)
                except Exception as e2:
                    print("stuck:", e2)
                    break

            try:
                await page.wait_for_function(
                    "(prev) => location.href !== prev", arg=prev, timeout=20000
                )
            except Exception:
                await page.wait_for_timeout(500)
                if page.url == prev:
                    if await page.locator("#ti-check").count():
                        await handle_task_intro(page)
                        try:
                            await click_next(page)
                            await page.wait_for_function(
                                "(prev) => location.href !== prev", arg=prev, timeout=10000
                            )
                            continue
                        except Exception:
                            pass
                    print("no navigation; stopping")
                    break

        await browser.close()

    print("merging PDF…")
    doc = fitz.open()
    cover = doc.new_page(width=595, height=842)
    cover.insert_text((50, 80), "Pilot 1 — send-only survey walkthrough", fontsize=16, fontname="helv")
    cover.insert_text((50, 110), "EXPERIMENT_PILOT = initial", fontsize=11, fontname="helv")
    cover.insert_text(
        (50, 135),
        "Text-selectable pages printed from the live survey (not screenshots).",
        fontsize=10, fontname="helv",
    )
    cover.insert_text(
        (50, 160),
        "Compose + decide whether to send; no receiving; # correct feedback only.",
        fontsize=10, fontname="helv",
    )
    cover.insert_text(
        (50, 185),
        f"{len(pages)} pages (repeat questions omitted after the first two per period).",
        fontsize=10, fontname="helv",
    )

    for label, path in pages:
        src = fitz.open(str(path))
        doc.insert_pdf(src)
        src.close()

    doc.save(str(OUT_PDF), deflate=True, garbage=4)
    doc.close()
    print("wrote", OUT_PDF, "pages", len(pages) + 1, "mb", round(OUT_PDF.stat().st_size / 1e6, 1))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("FATAL", e)
        sys.exit(1)
