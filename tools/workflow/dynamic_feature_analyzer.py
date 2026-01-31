#tools/workflow/dynamic_feature_analyzer.py
"""
Dynamic feature analyzer - Simplified version
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

class DynamicFeatureAnalyzer:
    """Dynamically analyze features from documentation and code"""
    
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        
    def generate_dynamic_report(self):
        """Generate a report based on current documentation and code analysis"""
        # Extract features from docs
        doc_features = self.extract_features_from_docs()
        
        # Combine all features from docs
        all_features = set()
        for category in doc_features.values():
            all_features.update(category)
        
        # Analyze code for these features
        feature_analysis = self.analyze_code_for_features(list(all_features))
        
        # Generate report
        report = []
        report.append("# DYNAMIC FEATURE ANALYSIS REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("")
        
        if doc_features['in_progress']:
            report.append("## Features In Progress")
            for feature in doc_features['in_progress']:
                analysis = feature_analysis.get(feature, {})
                status = analysis.get('implementation_status', 'unknown')
                files = analysis.get('found_in_files', [])
                
                report.append(f"### {feature}")
                report.append(f"Status: {status}")
                if files:
                    report.append("Found in:")
                    for file in files[:3]:
                        report.append(f"- `{file}`")
                    if len(files) > 3:
                        report.append(f"  ... and {len(files)-3} more files")
                else:
                    suggested = analysis.get('suggested_files_to_check', [])
                    if suggested:
                        report.append("Suggested files to implement:")
                        for file in suggested:
                            report.append(f"- `{file}`")
                report.append("")
        
        if doc_features['blocked']:
            report.append("## Blocked Features")
            for feature in doc_features['blocked']:
                report.append(f"- {feature}")
            report.append("")
        
        if doc_features['recently_completed']:
            report.append("## Recently Completed")
            for feature in doc_features['recently_completed']:
                report.append(f"- {feature}")
            report.append("")
        
        # Summary
        report.append("## Analysis Summary")
        total_features = len(all_features)
        implemented = sum(1 for f, a in feature_analysis.items() 
                         if a.get('implementation_status') in ['full_stack', 'backend_only', 'frontend_only'])
        
        report.append(f"Total features tracked: {total_features}")
        report.append(f"At least partially implemented: {implemented}")
        report.append(f"Documentation only: {total_features - implemented}")
        
        return '\n'.join(report)
    
    def extract_features_from_docs(self):
        """Extract features mentioned in documentation"""
        features = {
            'in_progress': [],
            'planned': [],
            'recently_completed': [],
            'blocked': []
        }
        
        # Read NEXT_SESSION.md for in-progress features
        next_session_path = self.project_root / "DOCS/NEXT_SESSION.md"
        if next_session_path.exists():
            with open(next_session_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                features['in_progress'] = self._extract_features_from_text(content, ['implement', 'fix', 'add', 'update'])
        
        # Read ACCOMPLISHMENTS.md for completed features
        accomplishments_path = self.project_root / "DOCS/ACCOMPLISHMENTS.md"
        if accomplishments_path.exists():
            with open(accomplishments_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Get last 2 entries (recent accomplishments)
                sections = content.split('## January')
                if len(sections) > 1:
                    recent = '## January' + sections[-1]  # Last month's accomplishments
                    features['recently_completed'] = self._extract_features_from_text(
                        recent, ['implemented', 'completed', 'added', 'fixed'])
        
        # Read WORK files for current work context
        work_files = list(self.project_root.glob("WORK_*.md"))
        if work_files:
            # Get most recent work file
            latest = max(work_files, key=lambda p: p.stat().st_mtime)
            with open(latest, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Look for issues or blockers
                if any(word in content.lower() for word in ['blocked', 'stuck', 'issue', 'problem']):
                    features['blocked'] = self._extract_features_from_text(content, ['blocked', 'issue', 'problem'])
        
        return features
    
    def _extract_features_from_text(self, text, trigger_words):
        """Extract feature names from text based on trigger words"""
        features = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            # Check if line contains any trigger word
            for trigger in trigger_words:
                if trigger in line_lower:
                    # Extract the feature name (text after trigger)
                    match = re.search(fr'{trigger}[^\w]*(.+)', line_lower)
                    if match:
                        feature_desc = match.group(1).strip()
                        # Clean up the description
                        feature_desc = re.sub(r'[#*\-`]', '', feature_desc)
                        feature_desc = re.sub(r'\s+', ' ', feature_desc)
                        # Extract likely feature name (first few words)
                        words = feature_desc.split()
                        if len(words) > 1:
                            # Try to get a concise feature name
                            feature_name = self._extract_feature_name(words)
                            if feature_name and feature_name not in features:
                                features.append(feature_name)
        
        return features
    
    def _extract_feature_name(self, words):
        """Extract a likely feature name from words"""
        # Skip common words
        skip_words = {'the', 'a', 'an', 'for', 'with', 'to', 'in', 'on', 'at', 'by'}
        meaningful = [w for w in words if w.lower() not in skip_words]
        
        if not meaningful:
            return None
        
        # Take first 2-3 meaningful words as feature name
        feature_name = ' '.join(meaningful[:min(3, len(meaningful))])
        
        # Remove trailing punctuation
        feature_name = re.sub(r'[.,;:]$', '', feature_name)
        
        return feature_name
    
    def analyze_code_for_features(self, feature_names):
        """Analyze codebase to check status of mentioned features"""
        results = {}
        
        for feature_name in feature_names:
            results[feature_name] = {
                'found_in_files': [],
                'implementation_status': 'unknown',
                'suggested_files_to_check': []
            }
            
            # Search for feature in code
            files_with_feature = self._find_files_mentioning_feature(feature_name)
            results[feature_name]['found_in_files'] = files_with_feature
            
            if files_with_feature:
                # Check implementation completeness
                status = self._assess_implementation_status(feature_name, files_with_feature)
                results[feature_name]['implementation_status'] = status
            else:
                # Suggest files that might need this feature
                suggested = self._suggest_files_for_feature(feature_name)
                results[feature_name]['suggested_files_to_check'] = suggested
        
        return results
    
    def _find_files_mentioning_feature(self, feature_name):
        """Find files that mention the feature"""
        # Convert feature name to search terms
        search_terms = self._feature_to_search_terms(feature_name)
        
        found_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip hidden and cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in 
                      ['__pycache__', 'venv', 'node_modules', 'archive']]
            
            for file in files:
                if not file.endswith(('.py', '.html', '.js', '.md')):
                    continue
                    
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        
                        # Check for any search term
                        for term in search_terms:
                            if term in content:
                                rel_path = filepath.relative_to(self.project_root)
                                found_files.append(str(rel_path))
                                break
                except:
                    continue
        
        return list(set(found_files))  # Remove duplicates
    
    def _feature_to_search_terms(self, feature_name):
        """Convert feature name to search terms"""
        feature_lower = feature_name.lower()
        words = feature_lower.split()
        
        # Generate possible search terms
        terms = []
        
        # Original feature name
        terms.append(feature_lower)
        
        # CamelCase version (for code)
        camel_case = ''.join(word.capitalize() for word in words)
        terms.append(camel_case)
        
        # Snake_case version (for code)
        snake_case = '_'.join(words)
        terms.append(snake_case)
        
        # Common variations
        if 'id' in feature_lower:
            terms.append(feature_lower.replace('id', 'ID'))
            terms.append(feature_lower.replace('id', 'Id'))
        
        # Add "game_" prefix if it's about game features
        if any(word in feature_lower for word in ['session', 'position', 'movement', 'dungeon']):
            terms.append('game_' + snake_case)
        
        return terms
    
    def _assess_implementation_status(self, feature_name, files):
        """Assess how implemented a feature is"""
        # Simple heuristic based on file types and content
        python_files = [f for f in files if f.endswith('.py')]
        html_files = [f for f in files if f.endswith('.html')]
        js_files = [f for f in files if f.endswith('.js')]
        
        has_backend = bool(python_files)
        has_frontend = bool(html_files or js_files)
        
        if has_backend and has_frontend:
            return 'full_stack'
        elif has_backend:
            return 'backend_only'
        elif has_frontend:
            return 'frontend_only'
        else:
            return 'documentation_only'
    
    def _suggest_files_for_feature(self, feature_name):
        """Suggest files that might need this feature based on patterns"""
        suggestions = []
        
        # Map feature types to likely files
        feature_lower = feature_name.lower()
        
        if any(word in feature_lower for word in ['game_id', 'session', 'position']):
            suggestions.extend([
                'dungeon_neo/dungeon_neo_web_app.py',
                'templates/world.html',
                'world/session_system.py'
            ])
        
        if any(word in feature_lower for word in ['movement', 'move', 'dungeon']):
            suggestions.extend([
                'dungeon_neo/movement_service.py',
                'dungeon_neo/ai_integration.py',
                'templates/world.html'
            ])
        
        if any(word in feature_lower for word in ['ui', 'interface', 'layout', 'frontend']):
            suggestions.extend([
                'templates/world.html',
                'static/js/world.js',
                'static/css/world.css'
            ])
        
        if any(word in feature_lower for word in ['phase', 'compliance', 'engine']):
            suggestions.extend([
                'engine/game_engine.py',
                'world/authority_system.py',
                'world/session_system.py'
            ])
        
        # Filter to existing files
        existing_suggestions = []
        for suggestion in suggestions:
            if (self.project_root / suggestion).exists():
                existing_suggestions.append(suggestion)
        
        return existing_suggestions

# Command line interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Dynamic feature analysis from docs')
    parser.add_argument('--report', action='store_true', help='Generate dynamic feature report')
    parser.add_argument('--list-features', action='store_true', help='List features found in docs')
    parser.add_argument('--analyze', type=str, help='Analyze specific feature')
    
    args = parser.parse_args()
    
    analyzer = DynamicFeatureAnalyzer()
    
    if args.report:
        print(analyzer.generate_dynamic_report())
    elif args.list_features:
        features = analyzer.extract_features_from_docs()
        print("Features found in documentation:")
        print("\nIn Progress:")
        for f in features['in_progress']:
            print(f"  - {f}")
        print("\nBlocked:")
        for f in features['blocked']:
            print(f"  - {f}")
        print("\nRecently Completed:")
        for f in features['recently_completed']:
            print(f"  - {f}")
    elif args.analyze:
        analysis = analyzer.analyze_code_for_features([args.analyze])
        if args.analyze in analysis:
            data = analysis[args.analyze]
            print(f"Analysis for '{args.analyze}':")
            print(f"  Status: {data.get('implementation_status')}")
            if data.get('found_in_files'):
                print("  Found in files:")
                for file in data['found_in_files']:
                    print(f"    - {file}")
            else:
                print("  Not found in code")
                if data.get('suggested_files_to_check'):
                    print("  Suggested files to check:")
                    for file in data['suggested_files_to_check']:
                        print(f"    - {file}")
        else:
            print(f"Feature '{args.analyze}' not found in documentation")
    else:
        print("Usage: python dynamic_feature_analyzer.py --report")
        print("       python dynamic_feature_analyzer.py --list-features")
        print("       python dynamic_feature_analyzer.py --analyze <feature>")