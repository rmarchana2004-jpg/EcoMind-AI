from fastembed import TextEmbedding
import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

model = TextEmbedding(model_name=MODEL_NAME)


def generate_embedding(text: str):
    embedding = next(model.embed([text]))
    return np.array(embedding, dtype=np.float32)