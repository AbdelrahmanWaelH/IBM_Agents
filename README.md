# IBM_Agents

BASE PROMPT : -

You’re joining us for a fast-paced hackathon project to build an AI-powered paper trading agent using IBM’s Granite model (granite-13b-instruct-v2). The goal is to simulate intelligent trading decisions based on real-time news analysis and stock market data.

🧠 Project Overview
We will leverage:

IBM Granite LLM + LangChain to process financial news and make buy/sell decisions.

NewsAPI and Yahoo Finance as primary sources of financial news and stock data.

FastAPI for the backend, organized under the app/ directory.

React + TypeScript + Shadcn UI for the frontend, initialized at frontend/ai-trader.

📈 Core Flow
BUY logic (Paper Trading only)

Collect financial news and stock data

Analyze using LangChain + IBM Granite model

Make trade decisions starting from an initial virtual balance

💻 Frontend Guidelines
Use Shadcn for UI components
➤ To add a new component: npx shadcn@latest add <component-name>

Maintain a clean, modern UI with dashboards to display:

Stock prices

Market caps

Current holdings

No need for authentication or user management.

🔌 Backend Notes
Use the environment variables IBM_API_KEY and IBM_BASE_MODEL from .env.

Ensure seamless syncing between backend logic and frontend data views.

🎯 Objective
Maximize the number of profitable decisions (wins) per day in a paper trading simulation. Avoid both over-engineering and oversimplifying – focus on functionality, clear flow, and practical use of AI capabilities.
