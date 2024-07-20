import hashlib
import json
import requests
import pyotp
import re
from . import urls

import asyncio
from playwright.async_api import async_playwright, TimeoutError
from playwright_stealth import stealth_async
from playwright_stealth.stealth import StealthConfig
from requests.cookies import cookiejar_from_dict


# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/"
VIEWPORT = { 'width': 1920, 'height': 1080 }

class SessionManager:
    def __init__(self, debug = False) -> None:
        """
        This class is using asynchronous playwright mode.

        :type debug: boolean
        :param debug: Enable debug logging
        """
        self.headers = {}
        self.session = requests.Session()
        self.playwright = None
        self.browser = None
        self.page = None
        self.debug = debug

        # cached credentials
        self.username = None
        self.username_hash = None
        self.password = None
        self.password_hash = None
        self.totp_secret = None
        self.totp_secret_hash = None

    def check_auth(self):
        r = self.session.get(urls.account_info_v2())
        if r.status_code != 200:
            return False
        return True

    def get_session(self):
        return self.session

    def login(self, username, password, totp_secret, lazy=False):
        """
        Logs the user into the Schwab API using asynchronous Playwright, saving
        the authentication cookies in the session header.

        :type username: str
        :param username: The username for the schwab account.

        :type password: str
        :param password: The password for the schwab account/

        :type totp_secret: str
        :param totp_secret: The TOTP secret used to complete multi-factor authentication

        :type lazy: boolean
        :param lazy: Store credentials but don't login until necessary

        :rtype: boolean
        :returns: True if login was successful and no further action is needed or False
            if login requires additional steps (i.e. SMS - no longer supported)
        """
        # update credentials
        self.username = username or ""
        self.password = password or ""
        self.totp_secret = totp_secret or ""

        # calculate hashes
        username_hash = hashlib.md5(self.username.encode('utf-8')).hexdigest()
        password_hash = hashlib.md5(self.password.encode('utf-8')).hexdigest()
        totp_secret_hash = hashlib.md5(self.totp_secret.encode('utf-8')).hexdigest()

        # attempt to load cached session
        if self._load_session_cache():
            # check hashed credentials
            if self.username_hash == username_hash and self.password_hash == password_hash and self.totp_secret_hash == totp_secret_hash:
                if self.debug:
                    print('DEBUG: hashed credentials okay')
                try:
                    if self.update_token():
                        return True
                except:
                    if self.debug:
                        print('DEBUG: update token failed, falling back to login')

        # update hashed credentials
        self.username_hash = username_hash
        self.password_hash = password_hash
        self.totp_secret_hash = totp_secret_hash

        if lazy:
            return True
        else:
            # attempt to login
            return asyncio.run(self._async_login())

    def update_token(self, token_type='api', login=True):
        r = self.session.get(f"https://client.schwab.com/api/auth/authorize/scope/{token_type}")
        if not r.ok:
            if login:
                if self.debug:
                    print("DEBUG: session invalid; logging in again")
                result = asyncio.run(self._async_login())
                return result
            else:
                raise ValueError(f"Error updating Bearer token: {r.reason}")

        token = json.loads(r.text)['token']
        self.headers['authorization'] = f"Bearer {token}"
        self._save_session_cache()
        return True

    async def _async_login(self):
        """
        Helper function to perform asynchronous login using Playwright
        """
        self.playwright = await async_playwright().start()
        if self.browserType == "firefox":
            self.browser = await self.playwright.firefox.launch(
                headless=self.headless
            )
        else:
            raise ValueError("Only supported browserType is 'firefox'")

        user_agent = USER_AGENT + self.browser.version
        self.page = await self.browser.new_page(
            user_agent=user_agent,
            viewport=VIEWPORT
        )

        config = StealthConfig()
        config.navigator_languages = False
        config.navigator_user_agent = False
        config.navigator_vendor = False
        await stealth_async(self.page, config)

        await self.page.goto("https://www.schwab.com/")
        await self.page.route(re.compile(r".*balancespositions*"), self._asyncCaptureAuthToken)

        login_frame = "schwablmslogin"
        await self.page.wait_for_selector("#" + login_frame)
        await self.page.frame(name=login_frame).select_option("select#landingPageOptions", index=3)

        # enter username
        await self.page.frame(name=login_frame).click("[placeholder=\"Login ID\"]")
        await self.page.frame(name=login_frame).fill("[placeholder=\"Login ID\"]", self.username)

        # append otp to passsword
        totp = pyotp.TOTP(self.totp_secret)
        password = self.password + str(totp.now())

        # enter password
        await self.page.frame(name=login_frame).press("[placeholder=\"Login ID\"]", "Tab")
        await self.page.frame(name=login_frame).fill("[placeholder=\"Password\"]", password)

        try:
            await self.page.frame(name=login_frame).press("[placeholder=\"Password\"]", "Enter")
            await self.page.wait_for_url(re.compile(r"app/trade"), wait_until="domcontentloaded") # Making it more robust than specifying an exact url which may change.
        except TimeoutError:
            raise Exception("Login was not successful; please check username and password")

        await self.page.wait_for_selector("#_txtSymbol")

        await self._async_save_and_close_session()
        return True

    async def _async_save_and_close_session(self):
        cookies = {cookie["name"]: cookie["value"] for cookie in await self.page.context.cookies()}
        self.session.cookies = cookiejar_from_dict(cookies)
        await self.page.close()
        await self.browser.close()
        await self.playwright.stop()
        self._save_session_cache()

    async def _asyncCaptureAuthToken(self, route):
        self.headers = await route.request.all_headers()
        await route.continue_()

    def _load_session_cache(self):
        if self.session_cache:
            try:
                with open(self.session_cache) as f:
                    data = f.read()
                    session = json.loads(data)
                    self.session.cookies = cookiejar_from_dict(session['cookies'])
                    self.headers = session['headers']
                    self.username_hash = session['username_hash']
                    self.password_hash = session['password_hash']
                    self.totp_secret_hash = session['totp_secret_hash']
                    return True
            except:
                # swallow exceptions
                pass

        return False

    def _save_session_cache(self):
        if self.session_cache:
            with open(self.session_cache, 'w') as f:
                session = {
                    'cookies': self.session.cookies.get_dict(),
                    'headers': self.headers,
                    'username_hash': self.username_hash,
                    'password_hash': self.password_hash,
                    'totp_secret_hash': self.totp_secret_hash
                }
                json.dump(session, f)
