const playwright = require('playwright-aws-lambda');
const fs = require('fs');

/**
 * Responds to any HTTP request.
 *
 * @param {!express:Request} req HTTP request context.
 * @param {!express:Response} res HTTP response context.
 */
exports.reqRes = async (req, res) => {
    let message = req.query.message || req.body.message || 'Hello World!';
    res.status(200).send(message);
};

async function test() {

  const storage_state = fs.readFileSync('auth.json')

  const browser = await playwright.launchChromium({
headless: true});

  const addons = await import('playwright-addons');
  await addons.stealth(browser);
  
  const context = await browser.newContext({
    user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.0 Safari/537.36',
    viewport: { 'width': 1920, 'height': 1080 },
    storage_state: JSON.parse(storage_state)
  });
  // Open new page
  const page = await context.newPage();
  // Go to https://www.schwab.com/
  await page.goto('https://www.schwab.com/');
  // Click [placeholder="Login ID"]
  await page.frame({
    name: 'LoginComponentForm'
  }).click('[placeholder="Login ID"]');
  // Fill [placeholder="Login ID"]
  await page.frame({
    name: 'LoginComponentForm'
  }).fill('[placeholder="Login ID"]', 'username');
  // Press Tab
  await page.frame({
    name: 'LoginComponentForm'
  }).press('[placeholder="Login ID"]', 'Tab');
  // Fill [placeholder="Password"]
  await page.frame({
    name: 'LoginComponentForm'
  }).fill('[placeholder="Password"]', 'password');
  // Press Enter
  await Promise.all([
    page.waitForNavigation(/*{ url: 'https://lms.schwab.com/Sua/Rba?clientId=schwab-prospect&suaType=RBA&returnCode=9999&redirectUrl=https%3A%2F%2Fclient.schwab.com%2Flogin%2Fsignon%2Fauthcodehandler.ashx' }*/),
    page.frame({
      name: 'LoginComponentForm'
    }).press('[placeholder="Password"]', 'Enter')
  ]);

  await page.goto('https://client.schwab.com/clientapps/accounts/summary/');
  // ---------------------
  await context.storageState({ path: 'auth.json' });
  await context.close();
  await browser.close();
}

test()
  