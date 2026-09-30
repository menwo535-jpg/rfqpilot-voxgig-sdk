// This VALID API request reproduces a generator typing limitation.
// It is intentionally outside src/test builds and is expected to fail
// the explicit typecheck documented in REPORT.md.
import { RfqpilotSDK } from './src/RfqpilotSDK';
const client = new RfqpilotSDK();
client.Quote().create({
  rfq: { format: 'txt', content: 'ITEMS\nA|Cable|2.5|M\nEND ITEMS' },
  catalogue_csv: 'code,description,unit,unit_price,currency,price_version\nA,Cable,M,1.23,USD,v1\n',
});
