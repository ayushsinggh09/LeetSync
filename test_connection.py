import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])

data_source_id = "*******************"

response = notion.data_sources.query(data_source_id=data_source_id)
print("Connected! Number of items found:", len(response["results"]))
