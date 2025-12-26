import os
from itertools import chain

import pandas as pd
import requests
from bs4 import BeautifulSoup
from rich.progress import track

URL = "https://www.senegel.org/fr/administration/pouvoir-executif/agences-nationales"


def fetch_agencies(url: str) -> list[dict[str, str]]:
	try:
		page = requests.get(url).text
	except Exception as e:
		print(f"Error fetching {url}: {e}")
		return None
	soup = BeautifulSoup(page, "html.parser")
	agences = []
	for card in soup.select("div.uk-card.uk-card-default.uk-margin"):
		a_tag = card.select_one("h3.uk-card-title a")
		if a_tag:
			nom = a_tag.get_text(strip=True)
			lien = a_tag.get("href")
			if lien.startswith("/"):
				lien = "https://www.senegel.org" + lien
			agences.append({"nom": nom, "lien_source": lien})
	return agences


def fetch_detail_description(agency) -> str:
	page = requests.get(agency["lien_source"]).text
	soup = BeautifulSoup(page, "html.parser")
	presentation_element = soup.find(string=lambda text: text and "Présentation" in text)
	if presentation_element:
		extracted_text = []
		for sibling in presentation_element.find_all_next():
			if sibling.name in ["p", "li"]:
				text = sibling.get_text(strip=True)
				if text:
					if "Vous êtes ici" in text:
						break
					extracted_text.append(text)
		agency["description"] = "\n".join(extracted_text)
	return agency


def main(out_folder: str = "") -> pd.DataFrame:
	agencies = list(
		chain.from_iterable(
			[
				fetch_agencies(f"{URL}?start={10 * p}")
				for p in track(range(5), description="Fetching agency list...")
			]
		)
	)
	for agency in track(agencies, description="Fetching agency details..."):
		try:
			agency = fetch_detail_description(agency)
		except Exception as e:
			print(f"Error fetching {agency['lien']}: {e}")
			agency["description"] = ""
	result = pd.DataFrame(
		agencies
	)  # .drop_duplicates(subset=["nom"]).reset_index(drop=True)
	result.to_excel(
		os.path.join(out_folder, "agences_nationales.xlsx"),
		index=False,
	)
	return result


if __name__ == "__main__":
	df = main(out_folder="data")
	print(df)
