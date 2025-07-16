
"""Listing Generation Tool.

Generates optimized KDP book listings including:
- SEO-optimized titles with keyword integration
- Compelling book descriptions with marketing copy
- Strategic keyword selection and placement
- Category recommendations and positioning
- Pricing strategy based on market analysis
- Content suggestions and unique angles

The tool creates listings that:
- Maximize discoverability through SEO
- Convert browsers into buyers
- Position products competitively
- Comply with KDP requirements and best practices
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ...data.cache_manager import CacheManager
from ...data.keepa_client import KeepaClient
from ...data.trends_client import TrendsClient
from ...models.listing_model import KDPListing, ContentType, TargetAudience
from ...models.niche_model import Niche
from ...models.trend_model import TrendAnalysis

logger = logging.getLogger(__name__)


class ListingStyle(Enum):
    """Different listing styles for various book types."""
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    EDUCATIONAL = "educational"
    INSPIRATIONAL = "inspirational"
    PRACTICAL = "practical"


@dataclass
class TitleTemplate:
    """Template for generating book titles."""
    pattern: str
    style: ListingStyle
    target_audience: TargetAudience
    examples: List[str]
    seo_strength: float


@dataclass
class DescriptionTemplate:
    """Template for generating book descriptions."""
    structure: List[str]  # List of section types
    style: ListingStyle
    word_count_range: Tuple[int, int]
    conversion_elements: List[str]


class TitleGenerator:
    """Generates SEO-optimized book titles."""
    
    # Title templates for different book types and audiences
    TITLE_TEMPLATES = {
        ContentType.JOURNAL: [
            TitleTemplate(
                pattern="{primary_keyword} Journal: {unique_angle} for {audience}",
                style=ListingStyle.PRACTICAL,
                target_audience=TargetAudience.ADULTS,
                examples=["Gratitude Journal: Daily Prompts for Mindful Living"],
                seo_strength=0.85
            ),
            TitleTemplate(
                pattern="The Ultimate {primary_keyword} {book_type}: {benefit} in {timeframe}",
                style=ListingStyle.PROFESSIONAL,
                target_audience=TargetAudience.PROFESSIONALS,
                examples=["The Ultimate Productivity Planner: Achieve Your Goals in 90 Days"],
                seo_strength=0.90
            ),
            TitleTemplate(
                pattern="{adjective} {primary_keyword} {book_type} for {audience}: {unique_angle}",
                style=ListingStyle.CREATIVE,
                target_audience=TargetAudience.GENERAL,
                examples=["Beautiful Mindfulness Journal for Women: Self-Care Through Daily Reflection"],
                seo_strength=0.80
            )
        ],
        ContentType.PLANNER: [
            TitleTemplate(
                pattern="{year} {primary_keyword} Planner: {unique_angle} for {audience}",
                style=ListingStyle.PRACTICAL,
                target_audience=TargetAudience.ADULTS,
                examples=["2024 Goal Planner: Monthly & Weekly Planning for Success"],
                seo_strength=0.88
            ),
            TitleTemplate(
                pattern="The {adjective} {primary_keyword} Planner: {benefit} System",
                style=ListingStyle.PROFESSIONAL,
                target_audience=TargetAudience.PROFESSIONALS,
                examples=["The Complete Business Planner: Strategic Growth System"],
                seo_strength=0.85
            )
        ],
        ContentType.WORKBOOK: [
            TitleTemplate(
                pattern="{primary_keyword} Workbook: {unique_angle} for {audience}",
                style=ListingStyle.EDUCATIONAL,
                target_audience=TargetAudience.STUDENTS,
                examples=["Math Practice Workbook: Essential Skills for Grade 3"],
                seo_strength=0.82
            ),
            TitleTemplate(
                pattern="Master {primary_keyword}: {benefit} Workbook with {feature}",
                style=ListingStyle.PROFESSIONAL,
                target_audience=TargetAudience.ADULTS,
                examples=["Master Public Speaking: Confidence Building Workbook with Exercises"],
                seo_strength=0.87
            )
        ]
    }
    
    # Word banks for title generation
    ADJECTIVES = {
        ListingStyle.PROFESSIONAL: ["Complete", "Ultimate", "Comprehensive", "Advanced", "Strategic"],
        ListingStyle.CREATIVE: ["Beautiful", "Inspiring", "Elegant", "Artistic", "Unique"],
        ListingStyle.EDUCATIONAL: ["Essential", "Fundamental", "Complete", "Step-by-Step", "Practical"],
        ListingStyle.INSPIRATIONAL: ["Transformative", "Life-Changing", "Empowering", "Motivational", "Uplifting"],
        ListingStyle.PRACTICAL: ["Daily", "Simple", "Effective", "Proven", "Easy"]
    }
    
    UNIQUE_ANGLES = {
        ContentType.JOURNAL: [
            "Daily Prompts and Reflections",
            "Guided Self-Discovery",
            "Mindful Living Practices",
            "Personal Growth Journey",
            "Habit Tracking and Goals"
        ],
        ContentType.PLANNER: [
            "Monthly and Weekly Planning",
            "Goal Setting and Achievement",
            "Time Management System",
            "Productivity and Focus",
            "Life Organization Method"
        ],
        ContentType.WORKBOOK: [
            "Step-by-Step Exercises",
            "Practice Problems and Solutions",
            "Skill Building Activities",
            "Interactive Learning",
            "Hands-On Practice"
        ]
    }
    
    @classmethod
    def generate_titles(
        cls,
        primary_keyword: str,
        content_type: ContentType,
        target_audience: TargetAudience,
        style_preference: Optional[ListingStyle] = None,
        additional_keywords: Optional[List[str]] = None,
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate multiple title options."""
        titles = []
        templates = cls.TITLE_TEMPLATES.get(content_type, [])
        
        if not templates:
            # Fallback generic template
            templates = [TitleTemplate(
                pattern="{primary_keyword} {book_type}: {unique_angle}",
                style=ListingStyle.PRACTICAL,
                target_audience=TargetAudience.GENERAL,
                examples=[],
                seo_strength=0.75
            )]
        
        # Filter templates by style preference
        if style_preference:
            templates = [t for t in templates if t.style == style_preference]
        
        # Generate titles from templates
        for template in templates[:count]:
            title_data = cls._generate_from_template(
                template, primary_keyword, content_type, target_audience, additional_keywords
            )
            titles.append(title_data)
        
        # Sort by SEO strength
        titles.sort(key=lambda x: x["seo_score"], reverse=True)
        
        return titles[:count]
    
    @classmethod
    def _generate_from_template(
        cls,
        template: TitleTemplate,
        primary_keyword: str,
        content_type: ContentType,
        target_audience: TargetAudience,
        additional_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate a title from a specific template."""
        # Get word banks
        adjectives = cls.ADJECTIVES.get(template.style, cls.ADJECTIVES[ListingStyle.PRACTICAL])
        unique_angles = cls.UNIQUE_ANGLES.get(content_type, ["Comprehensive Guide"])
        
        # Select words
        adjective = adjectives[0]  # Use first (most relevant) adjective
        unique_angle = unique_angles[0]  # Use first unique angle
        
        # Map content type to book type
        book_type_map = {
            ContentType.JOURNAL: "Journal",
            ContentType.PLANNER: "Planner",
            ContentType.WORKBOOK: "Workbook",
            ContentType.NOTEBOOK: "Notebook",
            ContentType.LOG_BOOK: "Log Book"
        }
        book_type = book_type_map.get(content_type, "Book")
        
        # Map target audience to readable format
        audience_map = {
            TargetAudience.CHILDREN: "Kids",
            TargetAudience.TEENS: "Teens",
            TargetAudience.ADULTS: "Adults",
            TargetAudience.SENIORS: "Seniors",
            TargetAudience.PROFESSIONALS: "Professionals",
            TargetAudience.STUDENTS: "Students",
            TargetAudience.GENERAL: "Everyone"
        }
        audience = audience_map.get(target_audience, "Adults")
        
        # Generate title
        title = template.pattern.format(
            primary_keyword=primary_keyword.title(),
            adjective=adjective,
            unique_angle=unique_angle,
            book_type=book_type,
            audience=audience,
            year=datetime.now().year,
            benefit="Enhanced Productivity",  # Default benefit
            timeframe="30 Days"  # Default timeframe
        )
        
        # Calculate SEO score
        seo_score = cls._calculate_title_seo_score(title, primary_keyword, additional_keywords)
        
        # Ensure title meets KDP requirements
        title = cls._optimize_title_length(title)
        
        return {
            "title": title,
            "template_style": template.style.value,
            "seo_score": seo_score,
            "character_count": len(title),
            "keyword_density": cls._calculate_keyword_density(title, primary_keyword),
            "readability": cls._assess_title_readability(title)
        }
    
    @classmethod
    def _calculate_title_seo_score(cls, title: str, primary_keyword: str, 
                                  additional_keywords: Optional[List[str]] = None) -> float:
        """Calculate SEO score for a title."""
        score = 0.0
        title_lower = title.lower()
        
        # Primary keyword presence (40% of score)
        if primary_keyword.lower() in title_lower:
            score += 40
            # Bonus for keyword at beginning
            if title_lower.startswith(primary_keyword.lower()):
                score += 10
        
        # Additional keywords (30% of score)
        if additional_keywords:
            keyword_count = sum(1 for kw in additional_keywords if kw.lower() in title_lower)
            score += min(30, keyword_count * 10)
        
        # Title length optimization (20% of score)
        title_length = len(title)
        if 30 <= title_length <= 60:  # Optimal length
            score += 20
        elif 20 <= title_length <= 80:  # Acceptable length
            score += 15
        else:
            score += 5
        
        # Readability and appeal (10% of score)
        word_count = len(title.split())
        if 3 <= word_count <= 8:  # Good word count
            score += 10
        elif word_count <= 12:
            score += 5
        
        return min(100, score)
    
    @classmethod
    def _calculate_keyword_density(cls, title: str, keyword: str) -> float:
        """Calculate keyword density in title."""
        title_words = title.lower().split()
        keyword_words = keyword.lower().split()
        
        if not title_words or not keyword_words:
            return 0.0
        
        # Count keyword occurrences
        keyword_count = 0
        for i in range(len(title_words) - len(keyword_words) + 1):
            if title_words[i:i+len(keyword_words)] == keyword_words:
                keyword_count += 1
        
        return (keyword_count * len(keyword_words)) / len(title_words) * 100
    
    @classmethod
    def _assess_title_readability(cls, title: str) -> str:
        """Assess title readability."""
        word_count = len(title.split())
        avg_word_length = sum(len(word) for word in title.split()) / word_count if word_count > 0 else 0
        
        if word_count <= 6 and avg_word_length <= 6:
            return "excellent"
        elif word_count <= 8 and avg_word_length <= 8:
            return "good"
        elif word_count <= 12:
            return "fair"
        else:
            return "poor"
    
    @classmethod
    def _optimize_title_length(cls, title: str) -> str:
        """Ensure title meets KDP length requirements."""
        # KDP title limit is 200 characters
        if len(title) <= 200:
            return title
        
        # Truncate while preserving meaning
        words = title.split()
        truncated = ""
        for word in words:
            if len(truncated + " " + word) <= 197:  # Leave room for "..."
                truncated += (" " if truncated else "") + word
            else:
                break
        
        return truncated + "..." if truncated != title else title


class DescriptionGenerator:
    """Generates compelling book descriptions."""
    
    # Description templates by style
    DESCRIPTION_TEMPLATES = {
        ListingStyle.PROFESSIONAL: DescriptionTemplate(
            structure=[
                "hook", "problem_statement", "solution_overview", 
                "key_features", "benefits", "target_audience", "call_to_action"
            ],
            style=ListingStyle.PROFESSIONAL,
            word_count_range=(150, 250),
            conversion_elements=["social_proof", "urgency", "guarantee"]
        ),
        ListingStyle.CREATIVE: DescriptionTemplate(
            structure=[
                "emotional_hook", "story_element", "transformation", 
                "unique_features", "emotional_benefits", "call_to_action"
            ],
            style=ListingStyle.CREATIVE,
            word_count_range=(120, 200),
            conversion_elements=["emotional_appeal", "visualization", "community"]
        ),
        ListingStyle.EDUCATIONAL: DescriptionTemplate(
            structure=[
                "learning_objective", "curriculum_overview", "methodology", 
                "skill_outcomes", "target_learners", "call_to_action"
            ],
            style=ListingStyle.EDUCATIONAL,
            word_count_range=(180, 280),
            conversion_elements=["credibility", "progress_tracking", "results"]
        )
    }
    
    # Content blocks for different sections
    CONTENT_BLOCKS = {
        "hook": {
            ContentType.JOURNAL: [
                "Transform your daily routine with intentional reflection and mindful living.",
                "Discover the power of journaling to unlock your potential and create lasting change.",
                "Start each day with purpose and end it with gratitude using this comprehensive journal."
            ],
            ContentType.PLANNER: [
                "Take control of your time and achieve your biggest goals with strategic planning.",
                "Turn your dreams into actionable plans with this comprehensive planning system.",
                "Master productivity and create the life you want with proven planning methods."
            ]
        },
        "problem_statement": {
            "general": [
                "Feeling overwhelmed by daily tasks and long-term goals?",
                "Struggling to maintain consistency in your personal development?",
                "Ready to break free from unproductive habits and create positive change?"
            ]
        },
        "solution_overview": {
            ContentType.JOURNAL: [
                "This thoughtfully designed journal provides the structure and guidance you need.",
                "Combining proven techniques with beautiful design, this journal makes reflection effortless."
            ],
            ContentType.PLANNER: [
                "This comprehensive planner system breaks down complex goals into manageable steps.",
                "With monthly, weekly, and daily planning pages, you'll stay organized and focused."
            ]
        }
    }
    
    @classmethod
    def generate_description(
        cls,
        title: str,
        content_type: ContentType,
        target_audience: TargetAudience,
        primary_keyword: str,
        unique_features: List[str],
        style: ListingStyle = ListingStyle.PROFESSIONAL,
        include_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate a compelling book description."""
        template = cls.DESCRIPTION_TEMPLATES.get(style, cls.DESCRIPTION_TEMPLATES[ListingStyle.PROFESSIONAL])
        
        # Build description sections
        sections = []
        for section_type in template.structure:
            section_content = cls._generate_section(
                section_type, content_type, target_audience, primary_keyword, unique_features
            )
            if section_content:
                sections.append(section_content)
        
        # Combine sections
        description = "\n\n".join(sections)
        
        # Optimize for keywords
        if include_keywords:
            description = cls._optimize_keyword_placement(description, include_keywords)
        
        # Ensure compliance with KDP requirements
        description = cls._ensure_kdp_compliance(description)
        
        # Calculate metrics
        metrics = cls._calculate_description_metrics(description, primary_keyword, include_keywords)
        
        return {
            "description": description,
            "word_count": len(description.split()),
            "character_count": len(description),
            "style": style.value,
            "seo_score": metrics["seo_score"],
            "readability_score": metrics["readability_score"],
            "conversion_elements": template.conversion_elements,
            "compliance_check": cls._check_kdp_compliance(description)
        }
    
    @classmethod
    def _generate_section(
        cls,
        section_type: str,
        content_type: ContentType,
        target_audience: TargetAudience,
        primary_keyword: str,
        unique_features: List[str]
    ) -> str:
        """Generate content for a specific section."""
        if section_type == "hook":
            hooks = cls.CONTENT_BLOCKS["hook"].get(content_type, [
                f"Discover the power of {primary_keyword.lower()} to transform your daily routine."
            ])
            return hooks[0]
        
        elif section_type == "problem_statement":
            problems = cls.CONTENT_BLOCKS["problem_statement"]["general"]
            return problems[0]
        
        elif section_type == "solution_overview":
            solutions = cls.CONTENT_BLOCKS["solution_overview"].get(content_type, [
                f"This comprehensive {content_type.value.lower()} provides everything you need."
            ])
            return solutions[0]
        
        elif section_type == "key_features":
            if unique_features:
                features_text = "\n".join([f"• {feature}" for feature in unique_features[:5]])
                return f"Key Features:\n{features_text}"
            return "Designed with your success in mind, featuring intuitive layouts and proven methodologies."
        
        elif section_type == "benefits":
            return cls._generate_benefits_section(content_type, target_audience)
        
        elif section_type == "target_audience":
            return cls._generate_audience_section(target_audience, content_type)
        
        elif section_type == "call_to_action":
            return "Start your transformation today. Order now and begin your journey to success!"
        
        return ""
    
    @classmethod
    def _generate_benefits_section(cls, content_type: ContentType, target_audience: udience) -> str:
        """Generate benefits section based on content type and audience."""
        benefits_map = {
            ContentType.JOURNAL: [
                "Develop greater self-awareness and emotional intelligence",
                "Build consistent reflection habits that stick",
                "Track your progress and celebrate your growth",
                "Reduce stress and increase mental clarity"
            ],
            ContentType.PLANNER: [
                "Achieve your goals faster with strategic planning",
                "Improve time management and productivity",
                "Reduce overwhelm and increase focus",
                "Create better work-life balance"
            ],
            ContentType.WORKBOOK: [
                "Master new skills through hands-on practice",
                "Build confidence with step-by-step guidance",
                "Track your learning progress effectively",
                "Apply knowledge immediately for better retention"
            ]
        }
        
        benefits = benefits_map.get(content_type, ["Achieve your goals with this comprehensive resource"])
        return "What You'll Gain:\n" + "\n".join([f"• {benefit}" for benefit in benefits[:4]])
    
    @classmethod
    def _generate_audience_section(cls, target_audience: TargetAudience, content_type: ContentType) -> str:
        """Generate target audience section."""
        audience_descriptions = {
            TargetAudience.PROFESSIONALS: "Perfect for busy professionals seeking to optimize their productivity and achieve career goals.",
            TargetAudience.STUDENTS: "Ideal for students looking to improve study habits and academic performance.",
            TargetAudience.ADULTS: "Designed for adults ready to take control of their personal development journey.",
            TargetAudience.GENERAL: "Suitable for anyone committed to personal growth and positive change."
        }
        
        return audience_descriptions.get(target_audience, 
            f"Perfect for anyone interested in {content_type.value.lower().replace('_', ' ')} and personal development.")
    
    @classmethod
    def _optimize_keyword_placement(cls, description: str, keywords: List[str]) -> str:
        """Optimize keyword placement in description."""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated NLP-based optimization
        optimized = description
        
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            if keyword.lower() not in optimized.lower():
                # Try to naturally incorporate the keyword
                optimized = optimized.replace(
                    "personal development", 
                    f"{keyword} and personal development", 
                    1
                )
        
        return optimized
    
    @classmethod
    def _ensure_kdp_compliance(cls, description: str) -> str:
        """Ensure description complies with KDP guidelines."""
        # Remove any prohibited content
        prohibited_phrases = [
            "best seller", "#1 bestseller", "award winning",
            "reviews", "rating", "customer feedback"
        ]
        
        cleaned = description
        for phrase in prohibited_phrases:
            cleaned = re.sub(phrase, "", cleaned, flags=re.IGNORECASE)
        
        # Ensure length limits (4000 characters for KDP)
        if len(cleaned) > 4000:
            cleaned = cleaned[:3997] + "..."
        
        return cleaned.strip()
    
    @classmethod
    def _calculate_description_metrics(cls, description: str, primary_keyword: str, 
                                     keywords: Optional[List[str]] = None) -> Dict[str, float]:
        """Calculate various metrics for the description."""
        words = description.split()
        word_count = len(words)
        
        # SEO Score
        seo_score = 0
        if primary_keyword.lower() in description.lower():
            seo_score += 30
        
        if keywords:
            keyword_count = sum(1 for kw in keywords if kw.lower() in description.lower())
            seo_score += min(40, keyword_count * 10)
        
        # Length optimization
        if 150 <= word_count <= 250:
            seo_score += 20
        elif 100 <= word_count <= 300:
            seo_score += 15
        
        # Structure bonus
        if "•" in description:  # Has bullet points
            seo_score += 10
        
        # Readability Score (simplified)
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        sentences = description.count('.') + description.count('!') + description.count('?')
        avg_sentence_length = word_count / sentences if sentences > 0 else word_count
        
        readability_score = 100
        if avg_word_length > 6:
            readability_score -= 10
        if avg_sentence_length > 20:
            readability_score -= 15
        
        return {
            "seo_score": min(100, seo_score),
            "readability_score": max(0, readability_score)
        }
    
    @classmethod
    def _check_kdp_compliance(cls, description: str) -> Dict[str, bool]:
        """Check KDP compliance requirements."""
        return {
            "length_compliant": len(description) <= 4000,
            "no_prohibited_content": not any(phrase in description.lower() for phrase in [
                "best seller", "#1", "award", "review", "rating"
            ]),
            "proper_formatting": "\n" in description,  # Has paragraph breaks
            "call_to_action_present": any(phrase in description.lower() for phrase in [
                "order", "buy", "get", "start", "begin"
            ])
        }


async def generate_kdp_listing(
    trends_client: Optional[TrendsClient],
    keepa_client: Optional[KeepaClient],
    cache_manager: CacheManager,
    niche: Niche,
    content_type: ContentType,
    target_audience: TargetAudience,
    unique_angle: str,
    style_preference: Optional[str] = None,
    include_pricing: bool = True
) -> Dict[str, Any]:
    """Generate a complete KDP listing.
    
    Args:
        trends_client: Google Trends client for keyword validation
        keepa_client: Keepa client for pricing analysis
        cache_manager: Cache manager for performance
        niche: Niche data for the listing
        content_type: Type of content (journal, planner, etc.)
        target_audience: Target audience for the book
        unique_angle: Unique selling proposition
        style_preference: Preferred listing style
        include_pricing: Whether to include pricing recommendations
    
    Returns:
        Dictionary containing complete listing data
    """
    logger.info(f"Generating KDP listing for niche: {niche.primary_keyword}")
    
    try:
        # Parse style preference
        style = ListingStyle.PROFESSIONAL
        if style_preference:
            try:
                style = ListingStyle(style_preference.lower())
            except ValueError:
                logger.warning(f"Invalid style preference: {style_preference}")
        
        # Generate titles
        title_options = TitleGenerator.generate_titles(
            primary_keyword=niche.primary_keyword,
            content_type=content_type,
            target_audience=target_audience,
            style_preference=style,
            additional_keywords=niche.keywords[:5],
            count=3
        )
        
        # Select best title
        best_title = title_options[0]["title"] if title_options else f"{niche.primary_keyword.title()} {content_type.value.title()}"
        
        # Prepare unique features
        unique_features = [
            unique_angle,
            f"Optimized for {target_audience.value.replace('_', ' ')}",
            "High-quality design and layout",
            "Proven methodology and structure"
        ]
        
        # Generate description
        description_data = DescriptionGenerator.generate_description(
            title=best_title,
            content_type=content_type,
            target_audience=target_audience,
            primary_keyword=niche.primary_keyword,
            unique_features=unique_features,
            style=style,
            include_keywords=niche.keywords[:7]
        )
        
        # Generate keyword recommendations
        keyword_recommendations = await _generate_keyword_recommendations(
            trends_client, niche, content_type, target_audience
        )
        
        # Generate category recommendations
        category_recommendations = _generate_category_recommendations(
            content_type, target_audience, niche.category
        )
        
        # Generate pricing recommendations
        pricing_data = None
        if include_pricing and keepa_client:
            pricing_data = await _generate_pricing_recommendations(
                keepa_client, niche, content_type
            )
        
        # Create KDP listing object
        kdp_listing = KDPListing(
            title=best_title,
            description=description_data["description"],
            keywords=keyword_recommendations["primary_keywords"],
            categories=category_recommendations["primary_categories"],
            content_type=content_type,
            target_audience=target_audience,
            pricing_tier="medium",  # Default
            unique_selling_points=[unique_angle] + unique_features[:3]
        )
        
        # Set pricing if available
        if pricing_data:
            kdp_listing.suggested_price = pricing_data["recommended_price"]
            kdp_listing.pricing_tier = pricing_data["pricing_tier"]
        
        # Compile final result
        result = {
            "listing": kdp_listing.to_dict(),
            "title_options": title_options,
            "description_analysis": {
                "word_count": description_data["word_count"],
                "seo_score": description_data["seo_score"],
                "readability_score": description_data["readability_score"],
                "compliance_check": description_data["compliance_check"]
            },
            "keyword_analysis": keyword_recommendations,
            "category_recommendations": category_recommendations,
            "pricing_analysis": pricing_data,
            "optimization_suggestions": _generate_optimization_suggestions(
                kdp_listing, niche, description_data
            ),
            "generation_metadata": {
                "niche_keyword": niche.primary_keyword,
                "content_type": content_type.value,
                "target_audience": target_audience.value,
                "style": style.value,
                "generation_timestamp": datetime.now().isoformat()
            }
        }
        
        logger.info(f"KDP listing generation completed for: {niche.primary_keyword}")
        return result
    
    except Exception as e:
        logger.error(f"KDP listing generation failed: {e}")
        return {
            "error": str(e),
            "niche_keyword": niche.primary_keyword if niche else "unknown",
            "generation_timestamp": datetime.now().isoformat()
        }


async def _generate_keyword_recommendations(
    trends_client: Optional[TrendsClient],
    niche: Niche,
    content_type: ContentType,
    target_audience: TargetAudience
) -> Dict[str, Any]:
    """Generate keyword recommendations for the listing."""
    primary_keywords = [niche.primary_keyword] + niche.keywords[:6]
    
    # Add content-type specific keywords
    content_keywords = {
        ContentType.JOURNAL: ["journal", "diary", "notebook", "reflection", "mindfulness"],
        ContentType.PLANNER: ["planner", "organizer", "schedule", "productivity", "goals"],
        ContentType.WORKBOOK: ["workbook", "exercises", "practice", "learning", "skills"]
    }
    
    type_keywords = content_keywords.get(content_type, [])
    
    # Add audience-specific keywords
    audience_keywords = {
        TargetAudience.PROFESSIONALS: ["professional", "business", "career", "workplace"],
        TargetAudience.STUDENTS: ["student", "study", "academic", "learning"],
        TargetAudience.CHILDREN: ["kids", "children", "fun", "colorful"]
    }
    
    audience_kws = audience_keywords.get(target_audience, [])
    
    # Combine and deduplicate
    all_keywords = list(set(primary_keywords + type_keywords + audience_kws))
    
    # Validate keywords with trends if available
    validated_keywords = all_keywords[:7]  # KDP limit
    trend_scores = {}
    
    if trends_client:
        try:
            for keyword in validated_keywords[:5]:  # Limit API calls
                trend_analysis = await trends_client.get_trend_analysis(keyword)
                if trend_analysis:
                    trend_scores[keyword] = trend_analysis.trend_score
        except Exception as e:
            logger.warning(f"Trend validation failed: {e}")
    
    return {
        "primary_keywords": validated_keywords,
        "trend_scores": trend_scores,
        "keyword_suggestions": {
            "content_type_keywords": type_keywords,
            "audience_keywords": audience_kws,
            "niche_keywords": niche.keywords[:10]
        }
    }


def _generate_category_recommendations(
    content_type: ContentType,
    target_audience: TargetAudience,
    niche_category: str
) -> Dict[str, Any]:
    """Generate Amazon category recommendations."""
    # Base categories by content type
    base_categories = {
        ContentType.JOURNAL: [
            "Books > Self-Help > Journal Writing",
            "Books > Health, Fitness & Dieting > Mental Health",
            "Office Products > Office & School Supplies > Calendars, Planners & Personal Organizers"
        ],
        ContentType.PLANNER: [
            "Office Products > Office & School Supplies > Calendars, Planners & Personal Organizers",
            "Books > Business & Money > Management & Leadership",
            "Books > Self-Help > Time Management"
        ],
        ContentType.WORKBOOK: [
            "Books > Education & Teaching > Schools & Teaching",
            "Books > Children's Books > Education & Reference",
            "Books > Test Preparation"
        ]
    }
    
    primary_categories = base_categories.get(content_type, [
        "Books > Self-Help",
        "Office Products > Office & School Supplies"
    ])
    
    # Audience-specific category adjustments
    if target_audience == TargetAudience.CHILDREN:
        primary_categories = [cat for cat in primary_categories if "Children" in cat or "Education" in cat]
        if not primary_categories:
            primary_categories = ["Books > Children's Books"]
    
    elif target_audience == TargetAudience.PROFESSIONALS:
        business_categories = [cat for cat in primary_categories if "Business" in cat or "Management" in cat]
        if business_categories:
            primary_categories = business_categories + primary_categories[:1]
    
    return {
        "primary_categories": primary_categories[:2],  # Amazon allows 2 categories
        "alternative_categories": primary_categories[2:5],
        "category_rationale": f"Selected based on {content_type.value} type and {target_audience.value} audience"
    }


async def _generate_pricing_recommendations(
    keepa_client: KeepaClient,
    niche: Niche,
    content_type: ContentType
) -> Dict[str, Any]:
    """Generate pricing recommendations based on market analysis."""
    try:
        # Search for similar products
        search_query = f"{niche.primary_keyword} {content_type.value.replace('_', ' ')}"
        similar_products = await keepa_client.search_products(search_query, limit=20)
        
        if not similar_products:
            # Fallback pricing
            return {
                "recommended_price": 9.99,
                "pricing_tier": "medium",
                "price_range": {"min": 5.99, "max": 14.99},
                "confidence": "low",
                "note": "No market data available - using default pricing"
            }
        
        # Analyze pricing
        prices = [p.current_price for p in similar_products if p.current_price and p.current_price > 0]
        
        if not prices:
            return {
                "recommended_price": 9.99,
                "pricing_tier": "medium",
                "price_range": {"min": 5.99, "max": 14.99},
                "confidence": "low",
                "note": "No valid pricing data found"
            }
        
        # Calculate pricing metrics
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        median_price = sorted(prices)[len(prices) // 2]
        
        # Determine recommended price (slightly below median for competitive advantage)
        recommended_price = max(5.99, median_price * 0.95)
        
        # Determine pricing tier
        if recommended_price <= 7.99:
            pricing_tier = "budget"
        elif recommended_price <= 12.99:
            pricing_tier = "medium"
        else:
            pricing_tier = "premium"
        
        return {
            "recommended_price": round(recommended_price, 2),
            "pricing_tier": pricing_tier,
            "price_range": {"min": round(min_price, 2), "max": round(max_price, 2)},
            "market_average": round(avg_price, 2),
            "market_median": round(median_price, 2),
            "analyzed_products": len(prices),
            "confidence": "high" if len(prices) >= 10 else "medium",
            "pricing_strategy": "Competitive positioning below median price"
        }
    
    except Exception as e:
        logger.warning(f"Pricing analysis failed: {e}")
        return {
            "recommended_price": 9.99,
            "pricing_tier": "medium",
            "error": str(e)
        }


def _generate_optimization_suggestions(
    listing: KDPListing,
    niche: Niche,
    description_data: Dict[str, Any]
) -> List[str]:
    """Generate optimization suggestions for the listing."""
    suggestions = []
    
    # Title optimization
    if len(listing.title) < 30:
        suggestions.append("Consider expanding the title to include more relevant keywords")
    elif len(listing.title) > 100:
        suggestions.append("Consider shortening the title for better readability")
    
    # Description optimization
    if description_data["seo_score"] < 70:
        suggestions.append("Improve SEO by incorporating more relevant keywords naturally")
    
    if description_data["readability_score"] < 70:
        suggestions.append("Improve readability by using shorter sentences and simpler words")
    
    # Keyword optimization
    if len(listing.keywords) < 7:
        suggestions.append("Add more relevant keywords to maximize discoverability")
    
    # Pricing optimization
    if hasattr(listing, 'suggested_price') and listing.suggested_price:
        if listing.suggested_price < 5.99:
            suggestions.append("Consider higher pricing to improve perceived value")
        elif listing.suggested_price > 19.99:
            suggestions.append("Consider lower pricing to improve accessibility")
    
    # Niche-specific suggestions
    if niche.competition_level and niche.competition_level.value == "high":
        suggestions.append("Focus on unique differentiation due to high competition")
    
    if niche.profitability_score < 70:
        suggestions.append("Consider targeting a more profitable niche or improving positioning")
    
    return suggestions