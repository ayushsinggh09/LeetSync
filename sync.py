import os
import time
import json
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from notion_client import Client
from twilio.rest import Client as TwilioClient

load_dotenv()

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
LEETCODE_SESSION = os.environ["LEETCODE_SESSION"]
LEETCODE_CSRF_TOKEN = os.environ["LEETCODE_CSRF_TOKEN"]
DATA_SOURCE_ID = "7548daa2-2d83-4e9b-ae5b-7bc9f4110b04"
STATS_DATA_SOURCE_ID = "2bfaae3d-ca1d-4511-af67-974b4198d6ab"
LEETCODE_USERNAME = "ayushsinggh09"  

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_WHATSAPP_FROM = os.environ["TWILIO_WHATSAPP_FROM"]
TWILIO_WHATSAPP_TO = os.environ["TWILIO_WHATSAPP_TO"]

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
        notion_request_with_retry(
            notion.pages.update,
            page_id=existing_stats[metric_name],
            properties=properties,
        )
    else:
        notion_request_with_retry(
            notion.pages.create,
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

    return current_streak, longest_streak, total_active_days


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
    """Build a map of {leetcode_id: {"page_id": ..., "status": ...}} for problems already in Notion."""
    existing = {}
    cursor = None

    while True:
        query_args = {"data_source_id": DATA_SOURCE_ID, "page_size": 100}
        if cursor:
            query_args["start_cursor"] = cursor

        response = notion.data_sources.query(**query_args)

        for page in response["results"]:
            id_prop = page["properties"].get("LeetCode ID", {})
            leetcode_id = id_prop.get("number")
            status_prop = page["properties"].get("Status", {}).get("select")
            old_status = status_prop["name"] if status_prop else None
            if leetcode_id is not None:
                existing[leetcode_id] = {"page_id": page["id"], "status": old_status}

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
    # LeetCode returns difficulty as an integer 1=Easy 2=Medium 3=Hard
    return {1: "Easy", 2: "Medium", 3: "Hard"}.get(diff, str(diff))


def build_properties(question):
    slug = question["titleSlug"]
    url = f"https://leetcode.com/problems/{slug}/"
    tags = [{"name": tag["name"]} for tag in question.get("topicTags", [])]

    return {
        "Name": {"title": [{"text": {"content": question["title"]}}]},
        "Difficulty": {"select": {"name": difficulty_label(question["difficulty"])}},
        "LeetCode ID": {"number": int(question["frontendQuestionId"])},
        "Status": {"select": {"name": status_to_label(question["status"])}},
        "URL": {"url": url},
        "Tags": {"multi_select": tags},
    }


def send_whatsapp_notification(message):
    try:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=TWILIO_WHATSAPP_TO,
            body=message,
        )
        print("WhatsApp notification sent.")
    except Exception as e:
        print(f"WhatsApp notification failed (sync itself still succeeded): {e}")


RECENT_AC_QUERY = """
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    title
    titleSlug
    timestamp
  }
}
"""

QUESTION_ID_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
  }
}
"""


def fetch_recent_ac_submissions(limit=20):
    payload = {
        "query": RECENT_AC_QUERY,
        "variables": {"username": LEETCODE_USERNAME, "limit": limit},
    }
    resp = requests.post(LEETCODE_GRAPHQL_URL, json=payload, headers=LEETCODE_HEADERS)
    resp.raise_for_status()
    return resp.json()["data"]["recentAcSubmissionList"]


def fetch_question_id(title_slug):
    payload = {"query": QUESTION_ID_QUERY, "variables": {"titleSlug": title_slug}}
    resp = requests.post(LEETCODE_GRAPHQL_URL, json=payload, headers=LEETCODE_HEADERS)
    resp.raise_for_status()
    return int(resp.json()["data"]["question"]["questionFrontendId"])


def get_stat_value(metric_name, default=0):
    response = notion.data_sources.query(
        data_source_id=STATS_DATA_SOURCE_ID,
        filter={"property": "Metric", "title": {"equals": metric_name}},
    )
    results = response.get("results", [])
    if results:
        return results[0]["properties"].get("Value", {}).get("number", default)
    return default


def find_page_by_leetcode_id(leetcode_id):
    response = notion.data_sources.query(
        data_source_id=DATA_SOURCE_ID,
        filter={"property": "LeetCode ID", "number": {"equals": leetcode_id}},
    )
    results = response.get("results", [])
    return results[0]["id"] if results else None


def quick_check():
    """Fast check: looks only at your most recent accepted submissions, updates those
    specific rows in Notion, and notifies immediately. Meant to run every few minutes."""
    print("Running quick real-time check...")
    submissions = fetch_recent_ac_submissions(limit=20)
    last_notified = get_stat_value("Last Notified Timestamp", default=0)

    new_subs = [s for s in submissions if int(s["timestamp"]) > last_notified]
    if not new_subs:
        print("No new submissions since last check.")
        return

    new_subs.sort(key=lambda s: int(s["timestamp"]))  # oldest first

    notified_titles = []
    max_timestamp = last_notified

    for sub in new_subs:
        title = sub["title"]
        timestamp = int(sub["timestamp"])
        max_timestamp = max(max_timestamp, timestamp)

        try:
            leetcode_id = fetch_question_id(sub["titleSlug"])
            page_id = find_page_by_leetcode_id(leetcode_id)
            if page_id:
                notion_request_with_retry(
                    notion.pages.update,
                    page_id=page_id,
                    properties={"Status": {"select": {"name": "Solved"}}},
                )
        except Exception as e:
            print(f"  Could not update Notion for {title}: {e}")

        notified_titles.append(title)
        time.sleep(0.4)

    existing_stats = fetch_existing_stats()
    upsert_stat("Last Notified Timestamp", max_timestamp, existing_stats)

    message = "Just solved on LeetCode:\n" + "\n".join(f"- {t}" for t in notified_titles)
    send_whatsapp_notification(message)
    print(f"Notified about {len(notified_titles)} new solve(s).")


def notion_request_with_retry(func, max_retries=5, **kwargs):
    """Call a notion-client function, retrying on transient network/timeout errors."""
    for attempt in range(1, max_retries + 1):
        try:
            return func(**kwargs)
        except Exception as e:
            if attempt == max_retries:
                raise
            wait = min(5 * attempt, 30)
            print(f"  Notion request failed ({e}), retrying in {wait}s... (attempt {attempt}/{max_retries})")
            time.sleep(wait)


def main():
    print("Step 1: Fetching problems from LeetCode...")
    problems = fetch_all_leetcode_problems()
    print(f"Total problems fetched: {len(problems)}\n")

    print("Step 2: Fetching existing Notion pages...")
    existing_pages = fetch_existing_notion_pages()
    print(f"Existing pages already in Notion: {len(existing_pages)}\n")

    print("Step 3: Syncing to Notion...")
    created, updated, skipped_paid, total_solved = 0, 0, 0, 0
    newly_solved = []

    for i, question in enumerate(problems, start=1):
        if question["paidOnly"]:
            skipped_paid += 1
            continue

        leetcode_id = int(question["frontendQuestionId"])
        properties = build_properties(question)
        new_status = status_to_label(question["status"])

        if new_status == "Solved":
            total_solved += 1

        existing_entry = existing_pages.get(leetcode_id)

        if existing_entry:
            old_status = existing_entry["status"]
            if old_status != "Solved" and new_status == "Solved":
                newly_solved.append(question["title"])

            notion_request_with_retry(
                notion.pages.update,
                page_id=existing_entry["page_id"],
                properties=properties,
            )
            updated += 1
        else:
            notion_request_with_retry(
                notion.pages.create,
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
    print(f"Total solved: {total_solved}")
    if newly_solved:
        print(f"Newly solved this run: {', '.join(newly_solved)}")

    print("\nStep 4: Syncing streak stats...")
    current_streak, longest_streak, total_active_days = sync_streaks()
    existing_stats = fetch_existing_stats()
    upsert_stat("Total Solved", total_solved, existing_stats)
    print("Streak stats updated.")

    print("\nStep 5: Sending WhatsApp notification...")

    if newly_solved:
        solved_lines = "\n".join(f"- {name}" for name in newly_solved[:15])
        more_note = f"\n(+{len(newly_solved) - 15} more)" if len(newly_solved) > 15 else ""
        solved_section = f"\n\nJust solved:\n{solved_lines}{more_note}"
    else:
        solved_section = ""

    summary_message = (
        "LeetSync update:\n"
        f"Created: {created} | Updated: {updated}\n"
        f"Total solved: {total_solved}\n"
        f"Current streak: {current_streak} days\n"
        f"Longest streak: {longest_streak} days\n"
        f"Total active days: {total_active_days}"
        f"{solved_section}"
    )
    send_whatsapp_notification(summary_message)


def check_and_send_reminder():
    """Lightweight check (no full sync) — reminds you via WhatsApp if you haven't solved anything today yet."""
    print("Checking today's LeetCode activity for reminder...")
    year = datetime.utcnow().year
    active_days = fetch_active_days_for_year(year)
    today = datetime.utcnow().date()

    if today in active_days:
        print("Already solved something today - no reminder needed.")
        return

    print("No activity today yet - sending reminder.")
    message = (
        "Reminder: you haven't solved a LeetCode problem today yet.\n"
        "Solve at least one to keep your streak going!"
    )
    send_whatsapp_notification(message)


if __name__ == "__main__":
    import sys

    if "--remind" in sys.argv:
        check_and_send_reminder()
    elif "--quick-check" in sys.argv:
        quick_check()
    else:
        main()