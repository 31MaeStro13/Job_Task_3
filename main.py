import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    port = os.environ.get("PORT", "8001")
    print(f"Запуск SVG Illustration Composer на http://0.0.0.0:{port} ...")
    execute_from_command_line(["manage.py", "runserver", f"0.0.0.0:{port}"])

if __name__ == "__main__":
    main()
