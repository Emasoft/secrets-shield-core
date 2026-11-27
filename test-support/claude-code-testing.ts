// WHY this file exists: the core tests import their test API from 'claude-code/testing', a module only the claude binary provides. describe, expect and mock are bun:test's own. test also takes an options object {timeoutMs} (the host's form); bun:test takes {timeout} as a third argument, so this wrapper maps one to the other. Without it the {timeoutMs} option is a type error and bun ignores it at run time, leaving the default 5 s limit on the timing tests.
import { describe, expect, mock, test as bunTest } from 'bun:test'

type Body = Parameters<typeof bunTest>[1]
type Options = { timeoutMs?: number }

function test(name: string, body: Body): void
function test(name: string, options: Options, body: Body): void
function test(name: string, second: Body | Options, third?: Body): void {
  if (typeof second === 'function') bunTest(name, second)
  else bunTest(name, third as Body, { timeout: second.timeoutMs })
}

export { describe, expect, mock, test }
