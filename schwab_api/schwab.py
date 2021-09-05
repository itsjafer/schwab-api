from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import json
import random
import os
import pyotp

class Schwab:
    __instance = None
    def __init__(self, **kwargs):
        """
            The Schwab class. Used to interact with schwab.

            Expected arguments:
                username -- the Schwab username,
                password -- the schwab password,
                user_agent -- the user agent we're using to scrape,

        """
        if Schwab.__instance is None:
            Schwab.__instance = self
        else:
            raise Exception("Only one Schwab instance is allowed")

        self.username = kwargs.get("username", None)
        self.password = kwargs.get("password", None)
        self.user_agent = kwargs.get("user_agent", None)
        self.user_data_dir = kwargs.get("user_data_dir", "user_data_dir")
        self.headless = kwargs.get("headless", False)
        self.totp = kwargs.get("totp", None)

        if self.username is None or self.password is None or self.user_agent is None:
            raise Exception("Schwab expects the following constructor variables: `username`, `password`, `user_agent`")

        self.playwright = sync_playwright().start()

        self.context = self.playwright.chromium.launch_persistent_context(
            slow_mo=random.randint(100,500),
            user_data_dir=self.user_data_dir, 
            headless=self.headless,
            user_agent=self.user_agent,
            viewport={ 'width': 1920, 'height': 1080 }
        )

        # Open new page
        self.page = self.context.new_page()
        stealth_sync(self.page)

    @staticmethod
    def get_instance(**kwargs):
        """The Schwab class. Used to interact with Charles Schwab. 
            This is a singleton class to prevent issues from arising 
            with playwright
        Parameters
        ----------
        username: Schwab username
        password: Schwab password
        user_agent: The user agent to spoof using Playwright. This needs to be something
            recent and up-to-date. Schwab doesn't allow logins from super old browsers.
        user_data_dir: The directory location of where to save persistent authentication 
            data. Defaults to `user_data_dir`
        **kwargs
            Parameters that are passed on to basically every module and methods
            that interact with this main class. These may or may not be documented
            in other places.
        """
        if not Schwab.__instance:
            Schwab(**kwargs)
        return Schwab.__instance

    def __del__(self):
        try:
            self.context.close()
        except:
            pass
        try:
            self.playwright.stop()
        except:
            pass


    def login(self, screenshot=False):
        """
            Logs into Schwab using the initialized username and password.

            Will save an auth.json that holds cookies/auth information which we might use later.

            screenshot (Bool) - Whether to screenshot after logging in

        """

        print("Attempting to login")
        # Go to https://www.schwab.com/
        with self.page.expect_navigation():
            self.page.goto("https://www.schwab.com/")

        self.page.wait_for_load_state('domcontentloaded')
        if screenshot:
            self.page.screenshot(path="Logging_in.png")

        selector = "schwablmslogin"
        try:
            self.page.wait_for_selector("#" + selector)
        except:
            selector = "lms-home"

        # Click [placeholder="Login ID"]
        self.page.frame(name=selector).click("[placeholder=\"Login ID\"]")
        # Fill [placeholder="Login ID"]
        self.page.frame(name=selector).fill("[placeholder=\"Login ID\"]", self.username)
        # Press Tab
        self.page.frame(name=selector).press("[placeholder=\"Login ID\"]", "Tab")
        # Fill [placeholder="Password"]
        self.page.frame(name=selector).fill("[placeholder=\"Password\"]", self.password)

        if screenshot:
            self.page.screenshot(path="Filled_in.png")

        # Press Enter
        # with page.expect_navigation(url="https://sws-gateway.schwab.com/ui/host/#/placeholder"):
        try:
            with self.page.expect_navigation():
                self.page.frame(name=selector).press("[placeholder=\"Password\"]", "Enter")
                if screenshot:
                    self.page.screenshot(path="clicked_enter.png")
        except:
            self.page.screenshot(path="error.png")


        self.page.wait_for_load_state('networkidle')
        self.context.storage_state(path="auth.json")

        print("Login info accepted successfully")


        # Run two factor authentication if necessary
        if self.page.url != "https://client.schwab.com/clientapps/accounts/summary/":
            self.first_time_setup(screenshot=screenshot)
        if screenshot:
            self.page.screenshot(path="Logged_in.png")



    def first_time_setup(self, screenshot=False):
        """
            We have to go through two factor authentication.

            We trust the current authentication for 30 days and store it in `user_data_dir`

            screenshot (Bool) - Whether to screenshot the process

        """

        print("Authentication state is not available. We will need to go through two factor authentication.")
        
        self.page.wait_for_load_state('networkidle')
        if screenshot:
            self.page.screenshot(path="MFA.png")

        if self.totp is not None:
            totp = pyotp.TOTP(self.totp)
            print(totp.now())
            # self.page.pause()
            self.page.click("#placeholderCode")
            # Fill [aria-label="Enter a 6 digit numeric value."]
            self.page.fill("#placeholderCode", str(totp.now()))
            # Click text=Continue
            # with page.expect_navigation(url="https://client.schwab.com/clientapps/accounts/summary/"):
            with self.page.expect_navigation():
                self.page.click("#continueButton")
            assert self.page.url == "https://client.schwab.com/clientapps/accounts/summary/"
            print("We should now be logged in")
            return

        
        try:
            # Click [aria-label="Text me a 6 digit security code"]
            # with page.expect_navigation(url="https://sws-gateway.schwab.com/ui/host/#/otp/code"):
            with self.page.expect_navigation():
                self.page.click("[aria-label=\"Text me a 6 digit security code\"]")
                print("You should receive a code on your phone number soon")

            # assert page.url == "https://sws-gateway.schwab.com/ui/host/#/"
            # Click input[type="text"]
            self.page.click("input[type=\"text\"]")
            # Fill input[type="text"]
            self.page.fill("input[type=\"text\"]", input("Please enter your security code: "))
            # Click text=Trust this device and skip this step in the future.
            self.page.click("text=Trust this device and skip this step in the future.")
            # Click text=Log In
            # with page.expect_navigation(url="https://client.schwab.com/clientapps/accounts/summary/"):
            with self.page.expect_navigation():
                self.page.click("text=Log In")
        except:
            # Fill input[name="DeliveryMethodSelection"]
            self.page.click("input[name=\"DeliveryMethodSelection\"]")
            # Click text=Text Message
            self.page.click("text=Text Message")
            # Click input:has-text("Continue")
            self.page.click("input:has-text(\"Continue\")")

            print("You should receive a code on your phone number soon")
            # assert page.url == "https://lms.schwab.com/Sua/DeviceTag/AccessCodeEntry?clientId=schwab-prospect&suaType=DeviceTag&selectedId=1&deliveryMethod=Sms&redirectUrl=https%3A%2F%2Fclient.schwab.com%2Flogin%2Fsignon%2Fauthcodehandler.ashx"
            # Check input[name="TrustDeviceChecked"]
            self.page.check("input[name=\"TrustDeviceChecked\"]")
            # Click [placeholder="Access Code"]
            self.page.click("[placeholder=\"Access Code\"]")
            # Fill [placeholder="Access Code"]
            self.page.fill("[placeholder=\"Access Code\"]", input("Please enter your security code: "))
            
            if screenshot:
                self.page.screenshot(path="MFA_entered.png")

            # Click text=Continue
            self.page.click("text=Continue")
            # assert page.url == "https://lms.schwab.com/Sua/DeviceTag/Success?clientId=schwab-prospect&redirectUrl=%2FLogin%2FResultDeviceTag%3FclientId%3Dschwab-prospect%26trustedDevice%3Dtrue%26redirectUri%3Dhttps%253A%252F%252Fclient.schwab.com%252Flogin%252Fsignon%252Fauthcodehandler.ashx&suaType=DeviceTag&trusted=True"
            # Click text=Continue
            # with page.expect_navigation(url="https://client.schwab.com/clientapps/accounts/summary/"):
            with self.page.expect_navigation():
                self.page.click("text=Continue")
                
        assert self.page.url == "https://client.schwab.com/clientapps/accounts/summary/"
        print("We should now be logged in")

    def trade(self, ticker, side, qty, account_index=0, screenshot=False):
        """
            ticker (Str) - The symbol you want to trade,
            side (str) - Either 'Buy' or 'Sell',
            qty (int) - The amount of shares to buy/sell,
            account_index - The index of the account you want to trade on. 
                For example, if you have more than one account, you may want
                to specify which account to perform the trade on. The default is
                0 (the first account). If you're looking to identify the index,
                choose the dropdown on https://client.schwab.com/Areas/Trade/Allinone/index.aspx,
            screenshot (Bool) - Whether to screenshot proof of the trade
        """

        print(f"Attempting to {side} {qty} shares of {ticker} on account #{account_index}")
        self.page.goto("https://client.schwab.com/clientapps/accounts/summary/")

        # Click text=Trade
        self.page.click("text=Trade")
        assert self.page.url == "https://client.schwab.com/Areas/Trade/Allinone/index.aspx"
        
        # Choose the account selector
        self.page.click("button[role=\"combobox\"]:has-text(\"Individual\")")

        # Choose the account number
        self.page.click("#brkAcct" + str(account_index + 1))

        # Click [placeholder="Enter Symbol"]
        self.page.click("[placeholder=\"Enter Symbol\"]")
        # Fill [placeholder="Enter Symbol"]
        self.page.fill("[placeholder=\"Enter Symbol\"]", ticker)
        # Press Tab
        self.page.press("[placeholder=\"Enter Symbol\"]", "Tab")
        # Select Buy
        self.page.select_option("select[name=\"action\"]", side)
        # Click input[role="spinbutton"]
        self.page.click("input[role=\"spinbutton\"]")
        # Click input[role="spinbutton"]
        self.page.click("input[role=\"spinbutton\"]")
        # Press a with modifiers
        self.page.press("input[role=\"spinbutton\"]", "Meta+a")
        # Fill input[role="spinbutton"]
        self.page.fill("input[role=\"spinbutton\"]", str(qty))
        # Select Market
        self.page.select_option("select[name=\"type\"]", "Market")
        
        self.page.click("text=Review Order")

        self.page.wait_for_load_state('networkidle')

        self.page.wait_for_selector('#btn-place-order', state='attached')

        # Click #btn-place-order
        self.page.click("#btn-place-order")

        self.page.wait_for_selector("text=Place Another Order", state='attached')

        print("Looks like we have successfully completed our trade!")
        if screenshot:
            print(f"Saving proof to {side}-{ticker}-({qty})-account{account_index + 1}.png")
            self.page.screenshot(path=f"{side}-{ticker}-({qty})-account{account_index + 1}.png")
        