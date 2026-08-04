import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

PAGES_TO_TEST = [
    '/',
    '/reportes/',
    '/cursos/',
    '/tareas/',
    '/evaluaciones/',
    '/calendario/',
    '/certificados/mis-certificados/',
    '/usuarios/mis-cursos/',
    '/login/',
]

def main():
    print("Starting server...")
    server = subprocess.Popen(["python", "manage.py", "runserver", "8000"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3) # Wait for server to start
    
    # We might need to create a superuser or use existing credentials.
    # The README says:
    # | admin | admin123 | Administrador |
    
    os.makedirs(".sisyphus/evidence", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print("Logging in...")
        page.goto("http://localhost:8000/login/")
        try:
            page.fill("input[name='username']", "admin")
            page.fill("input[name='password']", "admin123")
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")
        except Exception as e:
            print("Login failed, might not be needed or credentials wrong:", e)
        
        viewports = [
            {"width": 320, "height": 800},
            {"width": 375, "height": 800},
            {"width": 768, "height": 1024},
            {"width": 1024, "height": 768},
        ]
        
        for path in PAGES_TO_TEST:
            print(f"Testing {path}...")
            page.goto(f"http://localhost:8000{path}")
            
            # Check viewports
            for vp in viewports:
                page.set_viewport_size(vp)
                page.wait_for_timeout(500)
                
                # Check horizontal scroll
                scroll_width = page.evaluate("document.documentElement.scrollWidth")
                client_width = page.evaluate("document.documentElement.clientWidth")
                if scroll_width > client_width:
                    print(f"  [!] Horizontal scroll detected on {path} at {vp['width']}px! (Scroll: {scroll_width}, Client: {client_width})")
                else:
                    print(f"  [✓] Layout fits at {vp['width']}px")
            
            # Test Dark Mode
            page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
            page.wait_for_timeout(500)
            # Take a screenshot to prove dark mode works
            filename = path.strip('/').replace('/', '_') or 'inicio'
            page.screenshot(path=f".sisyphus/evidence/task-15-dark-{filename}.png")
            print(f"  [✓] Dark mode screenshot saved")
            
            # Reset to light mode for next tests
            page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")

        browser.close()
    
    print("Stopping server...")
    server.terminate()
    server.wait()

if __name__ == "__main__":
    main()
