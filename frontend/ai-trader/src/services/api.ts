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
