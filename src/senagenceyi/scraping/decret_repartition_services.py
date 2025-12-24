import os

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://primature.sn/publications/lois-et-reglements/decret-ndeg-2024-940-portant-repartition-des-services-de-letat-et"


def fetch(url: str) -> BeautifulSoup:
	response = requests.get(url)
	return BeautifulSoup(response.text, "html.parser")


def clean(text: str) -> str:
	return (
		text.replace(";", "")
		.replace(".", " ")
		.replace("\n", "")
		.replace("\t", "")
		.replace(":", "")
		.strip()
	)


def main(out_folder: str = "") -> str:
	try:
		soup = fetch(URL)
	except Exception as e:
		print(f"Error fetching {URL}: {e}")
		return ""
	start_heading = soup.find(
		string=lambda text: text and "PRÉSIDENCE DE LA RÉPUBLIQUE" in text
	)
	extracted_text = []
	if start_heading:
		current_element = start_heading.find_parent()
		for sibling in current_element.find_all_next():
			if sibling.name in ["p", "li"]:
				text = sibling.get_text(strip=True)
				if text:
					extracted_text.append(clean(text))
	pd.DataFrame({"decret_repartition_services": extracted_text}).to_excel(
		os.path.join(out_folder, "decret_repartition_services_raw.xlsx"), index=False
	)
	return "\n".join(extracted_text)


if __name__ == "__main__":
	result = main("data")
	print(result)
