# # File: app/create_db.py

# import os
# import sys

# def fix_working_directory():
#     """
#     Fix working directory to project root so relative paths work,
#     especially when running from .bat files.
#     """
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     os.chdir(os.path.join(current_dir, ".."))

# fix_working_directory()

# # Now import settings (this triggers DB creation)
# from app.settings import SQL_CON

# def main():
#     # Just trigger the SQL connection to ensure DB & tables are created
#     for _ in SQL_CON.get_db():
#         print("✅ Database and tables initialized successfully.")

# if __name__ == "__main__":
#     main()

# File: app/create_db.py

import os
import sys
import yaml
import time
from sqlalchemy.exc import IntegrityError
from app.settings import SQL_CON
from app.schemas import Users  # Make sure this path is correct

def fix_working_directory():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(current_dir, ".."))

fix_working_directory()

def create_admin_user():
    config_path = os.path.join("app", "configuration.yaml")
    if not os.path.exists(config_path):
        print("❌ configuration.yaml not found.")
        return

    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    admin_data = config.get("admin")
    if not admin_data:
        print("❌ Admin data not found in configuration.yaml.")
        return

    db_session = next(SQL_CON.get_db())

    existing = db_session.query(Users).filter_by(email=admin_data["email"]).first()
    if existing:
        print("ℹ️ Admin user already exists.")
        return

    # Map 'username' to 'first_name'
    user = Users(
        first_name=admin_data["username"],
        email=admin_data["email"],
        password=admin_data["password"],
        is_admin=True
    )
    db_session.add(user)
    try:
        db_session.commit()
        print("✅ Admin user created successfully.")
    except IntegrityError:
        db_session.rollback()
        print("⚠️ Failed to create admin user due to IntegrityError.")

def main():
    for _ in SQL_CON.get_db():
        print("✅ Database and tables initialized successfully.")
    create_admin_user()

if __name__ == "__main__":
    main()
