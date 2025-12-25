import os

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://primature.sn/publications/lois-et-reglements/decret-ndeg-2024-940-portant-repartition-des-services-de-letat-et"
REGEX_NUMBER = r"^\d+\s+°|\d+°"


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
	path = os.path.join(out_folder, "decret_repartition_services_raw.xlsx")
	if os.path.exists(path):
		path = path.replace(".xlsx", "_new.xlsx")
	pd.DataFrame({"decret_repartition_services": extracted_text}).to_excel(
		path, index=False
	)
	return "\n".join(extracted_text)


def service_contains(df: pd.DataFrame, text: str) -> pd.Series:
	return df.service.str.strip().str.startswith(text)


def lignes_entite(df: pd.DataFrame) -> pd.Series:
	return (
		service_contains(df, "MINISTÈRE")
		| service_contains(df, "MINISTERE")
		| service_contains(df, "PRIMATURE")
		| service_contains(df, "PRÉSIDENCE")
		| service_contains(df, "PRESIDENCE")
	)


def impute_entite(services: pd.DataFrame) -> pd.DataFrame:
	services.loc[lambda df: lignes_entite(df), "entite"] = services[
		lignes_entite(services)
	].service
	services.loc[:, "entite"] = services.entite.ffill().fillna(
		"PRÉSIDENCE DE LA REPUBLIQUE"
	)
	services = services.loc[lambda df: ~lignes_entite(df)].reset_index(drop=True)
	return services


def impute_admin(services: pd.DataFrame) -> pd.DataFrame:
	admin_mask = services.service.str.strip().str.match(REGEX_NUMBER)
	services.loc[admin_mask, "administration"] = services[admin_mask].service
	services.loc[:, "administration"] = services.administration.ffill()
	services = services.loc[~admin_mask].reset_index(drop=True)
	return services


def clean_raw_service_data(state_services: pd.DataFrame) -> pd.DataFrame:
	return (
		state_services.rename(columns={"decret_repartition_services": "service"})
		.assign(entite=None, administration=None)
		.pipe(impute_entite)
		.pipe(impute_admin)
		.iloc[:1145, :][["entite", "administration", "service"]]
		.loc[lambda df: ~df.service.str.strip().str.match(r"^Article\s+\d+")]
		.drop_duplicates()
		.assign(
			entite=lambda df: df.entite.str.strip()
			.str.replace("MINISTERE", "MINISTÈRE")
			.str.replace("PRESIDENCE", "PRÉSIDENCE"),
			administration=lambda df: df.administration.str.strip()
			.str.replace(REGEX_NUMBER, "", regex=True)
			.str.strip(),
			service=lambda df: df.service.str.strip(),
		)
		.reset_index(drop=True)
	)


if __name__ == "__main__":
	# result = main("data")
	# print(result)
	state_services = pd.read_excel("data/decret_repartition_services_raw.xlsx").pipe(
		clean_raw_service_data
	)
	print(state_services)
	state_services.to_excel("decret_repartition_services_structured.xlsx", index=False)
