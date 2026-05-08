"""
randomcsvgenerator.py

Generates a synthetic sales CSV for local testing.
Column names and value distributions are driven by config.ini so you can
change the schema without touching this script.

Usage:
    python randomcsvgenerator.py                  # generates 100-row 'generated.csv'
    python randomcsvgenerator.py --rows 500       # custom row count
    python randomcsvgenerator.py --out my_data.csv
"""

import argparse
import configparser
import random
import os


def _value_for(directive: str) -> str:
    """
    Convert a config directive string into a random value.

    Directives
    ----------
    highrandom : random int in [1_000_000, 9_999_999]
    medrandom  : random int in [10_000, 99_999]
    lowrandom  : random int in [100, 999]
    a,b,c,...  : random choice from comma-separated list
    """
    if directive == "highrandom":
        return str(random.randrange(1_000_000, 9_999_999))
    if directive == "medrandom":
        return str(random.randrange(10_000, 99_999))
    if directive == "lowrandom":
        return str(random.randrange(100, 999))
    if "," in directive:
        return random.choice(directive.split(","))
    # Fall-through: return the literal string (useful for fixed constants)
    return directive


def generate(rows: int = 100, config_path: str = "config.ini", out_path: str = "generated.csv") -> None:
    """Generate *rows* rows of synthetic sales data and write to *out_path*."""
    config = configparser.ConfigParser()
    config.read(config_path)

    if not config.sections():
        raise FileNotFoundError(f"Could not read config file: {config_path}")

    section = config.sections()[0]
    col_names = config.options(section)
    directives = {col: config.get(section, col) for col in col_names}

    with open(out_path, "w") as f:
        f.write(",".join(col_names) + "\n")
        for _ in range(rows):
            row = [_value_for(directives[col]) for col in col_names]
            f.write(",".join(row) + "\n")

    print(f"Generated {rows} rows → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a synthetic sales CSV.")
    parser.add_argument("--rows", type=int, default=100, help="Number of data rows (default: 100)")
    parser.add_argument("--out", default="generated.csv", help="Output filename (default: generated.csv)")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(__file__), "config.ini"),
        help="Path to config.ini",
    )
    args = parser.parse_args()
    generate(rows=args.rows, config_path=args.config, out_path=args.out)
