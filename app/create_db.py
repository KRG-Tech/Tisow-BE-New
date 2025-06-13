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

def fix_working_directory():
    """
    Fix working directory to project root so relative paths work,
    especially when running from .bat files.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(current_dir, ".."))

fix_working_directory()


from app.settings import SQL_CON, SETTINGS
from app.sql_schemas.models import Users, Base  
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash  # You can also use bcrypt or hashlib

def create_admin_user(session: Session):
    config = SETTINGS.admin_conf()
    username = config["username"]
    email = config["email"]
    password = config["password"]

    existing = session.query(Users).filter_by(username=username).first()
    if existing:
        print("ℹ️ Admin user already exists. Skipping creation.")
        return

    hashed_password = generate_password_hash(password)
    admin = Users(
        username=username,
        email=email,
        password=hashed_password,
        role="admin"  
    )
    session.add(admin)
    session.commit()
    print("✅ Admin user created successfully.")

def main():
    for db in SQL_CON.get_db():
        print("⚙️ Creating database and tables...")
        create_admin_user(db)
        print("✅ Database and tables initialized successfully.")

if __name__ == "__main__":
    main()

