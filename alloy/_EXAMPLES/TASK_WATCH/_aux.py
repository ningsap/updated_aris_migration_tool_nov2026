import json
import os
import random
import string
from pathlib import Path


def generate_random_value(depth=0):
    """Generates a random value with increasing complexity based on depth."""
    data_types = [
        lambda: random.randint(1, 1000),
        lambda: round(random.uniform(1, 1000), 2),
        lambda: ''.join(random.choices(string.ascii_letters, k=10)),
        lambda: bool(random.getrandbits(1)),
        lambda: [random.randint(1, 100) for _ in range(random.randint(2, 5))],
    ]
    if depth < 2:  # Limit recursion depth to avoid excessive nesting
        data_types.append(lambda: generate_random_dict(depth + 1))
    return random.choice(data_types)()


def generate_random_dict(depth=0, size=5):
    """Generates a dictionary with random key-value pairs."""
    return {f"key_{i}": generate_random_value(depth) for i in range(size)}


def _create_json_files(num_files: int, destination: str, complexity: int):
    """Creates multiple JSON files with varying complexity."""
    os.makedirs(destination, exist_ok=True)

    for i in range(num_files):
        json_data = generate_random_dict(size=complexity)
        file_path = Path(destination) / f"file_{i + 1}.json"

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)

    print(f"{num_files} JSON files created in {destination}")
