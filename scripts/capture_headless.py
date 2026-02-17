from playwright.sync_api import sync_playwright
from pathlib import Path

out_dir = Path('.')
root = 'http://127.0.0.1:8000/'
product_path = '/product/whitening-soap'
products_list_path = '/products'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    console_msgs = []

    def on_console(msg):
        console_msgs.append(f"{msg.type}: {msg.text}")

    page.on('console', on_console)
    # open products list page and navigate via client-side routing to ensure index fallback isn't needed
    page.goto(root, wait_until='networkidle')
    page.wait_for_timeout(600)
    # navigate to products page via client-side routing
    try:
        # click nav link to Products if present
        nav = page.query_selector("a[href='/products']")
        if nav:
            nav.click()
        else:
            page.goto(root.rstrip('/') + products_list_path, wait_until='networkidle')
    except Exception:
        page.goto(root.rstrip('/') + products_list_path, wait_until='networkidle')
    page.wait_for_timeout(1200)
    # find product card link and click
    try:
        link = page.query_selector(f"a[href='{product_path}']")
        if not link:
            link = page.query_selector(f"a[href*='{product_path.split('/').pop()}']")
        if link:
            link.click()
        else:
            # fallback: direct navigation
            page.goto(root.rstrip('/') + product_path, wait_until='networkidle')
    except Exception:
        page.goto(root.rstrip('/') + product_path, wait_until='networkidle')
    page.wait_for_timeout(1500)
    html = page.content()
    (out_dir / 'rendered_product.html').write_text(html, encoding='utf-8')
    (out_dir / 'render_console.log').write_text('\n'.join(console_msgs), encoding='utf-8')
    page.screenshot(path=str(out_dir / 'render_product.png'), full_page=True)
    browser.close()

print('Saved: rendered_product.html, render_console.log, render_product.png')