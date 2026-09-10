import os
import time
import json
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
LEETCODE_SESSION = os.environ["LEETCODE_SESSION"]
LEETCODE_CSRF_TOKEN = os.environ["LEETCODE_CSRF_TOKEN"]
DATA_SOURCE_ID = "7548daa2-2d83-4e9b-ae5b-7bc9f4110b04"
STATS_DATA_SOURCE_ID = "2bfaae3d-ca1d-4511-af67-974b4198d6ab"
LEETCODE_USERNAME = "ayushsinggh09"  

notion = Client(auth=NOTION_TOKEN)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"

LEETCODE_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "x-csrftoken": LEETCODE_CSRF_TOKEN,
    "Cookie": f"LEETCODE_SESSION={LEETCODE_SESSION}; csrftoken={LEETCODE_CSRF_TOKEN}",
}

CALENDAR_QUERY = """
query userProfileCalendar($username: String!, $year: Int) {
  matchedUser(username: $username) {
    userCalendar(year: $year) {
      activeYears
      submissionCalendar
    }
  }
}
"""


def fetch_active_years():
    payload = {
        "query": CALENDAR_QUERY,
        "variables": {"username": LEETCODE_USERNAME, "year": datetime.now().year},
    }
    resp = requests.post(LEETCODE_GRAPHQL_URL, json=payload, headers=LEETCODE_HEADERS)
    resp.raise_for_status()
    calendar = resp.json()["data"]["matchedUser"]["userCalendar"]
    return calendar["activeYears"]


def fetch_active_days_for_year(year):
    """Returns a set of date objects the user was active on, for a given year."""
    payload = {
        "query": CALENDAR_QUERY,
        "variables": {"username": LEETCODE_USERNAME, "year": year},
    }
    resp = requests.post(LEETCODE_GRAPHQL_URL, json=payload, headers=LEETCODE_HEADERS)
    resp.raise_for_status()
    calendar = resp.json()["data"]["matchedUser"]["userCalendar"]
    submission_calendar = json.loads(calendar["submissionCalendar"])

    active_days = set()
    for timestamp_str, count in submission_calendar.items():
        if int(count) > 0:
            day = datetime.utcfromtimestamp(int(timestamp_str)).date()
            active_days.add(day)

    return active_days


def compute_streaks(active_days):
    """Given a set of active date objects, compute current streak, longest streak, total active days."""
    if not active_days:
        return 0, 0, 0

    sorted_days = sorted(active_days)
    total_active_days = len(sorted_days)

    #scan for longest run of consecutive calendar days
    longest_streak = 1
    current_run = 1
    for i in range(1, len(sorted_days)):
        if (sorted_days[i] - sorted_days[i - 1]).days == 1:
            current_run += 1
            longest_streak = max(longest_streak, current_run)
        else:
            current_run = 1

    # Current streak
    today = datetime.utcnow().date()
    current_streak = 0
    cursor = today
    if today not in active_days:
        cursor = today - timedelta(days=1) 
    while cursor in active_days:
        current_streak += 1
        cursor -= timedelta(days=1)

    return current_streak, longest_streak, total_active_days


def fetch_existing_stats():
    """Map of {metric_name: page_id} from the Stats database."""
    existing = {}
    response = notion.data_sources.query(data_source_id=STATS_DATA_SOURCE_ID)
    for page in response["results"]:
        title_prop = page["properties"].get("Metric", {}).get("title", [])
        if title_prop:
            name = title_prop[0]["plain_text"]
            existing[name] = page["id"]
    return existing


def upsert_stat(metric_name, value, existing_stats):
    properties = {
        "Metric": {"title": [{"text": {"content": metric_name}}]},
        "Value": {"number": value},
    }
    if metric_name in existing_stats:
        notion.pages.update(page_id=existing_stats[metric_name], properties=properties)
    else:
        notion.pages.create(
            parent={"type": "data_source_id", "data_source_id": STATS_DATA_SOURCE_ID},
            properties=properties,
        )
    time.sleep(0.35)


def sync_streaks():
    print("Fetching solving-day history for streak calculation...")
    years = fetch_active_years()
    all_active_days = set()
    for year in years:
        all_active_days |= fetch_active_days_for_year(year)
        time.sleep(0.3)

    current_streak, longest_streak, total_active_days = compute_streaks(all_active_days)
    print(f"Current streak: {current_streak} | Longest streak: {longest_streak} | Total active days: {total_active_days}")

    existing_stats = fetch_existing_stats()
    upsert_stat("Current Streak", current_streak, existing_stats)
    upsert_stat("Longest Streak", longest_streak, existing_stats)
    upsert_stat("Total Active Days", total_active_days, existing_stats)


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
      topicTags {
        name
      }
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
    tags = [{"name": tag["name"]} for tag in question.get("topicTags", [])]

    return {
        "Name": {"title": [{"text": {"content": question["title"]}}]},
        "Difficulty": {"select": {"name": difficulty_label(question["difficulty"])}},
        "LeetCode ID": {"number": int(question["frontendQuestionId"])},
        "Slug": {"rich_text": [{"text": {"content": slug}}]},
        "Status": {"select": {"name": status_to_label(question["status"])}},
        "URL": {"url": url},
        "Tags": {"multi_select": tags},
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

    print("\nStep 4: Syncing streak stats...")
    sync_streaks()
    print("Streak stats updated.")


if __name__ == "__main__":
    main()