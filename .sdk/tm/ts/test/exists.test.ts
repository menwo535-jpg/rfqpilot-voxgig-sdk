
import { test, describe } from 'node:test'
import { equal } from 'node:assert'


import { RfqpilotSDK } from '..'


describe('exists', async () => {

  test('test-mode', () => {
    const testsdk = RfqpilotSDK.test()
    equal(testsdk instanceof RfqpilotSDK, true,
      'RfqpilotSDK.test() must return a client synchronously')
  })

})
