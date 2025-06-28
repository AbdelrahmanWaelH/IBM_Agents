#!/bin/bash

# Migration script to add user_preferences table
echo "Creating user_preferences table..."

# Check if we're using SQLite or PostgreSQL
if [ -f "ai_trading.db" ]; then
    echo "Using SQLite database"
    sqlite3 ai_trading.db << 'EOF'
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    risk_tolerance VARCHAR(20),
    investment_goals TEXT,
    time_horizon VARCHAR(20),
    sectors_of_interest TEXT,
    budget_range VARCHAR(20),
    experience_level VARCHAR(20),
    automated_trading_preference VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
EOF

    echo "✅ user_preferences table created successfully in SQLite"
else
    echo "Database file not found. Run this from the app directory or ensure database is initialized."
fi
