import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

notion = Client(auth=os.environ["NOTION_TOKEN"])

data_source_id = "7548daa2-2d83-4e9b-ae5b-7bc9f4110b04"
new_page = {
    "parent": {"type": "data_source_id", "data_source_id": data_source_id},
    "properties": {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": "Test Problem - Two Sum"
                    }
                }
            ]
        }
    }
}

response = notion.pages.create(**new_page)
print("Page created successfully!")
print("Page ID:", response["id"])
print("Page URL:", response["url"])