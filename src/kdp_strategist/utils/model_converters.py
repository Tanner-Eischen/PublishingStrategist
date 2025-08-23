"""Model conversion utilities for different output formats.

This module provides utilities to convert Keepa product data models
to various output formats including CSV, JSON, XML, and API responses.
"""

import csv
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, TextIO
from io import StringIO

from ..models.keepa_product_models import (
    EnhancedProductData,
    PriceHistoryData,
    CompetitionLevel
)


class ProductDataConverter:
    """Converter for product data to various formats."""
    
    @staticmethod
    def to_csv_string(products: List[EnhancedProductData], 
                     include_headers: bool = True) -> str:
        """Convert list of products to CSV string.
        
        Args:
            products: List of product data objects
            include_headers: Whether to include CSV headers
            
        Returns:
            CSV formatted string
        """
        if not products:
            return ""
        
        output = StringIO()
        
        # Get field names from first product
        fieldnames = list(products[0].to_csv_row().keys())
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        if include_headers:
            writer.writeheader()
        
        for product in products:
            writer.writerow(product.to_csv_row())
        
        return output.getvalue()
    
    @staticmethod
    def to_csv_file(products: List[EnhancedProductData], 
                   filename: str,
                   include_headers: bool = True) -> None:
        """Write products to CSV file.
        
        Args:
            products: List of product data objects
            filename: Output filename
            include_headers: Whether to include CSV headers
        """
        if not products:
            return
        
        fieldnames = list(products[0].to_csv_row().keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if include_headers:
                writer.writeheader()
            
            for product in products:
                writer.writerow(product.to_csv_row())
    
    @staticmethod
    def to_json_string(products: List[EnhancedProductData], 
                      indent: Optional[int] = None,
                      format_type: str = "enhanced") -> str:
        """Convert products to JSON string.
        
        Args:
            products: List of product data objects
            indent: JSON indentation (None for compact)
            format_type: "enhanced", "legacy", or "minimal"
            
        Returns:
            JSON formatted string
        """
        if format_type == "enhanced":
            data = [product.to_dict() for product in products]
        elif format_type == "legacy":
            data = [product.to_legacy_format() for product in products]
        elif format_type == "minimal":
            data = [ProductDataConverter._to_minimal_dict(product) for product in products]
        else:
            raise ValueError(f"Unknown format_type: {format_type}")
        
        return json.dumps(data, indent=indent, default=str)
    
    @staticmethod
    def to_json_file(products: List[EnhancedProductData], 
                    filename: str,
                    indent: Optional[int] = 2,
                    format_type: str = "enhanced") -> None:
        """Write products to JSON file.
        
        Args:
            products: List of product data objects
            filename: Output filename
            indent: JSON indentation
            format_type: "enhanced", "legacy", or "minimal"
        """
        json_string = ProductDataConverter.to_json_string(
            products, indent=indent, format_type=format_type
        )
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            jsonfile.write(json_string)
    
    @staticmethod
    def to_xml_string(products: List[EnhancedProductData]) -> str:
        """Convert products to XML string.
        
        Args:
            products: List of product data objects
            
        Returns:
            XML formatted string
        """
        root = ET.Element("products")
        
        for product in products:
            product_elem = ET.SubElement(root, "product")
            ProductDataConverter._add_product_to_xml(product_elem, product)
        
        return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def to_xml_file(products: List[EnhancedProductData], filename: str) -> None:
        """Write products to XML file.
        
        Args:
            products: List of product data objects
            filename: Output filename
        """
        root = ET.Element("products")
        
        for product in products:
            product_elem = ET.SubElement(root, "product")
            ProductDataConverter._add_product_to_xml(product_elem, product)
        
        tree = ET.ElementTree(root)
        tree.write(filename, encoding='utf-8', xml_declaration=True)
    
    @staticmethod
    def to_api_response(products: List[EnhancedProductData],
                       total_count: Optional[int] = None,
                       page: int = 1,
                       per_page: int = 20,
                       include_metadata: bool = True) -> Dict[str, Any]:
        """Convert products to API response format.
        
        Args:
            products: List of product data objects
            total_count: Total number of products (for pagination)
            page: Current page number
            per_page: Products per page
            include_metadata: Whether to include response metadata
            
        Returns:
            API response dictionary
        """
        response = {
            "products": [product.to_dict() for product in products],
            "count": len(products)
        }
        
        if include_metadata:
            response["metadata"] = {
                "page": page,
                "per_page": per_page,
                "total_count": total_count or len(products),
                "generated_at": datetime.now().isoformat(),
                "format_version": "1.0"
            }
            
            # Add pagination info if applicable
            if total_count:
                total_pages = (total_count + per_page - 1) // per_page
                response["metadata"]["total_pages"] = total_pages
                response["metadata"]["has_next"] = page < total_pages
                response["metadata"]["has_prev"] = page > 1
        
        return response
    
    @staticmethod
    def to_summary_report(products: List[EnhancedProductData]) -> Dict[str, Any]:
        """Generate summary report from products.
        
        Args:
            products: List of product data objects
            
        Returns:
            Summary report dictionary
        """
        if not products:
            return {
                "total_products": 0,
                "summary": "No products to analyze"
            }
        
        # Calculate summary statistics
        prices = [p.current_price for p in products if p.current_price]
        bsrs = [p.bsr_current for p in products if p.bsr_current]
        ratings = [p.review_data.rating for p in products if p.review_data.rating]
        review_counts = [p.review_data.review_count for p in products]
        sales = [p.sales_estimate.monthly_sales for p in products]
        
        # Competition level distribution
        competition_levels = [p.get_competition_level() for p in products]
        competition_dist = {
            level.value: competition_levels.count(level) 
            for level in CompetitionLevel
        }
        
        # Category distribution
        categories = [p.get_category_path() for p in products if p.get_category_path()]
        category_dist = {}
        for category in categories:
            category_dist[category] = category_dist.get(category, 0) + 1
        
        # Top categories (limit to top 10)
        top_categories = sorted(category_dist.items(), key=lambda x: x[1], reverse=True)[:10]
        
        summary = {
            "total_products": len(products),
            "price_statistics": {
                "count": len(prices),
                "average": sum(prices) / len(prices) if prices else 0,
                "min": min(prices) if prices else 0,
                "max": max(prices) if prices else 0
            },
            "bsr_statistics": {
                "count": len(bsrs),
                "average": sum(bsrs) / len(bsrs) if bsrs else 0,
                "min": min(bsrs) if bsrs else 0,
                "max": max(bsrs) if bsrs else 0
            },
            "rating_statistics": {
                "count": len(ratings),
                "average": sum(ratings) / len(ratings) if ratings else 0,
                "min": min(ratings) if ratings else 0,
                "max": max(ratings) if ratings else 0
            },
            "review_statistics": {
                "total_reviews": sum(review_counts),
                "average_per_product": sum(review_counts) / len(review_counts) if review_counts else 0,
                "min": min(review_counts) if review_counts else 0,
                "max": max(review_counts) if review_counts else 0
            },
            "sales_statistics": {
                "total_monthly_sales": sum(sales),
                "average_per_product": sum(sales) / len(sales) if sales else 0,
                "min": min(sales) if sales else 0,
                "max": max(sales) if sales else 0
            },
            "competition_distribution": competition_dist,
            "top_categories": dict(top_categories),
            "data_quality": {
                "average_score": sum(p.data_quality.overall_score for p in products) / len(products),
                "products_with_errors": len([p for p in products if p.data_quality.validation_errors])
            },
            "generated_at": datetime.now().isoformat()
        }
        
        return summary
    
    @staticmethod
    def _to_minimal_dict(product: EnhancedProductData) -> Dict[str, Any]:
        """Convert product to minimal dictionary format.
        
        Args:
            product: Product data object
            
        Returns:
            Minimal dictionary with essential fields only
        """
        return {
            "asin": product.asin,
            "title": product.title,
            "brand": product.brand,
            "price": product.current_price,
            "bsr": product.bsr_current,
            "rating": product.review_data.rating,
            "reviews": product.review_data.review_count,
            "monthly_sales": product.sales_estimate.monthly_sales,
            "competition": product.get_competition_level().value,
            "category": product.get_category_path()
        }
    
    @staticmethod
    def _add_product_to_xml(parent: ET.Element, product: EnhancedProductData) -> None:
        """Add product data to XML element.
        
        Args:
            parent: Parent XML element
            product: Product data object
        """
        # Basic info
        ET.SubElement(parent, "asin").text = product.asin
        ET.SubElement(parent, "title").text = product.title
        if product.brand:
            ET.SubElement(parent, "brand").text = product.brand
        
        # Pricing
        if product.current_price:
            ET.SubElement(parent, "current_price").text = str(product.current_price)
        
        # Sales rank
        if product.bsr_current:
            ET.SubElement(parent, "bsr_current").text = str(product.bsr_current)
        
        # Reviews
        reviews_elem = ET.SubElement(parent, "reviews")
        ET.SubElement(reviews_elem, "count").text = str(product.review_data.review_count)
        if product.review_data.rating:
            ET.SubElement(reviews_elem, "rating").text = str(product.review_data.rating)
        
        # Sales estimate
        sales_elem = ET.SubElement(parent, "sales_estimate")
        ET.SubElement(sales_elem, "monthly_sales").text = str(product.sales_estimate.monthly_sales)
        
        # Competition
        ET.SubElement(parent, "competition_level").text = product.get_competition_level().value
        
        # Category
        category_path = product.get_category_path()
        if category_path:
            ET.SubElement(parent, "category_path").text = category_path
        
        # Data quality
        quality_elem = ET.SubElement(parent, "data_quality")
        ET.SubElement(quality_elem, "score").text = str(product.data_quality.overall_score)
        
        # Metadata
        ET.SubElement(parent, "last_updated").text = product.last_updated.isoformat()


class PriceHistoryConverter:
    """Converter for price history data to various formats."""
    
    @staticmethod
    def to_csv_string(price_history: PriceHistoryData, 
                     include_headers: bool = True) -> str:
        """Convert price history to CSV string.
        
        Args:
            price_history: Price history data object
            include_headers: Whether to include CSV headers
            
        Returns:
            CSV formatted string
        """
        output = StringIO()
        
        fieldnames = ["timestamp", "price", "price_type"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        if include_headers:
            writer.writeheader()
        
        for point in price_history.price_points:
            writer.writerow({
                "timestamp": point.timestamp.isoformat(),
                "price": point.price,
                "price_type": point.price_type.value
            })
        
        return output.getvalue()
    
    @staticmethod
    def to_chart_data(price_history: PriceHistoryData) -> Dict[str, Any]:
        """Convert price history to chart-friendly format.
        
        Args:
            price_history: Price history data object
            
        Returns:
            Chart data dictionary
        """
        return {
            "asin": price_history.asin,
            "price_type": price_history.price_type.value,
            "data_points": [
                {
                    "x": point.timestamp.isoformat(),
                    "y": point.price
                }
                for point in price_history.price_points
            ],
            "statistics": price_history.statistics.to_dict(),
            "metadata": {
                "time_period_days": price_history.time_period_days,
                "total_points": len(price_history.price_points),
                "last_updated": price_history.last_updated.isoformat()
            }
        }
    
    @staticmethod
    def to_time_series(price_history: PriceHistoryData) -> Dict[str, List]:
        """Convert price history to time series format.
        
        Args:
            price_history: Price history data object
            
        Returns:
            Time series dictionary with separate timestamp and price arrays
        """
        timestamps = [point.timestamp.isoformat() for point in price_history.price_points]
        prices = [point.price for point in price_history.price_points]
        
        return {
            "timestamps": timestamps,
            "prices": prices,
            "asin": price_history.asin,
            "price_type": price_history.price_type.value
        }


class BatchConverter:
    """Batch converter for processing multiple products efficiently."""
    
    @staticmethod
    def convert_batch_to_format(products: List[EnhancedProductData],
                              output_format: str,
                              output_file: Optional[str] = None,
                              **kwargs) -> Union[str, Dict[str, Any]]:
        """Convert batch of products to specified format.
        
        Args:
            products: List of product data objects
            output_format: Target format ("csv", "json", "xml", "api", "summary")
            output_file: Optional output filename
            **kwargs: Additional format-specific arguments
            
        Returns:
            Converted data (string or dict) or None if written to file
        """
        if output_format.lower() == "csv":
            if output_file:
                ProductDataConverter.to_csv_file(products, output_file, **kwargs)
                return None
            else:
                return ProductDataConverter.to_csv_string(products, **kwargs)
        
        elif output_format.lower() == "json":
            if output_file:
                ProductDataConverter.to_json_file(products, output_file, **kwargs)
                return None
            else:
                return ProductDataConverter.to_json_string(products, **kwargs)
        
        elif output_format.lower() == "xml":
            if output_file:
                ProductDataConverter.to_xml_file(products, output_file)
                return None
            else:
                return ProductDataConverter.to_xml_string(products)
        
        elif output_format.lower() == "api":
            return ProductDataConverter.to_api_response(products, **kwargs)
        
        elif output_format.lower() == "summary":
            return ProductDataConverter.to_summary_report(products)
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    @staticmethod
    def convert_with_filtering(products: List[EnhancedProductData],
                             output_format: str,
                             filters: Optional[Dict[str, Any]] = None,
                             **kwargs) -> Union[str, Dict[str, Any]]:
        """Convert products with filtering applied.
        
        Args:
            products: List of product data objects
            output_format: Target format
            filters: Filter criteria dictionary
            **kwargs: Additional format-specific arguments
            
        Returns:
            Converted filtered data
        """
        if filters:
            filtered_products = BatchConverter._apply_filters(products, filters)
        else:
            filtered_products = products
        
        return BatchConverter.convert_batch_to_format(
            filtered_products, output_format, **kwargs
        )
    
    @staticmethod
    def _apply_filters(products: List[EnhancedProductData],
                      filters: Dict[str, Any]) -> List[EnhancedProductData]:
        """Apply filters to product list.
        
        Args:
            products: List of product data objects
            filters: Filter criteria dictionary
            
        Returns:
            Filtered list of products
        """
        filtered = products
        
        # Price range filter
        if "price_min" in filters:
            filtered = [p for p in filtered 
                       if p.current_price and p.current_price >= filters["price_min"]]
        
        if "price_max" in filters:
            filtered = [p for p in filtered 
                       if p.current_price and p.current_price <= filters["price_max"]]
        
        # BSR filter
        if "bsr_max" in filters:
            filtered = [p for p in filtered 
                       if p.bsr_current and p.bsr_current <= filters["bsr_max"]]
        
        # Rating filter
        if "rating_min" in filters:
            filtered = [p for p in filtered 
                       if p.review_data.rating and p.review_data.rating >= filters["rating_min"]]
        
        # Review count filter
        if "reviews_min" in filters:
            filtered = [p for p in filtered 
                       if p.review_data.review_count >= filters["reviews_min"]]
        
        # Competition level filter
        if "competition_level" in filters:
            target_level = CompetitionLevel(filters["competition_level"])
            filtered = [p for p in filtered if p.get_competition_level() == target_level]
        
        # Category filter
        if "category_contains" in filters:
            category_filter = filters["category_contains"].lower()
            filtered = [p for p in filtered 
                       if category_filter in p.get_category_path().lower()]
        
        # Brand filter
        if "brand" in filters:
            brand_filter = filters["brand"].lower()
            filtered = [p for p in filtered 
                       if p.brand and brand_filter in p.brand.lower()]
        
        return filtered


# Convenience functions for common conversions

def products_to_csv(products: List[EnhancedProductData], 
                   filename: Optional[str] = None) -> Optional[str]:
    """Convert products to CSV format.
    
    Args:
        products: List of product data objects
        filename: Optional output filename
        
    Returns:
        CSV string if no filename provided, None otherwise
    """
    if filename:
        ProductDataConverter.to_csv_file(products, filename)
        return None
    else:
        return ProductDataConverter.to_csv_string(products)


def products_to_json(products: List[EnhancedProductData], 
                    filename: Optional[str] = None,
                    format_type: str = "enhanced") -> Optional[str]:
    """Convert products to JSON format.
    
    Args:
        products: List of product data objects
        filename: Optional output filename
        format_type: "enhanced", "legacy", or "minimal"
        
    Returns:
        JSON string if no filename provided, None otherwise
    """
    if filename:
        ProductDataConverter.to_json_file(products, filename, format_type=format_type)
        return None
    else:
        return ProductDataConverter.to_json_string(products, format_type=format_type)


def create_summary_report(products: List[EnhancedProductData]) -> Dict[str, Any]:
    """Create summary report from products.
    
    Args:
        products: List of product data objects
        
    Returns:
        Summary report dictionary
    """
    return ProductDataConverter.to_summary_report(products)