import os
import requests
import json

FRESHDESK_API_KEY = os.environ.get("FRESHDESK_API_KEY")
FRESHDESK_DOMAIN = os.environ.get("FRESHDESK_DOMAIN")

def main():
    url = f"https://{FRESHDESK_DOMAIN}/api/v2/ticket_fields"
    response = requests.get(url, auth=(FRESHDESK_API_KEY, "X"))

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return

    fields = response.json()

    print("=" * 60)
    print("CAMPOS DISPONIBLES EN FRESHDESK")
    print("=" * 60)

    for field in fields:
        print(f"\nNombre: {field.get('label')}")
        print(f"  Campo API (name): {field.get('name')}")
        print(f"  Tipo: {field.get('type')}")
        print(f"  Requerido: {field.get('required_for_agents')}")

        # Si tiene opciones (choices), mostrarlas
        if field.get('choices'):
            choices = field.get('choices')
            print(f"  Opciones:")
            if isinstance(choices, dict):
                for key, val in choices.items():
                    print(f"    - {key}: {val}")
            elif isinstance(choices, list):
                for c in choices:
                    print(f"    - {c}")

if __name__ == "__main__":
    main()
