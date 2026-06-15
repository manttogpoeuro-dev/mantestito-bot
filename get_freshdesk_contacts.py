import os
import requests

FRESHDESK_API_KEY = os.environ.get("FRESHDESK_API_KEY")
FRESHDESK_DOMAIN = os.environ.get("FRESHDESK_DOMAIN")

def main():
    page = 1
    all_contacts = []

    while True:
        url = f"https://{FRESHDESK_DOMAIN}/api/v2/contacts"
        params = {"page": page, "per_page": 100}
        response = requests.get(url, auth=(FRESHDESK_API_KEY, "X"), params=params)

        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        data = response.json()
        if not data:
            break

        all_contacts.extend(data)
        print(f"Pagina {page}: {len(data)} contactos")
        page += 1

        if page > 20:  # safety limit
            break

    print("=" * 60)
    print(f"TOTAL CONTACTOS: {len(all_contacts)}")
    print("=" * 60)

    for c in all_contacts:
        nombre = c.get("name", "")
        email = c.get("email", "")
        empresa = c.get("company_id", "")
        print(f"Nombre: {nombre} | Email: {email} | company_id: {empresa}")

if __name__ == "__main__":
    main()
