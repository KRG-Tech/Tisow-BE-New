from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from app.sql_schemas.models import Base


class SqlConn:

    def __init__(self, db: str, connection_url: str):
        """
        Initializes the MariaSql connection

        :param db: Database name to connect (act as default db)
        :param connection_url: Sql connection string
        """
        self.url = connection_url
        self.db = db
        self.engine = None
        self.SessionLocal = None

    def create_database(self, db_engine):
        with db_engine.connect() as connection:
            connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {self.db}"))

    @staticmethod
    def create_schema(engine_schema):
        Base.metadata.create_all(engine_schema)

    def create_session(self):
        try:
            session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
            self.SessionLocal = session
        except Exception as err:
            print(f"failed to create session: {err}")

    def connection_manager(self):
        try:
            engine = create_engine(self.url)
            self.create_database(engine)
            connection_url = f"{self.url}{self.db}"
            self.engine = create_engine(
                connection_url,
                pool_size=10,  # Adjust based on app's needs
                max_overflow=20,  # Temporary overflow capacity
                pool_timeout=60,
            )
            SqlConn.create_schema(self.engine)
            self.create_session()
        except SQLAlchemyError as e:
            print(f"Error occurred: {str(e)}")
            return False

    def get_db(self):
        db: Session = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
