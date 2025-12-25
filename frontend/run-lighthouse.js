import { launch } from 'chrome-launcher';
import lighthouse from 'lighthouse';
import fs from 'fs';
import path from 'path';

const reportDir = './lighthouse-reports';
if (!fs.existsSync(reportDir)) fs.mkdirSync(reportDir);

const pages = [
  '', 'signup', 'login', 'services', 'about', 'contact',
  'worker-application', 'workerhome', 'userhome',
  'admin', 'complete-address', 'verifier1', 'verifier2'
];

const results = [];

async function runLighthouse(url, name) {
  try {
    console.log(`🚀 Testing ${url}...`);

    // Launch Chrome
    const chrome = await launch({ chromeFlags: ['--headless'] });

    // Run Lighthouse JSON report
    const options = { port: chrome.port, output: 'json', logLevel: 'info' };
    const runnerResult = await lighthouse(url, options);
    const jsonReport = runnerResult.report;
    fs.writeFileSync(path.join(reportDir, `${name || 'home'}.report.json`), jsonReport);

    // Run Lighthouse HTML report
    const htmlOptions = { port: chrome.port, output: 'html', logLevel: 'info' };
    const htmlResult = await lighthouse(url, htmlOptions);
    fs.writeFileSync(path.join(reportDir, `${name || 'home'}.html`), htmlResult.report);

    // Extract scores
    const data = JSON.parse(jsonReport);
    const cat = data.categories;
    results.push({
      Page: name || 'home',
      Performance: cat.performance.score * 100,
      Accessibility: cat.accessibility.score * 100,
      SEO: cat.seo.score * 100,
      'Best Practices': cat['best-practices'].score * 100
    });

    await chrome.kill();
  } catch (err) {
    console.error(`❌ Error testing ${url || 'home'}:`, err.message);
  }
}

(async () => {
  for (const page of pages) {
    await runLighthouse(`http://localhost:3000/${page}`, page || 'home');
  }

  console.log('\n📊 Lighthouse Summary\n');
  if (results.length > 0) console.table(results);
  else console.log('No results. Make sure your frontend is running at http://localhost:3000');

  const avg = (key) =>
    results.length > 0
      ? (results.reduce((sum, r) => sum + (r[key] || 0), 0) / results.length).toFixed(2)
      : 0;

  console.log(`\n✅ Average Performance: ${avg('Performance')}%`);
  console.log(`✅ Average Accessibility: ${avg('Accessibility')}%`);
  console.log(`✅ Average SEO: ${avg('SEO')}%`);
  console.log(`✅ Average Best Practices: ${avg('Best Practices')}%`);
})();
