"""Recommend-or-not for a single food, based on a user's like/dislike history.

Ratings are tuples: (user_id, food_name, liked)
    liked = True  -> user likes it
    liked = False -> user dislikes it

pip install fastembed numpy
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from fastembed import TextEmbedding

Rating = tuple[str, str, bool]


@dataclass
class Decision:
    recommend: bool
    score: float          # best like similarity minus best dislike similarity
    reason: str


def _norm(name: str) -> str:
    return " ".join(name.lower().split())


class FoodRecommender:
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        like_threshold: float = 0.55,   # how close to a liked food it must be
        margin: float = 0.05,           # how much closer to a like than to a dislike
    ) -> None:
        self.model = TextEmbedding(model_name)
        self.like_threshold = like_threshold
        self.margin = margin
        self._cache: dict[str, np.ndarray] = {}

    def _embed(self, names: list[str]) -> np.ndarray:
        """Embed names (normalized to unit length), caching each one."""
        missing = [n for n in dict.fromkeys(names) if n not in self._cache]
        if missing:
            for name, vec in zip(missing, self.model.embed(missing)):
                self._cache[name] = vec / np.linalg.norm(vec)
        return np.stack([self._cache[n] for n in names])

    def decide(self, user_id: str, food: str, ratings: list[Rating]) -> Decision:
        food = _norm(food)
        mine = [(_norm(f), liked) for uid, f, liked in ratings if uid == user_id]

        if not mine:
            return Decision(False, 0.0, "no ratings for this user yet")

        # Exact match short-circuits the model.
        for name, liked in mine:
            if name == food:
                return Decision(liked, 1.0 if liked else -1.0,
                                f"you {'liked' if liked else 'disliked'} this exact dish")

        names = [n for n, _ in mine]
        sims = self._embed(names) @ self._embed([food])[0]   # cosine similarity

        likes = [(s, n) for s, (n, l) in zip(sims, mine) if l]
        dislikes = [(s, n) for s, (n, l) in zip(sims, mine) if not l]
        best_like = max(likes, default=(0.0, None))
        best_dislike = max(dislikes, default=(0.0, None))

        score = float(best_like[0] - best_dislike[0])
        ok = best_like[0] >= self.like_threshold and score >= self.margin

        if ok:
            reason = f"similar to '{best_like[1]}' ({best_like[0]:.2f})"
        elif best_dislike[1] and best_dislike[0] >= best_like[0]:
            reason = f"closer to disliked '{best_dislike[1]}' ({best_dislike[0]:.2f})"
        else:
            reason = f"not close enough to anything you liked (best {best_like[0]:.2f})"
        return Decision(ok, score, reason)


_default: FoodRecommender | None = None


def should_recommend(food: str, ratings: list[Rating], user_id: str) -> bool:
    """Return True if `food` should be recommended to `user_id`.

    `ratings` is a list of (user_id, food_name, liked) tuples. The embedding
    model loads once on first call and is reused afterwards.
    """
    global _default
    if _default is None:
        _default = FoodRecommender()
    return _default.decide(user_id, food, ratings).recommend


if __name__ == "__main__":
    ratings: list[Rating] = [
        ("u1", "Orange Chicken", True),
        ("u1", "Pepperoni Pizza", True),
        ("u1", "Tofu Stir Fry", False),
        ("u1", "Garden Salad", False),
        ("u2", "Blueberry Muffin", True),
    ]
    for food in ["Chicken Teriyaki Bowl", "Cheese Pizza", "Caesar Salad",
                 "Vegetable Tofu Curry", "Scrambled Eggs"]:
        print(f"{food:25} -> {'YES' if should_recommend(food, ratings, 'u1') else 'no'}")
