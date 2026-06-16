import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from string import Template

class MergeAnalyzer:
    def __init__(self, current_architecture_path: str, new_architecture_path: Optional[str] = None):
        self.current = self._load_arch(current_architecture_path)
        self.new = self._load_arch(new_architecture_path) if new_architecture_path else None
        
    def _load_arch(self, path: str) -> Dict:
        with open(path) as f:
            return json.load(f)
    
    def generate_merge_prompt(self, output_path: str, strategy: str = "conservative"):
        """
        Generate comprehensive merge analysis prompt for LLM
        
        Args:
            strategy: 'conservative' (safe), 'aggressive' (full integration), or 'selective' (chooseive)
        """
        
        prompt_template = """You are an expert software architect tasked with merging two codebases.

## CURRENT SYSTEM ARCHITECTURE
```json
${current_system}
```
"""