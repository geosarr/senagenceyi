import asyncio
import os
from itertools import chain

import aiohttp
import pandas as pd
import requests
from bs4 import BeautifulSoup
from rich.progress import track

BASE_URL = "https://senegalservices.sn/services-administratifs"


async def fetch(session, url):
	async with session.get(url) as response:
		return await response.text()


def fetch_sync(url):
	return requests.get(url).text


def service_links(soup: BeautifulSoup):
	links = []
	for a_tag in soup.find_all("a", href=True):
		if "services-administratifs/" in a_tag["href"]:
			full_link = (
				a_tag["href"]
				if a_tag["href"].startswith("http")
				else f"https://senegalservices.sn{a_tag['href']}"
			)
			links.append(full_link)
	return links


async def scrape_service_links(session, url):
	try:
		html = await fetch(session, url)
	except Exception as e:
		print(f"Error fetching {url}: {e}")
		return []
	return service_links(BeautifulSoup(html, "html.parser"))


def initialize_result():
	return {
		"nom": None,
		"adresse": None,
		"telephone": None,
		"email": None,
		"site_web": None,
		"lien_source": None,
	}


def service_details(result: dict[str, str], soup: BeautifulSoup):
	result["nom"] = soup.find("h1").get_text(strip=True)
	for p in soup.find_all("p"):
		text = p.get_text(strip=True)
		if "adresse" in text.lower():
			adresse = p.find_next("p")
			if adresse:
				result["adresse"] = adresse.get_text(strip=True)
		if "téléphone" in text.lower():
			telephone = p.find_next("p")
			if telephone:
				if telephone.get_text(strip=True).startswith(("33", "+33")):
					result["telephone"] = telephone.get_text(strip=True)
		if "e-mail" in text.lower():
			mail = p.find_next("p")
			if mail:
				result["email"] = mail.get_text(strip=True)
		if "site web" in text.lower():
			link = p.find_next("a", href=True)
			if link:
				result["site_web"] = link["href"]
	return result


async def scrape_service_details(session, link):
	result = initialize_result()
	try:
		html = await fetch(session, link)
	except Exception as e:
		print(f"Error fetching {link}: {e}")
		return result
	return service_details(result, BeautifulSoup(html, "html.parser"))


async def scrape_page(url):
	print(f"Scraping page: {url}")
	async with aiohttp.ClientSession() as session:
		service_links = await scrape_service_links(session, url)
		tasks = [scrape_service_details(session, link) for link in service_links]
		return await asyncio.gather(*tasks)


def scrape_page_sync(url):
	print(f"Scraping page: {url}")
	html = fetch_sync(url)
	soup = BeautifulSoup(html, "html.parser")
	links = service_links(soup)
	records = []
	for link in links:
		service_html = fetch_sync(link)
		service_soup = BeautifulSoup(service_html, "html.parser")
		result = initialize_result()
		details = service_details(result, service_soup)
		records.append(details)
	return records


async def main(out_folder: str = ""):
	tasks = [scrape_page(f"{BASE_URL}?p={i}") for i in range(1, 50)]
	records = await asyncio.gather(*tasks)
	result = (
		pd.DataFrame(chain.from_iterable(records))
		.dropna(subset=["nom"])
		.assign(lien_source=BASE_URL)
	)
	result.to_excel(os.path.join(out_folder, "senegal_services.xlsx"), index=False)
	return result


def main_sync(out_folder: str = ""):
	records = []
	try:
		for page in track(range(1, 50), description="Scraping pages..."):
			records.extend(scrape_page_sync(f"{BASE_URL}?p={page}"))
	except Exception as e:
		print(f"Error during scraping: {e}")
	result = pd.DataFrame(records).dropna(subset=["nom"]).assign(lien_source=BASE_URL)
	result.to_excel(os.path.join(out_folder, "senegal_services.xlsx"), index=False)
	return result


if __name__ == "__main__":
	# Run from root folder senagenceyi
	# data = asyncio.run(main(out_folder="data"))
	data = main_sync(out_folder="data")
	print(data)
