import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface StockInfo {
  symbol: string;
  current_price: number;
  market_cap?: number;
  volume?: number;
  change_percent?: number;
}

export interface NewsItem {
  title: string;
  description: string;
  url: string;
  published_at: string;
  source: string;
  sentiment?: string;
}

export interface TradeDecision {
  symbol: string;
  action: 'buy' | 'sell' | 'hold';
  quantity: number;
  confidence: number;
  reasoning: string;
  suggested_price: number;
  decision_id?: number;
}

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  holdings: Array<{
    symbol: string;
    quantity: number;
    avg_price: number;
    current_price: number;
    value: number;
    profit_loss: number;
  }>;
  profit_loss: number;
  profit_loss_percent: number;
}

export interface TradeOrder {
  symbol: string;
  action: 'buy' | 'sell';
  quantity: number;
  price?: number;
  decision_id?: number;
}

export interface TradeExecutionResponse {
  message: string;
  symbol: string;
  action: string;
  quantity: number;
  price: number;
}

export interface TradeHistoryItem {
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  timestamp: string;
}

export interface ResetResponse {
  message: string;
}

// Trading API
export const tradingApi = {
  getStock: async (symbol: string): Promise<StockInfo> => {
    const response = await api.get(`/trading/stocks/${symbol}`);
    return response.data;
  },

  getMultipleStocks: async (symbols: string[]): Promise<StockInfo[]> => {
    const response = await api.get(`/trading/stocks?symbols=${symbols.join(',')}`);
    return response.data;
  },

  analyzeStock: async (symbol: string): Promise<TradeDecision> => {
    const response = await api.post(`/trading/analyze/${symbol}`);
    return response.data;
  },

  executeTrade: async (order: TradeOrder): Promise<TradeExecutionResponse> => {
    const response = await api.post('/trading/execute', order);
    return response.data;
  },
};

// Analytics interfaces
export interface AIDecision {
  id: number;
  symbol: string;
  action: string;
  confidence: number;
  reasoning: string;
  suggested_price: number;
  was_executed: boolean;
  created_at: string;
}

export interface NewsAnalysis {
  symbol: string;
  title: string;
  description: string;
  url: string;
  source: string;
  sentiment: string;
  published_at: string;
  analyzed_at: string;
}

export interface StockAnalysis {
  symbol: string;
  current_price: number;
  market_cap: number;
  volume: number;
  change_percent: number;
  analyzed_at: string;
}

export interface PortfolioPerformance {
  portfolio_value: number;
  cash_balance: number;
  total_trades: number;
  buy_trades: number;
  sell_trades: number;
  win_rate: number;
  holdings_count: number;
  holdings: Array<{
    symbol: string;
    quantity: number;
    average_price: number;
    current_value: number;
  }>;
}

export interface SentimentSummary {
  total_news_items: number;
  sentiment_distribution: {
    positive: number;
    negative: number;
    neutral: number;
  };
  sentiment_percentages: {
    positive: number;
    negative: number;
    neutral: number;
  };
  days_analyzed: number;
  symbol: string;
}

export interface TradingInsights {
  total_decisions: number;
  action_distribution: {
    buy: number;
    sell: number;
    hold: number;
  };
  average_confidence: number;
  execution_rate: number;
  most_recommended_action: string;
}

// Analytics API
export const analyticsApi = {
  getAIDecisions: async (symbol?: string, limit = 50, days?: number): Promise<AIDecision[]> => {
    const params = new URLSearchParams();
    if (symbol) params.append('symbol', symbol);
    params.append('limit', limit.toString());
    if (days) params.append('days', days.toString());
    
    const response = await api.get(`/analytics/ai-decisions?${params}`);
    return response.data;
  },

  getNewsAnalysis: async (symbol?: string, limit = 50): Promise<NewsAnalysis[]> => {
    const params = new URLSearchParams();
    if (symbol) params.append('symbol', symbol);
    params.append('limit', limit.toString());
    
    const response = await api.get(`/analytics/news-analysis?${params}`);
    return response.data;
  },

  getStockAnalysis: async (symbol?: string, limit = 50): Promise<StockAnalysis[]> => {
    const params = new URLSearchParams();
    if (symbol) params.append('symbol', symbol);
    params.append('limit', limit.toString());
    
    const response = await api.get(`/analytics/stock-analysis?${params}`);
    return response.data;
  },

  getPortfolioPerformance: async (): Promise<PortfolioPerformance> => {
    const response = await api.get('/analytics/portfolio-performance');
    return response.data;
  },

  getSentimentSummary: async (symbol?: string, days = 7): Promise<SentimentSummary> => {
    const params = new URLSearchParams();
    if (symbol) params.append('symbol', symbol);
    params.append('days', days.toString());
    
    const response = await api.get(`/analytics/sentiment-summary?${params}`);
    return response.data;
  },

  getTradingInsights: async (): Promise<TradingInsights> => {
    const response = await api.get('/analytics/trading-insights');
    return response.data;
  },

  markDecisionExecuted: async (decisionId: number): Promise<{ message: string }> => {
    const response = await api.post(`/analytics/mark-executed/${decisionId}`);
    return response.data;
  },
};

// News API
export const newsApi = {
  getFinancialNews: async (limit = 10): Promise<NewsItem[]> => {
    const response = await api.get(`/news/?limit=${limit}`);
    return response.data;
  },

  getStockNews: async (symbol: string, limit = 5): Promise<NewsItem[]> => {
    const response = await api.get(`/news/stock/${symbol}?limit=${limit}`);
    return response.data;
  },

  searchNews: async (query: string, limit = 10): Promise<NewsItem[]> => {
    const response = await api.get(`/news/search?query=${query}&limit=${limit}`);
    return response.data;
  },
};

// Portfolio API
export const portfolioApi = {
  getPortfolio: async (): Promise<Portfolio> => {
    const response = await api.get('/portfolio/');
    return response.data;
  },

  getTradeHistory: async (): Promise<TradeHistoryItem[]> => {
    const response = await api.get('/portfolio/history');
    return response.data;
  },

  resetPortfolio: async (): Promise<ResetResponse> => {
    const response = await api.post('/portfolio/reset');
    return response.data;
  },
};
