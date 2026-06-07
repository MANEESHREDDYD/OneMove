const { Client } = require('pg');
const fs = require('fs');

const env = fs.readFileSync('.env.local', 'utf-8')
  .split('\n')
  .find(l => l.startsWith('DIRECT_URL='))
  .split('=')[1]
  .trim()
  .replace(/^"|"$/g, '');

const client = new Client({ connectionString: env });

client.connect()
  .then(() => client.query('ALTER TABLE public.experiment_metrics ADD CONSTRAINT experiment_metrics_exp_var_key UNIQUE (experiment_id, variant_id);'))
  .then(() => {
    console.log('Unique constraint added successfully');
    client.end();
  })
  .catch(e => {
    console.error(e);
    process.exit(1);
  });
