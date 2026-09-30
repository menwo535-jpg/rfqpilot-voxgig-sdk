// Local adapter: give an explicitly injected real filesystem POSIX-form
// paths on Windows. Calls the unmodified Voxgig model and SDK generator.
const path = require('node:path');
const { Model } = require('@voxgig/model');
const filename = path.resolve(process.argv[2] || 'model/sdk.aontu');
const portable = value => process.platform === 'win32'
  ? value.replaceAll('\\', '/').replace(/^[A-Za-z]:/, '') : value;
const spec = {
  path: portable(filename),
  base: portable(path.dirname(filename)),
  require: process.cwd(),
  debug: 'info',
};
new Model(spec).run().then(result => { process.exitCode = result.ok ? 0 : 1; })
  .catch(error => { console.error(error); process.exitCode = 1; });
