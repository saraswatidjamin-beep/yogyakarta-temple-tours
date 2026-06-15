#!/usr/bin/env python3
"""
Image Dedup Check — Hard gate for affiliate site builds.

MD5-hashes every image in the site's images/ directory and blocks if any
two files share the same digest. This catches category-hero.jpg = category-something.jpg
(the exact bug Yogyakarta shipped with).

Exit 0 = all unique. Exit 1 = duplicates found (BLOCKS DEPLOY).

Usage:
  python3 image_dedup.py <site_dir> [--fix] [--json]
"""

import sys
import os
import hashlib
import glob
import json
from collections import defaultdict


def hash_file(path: str) -> str:
    """MD5 hash of a file."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def audit(site_dir: str) -> dict:
    """Find duplicate images. Returns dict with results."""
    images_dir = os.path.join(site_dir, 'images')
    if not os.path.isdir(images_dir):
        return {'pass': True, 'duplicates': [], 'images': 0}

    digest_map = defaultdict(list)  # digest -> [paths]
    for img in sorted(glob.glob(f'{images_dir}/*')):
        if not os.path.isfile(img):
            continue
        try:
            digest = hash_file(img)
            digest_map[digest].append(os.path.relpath(img, site_dir))
        except (IOError, OSError):
            pass

    duplicates = {d: paths for d, paths in digest_map.items() if len(paths) > 1}
    return {
        'pass': len(duplicates) == 0,
        'duplicates': duplicates,
        'images': sum(len(v) for v in digest_map.values()),
        'unique': len(digest_map),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: image_dedup.py <site_dir> [--fix] [--json]", file=sys.stderr)
        sys.exit(2)

    site_dir = sys.argv[1]
    do_fix = '--fix' in sys.argv
    json_out = '--json' in sys.argv

    results = audit(site_dir)

    if json_out:
        serializable = {
            'pass': results['pass'],
            'images': results['images'],
            'unique': results['unique'],
            'duplicates': {d: paths for d, paths in results['duplicates'].items()}
        }
        print(json.dumps(serializable, indent=2))
    else:
        print(f"Images: {results['images']} total, {results['unique']} unique")
        if results['duplicates']:
            print(f"\n❌ DUPLICATE IMAGES FOUND:")
            for digest, paths in results['duplicates'].items():
                print(f"  {digest[:16]}...")
                for p in paths:
                    print(f"    {p}")
            print(f"\n❌ {len(results['duplicates'])} DUPLICATE GROUP(S) — deploy blocked")
            sys.exit(1)
        else:
            print("✅ All images unique")

    if do_fix and results['duplicates']:
        print("\n--fix: removing duplicates (keeping first file, deleting rest)")
        for digest, paths in results['duplicates'].items():
            for p in paths[1:]:
                full = os.path.join(site_dir, p)
                os.remove(full)
                print(f"  deleted: {p}")
        print("Done. Re-run audit to verify.")

    if not results['pass']:
        sys.exit(1)


if __name__ == '__main__':
    main()
