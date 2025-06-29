import { useState, useCallback } from 'react';

interface AIDecision {
  decision_id: number;
  symbol: string;
  action: string;
  confidence: number;
  quantity: number;
  suggested_price: number;
  reasoning: string;
  timestamp: string;
}

interface TradeExecution {
  trade_id: number;
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  timestamp: string;
  status: string;
}

interface EngineStatus {
  is_running: boolean;
  last_run: string;
  next_run: string;
  run_count: number;
  errors: string[];
}

interface PortfolioUpdate {
  total_value: number;
  cash_balance: number;
  profit_loss: number;
  profit_loss_percent: number;
  holdings: Array<{
    symbol: string;
    quantity: number;
    average_price: number;
    current_price: number;
    market_value: number;
    profit_loss: number;
    profit_loss_percent: number;
  }>;
}

interface TradingData {
  aiDecisions: AIDecision[];
  tradeExecutions: TradeExecution[];
  engineStatus: EngineStatus | null;
  portfolioUpdate: PortfolioUpdate | null;
}

export const useEventDrivenData = () => {
  const [data, setData] = useState<TradingData>({
    aiDecisions: [],
    tradeExecutions: [],
    engineStatus: null,
    portfolioUpdate: null
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAllData = useCallback(async (): Promise<TradingData> => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch all data in parallel
      const [
        recentActivityResponse,
        engineStatusResponse,
        portfolioResponse
      ] = await Promise.all([
        fetch('http://localhost:8001/api/automated-trading/recent-activity').catch(() => null),
        fetch('http://localhost:8001/api/automated-trading/status').catch(() => null),
        fetch('http://localhost:8001/api/portfolio').catch(() => null)
      ]);

      const newData: TradingData = {
        aiDecisions: [],
        tradeExecutions: [],
        engineStatus: null,
        portfolioUpdate: null
      };

      // Process recent activity (contains both decisions and trades)
      if (recentActivityResponse && recentActivityResponse.ok) {
        try {
          const recentActivity = await recentActivityResponse.json();
          newData.aiDecisions = Array.isArray(recentActivity.recent_decisions) ? recentActivity.recent_decisions : [];
          newData.tradeExecutions = Array.isArray(recentActivity.recent_trades_24h) ? recentActivity.recent_trades_24h : [];
        } catch {
          console.warn('Failed to parse recent activity response');
        }
      }

      // Process engine status
      if (engineStatusResponse && engineStatusResponse.ok) {
        try {
          newData.engineStatus = await engineStatusResponse.json();
        } catch {
          console.warn('Failed to parse engine status response');
        }
      }

      // Process portfolio update
      if (portfolioResponse && portfolioResponse.ok) {
        try {
          newData.portfolioUpdate = await portfolioResponse.json();
        } catch {
          console.warn('Failed to parse portfolio response');
        }
      }

      setData(newData);
      return newData;

    } catch (err) {
      console.error('Data fetching error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshData = useCallback(async () => {
    try {
      await fetchAllData();
    } catch (error) {
      console.error('Failed to refresh data:', error);
    }
  }, [fetchAllData]);

  const refreshAfterAction = useCallback(async (actionDescription: string) => {
    console.log(`🔄 Refreshing data after: ${actionDescription}`);
    await refreshData();
  }, [refreshData]);

  return {
    data,
    isLoading,
    error,
    refreshData,
    refreshAfterAction,
    fetchAllData
  };
};
