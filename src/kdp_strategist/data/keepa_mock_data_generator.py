"""Realistic mock data generator for Keepa API testing and development.

This module provides:
- Realistic product data generation based on actual Amazon patterns
- Category-specific data generation with appropriate ranges
- Price history generation with realistic trends
- Edge case and error scenario generation
- Configurable data quality levels
"""

import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import math

# Import the data structures
from .keepa_client import ProductData, PricePoint, PriceHistoryData


@dataclass
class MockDataConfig:
    """Configuration for mock data generation."""
    include_edge_cases: bool = True
    data_quality_level: str = "high"  # low, medium, high
    include_missing_fields: bool = False
    include_invalid_data: bool = False
    price_volatility: str = "medium"  # low, medium, high
    category_focus: Optional[str] = None  # Books, Electronics, etc.


class KeepaDataGenerator:
    """Generates realistic mock data for Keepa API responses."""
    
    def __init__(self, config: Optional[MockDataConfig] = None):
        """Initialize the mock data generator."""
        self.config = config or MockDataConfig()
        
        # Category-specific data ranges
        self.category_data = {
            "Books": {
                "price_range": (5.99, 49.99),
                "bsr_range": (1, 5000000),
                "review_range": (0, 10000),
                "rating_range": (3.0, 5.0),
                "sales_multiplier": 0.8,
                "common_features": [
                    "Paperback edition",
                    "Large print available",
                    "Kindle edition available",
                    "Audio book available",
                    "Educational content"
                ]
            },
            "Electronics": {
                "price_range": (9.99, 999.99),
                "bsr_range": (1, 2000000),
                "review_range": (0, 50000),
                "rating_range": (2.5, 5.0),
                "sales_multiplier": 1.2,
                "common_features": [
                    "Wireless connectivity",
                    "Rechargeable battery",
                    "Waterproof design",
                    "1-year warranty",
                    "Energy efficient"
                ]
            },
            "Home & Kitchen": {
                "price_range": (4.99, 299.99),
                "bsr_range": (1, 3000000),
                "review_range": (0, 25000),
                "rating_range": (3.5, 5.0),
                "sales_multiplier": 1.0,
                "common_features": [
                    "Dishwasher safe",
                    "BPA-free materials",
                    "Easy to clean",
                    "Durable construction",
                    "Space-saving design"
                ]
            },
            "Clothing": {
                "price_range": (8.99, 199.99),
                "bsr_range": (1, 2500000),
                "review_range": (0, 15000),
                "rating_range": (3.0, 5.0),
                "sales_multiplier": 0.9,
                "common_features": [
                    "Machine washable",
                    "Comfortable fit",
                    "Breathable fabric",
                    "Wrinkle resistant",
                    "Available in multiple colors"
                ]
            },
            "Health & Personal Care": {
                "price_range": (3.99, 149.99),
                "bsr_range": (1, 1500000),
                "review_range": (0, 30000),
                "rating_range": (3.5, 5.0),
                "sales_multiplier": 1.1,
                "common_features": [
                    "Dermatologist tested",
                    "Natural ingredients",
                    "Hypoallergenic",
                    "Cruelty-free",
                    "FDA approved"
                ]
            }
        }
        
        # Common brand names by category
        self.brands = {
            "Books": ["Penguin Random House", "HarperCollins", "Simon & Schuster", "Macmillan", "Hachette"],
            "Electronics": ["Samsung", "Apple", "Sony", "LG", "Panasonic", "Anker", "Belkin"],
            "Home & Kitchen": ["OXO", "Cuisinart", "KitchenAid", "Pyrex", "Rubbermaid", "Hamilton Beach"],
            "Clothing": ["Levi's", "Nike", "Adidas", "Under Armour", "Calvin Klein", "Tommy Hilfiger"],
            "Health & Personal Care": ["Johnson & Johnson", "Procter & Gamble", "Unilever", "L'Oréal", "Neutrogena"]
        }
        
        # Sample titles by category
        self.title_templates = {
            "Books": [
                "The Complete Guide to {topic}",
                "{topic}: A Comprehensive Manual",
                "Mastering {topic} in 30 Days",
                "The Ultimate {topic} Handbook",
                "{topic} for Beginners: Step by Step Guide"
            ],
            "Electronics": [
                "{brand} {product} with Advanced Features",
                "Wireless {product} - Latest Model",
                "Professional Grade {product}",
                "Smart {product} with App Control",
                "Portable {product} for Travel"
            ],
            "Home & Kitchen": [
                "Premium {product} Set",
                "Professional {product} Collection",
                "Non-Stick {product} with Warranty",
                "Stainless Steel {product}",
                "Eco-Friendly {product}"
            ],
            "Clothing": [
                "{brand} {product} - Comfortable Fit",
                "Premium {product} Collection",
                "Athletic {product} for Performance",
                "Classic {product} Style",
                "Casual {product} for Everyday Wear"
            ],
            "Health & Personal Care": [
                "Natural {product} Formula",
                "Advanced {product} Treatment",
                "Gentle {product} for Sensitive Skin",
                "Professional {product} Solution",
                "Organic {product} with Vitamins"
            ]
        }
        
        # Product topics/types by category
        self.product_topics = {
            "Books": ["Python Programming", "Digital Marketing", "Personal Finance", "Cooking", "Photography", "Fitness", "Meditation"],
            "Electronics": ["Bluetooth Speaker", "Wireless Charger", "Smart Watch", "Headphones", "Power Bank", "USB Cable"],
            "Home & Kitchen": ["Coffee Maker", "Blender", "Knife Set", "Cutting Board", "Storage Container", "Cookware"],
            "Clothing": ["T-Shirt", "Jeans", "Hoodie", "Sneakers", "Jacket", "Dress", "Shorts"],
            "Health & Personal Care": ["Face Cream", "Shampoo", "Toothpaste", "Vitamin Supplement", "Hand Sanitizer", "Moisturizer"]
        }
    
    def generate_product_data(
        self,
        asin: Optional[str] = None,
        category: Optional[str] = None,
        include_history: bool = False
    ) -> Dict[str, Any]:
        """Generate realistic product data.
        
        Args:
            asin: Specific ASIN to use, or None to generate random
            category: Product category, or None to choose randomly
            include_history: Whether to include price history data
            
        Returns:
            Dictionary containing realistic product data
        """
        # Choose category
        if not category:
            category = self.config.category_focus or random.choice(list(self.category_data.keys()))
        
        category_info = self.category_data.get(category, self.category_data["Books"])
        
        # Generate ASIN
        if not asin:
            asin = self._generate_asin()
        
        # Generate basic product info
        product_data = {
            "asin": asin,
            "title": self._generate_title(category),
            "brand": self._generate_brand(category),
            "manufacturer": self._generate_manufacturer(category),
            "product_group": category,
            "description": self._generate_description(category),
            "primary_category": category,
            "all_categories": self._generate_category_hierarchy(category),
            "category_hierarchy": self._generate_category_nodes(category)
        }
        
        # Generate pricing data
        pricing_data = self._generate_pricing_data(category_info)
        product_data.update(pricing_data)
        
        # Generate rating and review data
        rating_data = self._generate_rating_data(category_info)
        product_data.update(rating_data)
        
        # Generate BSR data
        bsr_data = self._generate_bsr_data(category_info, rating_data["review_count"])
        product_data.update(bsr_data)
        
        # Generate sales estimates
        sales_data = self._generate_sales_estimates(bsr_data["bsr_current"], category_info)
        product_data.update(sales_data)
        
        # Generate product details
        details_data = self._generate_product_details(category)
        product_data.update(details_data)
        
        # Generate metadata
        metadata = self._generate_metadata()
        product_data.update(metadata)
        
        # Apply data quality modifications
        product_data = self._apply_data_quality_modifications(product_data)
        
        # Add price history if requested
        if include_history:
            product_data["price_history"] = self.generate_price_history(asin, category)
        
        return product_data
    
    def generate_batch_data(
        self,
        count: int,
        category: Optional[str] = None,
        include_history: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate a batch of realistic product data.
        
        Args:
            count: Number of products to generate
            category: Product category for all products, or None for mixed
            include_history: Whether to include price history data
            
        Returns:
            List of product data dictionaries
        """
        products = []
        
        for i in range(count):
            # Use different categories if not specified
            product_category = category
            if not product_category and not self.config.category_focus:
                product_category = random.choice(list(self.category_data.keys()))
            
            product = self.generate_product_data(
                category=product_category,
                include_history=include_history
            )
            products.append(product)
        
        return products
    
    def generate_price_history(
        self,
        asin: str,
        category: Optional[str] = None,
        days: int = 90,
        data_points: int = 50
    ) -> Dict[str, Any]:
        """Generate realistic price history data.
        
        Args:
            asin: Product ASIN
            category: Product category for realistic price ranges
            days: Number of days of history
            data_points: Number of price points to generate
            
        Returns:
            Price history data dictionary
        """
        if not category:
            category = random.choice(list(self.category_data.keys()))
        
        category_info = self.category_data[category]
        price_range = category_info["price_range"]
        
        # Generate base price
        base_price = random.uniform(price_range[0], price_range[1])
        
        # Generate price points with realistic trends
        price_points = []
        current_time = datetime.now()
        
        # Determine trend type
        trend_types = ["stable", "increasing", "decreasing", "volatile", "seasonal"]
        trend_weights = [0.4, 0.2, 0.2, 0.15, 0.05]  # Stable is most common
        trend_type = random.choices(trend_types, weights=trend_weights)[0]
        
        for i in range(data_points):
            # Calculate timestamp (evenly distributed over the period)
            days_back = (days * i) / data_points
            timestamp = current_time - timedelta(days=days_back)
            
            # Calculate price based on trend
            price = self._calculate_trend_price(base_price, i, data_points, trend_type, price_range)
            
            price_points.append({
                "timestamp": timestamp.isoformat(),
                "price": round(price, 2),
                "price_type": "amazon"
            })
        
        # Reverse to get chronological order
        price_points.reverse()
        
        # Calculate statistics
        prices = [point["price"] for point in price_points]
        statistics = {
            "current_price": prices[-1] if prices else base_price,
            "average_price": sum(prices) / len(prices) if prices else base_price,
            "min_price": min(prices) if prices else base_price,
            "max_price": max(prices) if prices else base_price,
            "price_volatility": self._calculate_price_volatility(prices),
            "trend_direction": self._determine_trend_direction(prices),
            "trend_strength": self._calculate_trend_strength(prices),
            "price_drops_count": self._count_price_drops(prices),
            "price_increases_count": self._count_price_increases(prices),
            "days_analyzed": days
        }
        
        return {
            "asin": asin,
            "price_points": price_points,
            "price_type": "amazon",
            "time_period_days": days,
            "data_points": len(price_points),
            "statistics": statistics,
            "last_updated": datetime.now().isoformat()
        }
    
    def generate_edge_case_data(self, case_type: str) -> Dict[str, Any]:
        """Generate edge case data for testing.
        
        Args:
            case_type: Type of edge case to generate
                - "missing_fields": Product with many missing fields
                - "invalid_data": Product with invalid data types
                - "extreme_values": Product with extreme but valid values
                - "empty_strings": Product with empty string values
                - "null_values": Product with null values
                - "malformed_asin": Product with invalid ASIN format
                
        Returns:
            Product data dictionary with edge case characteristics
        """
        base_data = self.generate_product_data()
        
        if case_type == "missing_fields":
            # Remove many optional fields
            fields_to_remove = [
                "brand", "manufacturer", "description", "avg_price_30d", "avg_price_90d",
                "lowest_price_30d", "highest_price_30d", "bsr_avg_30d", "bsr_avg_90d",
                "images", "features", "dimensions", "weight", "variation_asins"
            ]
            for field in fields_to_remove:
                base_data.pop(field, None)
        
        elif case_type == "invalid_data":
            # Add invalid data types
            base_data.update({
                "current_price": "not_a_number",
                "rating": "five_stars",
                "review_count": "many",
                "bsr_current": "very_good",
                "last_updated": "yesterday",
                "images": "single_image_url",
                "dimensions": "large"
            })
        
        elif case_type == "extreme_values":
            # Use extreme but technically valid values
            base_data.update({
                "current_price": 9999.99,
                "rating": 1.0,
                "review_count": 0,
                "bsr_current": 15000000,
                "estimated_sales_30d": 0,
                "title": "A" * 500,  # Very long title
                "images": ["https://example.com/image.jpg"] * 20  # Many images
            })
        
        elif case_type == "empty_strings":
            # Use empty strings for string fields
            base_data.update({
                "title": "",
                "brand": "",
                "manufacturer": "",
                "description": "",
                "primary_category": "",
                "all_categories": [""],
                "features": ["", "", ""]
            })
        
        elif case_type == "null_values":
            # Use None/null for various fields
            base_data.update({
                "brand": None,
                "current_price": None,
                "rating": None,
                "bsr_current": None,
                "images": None,
                "dimensions": None,
                "last_updated": None
            })
        
        elif case_type == "malformed_asin":
            # Use invalid ASIN formats
            invalid_asins = [
                "B123",  # Too short
                "B12345678901",  # Too long
                "b123456789",  # Lowercase
                "B12345678!",  # Special character
                "123456789A",  # Number first
                ""  # Empty
            ]
            base_data["asin"] = random.choice(invalid_asins)
        
        return base_data
    
    def generate_search_results(
        self,
        keyword: str,
        count: int = 20,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate realistic search results for a keyword.
        
        Args:
            keyword: Search keyword to base results on
            count: Number of results to generate
            category: Category to focus on, or None for mixed
            
        Returns:
            List of product data dictionaries relevant to the keyword
        """
        results = []
        
        for i in range(count):
            # Generate product with keyword-relevant title
            product = self.generate_product_data(category=category)
            
            # Modify title to include keyword
            if keyword.lower() not in product["title"].lower():
                # Insert keyword into title naturally
                title_parts = product["title"].split()
                insert_position = random.randint(0, len(title_parts))
                title_parts.insert(insert_position, keyword.title())
                product["title"] = " ".join(title_parts)
            
            # Adjust BSR based on position (earlier results should have better BSR)
            if product.get("bsr_current"):
                # Better BSR for earlier results
                bsr_multiplier = 1 + (i * 0.5)
                product["bsr_current"] = int(product["bsr_current"] * bsr_multiplier)
                
                # Recalculate sales estimates based on new BSR
                category_info = self.category_data.get(category or product.get("primary_category", "Books"))
                sales_data = self._generate_sales_estimates(product["bsr_current"], category_info)
                product.update(sales_data)
            
            results.append(product)
        
        return results
    
    def _generate_asin(self) -> str:
        """Generate a realistic ASIN."""
        # ASINs are 10 characters, usually starting with B for most products
        first_char = "B" if random.random() < 0.8 else random.choice("0123456789")
        remaining_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=9))
        return first_char + remaining_chars
    
    def _generate_title(self, category: str) -> str:
        """Generate a realistic product title."""
        templates = self.title_templates.get(category, self.title_templates["Books"])
        topics = self.product_topics.get(category, self.product_topics["Books"])
        brands = self.brands.get(category, self.brands["Books"])
        
        template = random.choice(templates)
        topic = random.choice(topics)
        brand = random.choice(brands)
        
        # Replace placeholders
        title = template.replace("{topic}", topic)
        title = title.replace("{product}", topic)
        title = title.replace("{brand}", brand)
        
        return title
    
    def _generate_brand(self, category: str) -> str:
        """Generate a realistic brand name."""
        brands = self.brands.get(category, self.brands["Books"])
        return random.choice(brands)
    
    def _generate_manufacturer(self, category: str) -> str:
        """Generate a realistic manufacturer name."""
        # Often same as brand, but sometimes different
        if random.random() < 0.7:
            return self._generate_brand(category)
        else:
            # Generate a different manufacturer
            all_brands = []
            for brand_list in self.brands.values():
                all_brands.extend(brand_list)
            return random.choice(all_brands)
    
    def _generate_description(self, category: str) -> str:
        """Generate a realistic product description."""
        descriptions = {
            "Books": "Comprehensive guide covering essential topics with practical examples and expert insights. Perfect for beginners and professionals alike.",
            "Electronics": "High-quality electronic device featuring advanced technology and reliable performance. Designed for everyday use with premium materials.",
            "Home & Kitchen": "Durable kitchen essential made from premium materials. Easy to use and clean, perfect for home cooking enthusiasts.",
            "Clothing": "Comfortable and stylish apparel made from high-quality materials. Perfect fit and long-lasting durability for everyday wear.",
            "Health & Personal Care": "Premium personal care product formulated with natural ingredients. Gentle yet effective for daily use."
        }
        
        base_description = descriptions.get(category, descriptions["Books"])
        
        # Add some variation
        variations = [
            " Highly rated by customers.",
            " Backed by satisfaction guarantee.",
            " Available in multiple options.",
            " Fast shipping available.",
            " Eco-friendly packaging."
        ]
        
        if random.random() < 0.6:
            base_description += random.choice(variations)
        
        return base_description
    
    def _generate_category_hierarchy(self, category: str) -> List[str]:
        """Generate realistic category hierarchy."""
        hierarchies = {
            "Books": ["Books", "Literature & Fiction", "Contemporary Fiction"],
            "Electronics": ["Electronics", "Accessories & Supplies", "Audio & Video Accessories"],
            "Home & Kitchen": ["Home & Kitchen", "Kitchen & Dining", "Small Appliances"],
            "Clothing": ["Clothing, Shoes & Jewelry", "Men", "Clothing"],
            "Health & Personal Care": ["Health & Household", "Health Care", "Personal Care"]
        }
        
        base_hierarchy = hierarchies.get(category, hierarchies["Books"])
        
        # Sometimes add an extra level
        if random.random() < 0.3:
            extra_levels = {
                "Books": "Mystery & Thrillers",
                "Electronics": "Cables & Interconnects",
                "Home & Kitchen": "Coffee Machines",
                "Clothing": "Casual Button-Down Shirts",
                "Health & Personal Care": "Skin Care"
            }
            base_hierarchy.append(extra_levels.get(category, "Subcategory"))
        
        return base_hierarchy
    
    def _generate_category_nodes(self, category: str) -> List[Dict[str, Any]]:
        """Generate category hierarchy nodes."""
        hierarchy = self._generate_category_hierarchy(category)
        nodes = []
        
        for i, cat_name in enumerate(hierarchy):
            nodes.append({
                "id": 1000 + i,
                "name": cat_name,
                "parent_id": 1000 + i - 1 if i > 0 else None,
                "level": i
            })
        
        return nodes
    
    def _generate_pricing_data(self, category_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic pricing data."""
        price_range = category_info["price_range"]
        
        # Generate current price
        current_price = round(random.uniform(price_range[0], price_range[1]), 2)
        
        # Generate historical prices with some variation
        price_variation = 0.2  # 20% variation
        
        avg_30d = current_price * random.uniform(0.95, 1.05)
        avg_90d = current_price * random.uniform(0.9, 1.1)
        
        lowest_30d = current_price * random.uniform(0.8, 0.95)
        highest_30d = current_price * random.uniform(1.05, 1.2)
        
        return {
            "current_price": round(current_price, 2),
            "avg_price_30d": round(avg_30d, 2),
            "avg_price_90d": round(avg_90d, 2),
            "lowest_price_30d": round(lowest_30d, 2),
            "highest_price_30d": round(highest_30d, 2)
        }
    
    def _generate_rating_data(self, category_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic rating and review data."""
        rating_range = category_info["rating_range"]
        review_range = category_info["review_range"]
        
        # Generate review count (log-normal distribution for realism)
        review_count = int(random.lognormvariate(3, 1.5))
        review_count = min(max(review_count, 0), review_range[1])
        
        # Generate rating (higher review counts tend to have more moderate ratings)
        if review_count == 0:
            rating = None
        else:
            # More reviews tend toward average ratings
            if review_count > 1000:
                rating = random.normalvariate(4.2, 0.5)
            elif review_count > 100:
                rating = random.normalvariate(4.0, 0.7)
            else:
                rating = random.uniform(rating_range[0], rating_range[1])
            
            # Clamp to valid range
            rating = max(rating_range[0], min(rating_range[1], rating))
            rating = round(rating, 1)
        
        return {
            "rating": rating,
            "review_count": review_count
        }
    
    def _generate_bsr_data(self, category_info: Dict[str, Any], review_count: int) -> Dict[str, Any]:
        """Generate realistic BSR data."""
        bsr_range = category_info["bsr_range"]
        
        # BSR correlates with review count (more reviews = better BSR generally)
        if review_count > 5000:
            bsr_multiplier = random.uniform(0.1, 0.3)
        elif review_count > 1000:
            bsr_multiplier = random.uniform(0.2, 0.5)
        elif review_count > 100:
            bsr_multiplier = random.uniform(0.3, 0.7)
        else:
            bsr_multiplier = random.uniform(0.5, 1.0)
        
        bsr_current = int(bsr_range[0] + (bsr_range[1] - bsr_range[0]) * bsr_multiplier)
        
        # Generate average BSRs with some variation
        bsr_avg_30d = bsr_current * random.uniform(0.8, 1.2)
        bsr_avg_90d = bsr_current * random.uniform(0.7, 1.3)
        
        return {
            "bsr_current": bsr_current,
            "bsr_avg_30d": round(bsr_avg_30d, 1),
            "bsr_avg_90d": round(bsr_avg_90d, 1)
        }
    
    def _generate_sales_estimates(self, bsr: int, category_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic sales estimates based on BSR."""
        sales_multiplier = category_info["sales_multiplier"]
        
        # Rough BSR to sales conversion (very approximate)
        if bsr <= 100:
            daily_sales = random.randint(50, 200)
        elif bsr <= 1000:
            daily_sales = random.randint(10, 50)
        elif bsr <= 10000:
            daily_sales = random.randint(2, 10)
        elif bsr <= 100000:
            daily_sales = random.randint(1, 5)
        else:
            daily_sales = random.randint(0, 2)
        
        # Apply category multiplier
        daily_sales = int(daily_sales * sales_multiplier)
        
        # Calculate monthly estimates
        monthly_sales = daily_sales * 30
        sales_30d = int(monthly_sales * random.uniform(0.8, 1.2))
        sales_90d = int(monthly_sales * 3 * random.uniform(0.7, 1.3))
        
        return {
            "estimated_sales_30d": sales_30d,
            "estimated_sales_90d": sales_90d,
            "monthly_sold": monthly_sales
        }
    
    def _generate_product_details(self, category: str) -> Dict[str, Any]:
        """Generate realistic product details."""
        # Generate images
        image_count = random.randint(1, 8)
        images = [f"https://m.media-amazon.com/images/I/{self._generate_asin()}.jpg" for _ in range(image_count)]
        
        # Generate features
        features = self.category_data[category]["common_features"].copy()
        random.shuffle(features)
        features = features[:random.randint(3, 5)]
        
        # Generate dimensions (if applicable)
        dimensions = None
        if category in ["Electronics", "Home & Kitchen", "Health & Personal Care"]:
            dimensions = {
                "length": round(random.uniform(2, 20), 1),
                "width": round(random.uniform(2, 15), 1),
                "height": round(random.uniform(1, 10), 1)
            }
        
        # Generate weight (if applicable)
        weight = None
        if category != "Books":  # Books usually don't have weight listed
            if category == "Electronics":
                weight = round(random.uniform(0.1, 5.0), 2)
            else:
                weight = round(random.uniform(0.2, 2.0), 2)
        
        # Generate variation ASINs (sometimes)
        variation_asins = []
        if random.random() < 0.3:  # 30% chance of having variations
            variation_count = random.randint(1, 5)
            variation_asins = [self._generate_asin() for _ in range(variation_count)]
        
        return {
            "images": images,
            "features": features,
            "dimensions": dimensions,
            "weight": weight,
            "variation_asins": variation_asins,
            "package_quantity": random.choice([1, 1, 1, 2, 4, 6])  # Mostly 1, sometimes more
        }
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate realistic metadata."""
        # Generate timestamp within last 24 hours
        last_updated = datetime.now() - timedelta(hours=random.uniform(0, 24))
        
        return {
            "last_updated": last_updated,
            "data_quality_score": round(random.uniform(0.7, 1.0), 2),
            "validation_errors": [],
            "additional_data": {
                "api_response_time": round(random.uniform(0.1, 2.0), 3),
                "cache_hit": random.choice([True, False]),
                "data_source": "keepa_api"
            }
        }
    
    def _apply_data_quality_modifications(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply data quality modifications based on configuration."""
        if self.config.data_quality_level == "low":
            # Remove many fields randomly
            optional_fields = ["brand", "manufacturer", "description", "dimensions", "weight", "features", "avg_price_30d", "bsr_avg_30d"]
            fields_to_remove = random.sample(optional_fields, random.randint(3, 6))
            for field in fields_to_remove:
                data.pop(field, None)
            
            # Add some problematic data
            if random.random() < 0.3:
                data["title"] = data["title"][:10]  # Very short title
            if random.random() < 0.2:
                data["current_price"] = round(random.uniform(0.01, 2.0), 2)  # Very low price
            
            # Lower quality score
            data["data_quality_score"] = round(random.uniform(0.2, 0.5), 2)
            
        elif self.config.data_quality_level == "medium":
            # Remove some optional fields
            if random.random() < 0.4:
                optional_fields = ["dimensions", "weight", "variation_asins", "manufacturer"]
                fields_to_remove = random.sample(optional_fields, random.randint(1, 2))
                for field in fields_to_remove:
                    data.pop(field, None)
            
            # Medium quality score
            data["data_quality_score"] = round(random.uniform(0.5, 0.8), 2)
        
        # High quality keeps all fields and high score (already set)
        
        return data
    
    def _calculate_trend_price(
        self,
        base_price: float,
        index: int,
        total_points: int,
        trend_type: str,
        price_range: Tuple[float, float]
    ) -> float:
        """Calculate price for a specific point in the trend."""
        progress = index / total_points  # 0 to 1
        
        if trend_type == "stable":
            # Small random variations around base price
            variation = random.uniform(-0.05, 0.05)  # ±5%
            price = base_price * (1 + variation)
            
        elif trend_type == "increasing":
            # Gradual increase over time
            increase_factor = progress * 0.3  # Up to 30% increase
            noise = random.uniform(-0.03, 0.03)  # ±3% noise
            price = base_price * (1 + increase_factor + noise)
            
        elif trend_type == "decreasing":
            # Gradual decrease over time
            decrease_factor = progress * 0.25  # Up to 25% decrease
            noise = random.uniform(-0.03, 0.03)  # ±3% noise
            price = base_price * (1 - decrease_factor + noise)
            
        elif trend_type == "volatile":
            # High volatility with random swings
            volatility = random.uniform(-0.2, 0.2)  # ±20%
            price = base_price * (1 + volatility)
            
        elif trend_type == "seasonal":
            # Seasonal pattern (sine wave)
            seasonal_factor = math.sin(progress * 2 * math.pi) * 0.15  # ±15%
            noise = random.uniform(-0.05, 0.05)  # ±5% noise
            price = base_price * (1 + seasonal_factor + noise)
        
        else:
            price = base_price
        
        # Ensure price stays within reasonable bounds
        price = max(price_range[0], min(price_range[1], price))
        
        return price
    
    def _calculate_price_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility."""
        if len(prices) < 2:
            return 0.0
        
        # Calculate standard deviation as percentage of mean
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)
        
        return round(std_dev / mean_price, 3) if mean_price > 0 else 0.0
    
    def _determine_trend_direction(self, prices: List[float]) -> str:
        """Determine overall trend direction."""
        if len(prices) < 2:
            return "unknown"
        
        start_price = sum(prices[:3]) / min(3, len(prices))  # Average of first few
        end_price = sum(prices[-3:]) / min(3, len(prices))   # Average of last few
        
        change_percent = (end_price - start_price) / start_price if start_price > 0 else 0
        
        if change_percent > 0.05:  # >5% increase
            return "up"
        elif change_percent < -0.05:  # >5% decrease
            return "down"
        else:
            return "stable"
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength (0.0 to 1.0)."""
        if len(prices) < 2:
            return 0.0
        
        # Simple linear regression to measure trend strength
        n = len(prices)
        x_values = list(range(n))
        
        # Calculate correlation coefficient
        x_mean = sum(x_values) / n
        y_mean = sum(prices) / n
        
        numerator = sum((x_values[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
        x_variance = sum((x - x_mean) ** 2 for x in x_values)
        y_variance = sum((y - y_mean) ** 2 for y in prices)
        
        if x_variance == 0 or y_variance == 0:
            return 0.0
        
        correlation = numerator / math.sqrt(x_variance * y_variance)
        
        return round(abs(correlation), 3)  # Return absolute correlation as strength
    
    def _count_price_drops(self, prices: List[float]) -> int:
        """Count number of price drops."""
        if len(prices) < 2:
            return 0
        
        drops = 0
        for i in range(1, len(prices)):
            if prices[i] < prices[i-1] * 0.95:  # >5% drop
                drops += 1
        
        return drops
    
    def _count_price_increases(self, prices: List[float]) -> int:
        """Count number of price increases."""
        if len(prices) < 2:
            return 0
        
        increases = 0
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1] * 1.05:  # >5% increase
                increases += 1
        
        return increases