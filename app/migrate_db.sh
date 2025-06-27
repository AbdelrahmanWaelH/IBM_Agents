#!/bin/bash

# Database migration script to add missing ai_decision_id column to trades table

echo "🔧 Running database migration..."

# Set database connection details
DB_NAME="ai_trading_agent"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"

# Check if the column exists
COLUMN_EXISTS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "
SELECT EXISTS (
  SELECT FROM information_schema.columns 
  WHERE table_name='trades' AND column_name='ai_decision_id'
);")

if [ "$COLUMN_EXISTS" = "f" ]; then
    echo "📝 Adding ai_decision_id column to trades table..."
    
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME << EOF
-- Add the ai_decision_id column
ALTER TABLE trades ADD COLUMN ai_decision_id INTEGER;

-- Add foreign key constraint
ALTER TABLE trades ADD CONSTRAINT fk_trades_ai_decision 
    FOREIGN KEY (ai_decision_id) REFERENCES ai_decisions(id);

-- Create index for better performance
CREATE INDEX idx_trades_ai_decision_id ON trades(ai_decision_id);

EOF
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully added ai_decision_id column to trades table"
    else
        echo "❌ Failed to add column to trades table"
        exit 1
    fi
else
    echo "✅ ai_decision_id column already exists in trades table"
fi

echo "🎉 Database migration completed successfully!"
