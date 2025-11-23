
import json
import sys

def validate_dataset(filepath):
    """
    Validates a JSON Lines dataset file.

    Checks for:
    1. Each line is a valid JSON object.
    2. Each JSON object has "question" and "response" keys.
    3. The values for "question" and "response" are not empty.
    """
    errors = []
    line_number = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line_number += 1
            try:
                data = json.loads(line)
                if "question" not in data or not data["question"]:
                    errors.append(f"Line {line_number}: Missing or empty 'question' key.")
                if "response" not in data or not data["response"]:
                    errors.append(f"Line {line_number}: Missing or empty 'response' key.")
            except json.JSONDecodeError:
                errors.append(f"Line {line_number}: Not a valid JSON object.")

    if not errors:
        print("Dataset validation successful: All lines are valid JSON with non-empty 'question' and 'response' fields.")
    else:
        print(f"Dataset validation failed with {len(errors)} errors:")
        for error in errors:
            print(error)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_dataset.py <filepath>")
        sys.exit(1)
    validate_dataset(sys.argv[1])
