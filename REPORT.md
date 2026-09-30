# First mini task: RFQ Pilot SDK

Prepared 30 September 2026 using Voxgig's generator and an existing personal API. AI-assisted preparation and automated checks; no professional human code review is claimed. The existing API work predates this exercise. No human coding time is billed or claimed here.

**Result:** generated TypeScript SDK, OpenAPI definition, generator model and reproducible checks under MIT. The SDK makes real `POST /quote` calls; there are remaining generator DX and typing issues listed below. Not published to npm.

**API choice:** [RFQ quote pilot](https://github.com/menwo535-jpg/rfq-quote-pilot), a local quotation-processing side project. Catalogue repository searches for `rfq`, `rfq-pilot` and `quotation` in `voxgig-sdk` returned no matches on 30 September. A personal API avoids creating trial accounts or paying for access. The scoped OpenAPI definition covers one existing endpoint, not the whole application.

**Toolchain:** Windows, Node 24.18.0, npm 11.16.0; `@voxgig/create-sdkgen` 0.30.4, `@voxgig/sdkgen` 4.32.1. The checked-in npm locks capture the parser/model/other package versions. The SDK source and tests are generator output; the authored files are the OpenAPI definition, project metadata overlay, portable model runner, real-API verifier and these notes.

**What worked well:** the parser identified one quote entity and one POST/create operation without a manual endpoint mapping. Bearer authentication, request transformation and response preservation worked against the actual Python API. The generated offline suite includes documentation examples and passed 196 checks (one cost-feature check skipped because that feature is absent). Six live checks passed: live mode, matched TXT, unresolved TXT, invalid input/422, wrong credential/401, and the PDF/XLSX sample. The PDF result retained six rows, four reviews and the exact USD32.50 matched subtotal while withholding the complete total. See `LIVE-RESULTS.json`, `OFFLINE-TESTS.txt` and `RUN-LOCAL.md`.

**Friction and reproducible observations:**

1. The initial scaffold command failed with `Failed to start npm: spawn npm ENOENT` at automatic dependency installation. `--no-install -t ts -f test` still failed when it tried to add the target through npm. `--no-install` without those two flags, followed by manual npm install/add-target/add-feature, worked. A Windows-aware npm launcher would improve first-run experience.
2. The unmodified model CLI failed with `[aontu/multisource_not_found] source not found: api/api-info.aontu` even though that file existed. The emitted search path did not resolve the project's `model/api` folder. A small adapter giving the Model API POSIX-style drive-relative paths allowed the real parser and generator to complete without editing their installed packages. A likely contributing factor is that the multisource resolver uses POSIX path rules for an explicitly injected filesystem, including the real filesystem provided by Model; this is an observation, not a claim to have tested an upstream fix.
3. Generated npm scripts assume `rm -rf` and single-quoted globs. Windows verification used explicit `npx tsc --build src test` and `node --test-concurrency=1 --test "dist-test/**/*.test.js"`. A platform-neutral clean command and glob quoting would make the advertised commands easier to use.
4. `QuoteCreateData` incorrectly requires the response fields `artifacts` and `quote` for a request whose OpenAPI request schema requires only `rfq` and `catalogue_csv`. The request is accepted by the real API and generated JavaScript operation; the small valid-request typecheck fails with TS2345. `consumer-typecheck.ts` and `TYPECHECK-OBSERVATION.txt` reproduce this. Separate request/response types would help APIs with asymmetric payloads.
5. Generation completed with warnings for missing `ReadmeFeatures_ts` and `AgentGuide_ts` components. The SDK still built and its offline/live checks passed; I have not investigated the effect on the full documentation output.

The first real PDF check returned 503 because the fresh local Python environment lacked the API's declared optional format dependencies. Installing `api/requirements.txt` in an isolated virtual environment resolved it; this was an API setup issue, not a generator defect.

I would keep the entity interface and generated test coverage, and prioritise the Windows setup path and request/response type separation. This small submission tests local synthetic data only; it is not a production certification or a finished customer deployment.
