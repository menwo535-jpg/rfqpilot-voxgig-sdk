
import { BaseFeature } from './feature/base/BaseFeature'
import { TestFeature } from './feature/test/TestFeature'



const FEATURE_CLASS: Record<string, typeof BaseFeature> = {
   test: TestFeature,

}


const FEATURE_PLUGINS: Record<string, any[]> = {
  
}


class Config {

  makeFeature(this: any, fn: string) {
    const fc = FEATURE_CLASS[fn]
    const fi = new fc()
    return fi
  }

  // False for a feature added at runtime via options.extend (station's
  // adopt path) - the constructor uses this to skip makeFeature for names
  // no generated class backs.
  hasFeature(this: any, fn: string) {
    return null != FEATURE_CLASS[fn]
  }


  main = {
    name: 'Rfqpilot',
        slug: "rfqpilot",
    version: "0.0.1",
    target: "ts",

  }


  feature = {
     test:     {
      "options": {
        "active": false
      },
      "optspec": {
        "entity": "`$MAP`",
        "net": "`$MAP`"
      },
      "strict": false,
      "transport": "base"
    },

  }


  options = {
    base: "http://127.0.0.1:8765",

    auth: {
      prefix: 'Bearer',
    },

    headers: {
      "content-type": "application/json"
    },

    entity: {
      
        quote: {
        },
  
    }
  }


  entity = {
    "quote": {
      "fields": [
        {
          "name": "artifacts",
          "title": "Artifacts",
          "type": "`$OBJECT`",
          "req": true
        },
        {
          "name": "catalogue_csv",
          "title": "Catalogue Csv",
          "type": "`$STRING`",
          "req": true
        },
        {
          "name": "include_xlsx",
          "title": "Include Xlsx",
          "type": "`$BOOLEAN`"
        },
        {
          "name": "quote",
          "title": "Quote",
          "type": "`$OBJECT`",
          "req": true,
          "short": "Original processor result; retains rows, review flags and exact decimal amounts as strings"
        },
        {
          "name": "rfq",
          "title": "Rfq",
          "type": "`$OBJECT`",
          "req": true
        }
      ],
      "name": "quote",
      "op": {
        "create": {
          "input": "data",
          "name": "create",
          "points": [
            {
              "kind": "http",
              "method": "POST",
              "orig": "/quote",
              "segments": [
                {
                  "lit": "quote"
                }
              ],
              "parts": [
                "quote"
              ],
              "rename": {},
              "transform": {
                "req": {
                  "catalogue_csv": "`reqdata.catalogue_csv`",
                  "include_xlsx": "`reqdata.include_xlsx`",
                  "rfq": "`reqdata.rfq`"
                },
                "res": "`body`"
              },
              "args": {},
              "select": {}
            }
          ]
        }
      },
      "relations": {
        "ancestors": []
      }
    }
  }
}


const config = new Config()

export {
  config,
  FEATURE_PLUGINS,
}

