#!/usr/bin/env python3
"""
Backfill source metadata for existing articles.

Since all current articles came from EBSCO exports, this script adds the
source field to existing metadata entries that don't have it.

Usage:
    python backfill_source_metadata.py
"""

import json
from pathlib import Path
from config import METADATA_REGISTRY

def backfill_source():
    """Add source='EBSCO' to articles missing it."""
    if not METADATA_REGISTRY.exists():
        print(f"Error: {METADATA_REGISTRY} not found")
        return

    with open(METADATA_REGISTRY, 'r') as f:
        registry = json.load(f)

    articles = registry.get('articles', [])
    updated_count = 0

    for article in articles:
        if 'source' not in article:
            # All current articles are from EBSCO exports
            article['source'] = 'EBSCO'
            updated_count += 1

    if updated_count > 0:
        with open(METADATA_REGISTRY, 'w') as f:
            json.dump(registry, f, indent=2)
        print(f"✓ Updated {updated_count} articles with EBSCO source")
        print(f"✓ Registry saved to {METADATA_REGISTRY}")
    else:
        print("No articles needed updating - all have source field")

if __name__ == '__main__':
    backfill_source()
