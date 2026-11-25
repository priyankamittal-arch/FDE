#!/usr/bin/env python3
"""Test suite for CSV Validator."""

import json
import tempfile
from pathlib import Path

from csv_validator import CSVValidator, SchemaValidator, ValidationError


def test_valid_rows():
    """Test that valid rows pass through."""
    schema = SchemaValidator.DEFAULT_SCHEMA
    validator = SchemaValidator(schema)
    csv_validator = CSVValidator(validator)

    csv_content = """order_id,customer_name,item_name,item_unit_price,quantity
ORD-001,Alice Smith,Laptop,1000,5
ORD-002,Bob Jones,Mouse,20,4"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 2
    assert len(csv_validator.errors) == 0
    assert csv_validator.valid_rows[0]["order_id"] == "ORD-001"
    assert csv_validator.valid_rows[0]["quantity"] == 5
    Path(f.name).unlink()
    print("✓ test_valid_rows passed")


def test_type_validation_integer():
    """Test that invalid integer types are rejected."""
    schema = SchemaValidator.DEFAULT_SCHEMA
    validator = SchemaValidator(schema)
    csv_validator = CSVValidator(validator)

    csv_content = """order_id,customer_name,item_name,item_unit_price,quantity
ORD-001,Alice,Laptop,1000,abc"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 0
    assert len(csv_validator.errors) == 1
    assert "must be an integer" in csv_validator.errors[0].reason
    Path(f.name).unlink()
    print("✓ test_type_validation_integer passed")


def test_min_rule():
    """Test that min rule validation works."""
    schema = SchemaValidator.DEFAULT_SCHEMA
    validator = SchemaValidator(schema)
    csv_validator = CSVValidator(validator)

    csv_content = """order_id,customer_name,item_name,item_unit_price,quantity
ORD-001,Alice,Laptop,1000,5
ORD-002,Bob,Mouse,20,0"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 1
    assert len(csv_validator.errors) == 1
    assert "must be >= 1" in csv_validator.errors[0].reason
    Path(f.name).unlink()
    print("✓ test_min_rule passed")


def test_non_empty_rule():
    """Test that non_empty rule rejects empty and whitespace strings."""
    schema = SchemaValidator.DEFAULT_SCHEMA
    validator = SchemaValidator(schema)
    csv_validator = CSVValidator(validator)

    csv_content = """order_id,customer_name,item_name,item_unit_price,quantity
ORD-001,Alice,Laptop,1000,5
ORD-002,,Mouse,20,3"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 1
    assert len(csv_validator.errors) == 1
    assert "is required" in csv_validator.errors[0].reason
    Path(f.name).unlink()
    print("✓ test_non_empty_rule passed")


def test_empty_csv():
    """Test that empty CSV produces empty JSON output."""
    schema = SchemaValidator.DEFAULT_SCHEMA
    validator = SchemaValidator(schema)
    csv_validator = CSVValidator(validator)

    csv_content = "order_id,customer_name,item_name,item_unit_price,quantity"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 0
    assert len(csv_validator.errors) == 0
    Path(f.name).unlink()
    print("✓ test_empty_csv passed")


def test_missing_required_column():
    """Test that missing required columns reject all rows."""
    schema = SchemaValidator.DEFAULT_SCHEMA
    validator = SchemaValidator(schema)
    csv_validator = CSVValidator(validator)

    csv_content = """order_id,customer_name,item_name
ORD-001,Alice,Laptop
ORD-002,Bob,Mouse"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 0
    assert len(csv_validator.errors) == 2
    assert "Missing required column" in csv_validator.errors[0].reason
    Path(f.name).unlink()
    print("✓ test_missing_required_column passed")


def test_extra_columns_ignored():
    """Test that extra columns in CSV are ignored."""
    schema = SchemaValidator.DEFAULT_SCHEMA
    validator = SchemaValidator(schema)
    csv_validator = CSVValidator(validator)

    csv_content = """order_id,customer_name,item_name,item_unit_price,quantity,extra_field
ORD-001,Alice,Laptop,1000,5,ignored"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 1
    assert len(csv_validator.errors) == 0
    assert "extra_field" not in csv_validator.valid_rows[0]
    Path(f.name).unlink()
    print("✓ test_extra_columns_ignored passed")


def test_decimal_output():
    """Test that decimals are output as JSON numbers."""
    schema = SchemaValidator.DEFAULT_SCHEMA
    validator = SchemaValidator(schema)
    csv_validator = CSVValidator(validator)

    csv_content = """order_id,customer_name,item_name,item_unit_price,quantity
ORD-001,Alice,Laptop,1000.50,5"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 1
    assert csv_validator.valid_rows[0]["item_unit_price"] == 1000.50
    Path(f.name).unlink()
    print("✓ test_decimal_output passed")


def test_custom_schema():
    """Test loading and using a custom schema."""
    custom_schema = {
        "fields": [
            {"name": "name", "type": "string", "required": True, "rules": {"non_empty": True}},
            {"name": "age", "type": "integer", "required": True, "rules": {"min": 0, "max": 150}},
        ]
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(custom_schema, f)
        f.flush()
        schema = SchemaValidator.load_schema(f.name)

    assert len(schema["fields"]) == 2
    assert schema["fields"][0]["name"] == "name"
    Path(f.name).unlink()
    print("✓ test_custom_schema passed")


def test_pattern_rule():
    """Test regex pattern validation."""
    custom_schema = {
        "fields": [
            {
                "name": "email",
                "type": "string",
                "required": True,
                "rules": {"pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"},
            }
        ]
    }

    validator = SchemaValidator(custom_schema)
    csv_validator = CSVValidator(validator)

    csv_content = """email
test@example.com
invalid-email"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 1
    assert len(csv_validator.errors) == 1
    assert "must match pattern" in csv_validator.errors[0].reason
    Path(f.name).unlink()
    print("✓ test_pattern_rule passed")


def test_allowed_values_rule():
    """Test allowed_values validation."""
    custom_schema = {
        "fields": [
            {
                "name": "status",
                "type": "string",
                "required": True,
                "rules": {"allowed_values": ["active", "inactive", "pending"]},
            }
        ]
    }

    validator = SchemaValidator(custom_schema)
    csv_validator = CSVValidator(validator)

    csv_content = """status
active
pending
invalid"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 2
    assert len(csv_validator.errors) == 1
    assert "must be one of" in csv_validator.errors[0].reason
    Path(f.name).unlink()
    print("✓ test_allowed_values_rule passed")


def test_date_validation():
    """Test date format validation."""
    custom_schema = {
        "fields": [
            {"name": "date", "type": "date", "required": True, "rules": {}}
        ]
    }

    validator = SchemaValidator(custom_schema)
    csv_validator = CSVValidator(validator)

    csv_content = """date
25-12-2025
13/12/2025
31-12-2025"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 2
    assert len(csv_validator.errors) == 1
    assert "must be a date" in csv_validator.errors[0].reason
    Path(f.name).unlink()
    print("✓ test_date_validation passed")


def test_boolean_validation():
    """Test boolean type validation."""
    custom_schema = {
        "fields": [
            {"name": "active", "type": "boolean", "required": True, "rules": {}}
        ]
    }

    validator = SchemaValidator(custom_schema)
    csv_validator = CSVValidator(validator)

    csv_content = """active
true
false
1
0
yes"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 4
    assert len(csv_validator.errors) == 1
    assert "must be a boolean" in csv_validator.errors[0].reason
    Path(f.name).unlink()
    print("✓ test_boolean_validation passed")


def test_length_rules():
    """Test length_min and length_max rules."""
    custom_schema = {
        "fields": [
            {
                "name": "code",
                "type": "string",
                "required": True,
                "rules": {"length_min": 3, "length_max": 5},
            }
        ]
    }

    validator = SchemaValidator(custom_schema)
    csv_validator = CSVValidator(validator)

    csv_content = """code
ab
abc
abcd
abcde
abcdef"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        f.flush()
        csv_validator.validate_file(f.name)

    assert len(csv_validator.valid_rows) == 3  # abc, abcd, abcde
    assert len(csv_validator.errors) == 2  # ab (too short), abcdef (too long)
    Path(f.name).unlink()
    print("✓ test_length_rules passed")


if __name__ == "__main__":
    test_valid_rows()
    test_type_validation_integer()
    test_min_rule()
    test_non_empty_rule()
    test_empty_csv()
    test_missing_required_column()
    test_extra_columns_ignored()
    test_decimal_output()
    test_custom_schema()
    test_pattern_rule()
    test_allowed_values_rule()
    test_date_validation()
    test_boolean_validation()
    test_length_rules()
    print("\n✅ All tests passed!")
