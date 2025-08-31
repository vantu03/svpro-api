import tiktoken
from openai import AsyncOpenAI
import base64
import asyncio

from app.admin import settings
from pricing import update_usage

async def bytes_to_base64(data: bytes, mime_type: str = "image/png"):
    encoded = await asyncio.to_thread(base64.b64encode, data)
    return f"data:{mime_type};base64,{encoded.decode()}"

class PDFEmbedder:
    def __init__(self, model="text-embedding-3-small"):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str, max_tokens=500):
        tokens = self.tokenizer.encode(text)
        for i in range(0, len(tokens), max_tokens):
            yield self.tokenizer.decode(tokens[i:i+max_tokens])

    async def embed_chunks(self, chunks: list[dict], max_tokens: int = 500):
        chunk_vecs = []

        for chunk in chunks:
            text = chunk.get("text", "")
            if not text.strip():
                continue  # bỏ trang trống

            parts = list(self.chunk_text(text, max_tokens=max_tokens))
            for part in parts:
                meta = {
                    "page": chunk["page"],
                    "text": part,
                    "images": chunk.get("images", []),
                    "page_image": chunk.get("page_image")
                }
                chunk_vecs.append(meta)

        if not chunk_vecs:
            return []

        # gọi API embeddings
        response = await self.client.embeddings.create(
            model=self.model,
            input=[meta["text"] for meta in chunk_vecs]
        )
        update_usage(response.model, response.usage.prompt_tokens, 0)
        vectors = [e.embedding for e in response.data]

        # ghép meta + embedding
        results = [(meta, vec) for meta, vec in zip(chunk_vecs, vectors)]

        return results
