import requests
from bs4 import BeautifulSoup
from googlesearch import search

def find_polish_exporters_to_uk():
    query = "site:.pl export to UK OR exporting to UK OR eksport do UK OR eksport Wielka Brytania"
    company_urls = []

    print("Searching for Polish companies exporting to the UK...")

    for url in search(query, num=20, stop=20, lang="pl"):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text().lower()
                
                # Look for keywords in the page text
                keywords = ["export to uk", "exporting to uk", "eksport do uk", "eksport wielka brytania"]
                if any(keyword in text for keyword in keywords):
                    company_urls.append(url)
                    print(f"Found: {url}")

        except requests.RequestException:
            print(f"Skipping {url} (error fetching page)")

    if not company_urls:
        print("No relevant company websites found.")
    else:
        print("\nList of Polish companies exporting to the UK:")
        for url in company_urls:
            print(url)

if __name__ == "__main__":
    find_polish_exporters_to_uk()
