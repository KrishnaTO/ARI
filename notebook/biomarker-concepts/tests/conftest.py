"""Put notebook/biomarker-concepts on sys.path so tests can `import sources` (the folder name has a hyphen)."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
