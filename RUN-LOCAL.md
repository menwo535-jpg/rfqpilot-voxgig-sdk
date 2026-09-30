# Reproduce the SDK checks

This repository targets the existing [personal RFQ API](https://github.com/menwo535-jpg/rfq-quote-pilot). The small `api/` snapshot and synthetic PDF/CSV fixtures are included so the HTTP verification is self-contained. No SaaS account, paid API or hosted endpoint is needed. Node 24 and Python 3.10+ are required for the checked route.

## Build and test the generated TypeScript client

From `ts/`:

```sh
npm ci
npx tsc --build src test
node --test-concurrency=1 --test "dist-test/**/*.test.js"
```

The generated npm `build`/`test` scripts contain POSIX shell assumptions (`rm -rf` and single-quoted globs). The explicit commands above were used on Windows; no generated SDK runtime source was hand-edited. `OFFLINE-TESTS.txt` records the result: 196 passes, one skipped cost-feature check, zero failures.

## Exercise the real API

From the repository root, install the two optional API format dependencies in a virtual environment and use its Python executable:

```sh
python -m venv .venv
```

On Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r api/requirements.txt
.\.venv\Scripts\python.exe verify-live.py
```

On a POSIX shell:

```sh
.venv/bin/python -m pip install -r api/requirements.txt
.venv/bin/python verify-live.py
```

The verifier starts the actual Python HTTP adapter on a temporary `127.0.0.1` port and uses the generated `RfqpilotSDK.Quote().create()` operation in LIVE mode. It supplies a fresh local credential only through the child process environment, then stops the server. `LIVE-RESULTS.json` records all six successful checks, including exact decimal amounts, unresolved rows, error statuses and PDF/XLSX artifacts. The POSIX commands are provided for convenience; this submission was checked on Windows.

## Regenerate from the model

From `.sdk/`:

```sh
npm ci
npm run build
node build/model-portable.cjs model/sdk.aontu
node build/model-portable.cjs test/test.aontu
```

`model-portable.cjs` calls the installed, unmodified `@voxgig/model` engine and its configured `@voxgig/apidef` and `@voxgig/sdkgen` actions. On Windows it normalises model paths to drive-relative POSIX form because the injected filesystem resolver otherwise misinterprets them. Run it from this project's `.sdk/` on the same drive as the project. The normal generated `npm run generate` route is left intact as a reproduction of the reported problem.

Original scaffold command (failed on Windows at automatic npm spawn):

```sh
npm create @voxgig/sdkgen@0.30.4 -- rfqpilot -o rfqpilot-sdk -d ./rfq-openapi.json -t ts -f test
```

Working scaffold/install sequence used here, before model generation:

```sh
npm create @voxgig/sdkgen@0.30.4 -- rfqpilot -o rfqpilot-sdk -d ./rfq-openapi.json --no-install
cd rfqpilot-sdk/.sdk
npm install
npm run add-target -- ts
npm run add-feature -- test
```

The OpenAPI source is also retained at `.sdk/def/rfq-openapi.json`. Package locks retain the exact installed dependency versions.

## Known typing limitation

The generated create type merges request and response fields. A valid API request containing only `rfq` and `catalogue_csv` fails TypeScript checking because `QuoteCreateData` also requires response-only `artifacts` and `quote`. The JavaScript live test calls the genuine generated operation and verifies its HTTP behavior; it does not establish that this generated TypeScript request type is correct.

To reproduce the expected compiler diagnostic from `ts/`:

```sh
npx tsc --noEmit --strict --skipLibCheck --target es2022 --module commonjs consumer-typecheck.ts
```

This intentionally failing example is outside the generated test build. See `TYPECHECK-OBSERVATION.txt`. No bogus response fields are added to the live API request to disguise the limitation.

Scope: only stateless `POST /quote` is specified. Saved jobs, UI, production hosting, generic PDF layouts and human approval are outside this SDK task. A `DRAFT_FOR_APPROVAL` result remains a draft; `REVIEW_REQUIRED` withholds the complete quotation total. No npm package or automated release workflow was published.
