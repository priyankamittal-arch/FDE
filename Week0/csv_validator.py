#!/usr/bin/env python3
"""CSV Validator CLI - Validates CSV data against a schema and outputs valid rows as JSON."""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ValidationError:
    """Represents a validation error for a row."""

    def __init__(self, row_number: int, reason: str):
        self.row_number = row_number
        self.reason = reason

    def __str__(self) -> str:
        return f"Row {self.row_number}: {self.reason}"


class SchemaValidator:
    """Validates data against a schema."""

    # Default schema to use when none is provided
    DEFAULT_SCHEMA = {
        "fields": [
            {
                "name": "order_id",
                "type": "string",
                "required": True,
                "rules": {"non_empty": True},
            },
            {
                "name": "customer_name",
                "type": "string",
                "required": True,
                "rules": {"non_empty": True},
            },
            {
                "name": "item_name",
                "type": "string",
                "required": True,
                "rules": {"non_empty": True},
            },
            {
                "name": "item_unit_price",
                "type": "decimal",
                "required": True,
                "rules": {"min": 0},
            },
            {
                "name": "quantity",
                "type": "integer",
                "required": True,
                "rules": {"min": 1},
            },
        ]
    }

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.field_map = {field["name"]: field for field in schema.get("fields", [])}

    @staticmethod
    def load_schema(schema_path: Optional[str]) -> Dict[str, Any]:
        """Load schema from file or return default schema."""
        if schema_path is None:
            return SchemaValidator.DEFAULT_SCHEMA

        schema_file = Path(schema_path)
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        try:
            with open(schema_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file: {e}")

    def validate_row(
        self, row: Dict[str, str], row_number: int, csv_headers: List[str]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[ValidationError]]:
        """
        Validate a single row against the schema.
        Returns (validated_row, error) where one will be None.
        """
        # Check for missing required columns
        for field_name in self.field_map:
            if field_name not in csv_headers:
                return None, ValidationError(
                    row_number, f"Missing required column: {field_name}"
                )

        validated_row = {}

        for field in self.schema.get("fields", []):
            field_name = field["name"]
            field_type = field["type"]
            is_required = field.get("required", False)
            rules = field.get("rules", {})

            value = row.get(field_name, "")

            # Type validation
            try:
                typed_value = self._validate_type(value, field_type, field_name)
            except ValueError as e:
                return None, ValidationError(row_number, str(e))

            # Required check
            if is_required and (value == "" or typed_value is None):
                return None, ValidationError(
                    row_number, f"{field_name} is required (got: empty)"
                )

            # Apply field-level rules
            error = self._validate_rules(typed_value, field_name, field_type, rules)
            if error:
                return None, ValidationError(row_number, error)

            validated_row[field_name] = typed_value

        return validated_row, None

    def _validate_type(self, value: str, field_type: str, field_name: str) -> Any:
        """Validate and coerce value to the specified type."""
        if field_type == "string":
            return value

        if field_type == "integer":
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be an integer (got: empty)")
            try:
                if "." in value:
                    raise ValueError(
                        f"{field_name} must be an integer (got: {value!r})"
                    )
                return int(value)
            except ValueError:
                raise ValueError(
                    f"{field_name} must be an integer (got: {value!r})"
                )

        if field_type == "decimal":
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a decimal (got: empty)")
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"{field_name} must be a decimal (got: {value!r})")

        if field_type == "date":
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a date (got: empty)")
            try:
                datetime.strptime(value, "%d-%m-%Y")
                return value
            except ValueError:
                raise ValueError(
                    f"{field_name} must be a date in DD-MM-YYYY format (got: {value!r})"
                )

        if field_type == "boolean":
            if value not in ("true", "false", "1", "0"):
                raise ValueError(
                    f"{field_name} must be a boolean (got: {value!r})"
                )
            return value in ("true", "1")

        raise ValueError(f"Unknown field type: {field_type}")

    def _validate_rules(
        self, value: Any, field_name: str, field_type: str, rules: Dict[str, Any]
    ) -> Optional[str]:
        """Validate field-level rules. Returns error string if validation fails."""
        if not rules:
            return None

        # non_empty rule (string-specific)
        if "non_empty" in rules and rules["non_empty"]:
            if field_type == "string" and (not value or not str(value).strip()):
                return f"{field_name} cannot be empty or whitespace-only"

        # min rule (numeric/date)
        if "min" in rules and value is not None:
            min_val = rules["min"]
            if field_type == "date":
                try:
                    value_date = datetime.strptime(value, "%d-%m-%Y")
                    min_date = datetime.strptime(str(min_val), "%d-%m-%Y")
                    if value_date < min_date:
                        return f"{field_name} must be >= {min_val} (got: {value})"
                except (ValueError, TypeError):
                    if isinstance(value, (int, float)) and value < min_val:
                        return f"{field_name} must be >= {min_val} (got: {value})"
            elif isinstance(value, (int, float)) and value < min_val:
                return f"{field_name} must be >= {min_val} (got: {value})"

        # max rule (numeric/date)
        if "max" in rules and value is not None:
            max_val = rules["max"]
            if field_type == "date":
                try:
                    value_date = datetime.strptime(value, "%d-%m-%Y")
                    max_date = datetime.strptime(str(max_val), "%d-%m-%Y")
                    if value_date > max_date:
                        return f"{field_name} must be <= {max_val} (got: {value})"
                except (ValueError, TypeError):
                    if isinstance(value, (int, float)) and value > max_val:
                        return f"{field_name} must be <= {max_val} (got: {value})"
            elif isinstance(value, (int, float)) and value > max_val:
                return f"{field_name} must be <= {max_val} (got: {value})"

        # pattern rule (string)
        if "pattern" in rules and field_type == "string":
            pattern = rules["pattern"]
            if not re.match(pattern, value):
                return f"{field_name} must match pattern {pattern!r} (got: {value!r})"

        # length_min rule (string)
        if "length_min" in rules and field_type == "string":
            length_min = rules["length_min"]
            if len(value) < length_min:
                return f"{field_name} length must be >= {length_min} (got: {len(value)})"

        # length_max rule (string)
        if "length_max" in rules and field_type == "string":
            length_max = rules["length_max"]
            if len(value) > length_max:
                return f"{field_name} length must be <= {length_max} (got: {len(value)})"

        # allowed_values rule
        if "allowed_values" in rules and value is not None:
            allowed = rules["allowed_values"]
            if value not in allowed:
                return f"{field_name} must be one of {allowed} (got: {value!r})"

        return None


class CSVValidator:
    """Main validator that reads CSV and applies schema validation."""

    def __init__(self, validator: SchemaValidator):
        self.validator = validator
        self.valid_rows: List[Dict[str, Any]] = []
        self.errors: List[ValidationError] = []

    def validate_file(self, csv_path: str) -> bool:
        """
        Validate a CSV file.
        Returns True if file was processed successfully (regardless of validation results).
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        try:
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                if not reader.fieldnames:
                    return True

                csv_headers = list(reader.fieldnames)

                for row_number, row in enumerate(reader, start=1):
                    # Check for malformed rows (incorrect column count)
                    if len(row) != len(csv_headers):
                        self.errors.append(
                            ValidationError(
                                row_number,
                                f"Row has incorrect number of columns (expected {len(csv_headers)}, got {len(row)})",
                            )
                        )
                        continue

                    validated_row, error = self.validator.validate_row(
                        row, row_number, csv_headers
                    )

                    if error:
                        self.errors.append(error)
                    else:
                        self.valid_rows.append(validated_row)

            return True
        except UnicodeDecodeError:
            raise ValueError("CSV file is not valid UTF-8")

    def write_output(self, output_path: str) -> None:
        """Write valid rows to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.valid_rows, f, indent=2)

    def print_summary(self) -> None:
        """Print validation summary to console."""
        print("Validation Results")
        print("=" * 18)
        print(f"Valid rows: {len(self.valid_rows)}")
        print(f"Rejected rows: {len(self.errors)}")

        if self.errors:
            print("\nRejected Rows:")
            for error in self.errors:
                print(f"- {error}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate CSV data against a schema and output valid rows as JSON.",
        prog="csv-validator",
    )
    parser.add_argument("input_csv", help="Input CSV file")
    parser.add_argument("output_json", help="Output JSON file")
    parser.add_argument(
        "--schema",
        help="Schema configuration file (JSON). If not provided, uses default schema.",
        default=None,
    )

    args = parser.parse_args()

    try:
        # Load schema
        schema = SchemaValidator.load_schema(args.schema)
        validator = SchemaValidator(schema)

        # Validate CSV
        csv_validator = CSVValidator(validator)
        csv_validator.validate_file(args.input_csv)

        # Write output
        csv_validator.write_output(args.output_json)

        # Print summary
        csv_validator.print_summary()

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
