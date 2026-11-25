# Acceptance Check Results

Ran the checks using command  cd /Users/priyankamittal/FDE/Week0 && python3 csv_validator.py input.csv output.json --schema schema.json

## Validation Results
==================
Valid rows: 1
Rejected rows: 2

Rejected Rows:
- Row 2: customer_name is required (got: empty)
- Row 3: quantity must be >= 1 (got: -1)

 ## Observations
 
| Check | Result | Observed |
|---|---|---|
| 1. Valid row passes through for ORD-007 | PASS | One record with the schema-defined fields was written; summary reported 1 valid row and 2 rejected rows. |
| 2. customer_name empty/ not provided for ORD-009| PASS | Row 2: customer_name is required (got: empty) |
| 3. Minimum rule rejects invalid value | PASS | Row 3: quantity must be >= 1 


# Account  information & Usage

## Account Information

## Usage
Claude usage : used $2.03 of $12.00 monthly limit. 


