"""Optional real-browser smoke test. Install playwright and Chromium first."""
from pathlib import Path
from threading import Thread
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright
from multi_asset.dashboard import create_app
from multi_asset.config import ROOT
app=create_app()
server=make_server('127.0.0.1',0,app.server,threaded=True)
thread=Thread(target=server.serve_forever,daemon=True);thread.start()
folder=ROOT/'reports/local';folder.mkdir(parents=True,exist_ok=True)
errors=[]
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1050})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='networkidle')
        page.wait_for_selector('#kpis strong')
        initial=page.locator('#kpis').inner_text()
        print('Balanced:',initial.replace('\n',' | '))
        page.locator('#profile').click()
        page.get_by_text('Growth',exact=True).click()
        page.wait_for_function("previous => document.querySelector('#kpis').innerText !== previous",arg=initial)
        print('Growth:',page.locator('#kpis').inner_text().replace('\n',' | '))
        page.locator('#fund').click()
        page.get_by_text('MINT',exact=True).click()
        page.wait_for_function("document.querySelector('#fund-table').innerText.includes('MINT')")
        slider=page.locator('#equity [role="slider"]')
        slider.press('Home')
        for _ in range(3):slider.press('ArrowRight')
        page.locator('#solve').click()
        page.wait_for_function("document.querySelector('#custom-message').innerText.includes('Equity 25%')")
        page.locator('#profile').click();page.get_by_text('Balanced',exact=True).click()
        page.wait_for_function("previous => document.querySelector('#kpis').innerText === previous",arg=initial)
        page.screenshot(path=str(folder/'dashboard-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_function("document.documentElement.scrollWidth <= window.innerWidth + 1 && [...document.querySelectorAll('.js-plotly-plot')].every(e => e.getBoundingClientRect().right <= window.innerWidth)")
        page.screenshot(path=str(folder/'dashboard-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'Mobile horizontal overflow'
        assert not errors,errors
        print('Browser checks passed: profile, fund, custom calculation, desktop/mobile; no JavaScript errors.')
        browser.close()
finally:
    server.shutdown()
