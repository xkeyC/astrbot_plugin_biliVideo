from astrbot.api import logger
from playwright.async_api import Page, ViewportSize, async_playwright


async def create_page(
    headless: bool = True,
    width: int = 1400,
    height: int = 10000,
    scale_factor: int = 2,
    is_mobile: bool = False,
) -> Page | None:
    try:
        playwright = await async_playwright().start()

        chrome_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run",
            "--disable-extensions",
            "--disable-default-apps",
        ]

        browser = await playwright.chromium.launch(
            headless=headless,
            args=chrome_args,
        )

        context = await browser.new_context(
            viewport=ViewportSize(width=width, height=height),
            device_scale_factor=scale_factor,
            is_mobile=is_mobile,
            has_touch=is_mobile,
        )
        page = await context.new_page()
        __original_close = page.close

        async def close_all(*args: object, **kwargs: object) -> None:
            page.close = __original_close
            try:
                await browser.close()
                await playwright.stop()
            except Exception as e:
                logger.error(f"关闭页面时出错: {e}")

        page.close = close_all
        return page
    except Exception as e:
        logger.error(f"初始化浏览器失败: {e}")
        return None


async def render_html_to_image(
    html_content: str,
    selector: str = "body",
    width: int = 1400,
    scale_factor: int = 2,
    is_mobile: bool = False,
    full_page: bool = True,
    timeout: int = 30000,
) -> bytes | None:
    page = await create_page(
        headless=True,
        width=width,
        height=10000,
        scale_factor=scale_factor,
        is_mobile=is_mobile,
    )
    if not page:
        return None

    try:
        await page.set_content(html_content, wait_until="networkidle", timeout=timeout)

        locator = page.locator(selector)
        if await locator.count() > 0:
            screenshot_bytes = await locator.screenshot(type="png", omit_background=False, animations="disabled")
        else:
            screenshot_bytes = await page.screenshot(full_page=full_page, type="png", animations="disabled")

        return screenshot_bytes
    except Exception as e:
        logger.error(f"渲染 HTML 失败: {e}")
        return None
    finally:
        if page:
            await page.close()
