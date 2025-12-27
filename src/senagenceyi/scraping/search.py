from concurrent.futures import ProcessPoolExecutor
from itertools import chain
from multiprocessing import Manager
from time import sleep

import pandas as pd
from ddgs import DDGS
from rich.progress import BarColumn, Progress, TimeElapsedColumn, TimeRemainingColumn


def process_result(results):
	for r in results:
		if "gouv.sn" in r["href"] or "sn" in r["href"]:
			return r["href"]
	if results:
		return results[0]["href"]
	return ""


def find_official_description(service):
	query = f"{service} Sénégal site officiel mission"
	return process_result(
		list(DDGS().text(query, region="fr-fr", safesearch="Off", max_results=3))
	)


def split(lst, n):
	"""Split list lst into n approximately equal parts."""
	k, m = divmod(len(lst), n)
	return [lst[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)]


def fetch_some_services(
	progress, task_id, services: list[str], contexts: list[str], verbosity: int = 0
) -> list[str]:
	liens = []
	for pos, service in enumerate(services):
		if verbosity > 0:
			print(f"Recherche pour : {service}")
		lien = find_official_description(service + " " + contexts[pos])
		liens.append({"service": service, "lien": lien})
		if verbosity > 0:
			print(service, ": ", lien)
		# sleep(1)  # To avoid being blocked
		progress[task_id] = {"progress": pos + 1, "total": len(services)}
	return liens


def progress_bar():
	return Progress(
		"[progress.description]{task.description}",
		BarColumn(),
		"[progress.percentage]{task.percentage:>3.0f}%",
		TimeRemainingColumn(),
		TimeElapsedColumn(),
		refresh_per_second=1,  # bit slower updates
	)


if __name__ == "__main__":
	n_workers = 8  # set this to the number of cores you have on your machine

	df = pd.read_excel("data/decret_repartition_services.xlsx")
	services_and_contexts = df[["service", "administration"]].drop_duplicates()
	services = services_and_contexts["service"].tolist()
	contexts = services_and_contexts["administration"].tolist()
	splitted_services = split(services, n_workers)
	splitted_contexts = split(contexts, n_workers)
	# Adapted from https://www.deanmontgomery.com/2022/03/24/rich-progress-and-multiprocessing/
	with (
		progress_bar() as progress,
		Manager() as manager,
		ProcessPoolExecutor(max_workers=n_workers) as executor,
	):
		futures = []  # keep track of the jobs
		# this is the key - we share some state between our
		# main process and our worker functions
		_progress = manager.dict()
		overall_progress_task = progress.add_task("[green]All jobs progress:")
		for n in range(0, n_workers):  # iterate over the jobs we need to run
			# set visible false so we don't have a lot of bars all at once:
			task_id = progress.add_task(f"task {n}", visible=False)
			futures.append(
				executor.submit(
					fetch_some_services,
					_progress,
					task_id,
					splitted_services[n],
					splitted_contexts[n],
				)
			)

		# monitor the progress:
		while (n_finished := sum([future.done() for future in futures])) <= len(futures):
			progress.update(
				overall_progress_task, completed=n_finished, total=len(futures)
			)
			for task_id, update_data in _progress.items():
				latest = update_data["progress"]
				total = update_data["total"]
				# update the progress bar for this task:
				progress.update(
					task_id,
					completed=latest,
					total=total,
					visible=latest < total,
				)
			if n_finished == len(futures):
				break

		links = chain.from_iterable([future.result() for future in futures])
		pd.DataFrame(links).to_excel("data/services_sites_officiels.xlsx", index=False)
