// Exercise the GENERATED entity against the actual personal API, not a mock.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { RfqpilotSDK } = require('./ts/dist/RfqpilotSDK');
const base = process.env.RFQ_TEST_BASE;
const token = process.env.RFQ_TEST_TOKEN;
if (!base || !token) throw new Error('Run through verify-live.py');
const sdk = new RfqpilotSDK({ base, apikey: token });
const results = [];
const check = async (name, work) => { await work(); results.push({name, passed: true}); };
const catalogue = 'code,description,unit,unit_price,currency,price_version\nA,Cable,M,1.23,USD,v1\n';
const request = content => ({rfq: {format: 'txt', content}, catalogue_csv: catalogue});
const create = async payload => (await sdk.Quote().create(payload)).data();
(async () => {
  await check('live mode is enabled', async () => assert.equal(sdk._mode, 'live'));
  await check('matched TXT draft retains exact decimal result and artifacts', async () => {
    const out = await create(request('ITEMS\nA|Cable|2.5|M\nEND ITEMS'));
    assert.equal(out.quote.status, 'DRAFT_FOR_APPROVAL');
    assert.equal(out.quote.review_count, 0);
    assert.equal(out.quote.rows[0].line_total, '3.08');
    assert.deepEqual(out.quote.complete_totals_by_currency, {USD: '3.08'});
    assert.match(out.artifacts.csv_utf8, /3\.08/);
    assert.match(out.artifacts.review_html, /DRAFT_FOR_APPROVAL/);
  });
  await check('unmatched TXT remains REVIEW_REQUIRED with no complete total', async () => {
    const out = await create(request('ITEMS\nB|Unknown|1|M\nEND ITEMS'));
    assert.equal(out.quote.status, 'REVIEW_REQUIRED');
    assert.equal(out.quote.review_count, 1);
    assert.equal(out.quote.complete_totals_by_currency, null);
    assert.equal(out.quote.rows[0].status, 'REVIEW');
  });
  await check('invalid payload surfaces HTTP 422', async () => {
    await assert.rejects(create(request('')), err => err.status === 422);
  });
  await check('wrong private local credential surfaces HTTP 401', async () => {
    const bad = new RfqpilotSDK({base, apikey: 'x'.repeat(24)});
    await assert.rejects(bad.Quote().create(request('ITEMS\nA|Cable|1|M\nEND ITEMS')), err => err.status === 401);
  });
  await check('PDF sample retains six rows, four reviews, USD32.50 subtotal and XLSX', async () => {
    const out = await create({rfq: {format: 'pdf_base64', content: fs.readFileSync(path.join(__dirname,'api/samples/rfq.pdf')).toString('base64')}, catalogue_csv: fs.readFileSync(path.join(__dirname,'api/samples/catalogue.csv'),'utf8'), include_xlsx: true});
    assert.equal(out.quote.rows.length, 6);
    assert.equal(out.quote.review_count, 4);
    assert.equal(out.quote.matched_subtotals_by_currency.USD, '32.50');
    assert.equal(out.quote.complete_totals_by_currency, null);
    assert.equal(Buffer.from(out.artifacts.xlsx_base64, 'base64').subarray(0,2).toString(), 'PK');
  });
  console.log(JSON.stringify({mode: 'real loopback HTTP; no test-mode mock', cases: results.length, results}, null, 2));
})().catch(error => { console.error(JSON.stringify({passed: results, error: error.message, status: error.status}, null, 2)); process.exitCode = 1; });
