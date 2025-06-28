from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
import logging
from services.company_search_service import company_search_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/search")
async def search_companies(
    query: str = Query(..., description="Company name or partial name to search for"),
    limit: int = Query(10, description="Maximum number of results to return")
):
    """Search for companies by name and get their stock symbols"""
    try:
        if not query or len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
        
        results = await company_search_service.search_companies(query.strip(), limit=limit)
        
        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching companies: {e}")
        raise HTTPException(status_code=500, detail="Company search failed")

@router.get("/popular")
async def get_popular_companies():
    """Get a list of popular companies for quick selection"""
    try:
        popular = company_search_service.get_popular_companies()
        return {
            "popular_companies": popular,
            "total": len(popular)
        }
        
    except Exception as e:
        logger.error(f"Error getting popular companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to get popular companies")

@router.get("/company/{symbol}")
async def get_company_info(symbol: str):
    """Get detailed company information for a specific symbol"""
    try:
        symbol = symbol.upper().strip()
        info = await company_search_service.get_company_details(symbol)
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Company information not found for {symbol}")
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get company information")

@router.post("/cache/refresh")
async def refresh_company_cache():
    """Refresh the company cache with latest data"""
    try:
        await company_search_service.refresh_cache()
        return {"message": "Company cache refreshed successfully"}
        
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh cache")

@router.get("/resolve-symbol")
async def resolve_symbol(
    query: str = Query(..., description="Company name or symbol to resolve"),
    search_type: str = Query("company", description="Type of search: 'symbol' or 'company'")
):
    """Resolve a company name to its stock symbol or validate a symbol"""
    try:
        if not query or len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Query must be at least 2 characters long")
        
        query = query.strip()
        
        if search_type == "symbol":
            # User indicated it's a symbol, just validate and return it
            symbol = query.upper()
            # Verify it's a valid symbol
            if await company_search_service.verify_symbol(symbol):
                return {
                    "query": query,
                    "symbol": symbol,
                    "is_symbol": True,
                    "resolved": True
                }
            else:
                return {
                    "query": query,
                    "symbol": None,
                    "is_symbol": True,
                    "resolved": False,
                    "error": f"Symbol '{symbol}' not found or invalid"
                }
        else:
            # User indicated it's a company name, resolve to symbol
            symbol = await company_search_service.get_symbol_from_name(query)
            
            if symbol:
                return {
                    "query": query,
                    "symbol": symbol,
                    "is_symbol": False,
                    "resolved": True
                }
            else:
                return {
                    "query": query,
                    "symbol": None,
                    "is_symbol": False,
                    "resolved": False,
                    "error": "Could not resolve company name to symbol"
                }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving symbol: {e}")
        raise HTTPException(status_code=500, detail="Symbol resolution failed")
