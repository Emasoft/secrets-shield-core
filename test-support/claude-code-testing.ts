// WHY this file exists: the core tests import their test API from 'claude-code/testing', a module only the claude binary provides (claude plugin test). The API they use (describe, expect, test, mock) is bun:test's, so tsconfig paths map the specifier here and bun test runs them with no change to the test files.
export { describe, expect, mock, test } from 'bun:test'
