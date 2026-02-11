#!/usr/bin/env python3
# coding=utf-8
"""
Run Analysis Suite - Executes all code analysis tools
Generates reports for the Project Auditor dashboard
Run this before using project_auditor_v2.py
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import time

PROJECT_ROOT = Path(r"C:\Users\bartl\dev\dj2")
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

def run_command(cmd, description, output_file=None):
    """Run a shell command and log results."""
    print(f"\n▶️  {description}...")
    print(f"   Command: {' '.join(cmd)}")
    
    start_time = time.time()
    
    try:
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='ignore',
                    cwd=PROJECT_ROOT,
                    timeout=300  # 5 minutes max
                )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                cwd=PROJECT_ROOT,
                timeout=300
            )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"   ✅ Completed in {elapsed:.1f}s")
            return True
        else:
            print(f"   ❌ Failed after {elapsed:.1f}s")
            print(f"   Error: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Timeout after 300s")
        return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def generate_analysis_manifest():
    """Create a manifest file with analysis metadata."""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "reports": {
            "coverage": str(REPORTS_DIR / "coverage.json"),
            "complexity": str(REPORTS_DIR / "source_complexity.json")
        },
        "directories_analyzed": [
            "core/",
            "dungeon_neo/", 
            "engine/",
            "recovered_code/",
            "routes/",
            "Scripts/",
            "tools/",
            "world/"
        ],
        "tools": {
            "coverage": {
                "command": "coverage run run_game.py && coverage json -o reports/coverage.json",
                "version": "6.5.0+"
            },
            "radon": {
                "command": "radon cc core/ dungeon_neo/ engine/ recovered_code/ routes/ Scripts/ tools/ world/ -a -j",
                "version": "5.1.0+"
            }
        }
    }
    
    with open(REPORTS_DIR / "analysis_manifest.json", 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

def check_dependencies():
    """Check if required tools are installed."""
    print("🔍 Checking dependencies...")
    
    tools = {
        "coverage": ["coverage", "--version"],
        "radon": ["radon", "--version"],
        "python": [sys.executable, "--version"]
    }
    
    missing = []
    
    for name, cmd in tools.items():
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[0] if result.stdout else "unknown"
                print(f"   ✅ {name}: {version}")
            else:
                print(f"   ❌ {name}: Not found")
                missing.append(name)
        except Exception:
            print(f"   ❌ {name}: Not found")
            missing.append(name)
    
    return missing

def cleanup_old_reports():
    """Remove old report files if they exist."""
    old_files = [
        REPORTS_DIR / "coverage.json",
        REPORTS_DIR / "source_complexity.json",
        REPORTS_DIR / ".coverage"
    ]
    
    print("\n🗑️  Cleaning up old reports...")
    for file in old_files:
        if file.exists():
            file.unlink()
            print(f"   Removed: {file.name}")

def run_full_analysis():
    """Run the complete analysis suite."""
    print("="*80)
    print("RUN ANALYSIS SUITE")
    print(f"Project: {PROJECT_ROOT}")
    print(f"Reports: {REPORTS_DIR}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Check dependencies first
    missing = check_dependencies()
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("\nInstall missing tools:")
        for tool in missing:
            if tool == "coverage":
                print("   pip install coverage")
            elif tool == "radon":
                print("   pip install radon")
        return False
    
    # Clean up old reports
    cleanup_old_reports()
    
    # Track success/failure
    successes = []
    
    # Step 1: Run coverage
    print("\n" + "="*80)
    print("STEP 1: TEST COVERAGE ANALYSIS")
    print("="*80)
    
    # Run coverage on your game
    success = run_command(
        [sys.executable, "-m", "coverage", "run", "run_game.py"],
        "Running tests with coverage"
    )
    
    if success:
        # Generate JSON report
        success = run_command(
            [sys.executable, "-m", "coverage", "json", "-o", "reports/coverage.json"],
            "Generating coverage JSON report"
        )
        if success:
            successes.append("coverage")
    
    # Step 2: Run complexity analysis  
    print("\n" + "="*80)
    print("STEP 2: CODE COMPLEXITY ANALYSIS")
    print("="*80)
    
    # Define directories to analyze
    dirs = [
        "core/",
        "dungeon_neo/", 
        "engine/",
        "recovered_code/",
        "routes/",
        "Scripts/",
        "tools/",
        "world/"
    ]
    
    # Build radon command
    radon_cmd = [sys.executable, "-m", "radon", "cc"]
    radon_cmd.extend(dirs)
    radon_cmd.extend(["-a", "-j"])
    
    success = run_command(
        radon_cmd,
        "Analyzing code complexity with radon",
        output_file=REPORTS_DIR / "source_complexity.json"
    )
    
    if success:
        successes.append("complexity")
    
    # Step 3: Generate manifest
    print("\n" + "="*80)
    print("STEP 3: GENERATING REPORTS")
    print("="*80)
    
    generate_analysis_manifest()
    
    # Show summary
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    if successes:
        print(f"✅ Generated {len(successes)} reports:")
        for report in successes:
            print(f"   • {report}.json")
        
        coverage_file = REPORTS_DIR / "coverage.json"
        if coverage_file.exists():
            try:
                with open(coverage_file, 'r') as f:
                    data = json.load(f)
                total_cov = data.get("totals", {}).get("percent_covered", 0)
                print(f"\n📊 Coverage summary: {total_cov:.1f}%")
            except:
                pass
        
        complexity_file = REPORTS_DIR / "source_complexity.json"
        if complexity_file.exists():
            try:
                with open(complexity_file, 'r') as f:
                    data = json.load(f)
                print(f"⚡ Files analyzed: {len(data)}")
                
                # Find highest complexity
                max_complexity = 0
                for module in data:
                    if isinstance(module, dict):
                        complexity = module.get("complexity", 0)
                        if complexity > max_complexity:
                            max_complexity = complexity
                if max_complexity > 0:
                    print(f"📈 Highest complexity: {max_complexity}")
            except:
                pass
        
        print(f"\n📁 Reports saved to: {REPORTS_DIR}")
        print("\n🎯 Next steps:")
        print("   1. View dashboard: python project_auditor_v2.py")
        print("   2. Check specific file: python project_auditor_v2.py --code-only")
        print("   3. Update metrics regularly: python run_analysis.py")
        
        return True
    else:
        print("❌ Analysis failed to generate any reports")
        return False

def run_quick_analysis():
    """Run a quicker analysis (coverage only)."""
    print("\n⚡ Running quick analysis (coverage only)...")
    
    success = run_command(
        [sys.executable, "-m", "coverage", "run", "run_game.py"],
        "Running tests with coverage"
    )
    
    if success:
        success = run_command(
            [sys.executable, "-m", "coverage", "json", "-o", "reports/coverage.json"],
            "Generating coverage report"
        )
    
    return success

def main():
    """Main entry point with command line options."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run code analysis suite for DJ2 project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_analysis.py           # Full analysis
  python run_analysis.py --quick   # Coverage only
  python run_analysis.py --clean   # Clean old reports only
  python run_analysis.py --check   # Check dependencies only
        """
    )
    
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run quick analysis (coverage only)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean old reports only"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check dependencies only"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run even if reports exist"
    )
    
    args = parser.parse_args()
    
    if args.check:
        missing = check_dependencies()
        if missing:
            print(f"\n❌ Missing: {', '.join(missing)}")
            return 1
        else:
            print("\n✅ All dependencies found")
            return 0
    
    if args.clean:
        cleanup_old_reports()
        return 0
    
    # Check if reports already exist (unless force)
    if not args.force:
        coverage_exists = (REPORTS_DIR / "coverage.json").exists()
        complexity_exists = (REPORTS_DIR / "source_complexity.json").exists()
        
        if coverage_exists and complexity_exists:
            print("📊 Reports already exist. Use --force to re-run.")
            print(f"   Coverage: {REPORTS_DIR / 'coverage.json'}")
            print(f"   Complexity: {REPORTS_DIR / 'source_complexity.json'}")
            
            # Show age of reports
            import os
            from datetime import datetime
            
            coverage_mtime = os.path.getmtime(REPORTS_DIR / "coverage.json")
            coverage_age = datetime.now() - datetime.fromtimestamp(coverage_mtime)
            hours_old = coverage_age.total_seconds() / 3600
            
            print(f"   Reports are {hours_old:.1f} hours old")
            
            if hours_old > 24:
                print("   ⚠️  Reports are over 24 hours old - consider updating")
            
            response = input("\nRe-run analysis anyway? (y/N): ")
            if response.lower() != 'y':
                print("Using existing reports.")
                return 0
    
    if args.quick:
        success = run_quick_analysis()
    else:
        success = run_full_analysis()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())