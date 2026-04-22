from ai.embedding import Embedder

e = Embedder()
print(e.is_available())   # should print True
vec = e.embed_text("hello world")
print(vec.shape)  