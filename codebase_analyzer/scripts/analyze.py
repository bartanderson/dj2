
### 6. `scripts/analyze.py` (CLI Entry Point)
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.mapper import ArchitectureMapper
from analyzer.packer import LLMContextPacker

def main():
    parser = argparse.ArgumentParser(description='Analyze codebase architecture')
    parser.add_argument('project_path', help='Path to project root')
    parser.add_argument('-o', '--output', default='output/architecture.json', 
                       help='Output JSON file')
    parser.add_argument('--pack', action='store_true', 
                       help='Also generate LLM-ready package')
    parser.add_argument('--pack-output', default='output/llm_package.json',
                       help='LLM package output path')
    parser.add_argument('--focus-module', 
                       help='Focus package on specific module')
    parser.add_argument('--exclude', nargs='+', default=['node_modules', '__pycache__', '.git'],
                       help='Directories to exclude')
    parser.add_argument('--include', nargs='+', default=['.py', '.js', '.html', '.css', '.jsx', '.ts'],
                       help='File extensions to include')
    
    args = parser.parse_args()
    
    # Phase 1: Analysis
    mapper = ArchitectureMapper(args.project_path)
    mapper.analyze_all(
        include_patterns=args.include,
        exclude_dirs=args.exclude
    )
    mapper.save(args.output)
    
    # Phase 2: Packaging (optional)
    if args.pack:
        packer = LLMContextPacker(mapper.files, mapper.module_graph)
        packer.save_package(args.pack_output, args.focus_module)
        print(f"\n✅ Analysis complete!")
        print(f"   Full data: {args.output}")
        print(f"   LLM package: {args.pack_output}")

if __name__ == '__main__':
    main()