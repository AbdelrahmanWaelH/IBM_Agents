#!/bin/bash

# PostgreSQL Database Setup Script for AI Trading Agent

echo "🗄️  Setting up PostgreSQL database..."

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install it first."
    echo "Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    echo "macOS: brew install postgresql"
    exit 1
fi

# Check if PostgreSQL service is running
if ! brew services list | grep -q "^postgresql.*started"; then
    echo "🔄 Starting PostgreSQL service..."
    brew services start postgresql
fi


# Create database and user
echo "📊 Creating database and user..."
psql -U $(whoami) -d postgres <<EOF
-- Create database
DROP DATABASE IF EXISTS ai_trading_agent;
CREATE DATABASE ai_trading_agent;

-- Create user (if not exists)
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ai_trader') THEN
        CREATE USER ai_trader WITH PASSWORD 'trading123';
    END IF;
END
\$\$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ai_trading_agent TO ai_trader;
ALTER USER ai_trader CREATEDB;

-- Connect to the database and grant schema privileges
\c ai_trading_agent;
GRANT ALL ON SCHEMA public TO ai_trader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ai_trader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ai_trader;

EOF

echo "✅ Database setup complete!"
echo "📝 Database details:"
echo "   - Database: ai_trading_agent"
echo "   - User: ai_trader"
echo "   - Password: trading123"
echo "   - Host: localhost"
echo "   - Port: 5432"
