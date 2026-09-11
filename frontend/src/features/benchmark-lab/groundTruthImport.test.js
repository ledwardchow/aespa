import { expect, test } from "vitest";
import { parseGroundTruthText, parseMarkdownGroundTruth } from "./groundTruthImport.js";

test("imports numbered OWASP vulnerability Markdown", () => {
  const parsed = parseMarkdownGroundTruth(`# Example vulnerabilities

## A01: Broken Access Control

### 1. IDOR in transaction detail
- **File:** \`src/Controllers/TransactionController.php\` — \`show()\`
- **Description:** Ownership is not checked before returning the transaction.
- **Exploit:** \`GET /api/transactions/1\` returns another user's record.

### 2. Missing audit logging
- **Description:** Security events are not logged.
`);

  expect(parsed.name).toBe("Example vulnerabilities");
  expect(parsed.items).toHaveLength(2);
  expect(parsed.items[0]).toMatchObject({
    external_id: "GT-1",
    category: "A01: Broken Access Control",
    locations: [{ path: "src/Controllers/TransactionController.php" }],
    affected_operation: "GET /api/transactions/1",
  });
  expect(parsed.items[1].external_id).toBe("GT-2");
});

test("continues to accept canonical JSON", () => {
  const parsed = parseGroundTruthText('{"name":"Fixture","items":[]}', "fixture.json");
  expect(parsed).toEqual({ name: "Fixture", items: [] });
});

test("preserves underscores in source identifiers", () => {
  const parsed = parseMarkdownGroundTruth(`# Fixture
## A03: Injection
### 1. Unsafe call
- **Description:** Input reaches \`file_get_contents()\` through \`avatar_url\`.
`);
  expect(parsed.items[0].description).toContain("file_get_contents()");
  expect(parsed.items[0].description).toContain("avatar_url");
});
