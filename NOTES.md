# Acceptance Check Results

Ran the checks through `./csv-validator` with temporary CSV, schema, and JSON
files. Each check asserted the CLI exit code, console summary/rejection reason,
and parsed JSON output.

| Check | Result | Observed |
|---|---|---|
| 1. Valid row passes through | PASS | One record with the schema-defined fields was written; summary reported 1 valid row and 0 rejected rows. |
| 2. Invalid integer is rejected | PASS | `quantity=abc` was rejected with an integer validation reason; output JSON was `[]`. |
| 3. Minimum rule rejects invalid value | PASS | `quantity=0` with `min: 1` was rejected with `quantity must be >= 1`; output JSON was `[]`. |
| Edge case: header-only CSV | PASS | Output JSON was `[]`; summary reported 0 valid rows and 0 rejected rows. |

All three acceptance checks passed, so no specification, implementation, or
check corrections were needed. The additional empty-CSV edge-case check also
passed.
