import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

app = FastAPI()

@app.get("/extract")
async def extract_m3u8(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")

    extracted_m3u8 = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context()
        page = await context.new_page()
        
        await stealth_async(page)

        async def handle_request(request):
            nonlocal extracted_m3u8
            if '.m3u8' in request.url:
                extracted_m3u8 = request.url

        page.on("request", handle_request)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Wait a few seconds to let any background JS execute and fetch m3u8
            for _ in range(10):
                if extracted_m3u8:
                    break
                await asyncio.sleep(1)

        except Exception as e:
            pass
        finally:
            await browser.close()

    if extracted_m3u8:
        return {"success": True, "m3u8": extracted_m3u8}
    else:
        return {"success": False, "error": "Could not extract m3u8"}

@app.get("/")
def read_root():
    return {"status": "running", "service": "Novix Extractor Proxy"}
