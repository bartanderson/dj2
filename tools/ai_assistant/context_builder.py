#tools/ai_assistant/context_builder.py
"""
BridgeAgent for building context - Simplified version
"""

import json
from typing import Dict, List, Optional
import requests
import time

try:
    # When context_builder is imported as part of tools.ai_assistant
    from ..ollama_client import get_ollama_client
except ImportError:
    # When running directly or from a different path
    from ollama_client import get_ollama_client

class BridgeAgent:
    def __init__(self, indexer: 'CodebaseIndexer', ollama_model: str = "llama3.2:3b"):
        self.indexer = indexer
        self.ollama_model = ollama_model
        self.client = get_ollama_client(ollama_model)
        self.ollama_available = self.client.is_available()
        
        if self.ollama_available:
            print(f"✓ Ollama available for BridgeAgent")
        else:
            print(f"⚠️ Ollama not available for BridgeAgent")
    
    def _call_ollama(self, prompt: str, system: str = None) -> str:
        """Call Ollama via unified client."""
        if not self.ollama_available:
            return ""
        
        return self.client.generate(
            prompt=prompt, 
            system=system or "You are a code analysis assistant. Be concise and factual.",
            temperature=0.1,
            max_tokens=500
        )
    
    # REMOVE the old _check_ollama_available method entirely
    # REMOVE the old _call_ollama method entirely
    
    def build_context_for_query(self, user_query: str, depth: str = "balanced") -> Dict:
        """Build context for a query, with or without Ollama"""

        if depth == "deep":
            # Extract topic from query
            if self.ollama_available:
                search_term = self._extract_search_term_with_ai(user_query)
            else:
                search_term = self._extract_code_terms_fallback(user_query)
            
            if not search_term:
                search_term = user_query.split()[0] if user_query.split() else user_query
            
            print(f"  Deep analysis for: '{search_term}'")
            
            # Get deep analysis
            deep_analysis = self.get_deep_analysis(search_term)
            
            # Also get search results
            search_results = self.indexer.search(search_term, limit=10) if self.indexer else []
            
            return {
                "query": user_query,
                "depth": "deep",
                "deep_analysis": deep_analysis,
                "search_results": search_results,
                "phase_violations": deep_analysis.get("layer1_code_reality", {}).get("enhanced_results", [])
            }
        
        # Use Ollama to extract search terms from natural language query
        if self.ollama_available:
            search_term = self._extract_search_term_with_ai(user_query)
            if not search_term:
                # Fallback: try to find code-like terms
                search_term = self._extract_code_terms_fallback(user_query)
        else:
            search_term = self._extract_code_terms_fallback(user_query)
        
        print(f"  Search term: '{search_term}'")
        
        # Step 1: Search Whoosh for relevant code
        search_results = self.indexer.search(search_term, limit=15)
        
        # Step 2: Get phase violation context if relevant
        phase_context = {}
        if any(word in user_query.lower() for word in ["phase", "violation", "compliance"]):
            phase_context = self.indexer.get_phase_violation_context()
        
        # Step 3: Structure the context (with Ollama if available, else simple)
        if self.ollama_available and search_results:
            context_prompt = f"""
            User Query: {user_query}
            
            Found {len(search_results)} relevant files in codebase.
            
            Key files found:
            {chr(10).join([f"- {r['path']}" for r in search_results[:5]])}
            
            Task: Provide 2-3 key insights about how to approach this query.
            Focus on:
            1. What files are most relevant and why
            2. Any phase compliance considerations
            3. Suggested approach based on codebase patterns
            
            Keep it very concise (3-4 sentences max).
            """
            
            structured_response = self._call_ollama(context_prompt)
            
            if structured_response:
                context_dict = {
                    "key_insights": structured_response[:500],
                    "relevant_files": [r["path"] for r in search_results[:8]],
                    "phase_warnings": []
                }
                
                # Add phase warnings if found
                if phase_context and phase_context.get('violations'):
                    context_dict['phase_warnings'] = [
                        f"Found {phase_context.get('total_violations', 0)} phase violations in audit"
                    ]
            else:
                # Ollama failed, fall back to simple
                context_dict = self._simple_context(search_results, phase_context)
        else:
            # No Ollama, use simple context
            context_dict = self._simple_context(search_results, phase_context)
        
        return {
            "whoosh_results": search_results,
            "structured_context": context_dict,
            "query": user_query,
        }

    def _extract_search_term_with_ai(self, query: str) -> str:
        """Use AI to extract the most relevant search term from natural language"""
        extraction_prompt = f"""
        User query: "{query}"
        
        Task: Extract the single most important code identifier or search term from this query.
        Look for:
        - Class names (like DMChatHandler, GameEngine)
        - File names (like world_controller.py)
        - System names (like dungeon_neo, world)
        - Key technical terms
        
        Return ONLY the search term, nothing else.
        
        Example:
        Query: "How to extract DMChatHandler from world_controller.py?"
        Response: DMChatHandler
        
        Query: "Where is the GameEngine class defined?"
        Response: GameEngine
        
        Query: "Show me phase violation issues"
        Response: phase violation
        """
        
        search_term = self._call_ollama(extraction_prompt).strip()
        
        # Validate: should be 2-50 characters, no sentence structure
        if len(search_term) < 2 or len(search_term) > 50 or '.' in search_term:
            return ""
        
        return search_term

    def _extract_code_terms_fallback(self, query: str) -> str:
        """Fallback method using simple heuristics when AI isn't available"""
        import re
        
        # Look for capitalized words that look like class names
        class_pattern = r'\b([A-Z][a-zA-Z0-9_]{3,})\b'
        class_matches = re.findall(class_pattern, query)
        
        if class_matches:
            # Return the longest class-like term
            return max(class_matches, key=len)
        
        # Look for file names with extensions
        file_pattern = r'\b([a-zA-Z0-9_]+\.(py|md|html|css|js|json))\b'
        file_matches = re.findall(file_pattern, query)
        if file_matches:
            return file_matches[0][0]
        
        # Look for phase-related terms
        phase_terms = ["phase violation", "phase compliance", "game engine", "dungeon", "world"]
        for term in phase_terms:
            if term in query.lower():
                return term
        
        # Default: use the whole query
        return query
    
    def _simple_context(self, search_results, phase_context):
        """Create simple context without Ollama"""
        phase_warnings = []
        if phase_context and phase_context.get('violations'):
            phase_warnings = [f"Found {phase_context.get('total_violations', 0)} phase violations in audit"]
        
        return {
            "relevant_files": [r["path"] for r in search_results[:8]],
            "key_insights": f"Found {len(search_results)} relevant files. Use the search results for detailed analysis.",
            "phase_warnings": phase_warnings
        }
    
    def validate_deepseek_response(self, deepseek_response: str, original_context: Dict) -> Dict:
        """Validate DeepSeek's response against project rules"""
        if not self.ollama_available:
            return {
                "is_valid": True,
                "issues": [],
                "suggested_fixes": [],
                "phase_compliance_check": "needs_review"
            }
        
        validation_prompt = f"""
        TASK: Validate this code change proposal against project rules.
        
        RESPONSE FORMAT (MUST BE VALID JSON):
        {{
          "is_valid": true/false,
          "issues": ["list", "of", "issues"],
          "suggested_fixes": ["list", "of", "fixes"],
          "phase_compliance_check": "pass/fail/needs_review"
        }}
        
        PROPOSAL TO VALIDATE:
        {deepseek_response[:1500]}
        
        PROJECT RULES:
        1. Phase compliance: AI never mutates state, proper phase boundaries
        2. System ownership: Don't cross system boundaries (see SYSTEM_OWNERSHIP.md)
        3. Backward compatibility: Don't break existing functionality
        4. Use git for version control
        
        ANALYSIS:
        """
        
        validation_result = self._call_ollama(validation_prompt)
        
        # Clean the response - extract JSON if wrapped in text
        import re
        json_match = re.search(r'\{.*\}', validation_result, re.DOTALL)
        if json_match:
            validation_result = json_match.group(0)
        
        try:
            result = json.loads(validation_result)
            return result
        except json.JSONDecodeError:
            return {
                "is_valid": True,
                "issues": ["Could not parse validation response"],
                "suggested_fixes": ["Ensure Ollama returns valid JSON"],
                "phase_compliance_check": "needs_review"
            }

    def get_deep_analysis(self, topic: str) -> Dict:
        """Get deep analysis using FourLayerAnalyzer"""
        # Import here to avoid circular dependencies
        from .four_layer import FourLayerAnalyzer
        
        # Create analyzer with our indexer (auto-indexer will work if indexer is None)
        analyzer = FourLayerAnalyzer(indexer=self.indexer)
        return analyzer.analyze_for_context(topic)

    def build_context_with_depth(self, query: str, depth: str = "balanced") -> Dict:
        """Build context with depth control"""
        if depth == "deep":
            # Extract search term
            if self.ollama_available:
                search_term = self._extract_search_term_with_ai(query)
            else:
                search_term = self._extract_code_terms_fallback(query)
            
            if not search_term:
                search_term = query.split()[0] if query.split() else query
            
            # Get deep analysis
            deep_analysis = self.get_deep_analysis(search_term)
            
            # Get regular search results
            search_results = self.indexer.search(search_term, limit=10) if self.indexer else []
            
            return {
                "query": query,
                "depth": "deep",
                "deep_analysis": deep_analysis,
                "search_results": search_results,
                "phase_violations": deep_analysis.get("layer1_code_reality", {}).get("enhanced_results", [])
            }
        else:
            # Original behavior
            return self.build_context_for_query(query)