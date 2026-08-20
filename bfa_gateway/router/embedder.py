# Copyright (c) 2026 Sandro G. All rights reserved.
# Licensed under AGPLv3 / Commercial Dual License.
from abc import ABC, abstractmethod
from typing import List
import hashlib
import numpy as np

class AbstractEmbedder(ABC):
    """
    Abstract Base Class defining the embedding driver interface for BFA Semantic Router.
    """
    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass

class DummyEmbedder(AbstractEmbedder):
    """
    Fast, deterministic offline embedder using SHA-256 hash vector projection.
    Used for unit testing and offline development without Torch or OpenAI dependencies.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _hash_text(self, text: str) -> List[float]:
        if not text:
            vec = np.zeros(self.dimension).astype("float32")
            vec[0] = 1.0
            return vec.tolist()
        np.random.seed(int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) % (2**32))
        vec = np.random.randn(self.dimension).astype("float32")
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_text(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._hash_text(text)

class LocalEmbedder(AbstractEmbedder):
    """
    Local embedding driver backed by SentenceTransformers.
    """
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            raise ImportError(
                "sentence-transformers package not found. "
                "SentenceTransformers is required for LocalEmbedder. "
                "Install with: pip install 'bfa-irc-a-sdk[local]'"
            )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

class OpenAIEmbedder(AbstractEmbedder):
    """
    Cloud embedding driver backed by OpenAI text-embedding-3-small API.
    """
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        import os
        self.model = model
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY environment variable or argument is required for OpenAIEmbedder.")
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=key)
        except ImportError:
            raise ImportError("openai package is required for OpenAIEmbedder. Install with: pip install openai")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        res = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in res.data]

    def embed_query(self, text: str) -> List[float]:
        res = self.client.embeddings.create(input=[text], model=self.model)
        return res.data[0].embedding
