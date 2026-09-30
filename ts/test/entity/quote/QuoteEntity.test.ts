

import Path from 'node:path'
import * as Fs from 'node:fs'

import { test, describe, afterEach } from 'node:test'
import assert from 'node:assert'
import { createLiveTransport } from '../../live-runner'
import { runLiveEntity } from '../../live-entity'


import { RfqpilotSDK, BaseFeature, stdutil } from '../../..'

import {
  envOverride,
  liveClientOptions,
  liveDelay,
  loadEnvLocal,
  makeCtrl,
  makeMatch,
  makeReqdata,
  makeStepData,
  makeValid,
  maybeSkipControl,
} from '../../utility'


loadEnvLocal(__dirname + '/../../../.env.local')


describe('QuoteEntity', async () => {

  // Per-test live pacing. Delay is read from sdk-test-control.json's
  // `test.live.delayMs`; only sleeps when RFQPILOT_TEST_LIVE=TRUE.
  afterEach(liveDelay('RFQPILOT_TEST_LIVE'))

  test('instance', async () => {
    const testsdk = RfqpilotSDK.test()
    const ent = testsdk.Quote()
    assert(null != ent)
  })


  test('basic', async (t) => {

    const live = 'TRUE' === process.env.RFQPILOT_TEST_LIVE
    for (const op of ['create']) {
      if (!live && maybeSkipControl(t, 'entityOp', 'quote.' + op, live)) return
    }

    
    const setup = basicSetup()
    if (setup.live) {
      return runLiveEntity(setup, {"active":true,"alias":{"field":{}},"fields":{"artifacts":{"a":true,"h":"Artifacts","n":"artifacts","r":true,"t":"`$OBJECT`","key$":"artifacts","index$":0},"catalogue_csv":{"a":true,"h":"Catalogue Csv","n":"catalogue_csv","r":true,"t":"`$STRING`","key$":"catalogue_csv","index$":1},"include_xlsx":{"a":true,"h":"Include Xlsx","n":"include_xlsx","r":false,"t":"`$BOOLEAN`","key$":"include_xlsx","index$":2},"quote":{"a":true,"h":"Quote","n":"quote","r":true,"sh":"Original processor result; retains rows, review flags and exact decimal amounts as strings","t":"`$OBJECT`","key$":"quote","index$":3},"rfq":{"a":true,"h":"Rfq","n":"rfq","r":true,"t":"`$OBJECT`","key$":"rfq","index$":4}},"name":"quote","op":{"create":{"input":"data","name":"create","points":[{"a":true,"co":{"id":"POST /quote","source":"openapi3","version":2},"g":{},"k":"http","m":"POST","o":"/quote","q":{},"r":{},"s":[{"lit":"quote"}],"t":{"req":{"catalogue_csv":"`reqdata.catalogue_csv`","include_xlsx":"`reqdata.include_xlsx`","rfq":"`reqdata.rfq`"},"res":"`body`"},"index$":0}],"key$":"create"}},"relations":{"ancestors":[]},"key$":"quote","name__orig":"quote","Name":"Quote","name_":"quote","name-":"quote","NAME":"QUOTE","index$":0}, {"active":true,"entity":"quote","key$":"BasicQuoteFlow","kind":"basic","name":"BasicQuoteFlow","param":{},"step":[{"a":true,"d":{},"i":{"ref":"quote_ref01"},"m":{},"o":"create","s":[],"v":[]}]}, 'Quote', {"POST /quote":{"protocol":"http","requestBody":{"required":true,"content":{"application/json":{"schema":{"type":"object","additionalProperties":false,"required":["rfq","catalogue_csv"],"properties":{"rfq":{"type":"object","additionalProperties":false,"required":["format","content"],"properties":{"format":{"type":"string","enum":["txt","pdf_base64"]},"content":{"type":"string","minLength":1}},"key$":"rfq"},"catalogue_csv":{"type":"string","minLength":1,"key$":"catalogue_csv"},"include_xlsx":{"type":"boolean","default":false,"key$":"include_xlsx"}},"x-ref":"#/components/schemas/QuoteRequest","index$":1}}}},"parameters":[]}})
    }
    const client = setup.client
    const struct = setup.struct

    const isempty = struct.isempty
    const select = struct.select


    // CREATE
    const quote_ref01_ent = client.Quote()
    let quote_ref01_data = setup.data.new.quote['quote_ref01']

    quote_ref01_data = (await quote_ref01_ent.create(quote_ref01_data)).data()
    assert(null != quote_ref01_data)


  })
})



function basicSetup(extra?: any) {
  // TODO: fix test def options
  const options: any = {} // null

  // TODO: needs test utility to resolve path
  const entityDataFile =
    Path.resolve(__dirname, 
      '../../../../.sdk/test/entity/quote/QuoteTestData.json')

  // TODO: file ready util needed?
  const entityDataSource = Fs.readFileSync(entityDataFile).toString('utf8')

  // TODO: need a xlang JSON parse utility in voxgig/struct with better error msgs
  const entityData = JSON.parse(entityDataSource)

  options.entity = entityData.existing

  let client = RfqpilotSDK.test(options, extra)
  const struct = client.utility().struct
  const merge = struct.merge
  const transform = struct.transform

  let idmap = transform(
    ['quote01','quote02','quote03'],
    {
      '`$PACK`': ['', {
        '`$KEY`': '`$COPY`',
        '`$VAL`': ['`$FORMAT`', 'upper', '`$COPY`']
      }]
    })

  const env = envOverride({
    'RFQPILOT_TEST_QUOTE_ENTID': idmap,
    'RFQPILOT_TEST_LIVE': 'FALSE',
    'RFQPILOT_TEST_EXPLAIN': 'FALSE',
    'RFQPILOT_APIKEY': '',
  })

  idmap = env['RFQPILOT_TEST_QUOTE_ENTID']

  const live = 'TRUE' === env.RFQPILOT_TEST_LIVE

  const transport = createLiveTransport()
  if (live) {
    const rawIds = process.env['RFQPILOT_TEST_QUOTE_ENTID']
    idmap = rawIds && rawIds.trim() ? JSON.parse(rawIds) : {}
    if (!idmap || Array.isArray(idmap) || typeof idmap !== 'object') {
      throw new Error('Live ENTID must be a JSON object')
    }
    client = new RfqpilotSDK(merge([
      // FIRST, so the generated fields below win: sdk-test-control.json's
      // test.client.options adds to the live client, it does not redirect it.
      liveClientOptions(),
      {
        apikey: env.RFQPILOT_APIKEY,
      },
      // 'extra || {}', not a bare 'extra': struct.merge returns UNDEFINED when the
      // last entry is undefined, and basicSetup is normally called with no
      // argument at all - so a bare 'extra' silently discarded the apikey
      // and server values above and handed the SDK undefined. Harmless
      // while there was nothing in that object; not harmless now.
      extra || {},
      { system: { fetch: transport.fetch } }
    ]))
  }

  const setup = {
    idmap,
    env,
    options,
    client,
    struct,
    data: entityData,
    explain: 'TRUE' === env.RFQPILOT_TEST_EXPLAIN,
    live,
    transport,
    now: Date.now(),
  }

  return setup
}
  
