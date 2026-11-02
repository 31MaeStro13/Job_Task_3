import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    print("Запуск SVG Illustration Composer на http://127.0.0.1:8000 ...")
    execute_from_command_line(["manage.py", "runserver", "0.0.0.0:8000"])

if __name__ == "__main__":
    main()
