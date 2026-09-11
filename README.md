# LeetSync
LeetSync

Automatically sync your entire LeetCode problem list and your live solved status into a Notion database.

Think of it as your own self-updating "Striver Sheet" style tracker, except it's built by you, pulls real-time data from your LeetCode account, and runs on autopilot in the cloud.

# What it does
1. Pulls every problem on LeetCode (title, difficulty, ID, topic tags, link) using LeetCode's GraphQL API
2. Detects your personal solve status per problem (Solved / Attempted / Not Started) using an authenticated session
3. Pushes everything into a Notion database, creating new entries or updating existing ones (no duplicates on re-run)
4. Tags each problem with its LeetCode topics (Array, Dynamic Programming, Graph, etc.) as a Notion multi-select
5. Calculates your current streak, longest streak, and total active days from your LeetCode submission history, and pushes them into a separate Notion "Stats" database
6. Sends a WhatsApp summary message after every sync (created/updated counts + streak numbers)
7. Skips premium/paid-only problems automatically
8. Runs on a schedule via GitHub Actions, so your Notion tracker stays fresh even when your laptop is off
9. Automatically retries on transient network/API timeouts, so a brief connection hiccup doesn't kill the whole run


# Why I built this

Manually tracking solved LeetCode problems in a spreadsheet or curated sheet (like NeetCode 150 or Striver SDE Sheet) is repetitive and easy to forget. This project automates that: solve problems on LeetCode as normal, and your personal Notion tracker reflects it automatically no manual updates needed.

# Tech Stack
1. Language Python 3
2. APIs LeetCode GraphQL API, Notion API (notion-client), Twilio API (WhatsApp)
3. Auth Environment-based secrets (python-dotenv)
4. Automation GitHub Actions (scheduled cron workflow)
5. Notifications Twilio WhatsApp Sandbox
6. Data store Notion databases (as the frontend/dashboard)

# Notion DashBoard
<img width="1917" height="944" alt="image" src="https://github.com/user-attachments/assets/c54dc455-835f-4724-b1b9-19503dce4ecb" />

# Terminal push all free problem to notion
<img width="1426" height="455" alt="Screenshot 2026-09-10 191226" src="https://github.com/user-attachments/assets/5104543e-5b70-4623-a835-0d7de2b564be" />
<img width="1912" height="720" alt="image" src="https://github.com/user-attachments/assets/608cb924-b39d-4d91-bff6-912045369361" />
<img width="1273" height="934" alt="image" src="https://github.com/user-attachments/assets/69def08e-b996-4c8a-837d-f41ed31ee5e8" />



