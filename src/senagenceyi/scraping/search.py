import time

import pandas as pd
from ddgs import DDGS, ddgs

df = pd.read_excel("data/decret_repartition_services.xlsx").head(3)

services = (df["service"] + " " + df["administration"]).dropna().unique().tolist()


def find_official_description(service):
	query = f"{service} Sénégal site officiel mission"
	results = list(DDGS().text(query, region="fr-fr", safesearch="Off", max_results=3))
	for r in results:
		if "gouv.sn" in r["href"] or "sn" in r["href"]:
			return r["href"]
	if results:
		return results[0]["href"]
	return ""


liens = []
for service in services:
	print(f"Recherche pour : {service}")
	lien = find_official_description(service)
	liens.append(lien)
	print(service, ": ", lien)
	time.sleep(1)  # To avoid being blocked

df_result = pd.DataFrame({"service": services, "site_officiel_mission": liens})

df_result.to_excel("data/services_sites_officiels.xlsx", index=False)
