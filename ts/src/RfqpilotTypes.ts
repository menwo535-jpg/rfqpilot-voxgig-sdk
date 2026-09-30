// Typed models for the Rfqpilot SDK.
//
// GENERATED from the API model: main.kit.entity.<e>.fields{} and per-op
// params (op.<name>.points[].g.params[]). Field/param types come from the
// canonical type sentinels via @voxgig/sdkgen canonToType (source of truth:
// @voxgig/apidef VALID_CANON). Do not edit by hand.

export interface Quote {
  artifacts: Record<string, any>
  catalogue_csv: string
  include_xlsx?: boolean
  quote: Record<string, any>
  rfq: Record<string, any>
}

export interface QuoteCreateData {
  artifacts: Record<string, any>
  catalogue_csv: string
  include_xlsx?: boolean
  quote: Record<string, any>
  rfq: Record<string, any>
}

