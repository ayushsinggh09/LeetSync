import os
import time
import requests
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
LEETCODE_SESSION = os.environ["LEETCODE_SESSION"]
LEETCODE_CSRF_TOKEN = os.environ["LEETCODE_CSRF_TOKEN"]
DATA_SOURCE_ID = "7548daa2-2d83-4e9b-ae5b-7bc9f4110b04"

notion = Client(auth=NOTION_TOKEN)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

LEETCODE_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "x-csrftoken": LEETCODE_CSRF_TOKEN,
    "Cookie": f"LEETCODE_SESSION={LEETCODE_SESSION}; csrftoken={LEETCODE_CSRF_TOKEN}",
}

QUESTION_LIST_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      difficulty
      frontendQuestionId: questionFrontendId
      paidOnly: isPaidOnly
      status
      title
      titleSlug
    }
  }
}
"""


def fetch_all_leetcode_problems():
    """Fetch every problem + the logged-in user's status for it."""
    all_questions = []
    skip = 0
    limit = 100

    while True:
        payload = {
            "query": QUESTION_LIST_QUERY,
            "variables": {
                "categorySlug": "",
                "skip": skip,
                "limit": limit,
                "filters": {},
            },
        }
        resp = requests.post(LEETCODE_GRAPHQL_URL, json=payload, headers=LEETCODE_HEADERS)
        resp.raise_for_status()
        data = resp.json()["data"]["problemsetQuestionList"]

        batch = data["questions"]
        all_questions.extend(batch)

        total = data["total"]
        skip += limit
        print(f"Fetched {len(all_questions)} / {total} problems...")

        if skip >= total or not batch:
            break

        time.sleep(0.3)  

    return all_questions


def fetch_existing_notion_pages():
    """Build a map of {titleSlug: notion_page_id} for problems already in Notion."""
    existing = {}
    cursor = None

    while True:
        query_args = {"data_source_id": DATA_SOURCE_ID, "page_size": 100}
        if cursor:
            query_args["start_cursor"] = cursor

        response = notion.data_sources.query(**query_args)

        for page in response["results"]:
            slug_prop = page["properties"].get("Slug", {})
            rich_text = slug_prop.get("rich_text", [])
            if rich_text:
                slug = rich_text[0]["plain_text"]
                existing[slug] = page["id"]

        if response.get("has_more"):
            cursor = response.get("next_cursor")
            time.sleep(0.3)
        else:
            break

    return existing


def status_to_label(lc_status):
    if lc_status == "ac":
        return "Solved"
    elif lc_status == "notac":
        return "Attempted"
    else:
        return "Not Started"


def difficulty_label(diff):
    # LeetCode returns difficulty level as an integer 1=Easy 2=Medium 3=Hard
    return {1: "Easy", 2: "Medium", 3: "Hard"}.get(diff, str(diff))


def build_properties(question):
    slug = question["titleSlug"]
    url = f"https://leetcode.com/problems/{slug}/"

    return {
        "Name": {"title": [{"text": {"content": question["title"]}}]},
        "Difficulty": {"select": {"name": difficulty_label(question["difficulty"])}},
        "LeetCode ID": {"number": int(question["frontendQuestionId"])},
        "Slug": {"rich_text": [{"text": {"content": slug}}]},
        "Status": {"select": {"name": status_to_label(question["status"])}},
        "URL": {"url": url},
    }


def main():
    print("Step 1: Fetching problems from LeetCode...")
    problems = fetch_all_leetcode_problems()
    print(f"Total problems fetched: {len(problems)}\n")

    print("Step 2: Fetching existing Notion pages...")
    existing_pages = fetch_existing_notion_pages()
    print(f"Existing pages already in Notion: {len(existing_pages)}\n")

    print("Step 3: Syncing to Notion...")
    created, updated, skipped_paid = 0, 0, 0

    for i, question in enumerate(problems, start=1):
        if question["paidOnly"]:
            skipped_paid += 1
            continue

        slug = question["titleSlug"]
        properties = build_properties(question)

        if slug in existing_pages:
            notion.pages.update(page_id=existing_pages[slug], properties=properties)
            updated += 1
        else:
            notion.pages.create(
                parent={"type": "data_source_id", "data_source_id": DATA_SOURCE_ID},
                properties=properties,
            )
            created += 1

        if i % 25 == 0:
            print(f"Progress: {i}/{len(problems)} (created={created}, updated={updated})")

        time.sleep(0.35)  # Notion ~3 requests/sec limit

    print("\nDone!")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Skipped (paid-only problems): {skipped_paid}")


if __name__ == "__main__":
    main()