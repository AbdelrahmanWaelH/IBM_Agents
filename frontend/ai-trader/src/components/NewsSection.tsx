import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { RefreshCw, ExternalLink, Calendar, Globe } from 'lucide-react';
import type { NewsItem } from '../services/api';

interface NewsSectionProps {
  news: NewsItem[];
  onRefresh: () => void;
}

const NewsSection: React.FC<NewsSectionProps> = ({ news, onRefresh }) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return 'bg-green-100 text-green-800';
      case 'negative':
        return 'bg-red-100 text-red-800';
      case 'neutral':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-blue-100 text-blue-800';
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center">
          <Globe className="h-5 w-5 mr-2" />
          Financial News
        </CardTitle>
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        {news.length === 0 ? (
          <div className="text-center py-8">
            <Globe className="h-12 w-12 mx-auto text-gray-300 mb-4" />
            <p className="text-gray-500">No news available</p>
            <p className="text-sm text-gray-400 mt-2">
              Check your internet connection or try refreshing
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {news.map((item, index) => (
              <div key={index} className="border-b border-gray-100 last:border-b-0 pb-4 last:pb-0">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg leading-tight mb-2 hover:text-blue-600 cursor-pointer">
                      <a 
                        href={item.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="flex items-start"
                      >
                        {item.title}
                        <ExternalLink className="h-4 w-4 ml-1 mt-0.5 flex-shrink-0" />
                      </a>
                    </h3>
                    
                    {item.description && (
                      <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                        {item.description}
                      </p>
                    )}
                    
                    <div className="flex items-center space-x-3 text-xs text-gray-500">
                      <div className="flex items-center">
                        <Calendar className="h-3 w-3 mr-1" />
                        {formatDate(item.published_at)}
                      </div>
                      <div className="flex items-center">
                        <Globe className="h-3 w-3 mr-1" />
                        {item.source}
                      </div>
                    </div>
                  </div>
                  
                  {item.sentiment && (
                    <Badge 
                      variant="outline" 
                      className={`ml-4 ${getSentimentColor(item.sentiment)}`}
                    >
                      {item.sentiment}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default NewsSection;
