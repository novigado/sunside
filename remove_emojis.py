#!/usr/bin/env python3
"""Remove emojis from markdown files."""

import re
import sys
from pathlib import Path

# Comprehensive emoji regex pattern
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-a
    "\U00002300-\U000023FF"  # misc technical
    "]+",
    flags=re.UNICODE
)

def remove_emojis(text):
    """Remove all emojis from text."""
    return EMOJI_PATTERN.sub('', text)

def process_file(file_path):
    """Process a single markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = remove_emojis(content)

        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False

def main():
    """Find and process all markdown files."""
    root = Path('.')
    exclude_dirs = {'_build', '.git', 'node_modules', '__pycache__'}

    count = 0
    for md_file in root.rglob('*.md'):
        # Skip excluded directories
        if any(excluded in md_file.parts for excluded in exclude_dirs):
            continue

        if process_file(md_file):
            count += 1
            print(f"Processed: {md_file}")

    print(f"\nTotal files processed: {count}")

if __name__ == '__main__':
    main()
