#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.merger import MergeAnalyzer

def main():
    parser = argparse.ArgumentParser(description='Generate merge analysis prompts')
    parser.add_argument('current_arch', help='Current architecture JSON')
    parser.add_argument('-n', '--new-arch', help='New architecture JSON (optional)')
    parser.add_argument('-o', '--output', default='output/merge_prompt.txt',
                       help='Output prompt file')
    parser.add_argument('-s', '--strategy', choices=['conservative', 'aggressive', 'selective'],
                       default='conservative', help='Merge strategy')
    parser.add_argument('-m', '--module', help='Analyze specific module only')
    
    args = parser.parse_args()
    
    analyzer = MergeAnalyzer(args.current_arch, args.new_arch)
    
    if args.module:
        analyzer.compare_specific_modules(args.module, args.output)
    else:
        analyzer.generate_merge_prompt(args.output, args.strategy)
    
    print(f"\n🚀 Next steps:")
    print(f"   1. Review: {args.output}")
    print(f"   2. Copy content to your LLM (Claude, GPT-4, etc.)")
    print(f"   3. Use JSON response to guide implementation")

if __name__ == '__main__':
    main()