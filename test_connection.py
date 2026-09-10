import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])

data_source_id = "7548daa2-2d83-4e9b-ae5b-7bc9f4110b04"

response = notion.data_sources.query(data_source_id=data_source_id)
print("Connected! Number of items found:", len(response["results"]))