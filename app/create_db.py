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
import time
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

# Step 1: Fix working directory (so relative imports work)
def fix_working_directory():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    os.chdir(project_root)

fix_working_directory()

# Step 2: Import app settings and models
from app.settings import SQL_CON, SETTINGS
from app.sql_schemas.models import Users, Base  # Do not change

def create_admin_user(session: Session):
    config = SETTINGS.admin_conf()
    username = config["username"]
    email = config["email"]
    password = config["password"]

    existing = session.query(Users).filter_by(email=email).first()
    if existing:
        print("ℹ️ Admin user already exists. Skipping creation.")
        return

    hashed_password = hashed_password = password

    admin = Users(
        first_name=username,
        second_name="",
        email=email,
        password=hashed_password,
        is_deleted=False,
        is_admin=True,
        timestamp=int(time.time()),
        role="admin",
        rule="fullaccess"
    )
    session.add(admin)
    session.commit()
    print("✅ Admin user created successfully.")

def main():
    print("⚙️ Creating database and tables...")
    for db in SQL_CON.get_db():
        Base.metadata.create_all(bind=SQL_CON.engine)
        create_admin_user(db)
        print("✅ Database and tables initialized successfully.")

if __name__ == "__main__":
    main()

