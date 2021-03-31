from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json

# Logs into Charles Schwab using a given username and password
def login(page, username, password):
    # Go to https://www.schwab.com/public/schwab/nn/login/login.html?lang=en
    page.goto("https://www.schwab.com/public/schwab/nn/login/login.html?lang=en")
    # Fill input[name="LoginId"]
    page.frame(name="loginIframe").fill("input[name=\"LoginId\"]", "")
    # Click input[name="LoginId"]
    page.frame(name="loginIframe").click("input[name=\"LoginId\"]")
    # Fill input[name="LoginId"]
    page.frame(name="loginIframe").fill("input[name=\"LoginId\"]", username)
    # Press Tab
    page.frame(name="loginIframe").press("input[name=\"LoginId\"]", "Tab")
    # Fill input[role="textbox"]
    page.frame(name="loginIframe").fill("input[role=\"textbox\"]", password)
    # Press Enter
    with page.expect_navigation():
        page.frame(name="loginIframe").press("input[role=\"textbox\"]", "Enter")

    page.wait_for_load_state('networkidle')

# On first login, we have to go through two factor authentication, which will require user input
# On subsequent attempts, we don't need to do this
def MFA(page):

    page.wait_for_load_state('networkidle')
    # Fill input[name="DeliveryMethodSelection"]
    page.click("input[name=\"DeliveryMethodSelection\"]")
    # Click text=Text Message
    page.click("text=Text Message")
    # Click input:has-text("Continue")
    page.click("input:has-text(\"Continue\")")
    # assert page.url == "https://lms.schwab.com/Sua/DeviceTag/AccessCodeEntry?clientId=schwab-prospect&suaType=DeviceTag&selectedId=1&deliveryMethod=Sms&redirectUrl=https%3A%2F%2Fclient.schwab.com%2Flogin%2Fsignon%2Fauthcodehandler.ashx"
    # Check input[name="TrustDeviceChecked"]
    page.check("input[name=\"TrustDeviceChecked\"]")
    # Click [placeholder="Access Code"]
    page.click("[placeholder=\"Access Code\"]")
    # Fill [placeholder="Access Code"]
    page.fill("[placeholder=\"Access Code\"]", input())
    # Click text=Continue
    page.click("text=Continue")
    # assert page.url == "https://lms.schwab.com/Sua/DeviceTag/Success?clientId=schwab-prospect&redirectUrl=%2FLogin%2FResultDeviceTag%3FclientId%3Dschwab-prospect%26trustedDevice%3Dtrue%26redirectUri%3Dhttps%253A%252F%252Fclient.schwab.com%252Flogin%252Fsignon%252Fauthcodehandler.ashx&suaType=DeviceTag&trusted=True"
    # Click text=Continue
    # with page.expect_navigation(url="https://client.schwab.com/clientapps/accounts/summary/"):
    with page.expect_navigation():
        page.click("text=Continue")
    # assert page.url == "https://client.schwab.com/clientapps/accounts/summary/"


# The actual trading function
def trade(page, side, ticker, qty, broker):
    # Click text=Trade
    page.click("text=Trade")
    # assert page.url == "https://client.schwab.com/Areas/Trade/Allinone/index.aspx"
    
    # Choose the account selector
    page.click("button[role=\"combobox\"]:has-text(\"Individual\")")

    # Choose the account number
    page.click("#brkAcct" + str(broker))

    # Click [placeholder="Enter Symbol"]
    page.click("[placeholder=\"Enter Symbol\"]")
    # Fill [placeholder="Enter Symbol"]
    page.fill("[placeholder=\"Enter Symbol\"]", ticker)
    # Press Tab
    page.press("[placeholder=\"Enter Symbol\"]", "Tab")
    # Select Buy
    page.select_option("select[name=\"action\"]", side)
    # Click input[role="spinbutton"]
    page.click("input[role=\"spinbutton\"]")
    # Click input[role="spinbutton"]
    page.click("input[role=\"spinbutton\"]")
    # Press a with modifiers
    page.press("input[role=\"spinbutton\"]", "Meta+a")
    # Fill input[role="spinbutton"]
    page.fill("input[role=\"spinbutton\"]", str(qty))
    # Select Market
    page.select_option("select[name=\"type\"]", "Market")

    page.click("text=Review Order")

    page.wait_for_load_state('networkidle')

    page.wait_for_selector('#btn-place-order', state='attached')

    # Click #btn-place-order
    page.click("#btn-place-order")

    page.wait_for_selector("text=Place Another Order", state='attached')
    page.screenshot(path=f"{side}-{ticker}-({qty})-account{broker}.png")


def run(playwright):
    user_data_dir = 'user_data_dir'
    context = playwright.chromium.launch_persistent_context(
        slow_mo=250, # We should consider randomizing this
        user_data_dir=user_data_dir, 
        headless=True,
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.0 Safari/537.36',
        viewport={ 'width': 1920, 'height': 1080 }
    )

    # Open new page
    page = context.new_page()
    stealth_sync(page)

    username = "username"
    password = "password"

    # Log in to Schwab
    login(page, username, password)

    # Run two factor authentication if necessary
    if page.url != "https://client.schwab.com/clientapps/accounts/summary/":
        MFA(page)

    num_accounts = 3

    for account in range(1, num_accounts + 1):
        # Make a trade
        trade(page, "Buy", "VISL", 1, account)

    # ---------------------
    context.storage_state(path="auth.json")
    context.close()
    # browser.close()

with sync_playwright() as playwright:
    run(playwright)