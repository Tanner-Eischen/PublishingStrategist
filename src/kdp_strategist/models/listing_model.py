"""KDP Listing data model for KDP Strategist.

Defines the KDPListing class and related data structures for representing
optimized book listings with titles, descriptions, keywords, and metadata.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import json
import re


class ListingCategory(Enum):
    """KDP category classifications for book listings."""
    KINDLE_EBOOKS = "Kindle eBooks"
    PAPERBACK = "Books"
    HARDCOVER = "Books"
    AUDIOBOOK = "Audible Audiobooks"


class ContentType(Enum):
    """Types of content for KDP listings."""
    FICTION = "Fiction"
    NON_FICTION = "Non-Fiction"
    CHILDREN = "Children's"
    EDUCATIONAL = "Educational"
    REFERENCE = "Reference"
    POETRY = "Poetry"
    DRAMA = "Drama"


class TargetAudience(Enum):
    """Common audience segments for KDP listings."""
    CHILDREN = "children"
    TEENS = "teens"
    ADULTS = "adults"
    SENIORS = "seniors"
    PROFESSIONALS = "professionals"
    STUDENTS = "students"
    GENERAL = "general"


@dataclass
class KDPListing:
    """Represents an optimized book listing for Amazon KDP.
    
    This class encapsulates all elements needed for a successful KDP listing,
    including title optimization, keyword strategy, and content planning.
    
    Attributes:
        title: Main book title (optimized for search)
        subtitle: Optional subtitle for additional context
        description: Book description/blurb for the product page
        keywords: List of 7 keyword phrases for KDP backend
        categories: Primary and secondary category selections
        target_audience: Description of intended readers
        unique_selling_points: Key differentiators from competitors
        estimated_page_count: Estimated number of pages
        suggested_price: Recommended pricing
        content_outline: High-level content structure
        content_type: Type of content (fiction, non-fiction, etc.)
        language: Primary language of the content
        series_info: Information if part of a series
        author_bio: Suggested author biography
        marketing_hooks: Key marketing messages
        competitive_advantages: Advantages over similar books
    """
    
    # Core listing elements
    title: str
    subtitle: str = ""
    description: str = ""
    
    # KDP-specific fields
    keywords: List[str] = field(default_factory=list)  # Max 7 keywords
    categories: List[str] = field(default_factory=list)  # Primary + secondary
    
    # Target market
    target_audience: TargetAudience = TargetAudience.GENERAL
    unique_selling_points: List[str] = field(default_factory=list)
    
    # Content planning
    estimated_page_count: int = 0
    suggested_price: float = 9.99
    content_outline: List[str] = field(default_factory=list)
    content_type: str = ContentType.NON_FICTION.value
    language: str = "English"
    
    # Series and branding
    series_info: Optional[Dict[str, Any]] = None
    author_bio: str = ""
    
    # Marketing elements
    marketing_hooks: List[str] = field(default_factory=list)
    competitive_advantages: List[str] = field(default_factory=list)
    
    # Metadata
    created_date: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    optimization_score: float = 0.0
    additional_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate data after initialization."""
        self._validate_title()
        self._validate_keywords()
        self._validate_categories()
        self._validate_price()
        self._validate_description()
        self.last_updated = datetime.now()
        self.optimization_score = self._calculate_optimization_score()
    
    def _validate_title(self) -> None:
        """Validate title meets KDP requirements."""
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty")
        
        if len(self.title) > 200:
            raise ValueError("Title cannot exceed 200 characters")
        
        # Check for prohibited characters or patterns
        prohibited_patterns = [
            r'\b(free|\$0\.00)\b',  # Price references
            r'\b(bestseller|#1)\b',  # Ranking claims
            r'[<>{}\[\]]',  # Special characters
        ]
        
        for pattern in prohibited_patterns:
            if re.search(pattern, self.title, re.IGNORECASE):
                raise ValueError(f"Title contains prohibited content: {pattern}")
    
    def _validate_keywords(self) -> None:
        """Validate keywords meet KDP requirements."""
        if len(self.keywords) > 7:
            raise ValueError("Cannot have more than 7 keywords")
        
        for keyword in self.keywords:
            if not isinstance(keyword, str) or not keyword.strip():
                raise ValueError("All keywords must be non-empty strings")
            
            if len(keyword) > 50:
                raise ValueError(f"Keyword too long (max 50 chars): {keyword}")
    
    def _validate_categories(self) -> None:
        """Validate category selections."""
        if len(self.categories) > 2:
            raise ValueError("Cannot select more than 2 categories")
        
        if len(self.categories) == 0:
            raise ValueError("Must select at least one category")
    
    def _validate_price(self) -> None:
        """Validate pricing meets KDP requirements."""
        if self.suggested_price < 0.99:
            raise ValueError("Price cannot be less than $0.99")
        
        if self.suggested_price > 200.00:
            raise ValueError("Price cannot exceed $200.00")
    
    def _validate_description(self) -> None:
        """Validate description meets KDP requirements."""
        if len(self.description) > 4000:
            raise ValueError("Description cannot exceed 4000 characters")
    
    def _calculate_optimization_score(self) -> float:
        """Calculate optimization score based on listing completeness and quality.
        
        Returns:
            Score from 0-100 indicating listing optimization level
        """
        score = 0.0
        max_score = 100.0
        
        # Title optimization (20 points)
        if self.title:
            score += 10
            if len(self.title) >= 30:  # Good length for SEO
                score += 5
            if any(keyword.lower() in self.title.lower() for keyword in self.keywords):
                score += 5
        
        # Subtitle (10 points)
        if self.subtitle and len(self.subtitle) >= 20:
            score += 10
        
        # Description quality (25 points)
        if self.description:
            score += 10
            if len(self.description) >= 500:  # Substantial description
                score += 10
            if len(self.description.split()) >= 100:  # Good word count
                score += 5
        
        # Keywords (20 points)
        keyword_score = (len(self.keywords) / 7) * 20
        score += keyword_score
        
        # Categories (10 points)
        if len(self.categories) >= 1:
            score += 5
        if len(self.categories) == 2:
            score += 5
        
        # Content planning (10 points)
        if self.content_outline:
            score += 5
        if self.estimated_page_count > 0:
            score += 5
        
        # Marketing elements (5 points)
        if self.unique_selling_points:
            score += 2.5
        if self.marketing_hooks:
            score += 2.5
        
        return round(min(score, max_score), 1)
    
    @property
    def is_optimized(self) -> bool:
        """Check if listing meets optimization criteria.
        
        Returns:
            True if listing is well-optimized
        """
        return self.optimization_score >= 80.0
    
    @property
    def character_counts(self) -> Dict[str, int]:
        """Get character counts for various fields.
        
        Returns:
            Dictionary with character counts for title, subtitle, description
        """
        return {
            "title": len(self.title),
            "subtitle": len(self.subtitle),
            "description": len(self.description),
            "title_remaining": 200 - len(self.title),
            "description_remaining": 4000 - len(self.description),
        }
    
    @property
    def seo_strength(self) -> str:
        """Assess SEO strength of the listing.
        
        Returns:
            SEO strength: 'weak', 'moderate', or 'strong'
        """
        keyword_in_title = any(keyword.lower() in self.title.lower() for keyword in self.keywords)
        has_good_keywords = len(self.keywords) >= 5
        has_substantial_description = len(self.description) >= 500
        
        strong_factors = sum([keyword_in_title, has_good_keywords, has_substantial_description])
        
        if strong_factors >= 3:
            return "strong"
        elif strong_factors >= 2:
            return "moderate"
        else:
            return "weak"
    
    def add_keyword(self, keyword: str) -> bool:
        """Add a keyword to the listing.
        
        Args:
            keyword: Keyword phrase to add
            
        Returns:
            True if keyword was added, False if limit reached
        """
        if len(self.keywords) >= 7:
            return False
        
        if keyword and keyword not in self.keywords:
            self.keywords.append(keyword.strip())
            self.last_updated = datetime.now()
            self.optimization_score = self._calculate_optimization_score()
            return True
        
        return False
    
    def add_category(self, category: str) -> bool:
        """Add a category to the listing.
        
        Args:
            category: Category to add
            
        Returns:
            True if category was added, False if limit reached
        """
        if len(self.categories) >= 2:
            return False
        
        if category and category not in self.categories:
            self.categories.append(category)
            self.last_updated = datetime.now()
            return True
        
        return False
    
    def add_unique_selling_point(self, usp: str) -> None:
        """Add a unique selling point.
        
        Args:
            usp: Unique selling point to add
        """
        if usp and usp not in self.unique_selling_points:
            self.unique_selling_points.append(usp)
            self.last_updated = datetime.now()
    
    def add_marketing_hook(self, hook: str) -> None:
        """Add a marketing hook.
        
        Args:
            hook: Marketing hook to add
        """
        if hook and hook not in self.marketing_hooks:
            self.marketing_hooks.append(hook)
            self.last_updated = datetime.now()
    
    def set_series_info(self, series_name: str, book_number: int, total_books: Optional[int] = None) -> None:
        """Set series information for the listing.
        
        Args:
            series_name: Name of the book series
            book_number: Position in the series
            total_books: Total planned books in series (optional)
        """
        self.series_info = {
            "series_name": series_name,
            "book_number": book_number,
            "total_books": total_books,
        }
        self.last_updated = datetime.now()
    
    def generate_full_title(self) -> str:
        """Generate the full title including subtitle.
        
        Returns:
            Complete title with subtitle if present
        """
        if self.subtitle:
            return f"{self.title}: {self.subtitle}"
        return self.title
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert listing to dictionary for serialization.
        
        Returns:
            Dictionary representation of the listing
        """
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "description": self.description,
            "keywords": self.keywords,
            "categories": self.categories,
            "target_audience": self.target_audience.value,
            "unique_selling_points": self.unique_selling_points,
            "estimated_page_count": self.estimated_page_count,
            "suggested_price": self.suggested_price,
            "content_outline": self.content_outline,
            "content_type": self.content_type,
            "language": self.language,
            "series_info": self.series_info,
            "author_bio": self.author_bio,
            "marketing_hooks": self.marketing_hooks,
            "competitive_advantages": self.competitive_advantages,
            "created_date": self.created_date.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "optimization_score": self.optimization_score,
            "additional_data": self.additional_data,
            "is_optimized": self.is_optimized,
            "character_counts": self.character_counts,
            "seo_strength": self.seo_strength,
            "full_title": self.generate_full_title(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KDPListing":
        """Create listing from dictionary.
        
        Args:
            data: Dictionary containing listing data
            
        Returns:
            KDPListing instance
        """
        # Handle datetime conversion
        for date_field in ["created_date", "last_updated"]:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])
        
        # Remove computed properties
        computed_fields = {
            "is_optimized", "character_counts", "seo_strength", "full_title"
        }
        filtered_data = {k: v for k, v in data.items() if k not in computed_fields}

        if "target_audience" in filtered_data and isinstance(filtered_data["target_audience"], str):
            try:
                filtered_data["target_audience"] = TargetAudience(filtered_data["target_audience"])
            except ValueError:
                filtered_data["target_audience"] = TargetAudience.GENERAL
        
        return cls(**filtered_data)
    
    def to_json(self) -> str:
        """Convert listing to JSON string.
        
        Returns:
            JSON representation of the listing
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "KDPListing":
        """Create listing from JSON string.
        
        Args:
            json_str: JSON string containing listing data
            
        Returns:
            KDPListing instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation of the listing."""
        return f"KDPListing(title='{self.title}', optimization_score={self.optimization_score})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the listing."""
        return (
            f"KDPListing(title='{self.title}', keywords={len(self.keywords)}, "
            f"categories={len(self.categories)}, price=${self.suggested_price}, "
            f"optimization_score={self.optimization_score})"
        )