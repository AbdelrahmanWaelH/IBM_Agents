import React, { useState, useEffect, useRef } from 'react';
import { Search, Building2, TrendingUp, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { companySearchApi, type Company } from '../services/api';

interface CompanySearchProps {
  onSelectCompany: (symbol: string, companyName: string) => void;
  placeholder?: string;
  value?: string;
  clearOnSelect?: boolean;
}

const CompanySearchComponent: React.FC<CompanySearchProps> = ({
  onSelectCompany,
  placeholder = "Search companies by name or symbol...",
  value = "",
  clearOnSelect = true
}) => {
  const [searchQuery, setSearchQuery] = useState(value);
  const [searchResults, setSearchResults] = useState<Company[]>([]);
  const [popularCompanies, setPopularCompanies] = useState<Company[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadPopularCompanies();
  }, []);

  useEffect(() => {
    setSearchQuery(value);
  }, [value]);

  const loadPopularCompanies = async () => {
    try {
      const data = await companySearchApi.getPopularCompanies();
      setPopularCompanies(data.popular_companies || []);
    } catch (error) {
      console.error('Error loading popular companies:', error);
    }
  };

  const searchCompanies = async (query: string) => {
    if (!query || query.length < 2) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    
    try {
      const data = await companySearchApi.searchCompanies(query, 10);
      setSearchResults(data.results || []);
      setShowResults(true);
      setSelectedIndex(-1);
    } catch (error) {
      console.error('Error searching companies:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);

    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Set new timeout for search
    searchTimeoutRef.current = setTimeout(() => {
      searchCompanies(query);
    }, 300);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showResults) return;

    const resultCount = searchResults.length;
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % resultCount);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev <= 0 ? resultCount - 1 : prev - 1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < resultCount) {
          handleSelectCompany(searchResults[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowResults(false);
        setSelectedIndex(-1);
        break;
    }
  };

  const handleSelectCompany = (company: Company) => {
    onSelectCompany(company.symbol, company.company_name);
    
    if (clearOnSelect) {
      setSearchQuery('');
    } else {
      setSearchQuery(company.symbol);
    }
    
    setShowResults(false);
    setSelectedIndex(-1);
    setSearchResults([]);
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setShowResults(false);
    setSelectedIndex(-1);
    searchInputRef.current?.focus();
  };

  const getSectorColor = (sector: string) => {
    const colors: { [key: string]: string } = {
      'Technology': 'bg-blue-100 text-blue-800',
      'Financial Services': 'bg-green-100 text-green-800',
      'Healthcare': 'bg-red-100 text-red-800',
      'Consumer Cyclical': 'bg-purple-100 text-purple-800',
      'Energy': 'bg-yellow-100 text-yellow-800',
      'Industrials': 'bg-gray-100 text-gray-800',
      'Other': 'bg-indigo-100 text-indigo-800'
    };
    return colors[sector] || colors['Other'];
  };

  const displayResults = searchResults.length > 0 ? searchResults : 
                         (searchQuery.length === 0 ? popularCompanies : []);

  return (
    <div className="relative w-full">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
        <Input
          ref={searchInputRef}
          type="text"
          placeholder={placeholder}
          value={searchQuery}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (searchQuery.length >= 2 && searchResults.length > 0) {
              setShowResults(true);
            } else if (searchQuery.length === 0) {
              setShowResults(true);
            }
          }}
          onBlur={(e) => {
            // Delay hiding results to allow clicking on them
            setTimeout(() => {
              if (!resultsRef.current?.contains(e.relatedTarget as Node)) {
                setShowResults(false);
              }
            }, 150);
          }}
          className="pl-10 pr-10"
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearSearch}
            className="absolute right-1 top-1/2 transform -translate-y-1/2 h-6 w-6 p-0"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>

      {showResults && displayResults.length > 0 && (
        <Card className="absolute top-full left-0 right-0 z-50 mt-1 max-h-96 overflow-y-auto shadow-lg">
          <CardContent className="p-2" ref={resultsRef}>
            {searchQuery.length === 0 && (
              <div className="px-3 py-2 text-sm text-gray-500 border-b">
                Popular Companies
              </div>
            )}
            
            {displayResults.map((company, index) => (
              <div
                key={`${company.symbol}-${index}`}
                className={`p-3 cursor-pointer rounded-lg flex items-center justify-between hover:bg-gray-50 transition-colors ${
                  selectedIndex === index ? 'bg-blue-50 border-blue-200' : ''
                }`}
                onClick={() => handleSelectCompany(company)}
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <Building2 className="h-5 w-5 text-white" />
                    </div>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-gray-900">
                        {company.symbol}
                      </span>
                      <Badge variant="outline" className={getSectorColor(company.sector || '')}>
                        {company.sector || 'N/A'}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600 truncate">
                      {company.company_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      Exchange: {company.exchange || 'N/A'}
                    </p>
                  </div>
                </div>
                
                <TrendingUp className="h-4 w-4 text-gray-400 flex-shrink-0" />
              </div>
            ))}
            
            {isSearching && (
              <div className="p-3 text-center text-gray-500">
                <div className="inline-flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Searching companies...
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default CompanySearchComponent;
