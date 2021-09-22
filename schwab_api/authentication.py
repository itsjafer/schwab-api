import requests
import pyotp
from . import urls

from playwright.sync_api import sync_playwright, TimeoutError
from requests.cookies import cookiejar_from_dict
from playwright_stealth import stealth_sync


# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36"
VIEWPORT = { 'width': 1920, 'height': 1080 }

class SessionManager:
    def __init__(self) -> None:
        self.session = requests.Session()

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.firefox.launch(
            headless=self.headless
        )

        self.page = self.browser.new_page(
            user_agent=USER_AGENT,
            viewport=VIEWPORT
        )

        stealth_sync(self.page)

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

    def login(self, username, password, totp_secret=None):
        """ This function will log the user into schwab using Playwright and saving
        the authentication cookies in the session header. 
        :type username: str
        :param username: The username for the schwab account.

        :type password: str
        :param password: The password for the schwab account/

        :type by_totp: Optional[str]
        :param by_totp: The TOTP secret used to complete multi-factor authentication 
            through Symantec VIP. If this isn't given, sign in will use SMS.

        :rtype: boolean
        :returns: True if login was successful and no further action is needed or False
            if login requires additional steps (i.e. SMS)
        """
        
        # Log in to schwab using Playwright
        with self.page.expect_navigation():
            self.page.goto("https://www.schwab.com/")
        self.page.wait_for_load_state('networkidle')

        # Wait for the login frame to load
        login_frame = "schwablmslogin"
        self.page.wait_for_selector("#" + login_frame)

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

        self.page.wait_for_load_state('networkidle')

        if self.page.url != urls.account_summary():
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

        # Save our session
        self.save_and_close_session()

        return True