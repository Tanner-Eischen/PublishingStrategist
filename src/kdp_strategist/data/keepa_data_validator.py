"""Comprehensive data validation and quality assurance for Keepa API data.

This module provides:
- Field validation for all parsed data types
- Data type checking and range validation
- Edge case handling for missing or null fields
- Data consistency validation across related fields
- Quality scoring and error reporting
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
import re
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Data validation error details."""
    field: str
    expected_type: str
    actual_value: Any
    actual_type: str
    message: str
    severity: str = "error"  # error, warning, info
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "field": self.field,
            "expected_type": self.expected_type,
            "actual_value": str(self.actual_value),
            "actual_type": self.actual_type,
            "message": self.message,
            "severity": self.severity
        }


@dataclass
class ValidationResult:
    """Result of data validation process."""
    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    field_completeness: Dict[str, bool] = field(default_factory=dict)
    consistency_checks: Dict[str, bool] = field(default_factory=dict)
    
    def add_error(self, error: ValidationError):
        """Add validation error."""
        if error.severity == "error":
            self.errors.append(error)
            self.is_valid = False
        elif error.severity == "warning":
            self.warnings.append(error)
    
    def get_all_issues(self) -> List[ValidationError]:
        """Get all validation issues (errors and warnings)."""
        return self.errors + self.warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_valid": self.is_valid,
            "quality_score": self.quality_score,
            "errors": [error.to_dict() for error in self.errors],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "field_completeness": self.field_completeness,
            "consistency_checks": self.consistency_checks
        }


class KeepaDataValidator:
    """Comprehensive validator for Keepa API data."""
    
    def __init__(self):
        """Initialize validator with validation rules."""
        self.logger = logging.getLogger(__name__)
        
        # ASIN validation pattern - must start with letter, then 9 alphanumeric
        self.asin_pattern = re.compile(r'^[A-Z][A-Z0-9]{9}$')
        
        # Valid price ranges (in dollars)
        self.min_price = 0.01
        self.max_price = 10000.0
        
        # Valid rating range
        self.min_rating = 0.0
        self.max_rating = 5.0
        
        # Valid BSR ranges by category (approximate)
        self.max_bsr_by_category = {
            "Books": 10000000,
            "Electronics": 5000000,
            "Home & Kitchen": 3000000,
            "Clothing": 2000000,
            "default": 20000000
        }
        
        # Required fields for different data types
        self.required_product_fields = {
            "asin", "title"
        }
        
        self.important_product_fields = {
            "current_price", "bsr_current", "review_count", "rating", "primary_category"
        }
    
    def validate_product_data(self, product_data: Dict[str, Any]) -> ValidationResult:
        """Validate complete product data structure.
        
        Args:
            product_data: Product data dictionary to validate
            
        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(is_valid=True, quality_score=1.0)
        
        try:
            # Validate required fields
            self._validate_required_fields(product_data, result)
            
            # Validate individual fields
            self._validate_asin(product_data.get("asin"), result)
            self._validate_title(product_data.get("title"), result)
            self._validate_pricing_data(product_data, result)
            self._validate_rating_data(product_data, result)
            self._validate_bsr_data(product_data, result)
            self._validate_category_data(product_data, result)
            self._validate_image_data(product_data, result)
            self._validate_dimension_data(product_data, result)
            self._validate_sales_estimates(product_data, result)
            self._validate_metadata(product_data, result)
            
            # Perform consistency checks
            self._validate_data_consistency(product_data, result)
            
            # Calculate field completeness
            self._calculate_field_completeness(product_data, result)
            
            # Calculate final quality score
            result.quality_score = self._calculate_quality_score(product_data, result)
            
        except Exception as e:
            self.logger.error(f"Unexpected error during validation: {e}")
            result.add_error(ValidationError(
                field="validation_process",
                expected_type="successful_validation",
                actual_value=str(e),
                actual_type="exception",
                message=f"Validation process failed: {str(e)}",
                severity="error"
            ))
        
        return result
    
    def validate_price_history_data(self, price_history: Dict[str, Any]) -> ValidationResult:
        """Validate price history data structure.
        
        Args:
            price_history: Price history data to validate
            
        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(is_valid=True, quality_score=1.0)
        
        try:
            # Validate ASIN
            self._validate_asin(price_history.get("asin"), result)
            
            # Validate price points
            price_points = price_history.get("price_points", [])
            if not isinstance(price_points, list):
                result.add_error(ValidationError(
                    field="price_points",
                    expected_type="list",
                    actual_value=price_points,
                    actual_type=type(price_points).__name__,
                    message="Price points must be a list",
                    severity="error"
                ))
            else:
                self._validate_price_points(price_points, result)
            
            # Validate time period
            time_period = price_history.get("time_period_days")
            if time_period is not None:
                if not isinstance(time_period, int) or time_period <= 0:
                    result.add_error(ValidationError(
                        field="time_period_days",
                        expected_type="positive_integer",
                        actual_value=time_period,
                        actual_type=type(time_period).__name__,
                        message="Time period must be a positive integer",
                        severity="error"
                    ))
            
            # Validate statistics
            statistics = price_history.get("statistics", {})
            if isinstance(statistics, dict):
                self._validate_price_statistics(statistics, result)
            
            # Calculate quality score
            result.quality_score = self._calculate_price_history_quality_score(price_history, result)
            
        except Exception as e:
            self.logger.error(f"Error validating price history: {e}")
            result.add_error(ValidationError(
                field="price_history_validation",
                expected_type="successful_validation",
                actual_value=str(e),
                actual_type="exception",
                message=f"Price history validation failed: {str(e)}",
                severity="error"
            ))
        
        return result
    
    def validate_batch_data(self, batch_data: List[Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """Validate a batch of product data.
        
        Args:
            batch_data: List of product data dictionaries
            
        Returns:
            Dictionary mapping ASIN to ValidationResult
        """
        results = {}
        
        if not isinstance(batch_data, list):
            # Return single error result
            error_result = ValidationResult(is_valid=False, quality_score=0.0)
            error_result.add_error(ValidationError(
                field="batch_data",
                expected_type="list",
                actual_value=batch_data,
                actual_type=type(batch_data).__name__,
                message="Batch data must be a list",
                severity="error"
            ))
            return {"batch_error": error_result}
        
        for i, product_data in enumerate(batch_data):
            try:
                asin = product_data.get("asin", f"unknown_{i}")
                results[asin] = self.validate_product_data(product_data)
            except Exception as e:
                self.logger.error(f"Error validating batch item {i}: {e}")
                error_result = ValidationResult(is_valid=False, quality_score=0.0)
                error_result.add_error(ValidationError(
                    field="batch_item",
                    expected_type="valid_product_data",
                    actual_value=str(e),
                    actual_type="exception",
                    message=f"Batch item {i} validation failed: {str(e)}",
                    severity="error"
                ))
                results[f"batch_item_{i}"] = error_result
        
        return results
    
    def _validate_required_fields(self, data: Dict[str, Any], result: ValidationResult):
        """Validate that required fields are present."""
        for field in self.required_product_fields:
            if field not in data or data[field] is None or data[field] == "":
                result.add_error(ValidationError(
                    field=field,
                    expected_type="non_empty_value",
                    actual_value=data.get(field),
                    actual_type=type(data.get(field)).__name__,
                    message=f"Required field '{field}' is missing or empty",
                    severity="error"
                ))
    
    def _validate_asin(self, asin: Any, result: ValidationResult):
        """Validate ASIN format."""
        if asin is None:
            result.add_error(ValidationError(
                field="asin",
                expected_type="string",
                actual_value=asin,
                actual_type="NoneType",
                message="ASIN cannot be None",
                severity="error"
            ))
            return
        
        if not isinstance(asin, str):
            result.add_error(ValidationError(
                field="asin",
                expected_type="string",
                actual_value=asin,
                actual_type=type(asin).__name__,
                message="ASIN must be a string",
                severity="error"
            ))
            return
        
        # Check length first
        if len(asin) != 10:
            result.add_error(ValidationError(
                field="asin",
                expected_type="10_character_string",
                actual_value=asin,
                actual_type="string",
                message=f"ASIN must be exactly 10 characters, got {len(asin)}",
                severity="error"
            ))
            return
        
        # Check alphanumeric pattern
        if not self.asin_pattern.match(asin):
            result.add_error(ValidationError(
                field="asin",
                expected_type="10_character_alphanumeric",
                actual_value=asin,
                actual_type="string",
                message="ASIN must be 10 alphanumeric characters (A-Z, 0-9)",
                severity="error"
            ))
    
    def _validate_title(self, title: Any, result: ValidationResult):
        """Validate product title."""
        if title is None:
            result.add_error(ValidationError(
                field="title",
                expected_type="string",
                actual_value=title,
                actual_type="NoneType",
                message="Title cannot be None",
                severity="error"
            ))
            return
        
        if not isinstance(title, str):
            result.add_error(ValidationError(
                field="title",
                expected_type="string",
                actual_value=title,
                actual_type=type(title).__name__,
                message="Title must be a string",
                severity="error"
            ))
            return
        
        if len(title.strip()) == 0:
            result.add_error(ValidationError(
                field="title",
                expected_type="non_empty_string",
                actual_value=title,
                actual_type="string",
                message="Title cannot be empty",
                severity="error"
            ))
        elif len(title) > 500:
            result.add_error(ValidationError(
                field="title",
                expected_type="string_under_500_chars",
                actual_value=f"{title[:50]}...",
                actual_type="string",
                message=f"Title is unusually long ({len(title)} characters)",
                severity="warning"
            ))
    
    def _validate_pricing_data(self, data: Dict[str, Any], result: ValidationResult):
        """Validate all pricing-related fields."""
        price_fields = [
            "current_price", "avg_price_30d", "avg_price_90d", 
            "lowest_price_30d", "highest_price_30d"
        ]
        
        for field in price_fields:
            price = data.get(field)
            if price is not None:
                self._validate_price_value(field, price, result)
        
        # Validate price relationships
        current_price = data.get("current_price")
        lowest_30d = data.get("lowest_price_30d")
        highest_30d = data.get("highest_price_30d")
        
        if all(p is not None for p in [current_price, lowest_30d, highest_30d]):
            if lowest_30d > highest_30d:
                result.add_error(ValidationError(
                    field="price_consistency",
                    expected_type="lowest <= highest",
                    actual_value=f"lowest: {lowest_30d}, highest: {highest_30d}",
                    actual_type="price_range",
                    message="Lowest price cannot be higher than highest price",
                    severity="error"
                ))
            
            if not (lowest_30d <= current_price <= highest_30d):
                result.add_error(ValidationError(
                    field="price_consistency",
                    expected_type="current_price_in_range",
                    actual_value=f"current: {current_price}, range: [{lowest_30d}, {highest_30d}]",
                    actual_type="price_range",
                    message="Current price should be within 30-day price range",
                    severity="warning"
                ))
    
    def _validate_price_value(self, field: str, price: Any, result: ValidationResult):
        """Validate individual price value."""
        if not isinstance(price, (int, float, Decimal)):
            result.add_error(ValidationError(
                field=field,
                expected_type="number",
                actual_value=price,
                actual_type=type(price).__name__,
                message=f"Price field '{field}' must be a number",
                severity="error"
            ))
            return
        
        try:
            price_value = float(price)
        except (ValueError, TypeError):
            result.add_error(ValidationError(
                field=field,
                expected_type="convertible_to_float",
                actual_value=price,
                actual_type=type(price).__name__,
                message=f"Price field '{field}' cannot be converted to float",
                severity="error"
            ))
            return
        
        if price_value < 0:
            result.add_error(ValidationError(
                field=field,
                expected_type="non_negative_number",
                actual_value=price_value,
                actual_type="float",
                message=f"Price field '{field}' cannot be negative",
                severity="error"
            ))
        elif price_value < self.min_price:
            result.add_error(ValidationError(
                field=field,
                expected_type=f"price >= {self.min_price}",
                actual_value=price_value,
                actual_type="float",
                message=f"Price field '{field}' is unusually low (${price_value:.2f})",
                severity="warning"
            ))
        elif price_value > self.max_price:
            result.add_error(ValidationError(
                field=field,
                expected_type=f"price <= {self.max_price}",
                actual_value=price_value,
                actual_type="float",
                message=f"Price field '{field}' is unusually high (${price_value:.2f})",
                severity="warning"
            ))
    
    def _validate_rating_data(self, data: Dict[str, Any], result: ValidationResult):
        """Validate rating and review data."""
        rating = data.get("rating")
        if rating is not None:
            if not isinstance(rating, (int, float)):
                result.add_error(ValidationError(
                    field="rating",
                    expected_type="number",
                    actual_value=rating,
                    actual_type=type(rating).__name__,
                    message="Rating must be a number",
                    severity="error"
                ))
            else:
                rating_value = float(rating)
                if rating_value < self.min_rating or rating_value > self.max_rating:
                    result.add_error(ValidationError(
                        field="rating",
                        expected_type=f"rating between {self.min_rating} and {self.max_rating}",
                        actual_value=rating_value,
                        actual_type="float",
                        message=f"Rating must be between {self.min_rating} and {self.max_rating}",
                        severity="error"
                    ))
        
        review_count = data.get("review_count")
        if review_count is not None:
            if not isinstance(review_count, int):
                result.add_error(ValidationError(
                    field="review_count",
                    expected_type="integer",
                    actual_value=review_count,
                    actual_type=type(review_count).__name__,
                    message="Review count must be an integer",
                    severity="error"
                ))
            elif review_count < 0:
                result.add_error(ValidationError(
                    field="review_count",
                    expected_type="non_negative_integer",
                    actual_value=review_count,
                    actual_type="integer",
                    message="Review count cannot be negative",
                    severity="error"
                ))
    
    def _validate_bsr_data(self, data: Dict[str, Any], result: ValidationResult):
        """Validate Best Seller Rank data."""
        bsr_fields = ["bsr_current", "bsr_avg_30d", "bsr_avg_90d"]
        
        for field in bsr_fields:
            bsr = data.get(field)
            if bsr is not None:
                if not isinstance(bsr, (int, float)):
                    result.add_error(ValidationError(
                        field=field,
                        expected_type="number",
                        actual_value=bsr,
                        actual_type=type(bsr).__name__,
                        message=f"BSR field '{field}' must be a number",
                        severity="error"
                    ))
                else:
                    bsr_value = int(bsr) if isinstance(bsr, float) and bsr.is_integer() else bsr
                    if bsr_value <= 0:
                        result.add_error(ValidationError(
                            field=field,
                            expected_type="positive_number",
                            actual_value=bsr_value,
                            actual_type=type(bsr_value).__name__,
                            message=f"BSR field '{field}' must be positive",
                            severity="error"
                        ))
                    else:
                        # Check against category-specific maximum
                        category = data.get("primary_category", "default")
                        max_bsr = self.max_bsr_by_category.get(category, self.max_bsr_by_category["default"])
                        if bsr_value > max_bsr:
                            result.add_error(ValidationError(
                                field=field,
                                expected_type=f"bsr <= {max_bsr}",
                                actual_value=bsr_value,
                                actual_type=type(bsr_value).__name__,
                                message=f"BSR field '{field}' is unusually high for category '{category}'",
                                severity="warning"
                            ))
    
    def _validate_category_data(self, data: Dict[str, Any], result: ValidationResult):
        """Validate category-related data."""
        primary_category = data.get("primary_category")
        if primary_category is not None and not isinstance(primary_category, str):
            result.add_error(ValidationError(
                field="primary_category",
                expected_type="string",
                actual_value=primary_category,
                actual_type=type(primary_category).__name__,
                message="Primary category must be a string",
                severity="error"
            ))
        
        all_categories = data.get("all_categories")
        if all_categories is not None:
            if not isinstance(all_categories, list):
                result.add_error(ValidationError(
                    field="all_categories",
                    expected_type="list",
                    actual_value=all_categories,
                    actual_type=type(all_categories).__name__,
                    message="All categories must be a list",
                    severity="error"
                ))
            else:
                for i, category in enumerate(all_categories):
                    if not isinstance(category, str):
                        result.add_error(ValidationError(
                            field=f"all_categories[{i}]",
                            expected_type="string",
                            actual_value=category,
                            actual_type=type(category).__name__,
                            message=f"Category at index {i} must be a string",
                            severity="error"
                        ))
        
        category_hierarchy = data.get("category_hierarchy")
        if category_hierarchy is not None:
            if not isinstance(category_hierarchy, list):
                result.add_error(ValidationError(
                    field="category_hierarchy",
                    expected_type="list",
                    actual_value=category_hierarchy,
                    actual_type=type(category_hierarchy).__name__,
                    message="Category hierarchy must be a list",
                    severity="error"
                ))
    
    def _validate_image_data(self, data: Dict[str, Any], result: ValidationResult):
        """Validate image-related data."""
        images = data.get("images")
        if images is not None:
            if not isinstance(images, list):
                result.add_error(ValidationError(
                    field="images",
                    expected_type="list",
                    actual_value=images,
                    actual_type=type(images).__name__,
                    message="Images must be a list",
                    severity="error"
                ))
            else:
                for i, image_url in enumerate(images):
                    if not isinstance(image_url, str):
                        result.add_error(ValidationError(
                            field=f"images[{i}]",
                            expected_type="string",
                            actual_value=image_url,
                            actual_type=type(image_url).__name__,
                            message=f"Image URL at index {i} must be a string",
                            severity="error"
                        ))
                    elif not self._is_valid_url(image_url):
                        result.add_error(ValidationError(
                            field=f"images[{i}]",
                            expected_type="valid_url",
                            actual_value=image_url,
                            actual_type="string",
                            message=f"Image URL at index {i} is not a valid URL",
                            severity="warning"
                        ))
    
    def _validate_dimension_data(self, data: Dict[str, Any], result: ValidationResult):
        """Validate dimension and weight data."""
        dimensions = data.get("dimensions")
        if dimensions is not None:
            if not isinstance(dimensions, dict):
                result.add_error(ValidationError(
                    field="dimensions",
                    expected_type="dict",
                    actual_value=dimensions,
                    actual_type=type(dimensions).__name__,
                    message="Dimensions must be a dictionary",
                    severity="error"
                ))
            else:
                dimension_fields = ["length", "width", "height"]
                for field in dimension_fields:
                    value = dimensions.get(field)
                    if value is not None:
                        if not isinstance(value, (int, float)):
                            result.add_error(ValidationError(
                                field=f"dimensions.{field}",
                                expected_type="number",
                                actual_value=value,
                                actual_type=type(value).__name__,
                                message=f"Dimension '{field}' must be a number",
                                severity="error"
                            ))
                        elif value <= 0:
                            result.add_error(ValidationError(
                                field=f"dimensions.{field}",
                                expected_type="positive_number",
                                actual_value=value,
                                actual_type=type(value).__name__,
                                message=f"Dimension '{field}' must be positive",
                                severity="error"
                            ))
        
        weight = data.get("weight")
        if weight is not None:
            if not isinstance(weight, (int, float)):
                result.add_error(ValidationError(
                    field="weight",
                    expected_type="number",
                    actual_value=weight,
                    actual_type=type(weight).__name__,
                    message="Weight must be a number",
                    severity="error"
                ))
            elif weight <= 0:
                result.add_error(ValidationError(
                    field="weight",
                    expected_type="positive_number",
                    actual_value=weight,
                    actual_type=type(weight).__name__,
                    message="Weight must be positive",
                    severity="error"
                ))
    
    def _validate_sales_estimates(self, data: Dict[str, Any], result: ValidationResult):
        """Validate sales estimate data."""
        sales_fields = ["estimated_sales_30d", "estimated_sales_90d", "monthly_sold"]
        
        for field in sales_fields:
            sales = data.get(field)
            if sales is not None:
                if not isinstance(sales, int):
                    result.add_error(ValidationError(
                        field=field,
                        expected_type="integer",
                        actual_value=sales,
                        actual_type=type(sales).__name__,
                        message=f"Sales field '{field}' must be an integer",
                        severity="error"
                    ))
                elif sales < 0:
                    result.add_error(ValidationError(
                        field=field,
                        expected_type="non_negative_integer",
                        actual_value=sales,
                        actual_type="integer",
                        message=f"Sales field '{field}' cannot be negative",
                        severity="error"
                    ))
    
    def _validate_metadata(self, data: Dict[str, Any], result: ValidationResult):
        """Validate metadata fields."""
        last_updated = data.get("last_updated")
        if last_updated is not None:
            if isinstance(last_updated, str):
                try:
                    datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                except ValueError:
                    result.add_error(ValidationError(
                        field="last_updated",
                        expected_type="iso_datetime_string",
                        actual_value=last_updated,
                        actual_type="string",
                        message="Last updated must be a valid ISO datetime string",
                        severity="error"
                    ))
            elif not isinstance(last_updated, datetime):
                result.add_error(ValidationError(
                    field="last_updated",
                    expected_type="datetime_or_iso_string",
                    actual_value=last_updated,
                    actual_type=type(last_updated).__name__,
                    message="Last updated must be a datetime object or ISO string",
                    severity="error"
                ))
        
        quality_score = data.get("data_quality_score")
        if quality_score is not None:
            if not isinstance(quality_score, (int, float)):
                result.add_error(ValidationError(
                    field="data_quality_score",
                    expected_type="number",
                    actual_value=quality_score,
                    actual_type=type(quality_score).__name__,
                    message="Data quality score must be a number",
                    severity="error"
                ))
            elif not (0.0 <= quality_score <= 1.0):
                result.add_error(ValidationError(
                    field="data_quality_score",
                    expected_type="number_between_0_and_1",
                    actual_value=quality_score,
                    actual_type=type(quality_score).__name__,
                    message="Data quality score must be between 0.0 and 1.0",
                    severity="error"
                ))
    
    def _validate_data_consistency(self, data: Dict[str, Any], result: ValidationResult):
        """Validate consistency across related fields."""
        # Check rating vs review count consistency
        rating = data.get("rating")
        review_count = data.get("review_count", 0)
        
        if rating is not None and review_count == 0:
            result.add_error(ValidationError(
                field="rating_review_consistency",
                expected_type="rating_with_reviews",
                actual_value=f"rating: {rating}, reviews: {review_count}",
                actual_type="consistency_check",
                message="Product has rating but no reviews",
                severity="warning"
            ))
        
        # Check BSR vs sales estimates consistency
        bsr_current = data.get("bsr_current")
        estimated_sales_30d = data.get("estimated_sales_30d", 0)
        
        if bsr_current is not None and estimated_sales_30d > 0:
            # Very rough consistency check: lower BSR should mean higher sales
            if bsr_current > 100000 and estimated_sales_30d > 1000:
                result.add_error(ValidationError(
                    field="bsr_sales_consistency",
                    expected_type="consistent_bsr_sales",
                    actual_value=f"BSR: {bsr_current}, sales: {estimated_sales_30d}",
                    actual_type="consistency_check",
                    message="High BSR with high sales estimates seems inconsistent",
                    severity="warning"
                ))
        
        # Check price vs category consistency
        current_price = data.get("current_price")
        primary_category = data.get("primary_category")
        
        if current_price is not None and primary_category is not None:
            # Books should generally be lower priced
            if primary_category.lower() == "books" and current_price > 50:
                result.add_error(ValidationError(
                    field="price_category_consistency",
                    expected_type="reasonable_book_price",
                    actual_value=f"price: ${current_price}, category: {primary_category}",
                    actual_type="consistency_check",
                    message="Book price seems unusually high",
                    severity="warning"
                ))
        
        # Store consistency check results
        result.consistency_checks = {
            "rating_review_consistency": rating is None or review_count > 0,
            "bsr_sales_consistency": not (bsr_current and bsr_current > 100000 and estimated_sales_30d > 1000),
            "price_category_consistency": not (primary_category and primary_category.lower() == "books" and current_price and current_price > 50)
        }
    
    def _validate_price_points(self, price_points: List[Dict[str, Any]], result: ValidationResult):
        """Validate price history points."""
        for i, point in enumerate(price_points):
            if not isinstance(point, dict):
                result.add_error(ValidationError(
                    field=f"price_points[{i}]",
                    expected_type="dict",
                    actual_value=point,
                    actual_type=type(point).__name__,
                    message=f"Price point at index {i} must be a dictionary",
                    severity="error"
                ))
                continue
            
            # Validate timestamp
            timestamp = point.get("timestamp")
            if timestamp is not None:
                if isinstance(timestamp, str):
                    try:
                        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except ValueError:
                        result.add_error(ValidationError(
                            field=f"price_points[{i}].timestamp",
                            expected_type="iso_datetime_string",
                            actual_value=timestamp,
                            actual_type="string",
                            message=f"Price point {i} timestamp is not valid ISO format",
                            severity="error"
                        ))
                elif not isinstance(timestamp, datetime):
                    result.add_error(ValidationError(
                        field=f"price_points[{i}].timestamp",
                        expected_type="datetime_or_iso_string",
                        actual_value=timestamp,
                        actual_type=type(timestamp).__name__,
                        message=f"Price point {i} timestamp must be datetime or ISO string",
                        severity="error"
                    ))
            
            # Validate price
            price = point.get("price")
            if price is not None:
                self._validate_price_value(f"price_points[{i}].price", price, result)
    
    def _validate_price_statistics(self, statistics: Dict[str, Any], result: ValidationResult):
        """Validate price statistics data."""
        numeric_stats = [
            "current_price", "average_price", "min_price", "max_price",
            "price_volatility", "trend_strength"
        ]
        
        for stat in numeric_stats:
            value = statistics.get(stat)
            if value is not None and not isinstance(value, (int, float)):
                result.add_error(ValidationError(
                    field=f"statistics.{stat}",
                    expected_type="number",
                    actual_value=value,
                    actual_type=type(value).__name__,
                    message=f"Statistic '{stat}' must be a number",
                    severity="error"
                ))
        
        # Validate trend direction
        trend_direction = statistics.get("trend_direction")
        if trend_direction is not None:
            valid_directions = ["up", "down", "stable", "unknown"]
            if trend_direction not in valid_directions:
                result.add_error(ValidationError(
                    field="statistics.trend_direction",
                    expected_type=f"one_of_{valid_directions}",
                    actual_value=trend_direction,
                    actual_type=type(trend_direction).__name__,
                    message=f"Trend direction must be one of: {valid_directions}",
                    severity="error"
                ))
    
    def _calculate_field_completeness(self, data: Dict[str, Any], result: ValidationResult):
        """Calculate completeness score for each field category."""
        all_fields = {
            "basic_info": ["asin", "title", "brand", "manufacturer"],
            "pricing": ["current_price", "avg_price_30d", "lowest_price_30d", "highest_price_30d"],
            "ratings": ["rating", "review_count"],
            "ranking": ["bsr_current", "bsr_avg_30d"],
            "category": ["primary_category", "all_categories"],
            "details": ["images", "features", "dimensions", "weight"],
            "sales": ["estimated_sales_30d", "monthly_sold"]
        }
        
        for category, fields in all_fields.items():
            completed_fields = sum(1 for field in fields if data.get(field) is not None)
            completeness = completed_fields / len(fields) if fields else 0.0
            result.field_completeness[category] = completeness
        
        # Overall completeness
        total_fields = sum(len(fields) for fields in all_fields.values())
        total_completed = sum(1 for fields in all_fields.values() for field in fields if data.get(field) is not None)
        result.field_completeness["overall"] = total_completed / total_fields if total_fields else 0.0
    
    def _calculate_quality_score(self, data: Dict[str, Any], result: ValidationResult) -> float:
        """Calculate overall data quality score."""
        base_score = 1.0
        
        # Deduct for errors (more severe penalty)
        error_penalty = len(result.errors) * 0.15  # Increased penalty for errors
        base_score -= min(error_penalty, 0.9)  # Cap error penalty at 90%
        
        # Deduct for warnings (less severe penalty)
        warning_penalty = len(result.warnings) * 0.05
        base_score -= min(warning_penalty, 0.2)  # Cap warning penalty at 20%
        
        # If there are many errors, ensure low score
        if len(result.errors) >= 5:
            base_score = min(base_score, 0.4)  # Cap at 0.4 for many errors
        elif len(result.errors) >= 3:
            base_score = min(base_score, 0.6)  # Cap at 0.6 for several errors
        
        # Bonus for completeness (only if no major errors)
        if len(result.errors) < 3:
            overall_completeness = result.field_completeness.get("overall", 0.0)
            completeness_bonus = overall_completeness * 0.15
            base_score += completeness_bonus
        
        # Bonus for important fields (only if valid)
        if result.is_valid:
            important_field_bonus = 0.0
            for field in self.important_product_fields:
                if data.get(field) is not None:
                    important_field_bonus += 0.03
            base_score += min(important_field_bonus, 0.15)  # Cap bonus at 15%
        
        # Bonus for consistency (only if valid)
        if result.is_valid and result.consistency_checks:
            consistency_score = sum(result.consistency_checks.values()) / len(result.consistency_checks)
            consistency_bonus = consistency_score * 0.1
            base_score += consistency_bonus
        
        return max(0.0, min(1.0, base_score))  # Ensure score is between 0 and 1
    
    def _calculate_price_history_quality_score(self, price_history: Dict[str, Any], result: ValidationResult) -> float:
        """Calculate quality score for price history data."""
        base_score = 1.0
        
        # Deduct for errors and warnings
        error_penalty = len(result.errors) * 0.15
        warning_penalty = len(result.warnings) * 0.05
        base_score -= min(error_penalty + warning_penalty, 0.8)
        
        # Bonus for data points
        price_points = price_history.get("price_points", [])
        if len(price_points) > 10:
            base_score += 0.1
        elif len(price_points) > 5:
            base_score += 0.05
        
        # Bonus for statistics
        statistics = price_history.get("statistics", {})
        if statistics and len(statistics) > 3:
            base_score += 0.1
        
        return max(0.0, min(1.0, base_score))
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if string is a valid URL."""
        try:
            # Basic URL validation
            return url.startswith(('http://', 'https://')) and '.' in url
        except Exception:
            return False