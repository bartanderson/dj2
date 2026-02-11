#tools/workflow/living_workflow.py
# coding=utf-8
"""
LIVING WORKFLOW - Complete analysis and integration workflow
Simplified version
"""
import subprocess
import sys
from pathlib import Path

def run_living_workflow():
    """Run the complete living system analysis workflow"""
    print("=" * 80)
    print("LIVING SYSTEM WORKFLOW")
    print("=" * 80)
    
    # Step 1: Dynamic feature analysis
    print("\n[1/4] 📋 Dynamic Feature Analysis")
    try:
        result = subprocess.run([sys.executable, "tools/workflow/dynamic_feature_analyzer.py", "--report"], 
                              capture_output=True, text=True)
        print(result.stdout[:1000] + "..." if len(result.stdout) > 1000 else result.stdout)
    except:
        print("  ⚠️ Dynamic feature analyzer not available")
    
    # Step 2: Living architecture analysis
    print("\n[2/4] 🏗️ Living Architecture Analysis")
    try:
        architect_result = subprocess.run([sys.executable, "tools/architecture/enhanced_architect.py", "--analyze"],
                                        capture_output=True, text=True)
        print(architect_result.stdout[:1000] + "..." if len(architect_result.stdout) > 1000 else architect_result.stdout)
    except:
        print("  ⚠️ Enhanced architect not available")
    
    # Step 3: Check recovered functions if they exist
    recovered_dir = Path("recovered_functions")
    if recovered_dir.exists():
        print("\n[3/4] 🔄 Recovered Function Analysis")
        print(f"  Found recovered functions directory: {recovered_dir}")
        print("  Use: python ai.py analyze 'recovered_function'")
    
    # Step 4: Phase compliance check
    print("\n[4/4] ⚖️ Phase Compliance Verification")
    
    # Check existing phase audit
    phase_audit = Path("DOCS/PHASE_AUDIT.md")
    if phase_audit.exists():
        content = phase_audit.read_text()
        if "❌" in content or "⚠️" in content:
            print("⚠️ Phase violations detected in PHASE_AUDIT.md")
            # Count violations
            critical = content.count("❌")
            warnings = content.count("⚠️")
            print(f"  Critical: {critical}, Warnings: {warnings}")
        else:
            print("✅ No phase violations in audit")
    else:
        print("  ⚠️ PHASE_AUDIT.md not found")
    
    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETE")
    print("=" * 80)
    print("\n📋 Next Actions:")
    print("1. Review analysis reports")
    print("2. Fix any phase violations")
    print("3. Use git for version control")
    print("4. Run specific commands for detailed analysis:")
    print("   - python ai.py violations .")
    print("   - python ai.py analyze-project")
    print("   - python ai.py refactor-plan")

if __name__ == "__main__":
    run_living_workflow()