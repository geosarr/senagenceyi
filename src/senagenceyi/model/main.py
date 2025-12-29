from functools import partial

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


def n_largest_indices(arr, n):
	_arr = np.array(arr)
	indices = np.argpartition(_arr, n)[-n:]
	return indices[np.argsort(_arr[indices])][::-1]


model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

df = (
	pd.read_excel("data/agences_nationales.xlsx")
	.dropna(subset=["description"])
	.reset_index(drop=True)
)
sentences = df.description.tolist()

embeddings = model.encode(sentences, normalize_embeddings=True)
cosine_scores = (embeddings @ embeddings.T).round(3)
print(cosine_scores)

top = 5
df.loc[:, "cosine_similarity"] = list(cosine_scores)
df.loc[:, "top_cosine"] = df.cosine_similarity.apply(
	partial(n_largest_indices, n=top + 1)
).apply(lambda x: x[1:])
df = (
	df.assign(
		top_similar_agencies=df.top_cosine.apply(
			lambda indices: [df.iloc[i].nom for i in indices]
		),
		rank_similarities=[list(range(1, top + 1))] * len(df),
	)
	.explode(["top_similar_agencies", "rank_similarities"])
	.reset_index(drop=True)
	.rename(
		columns={
			"top_similar_agencies": "nom_agence_similaire",
			"rank_similarities": "rang_similarite",
		}
	)[["nom", "description", "nom_agence_similaire", "rang_similarite"]]
)

df.to_excel("data/agences_nationales_similarites.xlsx", index=False)
