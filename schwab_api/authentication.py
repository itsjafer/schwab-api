import requests
import pyotp
import re
from . import urls

import asyncio
from playwright.async_api import async_playwright, TimeoutError as AsyncTimeoutError
from playwright_stealth import stealth_async
from playwright.sync_api import sync_playwright, TimeoutError
from requests.cookies import cookiejar_from_dict
from playwright_stealth import stealth_sync


# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/"
VIEWPORT = { 'width': 1920, 'height': 1080 }

class SessionManager:
    def __init__(self, use_async=False) -> None:
        """ This class can be used in synchonous or asynchonous mode. Some cloud services may require to use Playwright in asynchonous mode.
        :type async: boolean
        :param async: authentification in synchonous or asynchonous mode.
        """
        self.use_async = use_async
        self.headers = None
        self.session = requests.Session()

        if not use_async:
            self.playwright = sync_playwright().start()
            if self.browserType == "firefox":
                self.browser = self.playwright.firefox.launch(
                    headless=self.headless
                )
            else:
                #webkit doesn't or no longer works when trying to log in.
                raise ValueError("Only supported browserType is 'firefox'")

            user_agent = USER_AGENT + self.browser.version
            self.page = self.browser.new_page(
                user_agent=user_agent,
                viewport=VIEWPORT
            )
    
            stealth_sync(self.page)
        else:
            self.playwright = None
            self.browser = None
            self.page = None

    async def async_init(self):
        if self.use_async:
            self.playwright = await async_playwright().start()
            if self.browserType == "firefox":
                self.browser = await self.playwright.firefox.launch(
                    headless=self.headless
                )
            else:
               #webkit doesn't or no longer works when trying to log in.
                raise ValueError("Only supported browserType is 'firefox'")

            user_agent = USER_AGENT + self.browser.version
            self.page = await self.browser.new_page(
                user_agent=USER_AGENT,
                viewport=VIEWPORT
            )
            await stealth_async(self.page)
        else:
            print("async_init() method called without setting use_async to True in SessionManager.")

    def check_auth(self):
        r = self.session.get(urls.account_info_v2())
        if r.status_code != 200:
            return False
        return True

    async def async_save_and_close_session(self):
        cookies = {cookie["name"]: cookie["value"] for cookie in await self.page.context.cookies()}
        self.session.cookies = cookiejar_from_dict(cookies)
        await self.page.close()
        await self.browser.close()
        await self.playwright.stop()

    def save_and_close_session(self):
        cookies = {cookie["name"]: cookie["value"] for cookie in self.page.context.cookies()}
        self.session.cookies = cookiejar_from_dict(cookies)
        self.page.close()
        self.browser.close()
        self.playwright.stop()

    def get_session(self):
        return self.session

    def sms_login(self, code):

        # Inconsistent UI for SMS Authentication means we try both
        try:
            self.page.click("input[type=\"text\"]")
            self.page.fill("input[type=\"text\"]", str(code))
            self.page.click("text=Trust this device and skip this step in the future.")
            with self.page.expect_navigation():
                self.page.click("text=Log In")
        except:
            self.page.check("input[name=\"TrustDeviceChecked\"]")
            self.page.click("[placeholder=\"Access Code\"]")
            self.page.fill("[placeholder=\"Access Code\"]", str(code))
            with self.page.expect_navigation():
                self.page.click("text=Continue")
                
        self.save_and_close_session()
        return self.page.url == urls.account_summary()

    def captureAuthToken(self, route):
            self.headers = route.request.all_headers()
            route.continue_()

    async def asyncCaptureAuthToken(self, route):
        self.headers = await route.request.all_headers()
        await route.continue_()
    
    def login(self, username, password, totp_secret=None):
        """ This function will log the user into schwab using Playwright and saving
        the authentication cookies in the session header. 
        :type username: str
        :param username: The username for the schwab account.

        :type password: str
        :param password: The password for the schwab account/

        :type totp_secret: Optional[str]
        :param totp_secret: The TOTP secret used to complete multi-factor authentication 
            through Symantec VIP. If this isn't given, sign in will use SMS.

        :rtype: boolean
        :returns: True if login was successful and no further action is needed or False
            if login requires additional steps (i.e. SMS)
        """
        if self.use_async:
            result = asyncio.run(self.async_login(username, password, totp_secret))
            return result

        else:
            # Log in to schwab using Playwright (synchonous)
            with self.page.expect_navigation():
                self.page.goto("https://www.schwab.com/")
    
    
            # Capture authorization token.
            self.page.route(re.compile(r".*balancespositions*"), self.captureAuthToken)
    
            # Wait for the login frame to load
            login_frame = "schwablmslogin"
            self.page.wait_for_selector("#" + login_frame)
    
            self.page.frame(name=login_frame).select_option("select#landingPageOptions", index=3)
    
            # Fill username
            self.page.frame(name=login_frame).click("[placeholder=\"Login ID\"]")
            self.page.frame(name=login_frame).fill("[placeholder=\"Login ID\"]", username)
            
            # Add TOTP to password
            if totp_secret is not None:
                totp = pyotp.TOTP(totp_secret)
                password += str(totp.now())
    
            # Fill password
            self.page.frame(name=login_frame).press("[placeholder=\"Login ID\"]", "Tab")
            self.page.frame(name=login_frame).fill("[placeholder=\"Password\"]", password)
    
            # Submit
            try:
                with self.page.expect_navigation():
                    self.page.frame(name=login_frame).press("[placeholder=\"Password\"]", "Enter")
            except TimeoutError:
                raise Exception("Login was not successful; please check username and password")
    
            # NOTE: THIS FUNCTIONALITY WILL SOON BE UNSUPPORTED/DEPRECATED.
            if self.page.url != urls.trade_ticket():
                # We need further authentication, so we'll send an SMS
                print("Authentication state is not available. We will need to go through two factor authentication.")
                print("You should receive a code through SMS soon")
    
                # Send an SMS. The UI is inconsistent so we'll try both.
                try:
                    with self.page.expect_navigation():
                        self.page.click("[aria-label=\"Text me a 6 digit security code\"]")
                except:
                    self.page.click("input[name=\"DeliveryMethodSelection\"]")
                    self.page.click("text=Text Message")
                    self.page.click("input:has-text(\"Continue\")")
                return False
    
            self.page.wait_for_selector("#_txtSymbol")
    
            # Save our session
            self.save_and_close_session()
    
            return True

    async def async_login(self, username, password, totp_secret=None):
        """ This function will log the user into schwab using asynchoneous Playwright and saving
        the authentication cookies in the session header. 
        :type username: str
        :param username: The username for the schwab account.

        :type password: str
        :param password: The password for the schwab account/

        :type totp_secret: Optional[str]
        :param totp_secret: The TOTP secret used to complete multi-factor authentication 
            through Symantec VIP. SMS is not supported for asynchoneous login.

        :rtype: boolean
        :returns: True if login was successful and no further action is needed or False
            if login requires additional steps (i.e. SMS)
        """
        await self.async_init()
        await self.page.goto("https://www.schwab.com/")

        await self.page.route(re.compile(r".*balancespositions*"), self.asyncCaptureAuthToken)

        login_frame = "schwablmslogin"
        await self.page.wait_for_selector("#" + login_frame)

        await self.page.frame(name=login_frame).select_option("select#landingPageOptions", index=3)

        await self.page.frame(name=login_frame).click("[placeholder=\"Login ID\"]")
        await self.page.frame(name=login_frame).fill("[placeholder=\"Login ID\"]", username)

        if totp_secret is not None:
            totp = pyotp.TOTP(totp_secret)
            password += str(totp.now())

        await self.page.frame(name=login_frame).press("[placeholder=\"Login ID\"]", "Tab")
        await self.page.frame(name=login_frame).fill("[placeholder=\"Password\"]", password)

        try:
            await self.page.frame(name=login_frame).press("[placeholder=\"Password\"]", "Enter")
            await self.page.wait_for_url(urls.trade_ticket())
        except AsyncTimeoutError:
            raise Exception("Login was not successful; please check username and password")
            return False

        await self.page.wait_for_selector("#_txtSymbol")

        await self.async_save_and_close_session()
        return True
