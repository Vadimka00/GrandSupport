import os
from dotenv import load_dotenv

load_dotenv(override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_WEB = os.getenv("ADMIN_WEB")
DB_URL = os.getenv("DB_URL")

SUPPORT_GROUP_RU_ID = int(os.getenv("SUPPORT_GROUP_RU_ID"))
SUPPORT_GROUP_EN_ID = int(os.getenv("SUPPORT_GROUP_EN_ID"))

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
