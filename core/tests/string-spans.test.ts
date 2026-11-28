// WHY this file exists (secrets-shield-core#2): core/tests/json-line.test.ts reaches stringSpans only through redactJsonLine, so these tests call it directly. Moved here from reports-sanitizer,
// which carried it outside its pin of this repo.
import { describe, expect, test } from 'claude-code/testing'

import { stringSpans } from '../patterns'

describe('stringSpans', () => {
  test('an escaped quote does not end a string token', () => {
    // doc: {"a":"x\"y"}
    expect(stringSpans('{"a":"x\\"y"}')).toEqual([[1, 4], [5, 11]])
  })
  test('an escaped backslash before a quote does end the token', () => {
    // doc: {"a":"x\\"}
    expect(stringSpans('{"a":"x\\\\"}')).toEqual([[1, 4], [5, 10]])
  })
  test('a backslash-n escape stays inside its token', () => {
    // doc: {"t":"a\nb"}
    expect(stringSpans('{"t":"a\\nb"}')).toEqual([[1, 4], [5, 11]])
  })
  test('a non-string token (true, 1) yields no span', () => {
    expect(stringSpans('{"a":true,"b":1}')).toEqual([[1, 4], [10, 13]])
  })
})
