# LeetSync
Automatically sync your entire LeetCode problem list and your live solved status into a Notion database. Now with topic tags a solving-streak tracker real time solve notifications and a daily reminder all via email.

Think of it as your own self-updating "Striver Sheet" style tracker except it's built by you pulls real-time data from your LeetCode account and runs on autopilot in the cloud.

# What it does
1. Pulls every problem on LeetCode (title, difficulty, ID, topic tags, link) using LeetCode's GraphQL API
2. Detects your personal solve status per problem (Solved / Attempted / Not Started) using an authenticated session
3. Pushes everything into a Notion database, creating new entries or updating existing ones (no duplicates on re-run)
4. Tags each problem with its LeetCode topics (Array, Dynamic Programming, Graph, etc.) as a Notion multi-select
5. Calculates your current streak, longest streak, and total active days from your LeetCode submission history, and pushes them into a separate Notion "Stats" database
6. Sends an email the moment you solve a new problem (checked every 10 minutes), so it feels near real-time
   Sends a daily reminder email at 6 PM if you haven't solved anything that day yet
   Sends a full sync summary email every hour
7. Skips premium/paid-only problems automatically
8. Runs on a schedule via GitHub Actions, so your Notion tracker stays fresh even when your laptop is off
9. Automatically retries on transient network/API timeouts, so a brief connection hiccup doesn't kill the whole run

# Block Diagram    
<img width="2720" height="2176" alt="leetsync_architecture_diagram" src="https://github.com/user-attachments/assets/8cf8481c-fe60-4c58-a4ce-3a14c0ea4e1d" />

# Why I built this

Manually tracking solved LeetCode problems in a spreadsheet or curated sheet (like NeetCode 150 or Striver SDE Sheet) is repetitive and easy to forget. This project automates that: solve problems on LeetCode as normal, and your personal Notion tracker reflects it automatically no manual updates needed.

# Tech Stack
1. Language Python 3
2. APIs LeetCode GraphQL API, Notion API (notion-client), Twilio API (WhatsApp)
3. Auth Environment-based secrets (python-dotenv)
4. Automation GitHub Actions (scheduled cron workflow)
5. Notifications Email via Gmail SMTP
6. Data store Notion databases (as the frontend/dashboard)

# TimeZone 
1. 0 * * * * → every hour
2. */10 * * * * → every 10 minutes
3. 30 12 * * * → daily at 12:30 UTC (6:00 PM IST)

# Notion DashBoard
<img width="1908" height="926" alt="image" src="https://github.com/user-attachments/assets/ba1bbfa9-f589-4db5-a41f-670c796aa573" />


# Terminal push all free problem push to notion
<img width="1426" height="455" alt="Screenshot 2026-09-10 191226" src="https://github.com/user-attachments/assets/5104543e-5b70-4623-a835-0d7de2b564be" />
<img width="1912" height="720" alt="image" src="https://github.com/user-attachments/assets/608cb924-b39d-4d91-bff6-912045369361" />



