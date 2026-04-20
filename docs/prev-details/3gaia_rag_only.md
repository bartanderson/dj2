Good—this is the right instinct. If it doesn’t slot cleanly into your engine, it’s just noise.
I’ll give you a drop-in integration slice that:


Uses GAIA only for RAG + constrained generation


Preserves your engine authority


Is structured so you can expand later without rewrites


This includes:


Integration interface (clean boundary)


Prompt templates (tight, enforceable)


Validation layer (practical, not academic)



1) Integration Interface (fits your architecture)
This is designed to sit where your NarrativeEngine would be.
narrative_service.py
from typing import Dict, Any, Listimport reclass NarrativeService:    def __init__(self, rag_client, llm_client):        self.rag = rag_client        self.llm = llm_client    # ---------- PUBLIC API ----------    def describe_room(self, room: Dict, party: Dict) -> str:        context = self._get_context(room)        prompt = self._build_room_prompt(room, party, context)        raw = self.llm.generate(prompt)        return self._validate_and_clean(raw, room)    def describe_combat_result(self, event: Dict) -> str:        prompt = self._build_combat_prompt(event)        raw = self.llm.generate(prompt)        return self._validate_and_clean(raw, event)    def describe_event(self, event: Dict) -> str:        context = self._get_context(event)        prompt = self._build_event_prompt(event, context)        raw = self.llm.generate(prompt)        return self._validate_and_clean(raw, event)    # ---------- RAG ----------    def _get_context(self, obj: Dict) -> str:        query = {            "type": obj.get("type"),            "tags": obj.get("tags", []),            "id": obj.get("id")        }        return self.rag.query(query)    # ---------- PROMPTS ----------    def _build_room_prompt(self, room, party, context) -> str:        return f"""You are a narrative renderer for a dungeon crawler.RULES:- Max 3 sentences- Only describe provided elements- Do NOT add objects, enemies, or events- No decisions, no player guidanceROOM:{room}PARTY:{party}CONTEXT:{context}OUTPUT:Plain text only."""    def _build_combat_prompt(self, event) -> str:        return f"""You are a combat narrator.RULES:- Max 2 sentences- Describe ONLY the outcome provided- Do NOT add effects or extra actionsEVENT:{event}OUTPUT:Plain text only."""    def _build_event_prompt(self, event, context) -> str:        return f"""You are a narrative renderer.RULES:- Max 2 sentences- No new objects or facts- Only describe the given eventEVENT:{event}CONTEXT:{context}OUTPUT:Plain text only."""    # ---------- VALIDATION ----------    def _validate_and_clean(self, text: str, source: Dict) -> str:        text = text.strip()        # Sentence limit enforcement        sentences = [s for s in re.split(r'[.!?]', text) if s.strip()]        max_sentences = 3        text = '. '.join(sentences[:max_sentences]).strip()        if not text.endswith('.'):            text += '.'        # Basic hallucination guard (token-based)        allowed_terms = self._extract_allowed_terms(source)        if self._contains_unknown_terms(text, allowed_terms):            return self._fallback(source)        return text    def _extract_allowed_terms(self, source: Dict) -> List[str]:        terms = set()        def extract(obj):            if isinstance(obj, dict):                for v in obj.values():                    extract(v)            elif isinstance(obj, list):                for v in obj:                    extract(v)            elif isinstance(obj, str):                terms.add(obj.lower())        extract(source)        return list(terms)    def _contains_unknown_terms(self, text: str, allowed_terms: List[str]) -> bool:        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())        for word in words:            if word not in allowed_terms:                # allow common filler words                if word in {"dark", "light", "stone", "air", "room", "figure"}:                    continue                return True        return False    def _fallback(self, source: Dict) -> str:        return "You see what lies before you, unchanged."

2) GAIA Adapter Layer (clean swap-in)
You do NOT want GAIA leaking into your engine.
gaia_adapter.py
class GaiaRAG:    def __init__(self, gaia_client):        self.client = gaia_client    def query(self, query_dict):        # Map your structure to GAIA query        return self.client.retrieve(            query=str(query_dict),            top_k=3        )class GaiaLLM:    def __init__(self, gaia_client):        self.client = gaia_client    def generate(self, prompt: str) -> str:        response = self.client.generate(            prompt=prompt,            temperature=0.3,   # keep deterministic-ish            max_tokens=120        )        return response.strip()

3) Where this plugs into YOUR system
Based on your architecture:
In your engine loop
# Room entrydesc = narrative.describe_room(room_state, party_state)ui.display(desc)

After combat resolution (important separation)
result = combat_engine.resolve_attack(...)event = {    "attacker": result.attacker,    "target": result.target,    "outcome": result.outcome,    "damage": result.damage}desc = narrative.describe_combat_result(event)ui.display(desc)

For generic events
event = {    "type": "door_opened",    "description": "A heavy wooden door creaks open"}desc = narrative.describe_event(event)

4) Prompt discipline (why this works)
These prompts enforce:


No new entities


No decisions


No system control


Tight verbosity


That’s what keeps it compatible with your deterministic engine.

5) What you gain immediately
Without changing your core systems:


Better room descriptions


Better combat narration


Context-aware flavor (via RAG)


Without risk:


No logic delegation


No state mutation


No tool-calling chaos



6) What to watch for (real issues)
1. Over-rejection by validator
You may see too many fallbacks.
Fix:


Expand allowed vocabulary whitelist


Or allow “soft violations” instead of hard fail



2. Bland output
Fix:


Add style constraints:


Tone: grim, grounded, sensory (sight + sound only)

3. Latency
Fix:


Cache RAG results per room


Cache descriptions after first generation



7) Minimal implementation path (do this in order)


Stub GaiaLLM with your current LLM


Implement NarrativeService.describe_room


Hook into room entry only


Add validator


Then add combat narration



Final judgment
This is the smallest integration that actually moves the needle:


Uses GAIA where it’s strong (RAG + generation)


Avoids everything that would break your system


Fits your architecture without rewrites



If you want next, I can:


Tune the validator so it’s less brittle (right now it’s intentionally strict)


Or align this exactly with your existing file/module layout so you can drop it in without friction