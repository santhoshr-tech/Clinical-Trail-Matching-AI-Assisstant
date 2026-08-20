from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ExtractionResult(BaseModel):
    facts: List[Dict[str, Any]]
    confidence: float
    provider: str

class AIProvider(ABC):
    @abstractmethod
    async def extract_patient_facts(self, text: str) -> ExtractionResult:
        pass

    @abstractmethod
    async def extract_trial_criteria(self, protocol_text: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def normalize_medical_terms(self, raw_terms: List[str]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def detect_negation(self, text_spans: List[str]) -> List[Dict[str, Any]]:
        pass

class MockProvider(AIProvider):
    async def extract_patient_facts(self, text: str) -> ExtractionResult:
        return ExtractionResult(
            facts=[{"type": "condition", "raw_text": "Mock NSCLC Diagnosis"}],
            confidence=0.95,
            provider="mock"
        )

    async def extract_trial_criteria(self, protocol_text: str) -> Dict[str, Any]:
        return {"inclusion": ["Age >= 18"], "exclusion": ["Prior immunotherapy"]}

    async def normalize_medical_terms(self, raw_terms: List[str]) -> List[Dict[str, Any]]:
        return [{"raw_text": term, "normalized_label": f"Mock_{term}", "coding_system": "RxNorm"} for term in raw_terms]

    async def detect_negation(self, text_spans: List[str]) -> List[Dict[str, Any]]:
        return [{"span": span, "is_negated": False} for span in text_spans]

def get_ai_provider() -> AIProvider:
    """Factory function to return configured AIProvider instance."""
    from app.core.config import settings
    provider_name = (settings.AI_PROVIDER or "gemini").lower()
    if provider_name == "gemini":
        from app.ai.gemini import GeminiProvider
        return GeminiProvider()
    return MockProvider()

