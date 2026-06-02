import sys
from pathlib import Path

# Add the current directory to python path in case it is run directly
sys.path.insert(0, str(Path(__file__).parent))

try:
    from aegis.cli import main
except ImportError as e:
    print(
        f"Error: Missing dependencies or package not installed correctly. Run 'pip install -e .[server]' first.",
        file=sys.stderr,
    )
    print(f"Original error: {e}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()

