---
title: CSV Validator CLI
type: command-line-utility
status: draft
created: 2026-11-25
---

# CSV Validator

## Intent

A lightweight command-line utility that validates CSV data against a user-defined schema, filters valid rows into a JSON output, and reports summary statistics on rejected rows. Use this tool to clean and standardize data before downstream processing, with flexible field definitions and validation rules.

**Key capability**: Accept a CSV input file and schema configuration, reject malformed or invalid rows with clear error reasons, print a summary of rejected rows while preserving valid rows in machine-readable JSON format.

## Boundaries & Constraints

**In scope:**
- Read CSV input with headers
- Accept field schema configuration (JSON format)
- Validate each row against configured rules
- Write valid rows to JSON file
- Print rejection summary to console

**Out of scope:**
- Modifying or correcting invalid data
- Interactive user prompts for fixes
- Supporting multiple CSV formats

**Constraints:**
- Input must be valid UTF-8 CSV
- CSV must have headers in first row
- Schema if supplied defines all validation rules
- Use default schema when not supplied
- Output JSON file location determined by CLI argument
- Row numbers in console output are 1-indexed and refer to data rows (not counting the header)

## Input & Output Specification

### Input

**Format:** CSV with headers + JSON schema configuration

**CSV Format:**
- Must contain headers in first row
- Column names must match schema field names
- Values must conform to configured field types

**Schema Configuration (JSON):**
Defines validation rules for each field. A custom schema file is passed via the `--schema` CLI argument; if `--schema` is omitted, the tool applies the built-in default schema shown below.

```json
{
  "fields": [
    {
      "name": "order_id",
      "type": "string",
      "required": true,
      "rules": {
        "non_empty": true
      }
    },
    {
      "name": "customer_name",
      "type": "string",
      "required": true,
      "rules": {
        "non_empty": true
      }
    },
    {
      "name": "item_name",
      "type": "string",
      "required": true,
      "rules": {
        "non_empty": true
      }
    },
    {
      "name": "item_unit_price",
      "type": "decimal",
      "required": true,
      "rules": {
        "min": 0
      }
    },
    {
      "name": "quantity",
      "type": "integer",
      "required": true,
      "rules": {
        "min": 1
      }
    }
  ]
}
```

**Example CSV:**
```
order_id,customer_name,item_name,item_unit_price,quantity
ORD-001,Alice Smith,Laptop,1000,5
ORD-002,Bob Jones,Mouse,20,4
```

**Field Type Support:**
- `string`: Text values
- `integer`: Whole numbers
- `decimal`: Floating-point numbers
- `date`: Date format (DD-MM-YYYY)
- `boolean`: true/false

### Output

**Valid rows JSON file:**
All fields from schema preserved, with types coerced to match field definitions:
```json
[
  {
    "order_id": "ORD-001",
    "customer_name": "Alice Smith",
    "item_name": "Laptop",
    "item_unit_price": 1000,
    "quantity": 5
  },
  {
    "order_id": "ORD-002",
    "customer_name": "Bob Jones",
    "item_name": "Mouse",
    "item_unit_price": 20,
    "quantity": 4
  }
]
```

**Rejection summary (console output):**
```
Validation Results
==================
Valid rows: 1
Rejected rows: 3

Rejected Rows:
- Row 2: quantity must be >= 1 (got: 0)
- Row 3: customer_name is required (got: empty)
- Row 4: quantity must be an integer (got: "abc")
```

## Validation Rules

### Type Validation
- **string**: Value treated as text; numeric and boolean values are coerced to their string representation. Rejects: (none on type alone, all CSV values are initially strings)
- **integer**: Value must parse as whole number with no decimal point. Rejects: decimals, non-numeric, empty
- **decimal**: Value must parse as a valid number (integer or decimal). Rejects: non-numeric, empty. Output as JSON number (e.g., `1000` or `1000.50`)
- **date**: Value must be in Date format (DD-MM-YYYY). Dates are parsed before min/max comparison. Rejects: invalid formats, unparseable values
- **boolean**: Value must be "true", "false", "1", or "0". Rejects: other values

### Field-Level Rules
Applied per field in schema `rules` object:

1. **required**: If true, field must be present and not empty (applies to all types). Rejects: missing columns, empty values
2. **non_empty**: For string fields only. Rejects empty strings or strings containing only whitespace. Rejects: "", "   " (stricter than `required` alone, which accepts any non-empty value)
3. **min**: Numeric/date value must be >= min. Rejects: values below threshold
4. **max**: Numeric/date value must be <= max. Rejects: values above threshold
5. **pattern**: String must match regex pattern. Rejects: non-matching values
6. **length_min**: String length must be >= threshold. Rejects: shorter strings
7. **length_max**: String length must be <= threshold. Rejects: longer strings
8. **allowed_values**: Value must be in provided list. Rejects: values not in list

## Edge Cases

### Edge Case 1: Empty CSV
**Scenario:** Input CSV contains only headers or is completely empty

**Expected behavior:**
- JSON output file contains empty array: `[]`
- Console summary shows: "Valid rows: 0, Rejected rows: 0"
- Exit code: 0 (success)

### Edge Case 2: Missing Required Columns
**Scenario:** CSV is missing one or more columns defined in schema

**Expected behavior:**
- Each row is rejected with error: "Missing required column: <column_name>"
- All rows fail validation (data/schema mismatch), appear in rejection summary
- JSON output is empty array
- Console shows rejection count equal to data row count
- Exit code: 0 (success, data quality issue, not configuration error)

### Edge Case 3: Malformed Row
**Scenario:** A row has fewer columns than headers

**Expected behavior:**
- Entire row is rejected with error reason: "Row has incorrect number of columns (expected N, got M)"
- Row appears in rejection summary
- Processing continues with remaining rows
- Exit code: 0 (success, with rejected data logged)

### Edge Case 3b: Extra Columns in CSV
**Scenario:** CSV contains columns not defined in the schema

**Expected behavior:**
- Extra columns are ignored (not included in output JSON)
- Rows are validated only against schema-defined columns
- Processing continues normally
- Exit code: 0 (success)

### Edge Case 4: Schema File Not Found
**Scenario:** Specified schema file does not exist

**Expected behavior:**
- Exit code: 1 (error)
- Print to stderr: "Error: Schema file not found: <path>"
- No CSV processing occurs

### Edge Case 5: Schema Not Specified
**Scenario:** `--schema` argument is not supplied

**Expected behavior:**
- The built-in default schema (see Input & Output Specification) is applied
- CSV processing continues normally against the default schema
- JSON output and console summary are produced as usual
- Exit code: 0 (success)


## Acceptance Criteria

### Check 1: Valid Rows Pass Through
**Given** a CSV with one valid row (all schema-defined fields present and valid)
**When** the validator runs with a schema
**Then** the JSON output contains exactly one record with all fields, and console shows "Valid rows: 1, Rejected rows: 0"

### Check 2: Type Validation Rejects Invalid Types
**Given** a CSV with one row where an integer field contains "abc"
**When** the validator runs
**Then** the row is rejected, appears in the rejection summary with reason "field_name must be an integer", and JSON output is empty

### Check 3: Custom Rules Reject Invalid Values
**Given** a schema with rule `{"min": 1}` on a quantity field, and a CSV row with quantity: 0
**When** the validator runs
**Then** the row is rejected, appears in the rejection summary with reason "quantity must be >= 1", and JSON output is empty

### Check 4: Empty CSV Produces Empty JSON
**Given** a CSV with headers only and no data rows
**When** the validator runs with any valid schema
**Then** the JSON output is an empty array `[]`, console shows "Valid rows: 0, Rejected rows: 0", and exit code is 0

### Check 5: Invalid Schema Returns Error
**Given** a schema file path that does not exist
**When** the validator runs
**Then** exit code is 1, stderr contains "Schema file not found", and no CSV processing occurs

## Verification

### CLI Usage
```bash
./csv-validator <input.csv> <output.json> [--schema <schema.json>]
```

Run the command from the `Week0` directory. The Bash entry point forwards all
arguments to `csv_validator.py`, so a custom schema is optional:

```bash
./csv-validator orders.csv output.json
./csv-validator orders.csv output.json --schema schema.json
```

### Manual Testing Example

**Create schema:**
```bash
cat > schema.json << 'EOF'
{
  "fields": [
    {"name": "order_id", "type": "string", "required": true, "rules": {"non_empty": true}},
    {"name": "customer_name", "type": "string", "required": true, "rules": {"non_empty": true}},
    {"name": "item_name", "type": "string", "required": true, "rules": {"non_empty": true}},
    {"name": "item_unit_price", "type": "decimal", "required": true, "rules": {"min": 0}},
    {"name": "quantity", "type": "integer", "required": true, "rules": {"min": 1}}
  ]
}
EOF
```

**Create test CSV:**
```bash
cat > orders.csv << 'EOF'
order_id,customer_name,item_name,item_unit_price,quantity
ORD-001,Alice,Laptop,1000,5
ORD-002,,Mouse,20,3
ORD-003,Charlie,Keyboard,50,-1
EOF
```

**Run validator:**
```bash
./csv-validator orders.csv output.json --schema schema.json
```

**Verify output:**
```bash
cat output.json  # Should contain only ORD-001
# Check console output for rejection summary
```

### Success Criteria
- ✓ JSON output is valid and parseable
- ✓ All valid rows appear in JSON with correct fields
- ✓ All invalid rows listed in console with specific rejection reason
- ✓ Exit code is 0 for successful validation (even with rejections)
- ✓ Exit code is 1 for configuration errors (missing schema file)
- ✓ Empty CSV produces empty JSON array, not error
- ✓ Type mismatches produce specific error messages, not crashes
- ✓ Custom rules (min, max, pattern, etc.) are properly enforced
