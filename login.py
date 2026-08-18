from playwright.sync_api import sync_playwright
from config import (
    IMASTER_URL,
    USUARIO,
    CONTRASENA,
    HEADLESS,
    TIMEOUT
)


def iniciar_navegador():

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        headless=HEADLESS
    )

    context = browser.new_context(
        accept_downloads=True
    )

    page = context.new_page()

    page.set_default_timeout(TIMEOUT)

    print("====================================")
    print("   ROBOT DASHBOARD")
    print("====================================")

    print("Abriendo iMaster...")
    page.goto(IMASTER_URL)

    print("Escribiendo usuario...")
    page.get_by_placeholder(
        "Tenant/Username or username"
    ).fill(USUARIO)

    print("Escribiendo contraseña...")
    page.get_by_placeholder(
        "Password"
    ).fill(CONTRASENA)

    print("Iniciando sesión...")
    page.locator("#submitDataverify").click()

    page.wait_for_load_state("networkidle")

    print("Login exitoso.")

    return playwright, browser, context, page