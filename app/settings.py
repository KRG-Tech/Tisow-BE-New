import os
from typing import Dict, List
import yaml
from app.sql_conn import SqlConn
import paho.mqtt.client as mqtt
from fastapi import WebSocket
import sys


class AppConfig:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            # If the application is frozen (running as an exe)
            dir_path = os.path.dirname(sys.executable)
        else:
            # If the application is running as a script
            dir_path = os.path.dirname(os.path.abspath(__file__))

            # Construct the path to configurations.yaml
        config_path = os.path.join(dir_path, "configurations.yaml")
        with open(config_path, "r") as ymlFile:
            self.cfg = yaml.load(ymlFile, Loader=yaml.FullLoader)

    def admin_conf(self):
        return self.cfg["admin"]

    def database(self):
        return self.cfg["DB"]["database"]

    def maria_connectio_string(self):
        """
        Returns the MariaDB Connection String.

        :return: string: MariaDB Connection String
        """
        connection_config = self.cfg["DB"]
        return (
            f"mariadb+mariadbconnector://{connection_config['username']}:{connection_config['password']}"
            f"@{connection_config['host']}:{connection_config['port']}/"
        )

    def maria_conn(self):
        try:
            sql_con = SqlConn(
                db=self.database(), connection_url=self.maria_connectio_string()
            )
            sql_con.connection_manager()
            return sql_con
        except Exception as err:
            print(f"Failed to make connection with db: {err}")
            exit(1)

    def mqtt_conf(self):
        return self.cfg["mqtt"]

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        print("Connected to MQTT Broker!")

    @staticmethod
    def on_message(client, userdata, msg):
        # Placeholder function to be overridden
        pass

    def create_mqtt_client(self):
        client = mqtt.Client()
        mqtt_conf = self.mqtt_conf()
        client.username_pw_set(mqtt_conf["username"], mqtt_conf["password"])
        return client

    def setup_mqtt(self):
        mqtt_conf = self.mqtt_conf()
        client = self.create_mqtt_client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(mqtt_conf["host"], mqtt_conf["port"], 60)
        return client

    def ws_topic(self):
        return self.cfg["websocket"]["topic"]


SETTINGS = AppConfig()

# DB Connection
SQL_CON = SETTINGS.maria_conn()
DB = SQL_CON.get_db

# MQTT Connection
# MQTT_CLIENT = SETTINGS.setup_mqtt()
# MQTT_TOPICS = SETTINGS.mqtt_conf()['topics']


TOPICS: Dict[str, List[WebSocket]] = {}
WS_LIVE_TOPIC = SETTINGS.ws_topic()
