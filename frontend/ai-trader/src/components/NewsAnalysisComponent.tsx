import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { analyticsApi, type NewsAnalysis } from '@/services/api';
import { Newspaper, ExternalLink, Calendar, TrendingUp, TrendingDown, Minus } from 'lucide-react';

const NewsAnalysisComponent: React.FC = () => {
  const [newsData, setNewsData] = useState<NewsAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadNewsAnalysis();
  }, []);

  const loadNewsAnalysis = async (symbol?: string) => {
    try {
      setLoading(true);
      const data = await analyticsApi.getNewsAnalysis(symbol, 100);
      setNewsData(data);
    } catch (error) {
      console.error('Error loading news analysis:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadNewsAnalysis(searchSymbol || undefined);
  };

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'negative': return <TrendingDown className="h-4 w-4 text-red-500" />;
      default: return <Minus className="h-4 w-4 text-yellow-500" />;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return 'bg-green-100 text-green-800 border-green-200';
      case 'negative': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    }
  };

  const filteredNews = newsData.filter(item => {
    if (filter === 'all') return true;
    return item.sentiment?.toLowerCase() === filter;
  });

  const sentimentCounts = newsData.reduce((acc, item) => {
    const sentiment = item.sentiment?.toLowerCase() || 'neutral';
    acc[sentiment] = (acc[sentiment] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Newspaper className="h-6 w-6 text-blue-600" />
          <h2 className="text-2xl font-bold">News Analysis</h2>
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="Filter by symbol..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="w-48"
          />
          <Button onClick={handleSearch} variant="outline">
            Search
          </Button>
        </div>
      </div>

      {/* Sentiment Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Articles</CardTitle>
            <Newspaper className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{newsData.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Positive</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {sentimentCounts.positive || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Negative</CardTitle>
            <TrendingDown className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {sentimentCounts.negative || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Neutral</CardTitle>
            <Minus className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {sentimentCounts.neutral || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter Buttons */}
      <div className="flex gap-2">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          onClick={() => setFilter('all')}
        >
          All
        </Button>
        <Button
          variant={filter === 'positive' ? 'default' : 'outline'}
          onClick={() => setFilter('positive')}
        >
          Positive
        </Button>
        <Button
          variant={filter === 'negative' ? 'default' : 'outline'}
          onClick={() => setFilter('negative')}
        >
          Negative
        </Button>
        <Button
          variant={filter === 'neutral' ? 'default' : 'outline'}
          onClick={() => setFilter('neutral')}
        >
          Neutral
        </Button>
      </div>

      {/* News List */}
      <Card>
        <CardHeader>
          <CardTitle>News Articles with Sentiment Analysis</CardTitle>
          <CardDescription>
            AI-analyzed news articles with sentiment scoring
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredNews.map((item, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="font-mono">
                        {item.symbol}
                      </Badge>
                      <Badge className={getSentimentColor(item.sentiment)}>
                        {getSentimentIcon(item.sentiment)}
                        <span className="ml-1 capitalize">{item.sentiment}</span>
                      </Badge>
                      <span className="text-sm text-gray-500">{item.source}</span>
                    </div>
                    <h3 className="font-semibold text-lg leading-tight">
                      {item.title}
                    </h3>
                    <p className="text-gray-600 text-sm">
                      {item.description}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => window.open(item.url, '_blank')}
                    className="flex-shrink-0"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-400">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Published: {new Date(item.published_at).toLocaleString()}
                  </div>
                  <div>
                    Analyzed: {new Date(item.analyzed_at).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
            {filteredNews.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                No news articles found matching the current filter.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default NewsAnalysisComponent;
