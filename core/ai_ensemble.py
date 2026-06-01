"""
AI Ensemble Voting System.
Gunakan multiple AI models dengan voting untuk mengurangi hallucination single model.
Mendukung: 9Router, Ollama lokal, dan model tambahan.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from .ai import AIDecisionEngine
from providers.ninerouter import NineRouterClient


class AIEnsemble:
    """
    Ensemble AI dengan voting system.
    Jalankan 2-3 model berbeda, ambil keputusan berdasarkan majority vote.
    Mengurangi hallucination single model dan meningkatkan robustness.
    """

    def __init__(
        self,
        primary_model: str = "auto",
        secondary_models: List[str] = None,
        ninerouter_url: str = "http://localhost:20128/v1",
        ninerouter_api_key: Optional[str] = None,
        db_path: str = "db/sqlite.db",
        min_agreement: int = 2,  # Minimal model yang harus setuju
    ):
        self.min_agreement = min_agreement
        self.db_path = db_path

        # Inisialisasi models
        self.models = []

        # Model 1: Default dari AIDecisionEngine
        self.models.append(AIDecisionEngine(
            model=primary_model,
            db_path=db_path,
            ninerouter_url=ninerouter_url,
            ninerouter_api_key=ninerouter_api_key,
        ))

        # Model 2, 3: Secondary models via 9Router
        if secondary_models:
            for model_name in secondary_models:
                engine = AIDecisionEngine(
                    model=model_name,
                    db_path=db_path,
                    ninerouter_url=ninerouter_url,
                    ninerouter_api_key=ninerouter_api_key,
                )
                self.models.append(engine)

        # Voting statistics
        self.voting_history: List[Dict[str, Any]] = []

    async def decide_ensemble(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ambil keputusan dari multiple models dan lakukan voting.
        Returns final decision based on majority vote.
        """
        if len(self.models) == 1:
            # Single model mode: langsung return
            return await self.models[0].decide(context)

        # Jalankan semua models secara parallel
        tasks = [model.decide(context) for model in self.models]
        decisions = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse decisions
        valid_decisions = []
        for i, dec in enumerate(decisions):
            if isinstance(dec, Exception):
                print(f"[ENSEMBLE] Model {i} error: {dec}")
                continue
            if dec["action"] != "HOLD":
                valid_decisions.append(dec)

        # Counting votes
        action_votes = {}
        for dec in valid_decisions:
            action = dec["action"]
            if action not in action_votes:
                action_votes[action] = []
            action_votes[action].append(dec)

        # Jika semua HOLD atau tidak cukup voting
        if not action_votes:
            return {
                "action": "HOLD",
                "confidence": 0,
                "reason": "All models voted HOLD",
                "ensemble_votes": {},
            }

        # Find majority action
        best_action = max(action_votes, key=lambda k: len(action_votes[k]))
        best_votes = action_votes[best_action]

        if len(best_votes) < self.min_agreement:
            return {
                "action": "HOLD",
                "confidence": 0,
                "reason": f"Insufficient agreement: {len(best_votes)}/{len(self.models)} for {best_action}",
                "ensemble_votes": {k: len(v) for k, v in action_votes.items()},
            }

        # Average confidence dari majority
        avg_confidence = sum(d["confidence"] for d in best_votes) / len(best_votes)

        # Combine reasons
        reasons = [d["reason"] for d in best_votes]
        combined_reason = f"Ensemble({len(best_votes)}/{len(valid_decisions)}): {'; '.join(reasons[:3])}"

        final_decision = {
            "action": best_action,
            "confidence": round(avg_confidence, 1),
            "reason": combined_reason,
            "ensemble_votes": {k: len(v) for k, v in action_votes.items()},
            "ensemble_agreement": round(len(best_votes) / len(valid_decisions) * 100, 0) if valid_decisions else 0,
        }

        # Record voting history
        self.voting_history.append({
            "timestamp": datetime.now().isoformat(),
            "context_snapshot": {
                "rsi": context.get("rsi"),
                "trend_m15": context.get("trend_m15"),
            },
            "votes": final_decision["ensemble_votes"],
            "final_action": best_action,
        })

        return final_decision

    def get_ensemble_stats(self) -> Dict[str, Any]:
        """Get ensemble voting statistics."""
        if not self.voting_history:
            return {"status": "No history yet"}

        total_decisions = len(self.voting_history)
        actions = {}

        for entry in self.voting_history:
            action = entry["final_action"]
            actions[action] = actions.get(action, 0) + 1

        return {
            "total_decisions": total_decisions,
            "action_distribution": actions,
            "models_count": len(self.models),
            "min_agreement": self.min_agreement,
        }