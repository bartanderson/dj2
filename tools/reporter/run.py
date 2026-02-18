#!/usr/bin/env python3
import sys
import json

def main():
    inputs = json.loads(sys.argv[1])
    data = inputs.get('data', {})
    format_type = inputs.get('format', 'summary')
    
    if format_type == 'summary':
        report = f"""
📊 COVERAGE REPORT
==================
Total files: {data.get('total_files', 0)}
Covered: {data.get('covered_files', 0)}
Coverage: {data.get('coverage_percent', 0):.1f}%

Uncovered files:
"""
        for f in data.get('uncovered_files', []):
            report += f"  ❌ {f}\n"
        
        if data.get('coverage_percent', 0) == 100:
            report += "\n✅ Perfect coverage!"
    
    result = {
        'report': report,
        'format': format_type,
        'status': 'success'
    }
    
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()