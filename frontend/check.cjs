const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  
  await page.goto('http://localhost:5173', {waitUntil: 'networkidle0'});
  await new Promise(r => setTimeout(r, 5000));
  
  const loaderClass = await page.$eval('#loader', el => el.className).catch(() => 'NOT_FOUND');
  console.log('Loader classes:', loaderClass);
  
  console.log('App HTML:', await page.content());
  
  await browser.close();
})();
