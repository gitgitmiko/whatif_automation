"""Animate still scene pictures into short Omni clips through Flow's agent composer, one browser session for all.

gflow cannot do image-to-video on this account: Flow serves it the agent-only composer, and gflow drives that
composer for text prompts only. The composer itself takes pictures ("Add ingredients" -> Upload media -> Add to
prompt), so this attaches each picture, asks for a clip that starts from it, approves the credit confirmation
only when it quotes one clip at no more than the allowed price, and downloads the result with gflow's own
helpers. Runs under gflow's venv (it imports gflow_cli):

    flowclip.py job.json        job = {"project": id, "max_credits": 12, "dry_run": false,
                                       "items": [{"image": path, "prompt": text, "out": path}]}

Prints one JSON line per item: {"out": path, "ok": bool, "credits": n, "error": text}. Stops at the first item
that fails after its submit, since whether it was billed is then unknown.
"""
import asyncio, json, re, sys, time
from pathlib import Path

from playwright.async_api import async_playwright
from gflow_cli.auth import profile_dir
from gflow_cli.api.client import channel_for_profile
from gflow_cli.api.transports import agent_only_composer as aoc

PROFILE = "sjatmiko30"
BOX = "flow-creative-agent-prompt-box"
TUNE = f"{BOX} button:has(mat-icon:text-is('tune'))"
LIVE_GATE = aoc.LIVE_GATE
APPROVE_ROW, REJECT_ROW = aoc.APPROVE_ROW, aoc.REJECT_ROW
GATE_WAIT_S, CLIP_WAIT_S = 180, 900
DIRECTIVE = ("Make me a {seconds} second video in a 16:9 aspect ratio that starts exactly from the attached image as "
             "its first frame, keeping the same drawing style, the same people and the same place. {prompt} "
             "No text, no captions.")


class Billed(Exception):
    """A failure after the submit: the clip may have been paid for."""


async def confirm_is_always(page):
    """Agent settings' "Confirm before generating" must be Always, or a request could bill unseen."""
    await page.locator(TUNE).last.click()
    await page.locator("flow-settings-view").wait_for(timeout=8000)
    value = await page.evaluate("""() => { const c = [...document.querySelectorAll(
        'flow-settings-view input[type=radio]')].find(i => i.checked); return c ? c.value : null }""")
    await page.locator(aoc.PANE_BACK).first.click()
    await page.wait_for_timeout(1500)
    return value == "1"  # Always 1, Never 2 (gflow measured these by input value)


async def attach(page, image):
    """A fresh agent session with this picture as its one ingredient."""
    new = page.locator("flow-agent-panel button[aria-label='Start new session']")
    if await new.count():
        await new.first.click()
        await page.wait_for_timeout(2500)
    await page.locator(f"{BOX} button[aria-label='Add ingredients to the prompt box']").click()
    upload = page.locator(".cdk-overlay-container button:visible", has_text="Upload media").first
    await upload.wait_for(timeout=8000)
    # A name nothing else in the project has, so the picker row can be found by it after the upload.
    name = f"clip-{int(time.time() * 1000)}{Path(image).suffix}"
    async with page.expect_file_chooser(timeout=10000) as fc:
        await upload.click()
    await (await fc.value).set_files({"name": name, "mimeType": "image/jpeg", "buffer": Path(image).read_bytes()})
    row = page.locator(".cdk-overlay-container button:visible", has_text=name).first
    await row.wait_for(timeout=60000)
    await row.click()
    await page.wait_for_timeout(1500)
    await page.get_by_role("button", name="Add to prompt").click()
    chip = page.locator(f"{BOX} img")
    for _ in range(30):
        if await chip.count():
            break
        await page.wait_for_timeout(1000)
    else:
        raise RuntimeError("the uploaded picture never showed up in the prompt box")
    await page.wait_for_timeout(2000)


async def one(page, comp, item, max_credits, dry_run):
    await attach(page, item["image"])
    base, head0 = await comp._video_baseline(page)
    gates0 = await page.locator(LIVE_GATE).count()
    editor = page.locator(f"{BOX} div.ProseMirror").last
    await editor.click()
    await page.keyboard.insert_text(DIRECTIVE.format(seconds=item.get("seconds", 4), prompt=item["prompt"]))
    await page.locator(f"{BOX} button[aria-label='Start generation']").click()
    t0 = time.time()
    while await page.locator(LIVE_GATE).count() <= gates0:
        if time.time() - t0 > GATE_WAIT_S:
            raise Billed(f"no credit confirmation within {GATE_WAIT_S}s")
        await page.wait_for_timeout(2000)
    gate = page.locator(LIVE_GATE).nth(gates0)
    title = (await gate.locator(aoc.GATE_TITLE).first.inner_text()).strip()
    nums = [int(n) for n in re.findall(r"\d+", title)]
    ok = len(nums) >= 2 and nums[0] == 1 and nums[-1] <= max_credits
    if dry_run or not ok:
        await gate.locator(REJECT_ROW).first.click(timeout=5000)
        await page.locator(LIVE_GATE).nth(gates0).wait_for(state="detached", timeout=15000)
        if not ok:
            raise RuntimeError(f"confirmation quoted {title!r}; rejected")
        return {"ok": False, "credits": 0, "error": f"dry run, rejected: {title}"}
    await gate.locator(APPROVE_ROW).first.click(timeout=5000)
    await page.locator(LIVE_GATE).nth(gates0).wait_for(state="detached", timeout=15000)
    t0, peak = time.time(), 0
    while time.time() - t0 < CLIP_WAIT_S:
        state = await page.evaluate(aoc._VIDEO_JS)
        peak = max(peak, state["pending"])
        if peak > 1:
            raise Billed(f"{peak} clips queued where 1 was asked")
        named = [u for u in aoc._video_uuids(state) if u not in base]
        ready = await comp._ready_video(page, state, named, head0)
        if ready:
            async def save(uuid, body):
                Path(item["out"]).write_bytes(body)
                return Path(item["out"])
            await aoc.download_video(page, ready.src, ready.uuid, save)
            return {"ok": True, "credits": nums[-1], "error": ""}
        await page.wait_for_timeout(5000)
    raise Billed(f"the clip was not ready within {CLIP_WAIT_S}s")


async def main(job):
    p = profile_dir(PROFILE)
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(p), headless=False, viewport={"width": 1280, "height": 720}, locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}, channel=channel_for_profile(p),
            ignore_default_args=["--enable-automation", "--no-sandbox"],
            args=["--password-store=basic", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"])
        await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            await page.goto(f"https://flow.google.com/project/{job['project']}?hl=en", wait_until="domcontentloaded")
            await page.locator(TUNE).last.wait_for(timeout=40000)
            await page.wait_for_timeout(4000)
            if not await confirm_is_always(page):
                sys.exit("Flow's agent is not set to confirm before generating; refusing to send anything")
            comp = aoc.AgentOnlyComposer()
            for item in job["items"]:
                try:
                    r = await one(page, comp, item, job.get("max_credits", 12), job.get("dry_run", False))
                except Billed as e:
                    print(json.dumps({"out": item["out"], "ok": False, "credits": None, "error": str(e)}), flush=True)
                    await page.screenshot(path=str(Path(item["out"]).with_suffix(".error.png")))
                    break
                except Exception as e:  # noqa: BLE001 - before the submit or after a rejection: nothing was billed
                    r = {"ok": False, "credits": 0, "error": repr(e)[:500]}
                    await page.screenshot(path=str(Path(item["out"]).with_suffix(".error.png")))
                print(json.dumps({"out": item["out"], **r}), flush=True)
        finally:
            await ctx.close()


if __name__ == "__main__":
    asyncio.run(main(json.loads(Path(sys.argv[1]).read_text())))
