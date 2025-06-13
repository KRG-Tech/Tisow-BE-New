# File: app/create_db.py

import os
import sys

def fix_working_directory():
    """
    Fix working directory to project root so relative paths work,
    especially when running from .bat files.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(current_dir, ".."))

fix_working_directory()

# Now import settings (this triggers DB creation)
from app.settings import SQL_CON

def main():
    # Just trigger the SQL connection to ensure DB & tables are created
    for _ in SQL_CON.get_db():
        print("✅ Database and tables initialized successfully.")

if __name__ == "__main__":
    main()
