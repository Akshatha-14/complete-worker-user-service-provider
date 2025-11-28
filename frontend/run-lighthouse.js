const { execSync } = require("child_process");
const fs = require("fs");

// ✅ Ensure report folder exists
const reportDir = "./lighthouse-reports";
if (!fs.existsSync(reportDir)) {
  fs.mkdirSync(reportDir);
}

// ✅ Pages to test (add or remove as needed)
const pages = [
  "",
  "signup",
  "login",
  "services",
  "about",
  "contact",
  "worker-application",
  "workerhome",
  "userhome",
  "admin",
  "complete-address",
  "verifier1",
  "verifier2",
];

const results = [];

function runLighthouse(url, outputFile) {
  console.log(`🚀 Testing ${url}...`);
  try {
    // Run Lighthouse and capture JSON output
    const jsonPath = `${reportDir}/${outputFile}.json`;
    execSync(
      `npx lighthouse http://localhost:3000/${url} --output json --output html --output-path=${reportDir}/${outputFile}.html --chrome-flags="--headless --disable-gpu --no-sandbox --ignore-certificate-errors"`,
      { stdio: "ignore" }
    );

    // Read JSON report
    const jsonFile = fs.readFileSync(`${reportDir}/${outputFile}.report.json`, "utf8");
    const data = JSON.parse(jsonFile);
    const categories = data.categories;

    // Extract key scores
    const perf = categories.performance.score * 100;
    const access = categories.accessibility.score * 100;
    const seo = categories.seo.score * 100;
    const best = categories["best-practices"].score * 100;

    results.push({ Page: url || "home", Performance: perf, Accessibility: access, SEO: seo, "Best Practices": best });
  } catch (err) {
    console.error(`❌ Error testing ${url}:`, err.message);
  }
}

(async () => {
  for (const page of pages) {
    runLighthouse(page, page || "home");
  }

  // ✅ Print result table
  console.log("\n📊 Lighthouse Summary\n");
  console.table(results);

  // ✅ Calculate averages
  const avg = (key) =>
    (results.reduce((sum, r) => sum + (r[key] || 0), 0) / results.length).toFixed(2);

  console.log(`\n✅ Average Performance: ${avg("Performance")}%`);
  console.log(`✅ Average Accessibility: ${avg("Accessibility")}%`);
  console.log(`✅ Average SEO: ${avg("SEO")}%`);
  console.log(`✅ Average Best Practices: ${avg("Best Practices")}%`);
})();
