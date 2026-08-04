import sys
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        page.goto("http://localhost:8000/login/")
        try:
            page.fill("input[name='username']", "admin")
            page.fill("input[name='password']", "admin123")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
        except:
            pass
            
        page.goto("http://localhost:8000/calendario/")
        page.set_viewport_size({"width": 320, "height": 1024})
        page.wait_for_timeout(500)
        
        widest = page.evaluate("""() => {
            let maxW = 0;
            let maxEl = null;
            document.querySelectorAll('*').forEach(el => {
                if (el.scrollWidth > maxW && el.tagName !== 'HTML' && el.tagName !== 'BODY') {
                    maxW = el.scrollWidth;
                    maxEl = el.outerHTML.substring(0, 200);
                }
            });
            return { width: maxW, element: maxEl };
        }""")
        print("Widest element on /calendario/ at 320px:", widest)
        
        browser.close()

if __name__ == "__main__":
    main()
