const autocannon = require('autocannon');

const targetUrl = 'http://localhost:3000';

async function runLoadTest() {
  console.log(`Starting load test against ${targetUrl}...`);

  const instance = autocannon({
    url: targetUrl,
    connections: 10,
    pipelining: 1,
    duration: 10,
    requests: [
      { method: 'GET', path: '/' },
      { method: 'GET', path: '/customer/eats' },
      { method: 'GET', path: '/customer/grocery' },
      { method: 'GET', path: '/merchant' },
      { method: 'GET', path: '/partner' },
      { method: 'GET', path: '/admin/command-center' },
    ]
  }, console.log);

  autocannon.track(instance, { renderProgressBar: true });

  instance.on('done', (result) => {
    console.log('Load test completed.');
    
    // Check our budgets
    const p99 = result.latency.p99;
    if (p99 > 3000) {
      console.warn(`WARNING: p99 latency (${p99}ms) exceeded 3000ms budget.`);
    } else {
      console.log(`SUCCESS: p99 latency (${p99}ms) is within budget.`);
    }

    if (result.non2xx > 0) {
      console.error(`ERROR: ${result.non2xx} non-2xx responses detected.`);
      process.exit(1);
    } else {
      console.log('SUCCESS: 0 errors detected.');
      process.exit(0);
    }
  });
}

runLoadTest();
