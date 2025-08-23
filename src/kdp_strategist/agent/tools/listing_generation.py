"""
Listing generation and optimization tools for KDP books.
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import random
from datetime import datetime

from ...models.niche_model import Niche, CompetitionLevel


@dataclass
class ListingOptimizationConfig:
    """Configuration for listing optimization."""
    max_title_length: int = 200
    max_description_length: int = 4000
    max_keywords: int = 7
    target_seo_score: float = 80.0


class ListingGenerator:
    """Generate optimized KDP book listings."""
    
    def __init__(self, config: Optional[ListingOptimizationConfig] = None):
        self.config = config or ListingOptimizationConfig()
        self.title_templates = {
            'journal': [
                "The {keyword} Journal: {subtitle}",
                "{keyword} Daily Journal for {audience}",
                "The Ultimate {keyword} Journal: {subtitle}"
            ],
            'workbook': [
                "The {keyword} Workbook: {subtitle}",
                "{keyword} Workbook for {audience}",
                "Complete {keyword} Workbook: {subtitle}"
            ],
            'guide': [
                "The {keyword} Guide: {subtitle}",
                "{keyword} for {audience}: {subtitle}",
                "The Complete Guide to {keyword}: {subtitle}"
            ],
            'planner': [
                "The {keyword} Planner: {subtitle}",
                "{keyword} Daily Planner for {audience}",
                "Ultimate {keyword} Planner: {subtitle}"
            ]
        }
        
        self.subtitle_templates = [
            "A Step-by-Step Guide to {benefit}",
            "Transform Your {area} with Proven Strategies",
            "Daily Practices for {benefit}",
            "Achieve {goal} in 30 Days",
            "The Essential Guide for {audience}"
        ]
    
    def generate_title(self, niche: Niche, target_audience: str, book_type: str, 
                      include_keywords: Optional[List[str]] = None,
                      unique_angle: Optional[str] = None) -> str:
        """Generate optimized book title."""
        templates = self.title_templates.get(book_type, self.title_templates['guide'])
        template = random.choice(templates)
        
        # Generate subtitle
        subtitle = self._generate_subtitle(niche, target_audience, unique_angle)
        
        # Format title
        title = template.format(
            keyword=niche.primary_keyword.title(),
            audience=target_audience.title(),
            subtitle=subtitle
        )
        
        # Clean up redundant words
        title = self._clean_redundant_words(title)
        
        # Add additional keywords if specified
        if include_keywords:
            for keyword in include_keywords[:2]:  # Limit to 2 additional
                if keyword.lower() not in title.lower() and len(title) < 150:
                    title = f"{title} - {keyword.title()}"
        
        # Ensure title length is within limits
        if len(title) > self.config.max_title_length:
            title = title[:self.config.max_title_length-3] + "..."
        
        return title
    
    def generate_description(self, niche: Niche, target_audience: str, book_type: str,
                           title: str, key_features: Optional[List[str]] = None,
                           unique_angle: Optional[str] = None) -> str:
        """Generate optimized book description."""
        description_parts = []
        
        # Opening hook
        hook = self._generate_opening_hook(niche, target_audience, book_type)
        description_parts.append(hook)
        
        # Main benefits
        benefits = self._generate_benefits_section(niche, target_audience, book_type)
        description_parts.append(benefits)
        
        # Features section
        if key_features:
            features_text = self._generate_features_section(key_features)
            description_parts.append(features_text)
        else:
            default_features = self._generate_default_features(book_type)
            features_text = self._generate_features_section(default_features)
            description_parts.append(features_text)
        
        # Target audience section
        audience_section = self._generate_audience_section(target_audience)
        description_parts.append(audience_section)
        
        # Call to action
        cta = self._generate_call_to_action(niche.primary_keyword, book_type)
        description_parts.append(cta)
        
        description = "\n\n".join(description_parts)
        
        # Ensure description length is within limits
        if len(description) > self.config.max_description_length:
            description = description[:self.config.max_description_length-3] + "..."
        
        return description
    
    def generate_html_description(self, niche: Niche, target_audience: str, book_type: str,
                                title: str, key_features: Optional[List[str]] = None,
                                unique_angle: Optional[str] = None) -> str:
        """Generate HTML-formatted book description for better presentation."""
        # Opening hook
        hook = self._generate_opening_hook(niche, target_audience, book_type)
        
        # Main benefits
        benefits = self._generate_benefits_list(niche, target_audience, book_type)
        
        # Features section
        if key_features:
            features = key_features
        else:
            features = self._generate_default_features(book_type)
        
        # Target audience section
        audience_section = self._generate_audience_section(target_audience)
        
        # Call to action
        cta = self._generate_call_to_action(niche.primary_keyword, book_type)
        
        # Build HTML description
        html_parts = [
            f"<p><strong>{hook}</strong></p>",
            "<p><strong>What you'll gain from this " + book_type + ":</strong></p>",
            "<ul>"
        ]
        
        for benefit in benefits:
            html_parts.append(f"<li>{benefit}</li>")
        
        html_parts.extend([
            "</ul>",
            "<p><strong>Key Features:</strong></p>",
            "<ul>"
        ])
        
        for feature in features:
            html_parts.append(f"<li>{feature}</li>")
        
        html_parts.extend([
            "</ul>",
            f"<p>{audience_section}</p>",
            f"<p><strong>{cta}</strong></p>"
        ])
        
        html_description = "\n".join(html_parts)
        
        # Ensure description length is within limits
        if len(html_description) > self.config.max_description_length:
            html_description = html_description[:self.config.max_description_length-3] + "..."
        
        return html_description
    
    def generate_keywords_list(self, niche: Niche, target_audience: str, book_type: str,
                             max_keywords: Optional[int] = None) -> List[str]:
        """Generate optimized keywords list."""
        max_kw = max_keywords or self.config.max_keywords
        keywords = []
        
        # Primary keyword
        keywords.append(niche.primary_keyword)
        
        # Niche keywords (avoid duplicates)
        for kw in niche.keywords[:3]:
            if kw not in keywords and kw.lower() != niche.primary_keyword.lower():
                keywords.append(kw)
        
        # Book type variations
        book_type_keywords = [
            f"{niche.primary_keyword} {book_type}",
            f"{book_type} for {target_audience}",
            f"daily {niche.primary_keyword}"
        ]
        
        for kw in book_type_keywords:
            if len(keywords) >= max_kw:
                break
            if kw not in keywords and not self._is_duplicate_keyword(kw, keywords):
                keywords.append(kw)
        
        # Additional relevant keywords
        additional_keywords = [
            f"{niche.primary_keyword} guide",
            f"{target_audience} {niche.primary_keyword}",
            f"self help {book_type}"
        ]
        
        for kw in additional_keywords:
            if len(keywords) >= max_kw:
                break
            if kw not in keywords and len(kw) <= 50 and not self._is_duplicate_keyword(kw, keywords):
                keywords.append(kw)
        
        return keywords[:max_kw]
    
    def generate_categories(self, niche: Niche, book_type: str) -> List[str]:
        """Generate appropriate categories for the book."""
        primary_category = niche.category
        
        # Map to Amazon categories
        category_mapping = {
            'Self-Help': 'Self-Help',
            'Business': 'Business & Money',
            'Health': 'Health, Fitness & Dieting',
            'Education': 'Education & Teaching',
            'Fiction': 'Literature & Fiction'
        }
        
        primary = category_mapping.get(primary_category, 'Self-Help')
        
        # Secondary category based on book type
        secondary_mapping = {
            'journal': 'Self-Help > Journal Writing',
            'workbook': 'Education & Teaching > Studying & Workbooks',
            'guide': 'Self-Help > Personal Transformation',
            'planner': 'Business & Money > Skills'
        }
        
        secondary = secondary_mapping.get(book_type, 'Self-Help')
        
        return [primary, secondary] if primary != secondary else [primary]
    
    def generate_complete_listing(self, niche: Niche, target_audience: str, book_type: str,
                                additional_keywords: Optional[List[str]] = None,
                                key_features: Optional[List[str]] = None,
                                unique_angle: Optional[str] = None) -> Dict[str, Any]:
        """Generate complete optimized listing."""
        title = self.generate_title(niche, target_audience, book_type, additional_keywords, unique_angle)
        description = self.generate_description(niche, target_audience, book_type, title, key_features, unique_angle)
        html_description = self.generate_html_description(niche, target_audience, book_type, title, key_features, unique_angle)
        keywords = self.generate_keywords_list(niche, target_audience, book_type)
        categories = self.generate_categories(niche, book_type)
        
        # Calculate SEO score
        seo_optimizer = SEOOptimizer()
        listing_data = {
            'title': title,
            'description': description,
            'keywords': keywords,
            'primary_keyword': niche.primary_keyword
        }
        seo_score = seo_optimizer.calculate_seo_score(listing_data)
        
        return {
            'title': title,
            'description': description,
            'html_description': html_description,
            'keywords': keywords,
            'categories': categories,
            'seo_score': seo_score,
            'character_counts': {
                'title': len(title),
                'description': len(description),
                'html_description': len(html_description)
            },
            'metadata': {
                'primary_keyword': niche.primary_keyword,
                'target_audience': target_audience,
                'book_type': book_type,
                'generation_timestamp': datetime.now().isoformat()
            }
        }
    
    def _generate_subtitle(self, niche: Niche, target_audience: str, unique_angle: Optional[str] = None) -> str:
        """Generate subtitle for the book."""
        templates = self.subtitle_templates
        template = random.choice(templates)
        
        benefit_mapping = {
            'productivity': 'Maximum Efficiency and Success',
            'time management': 'Better Time Control and Organization',
            'goal setting': 'Achievement and Success',
            'habits': 'Positive Life Changes',
            'mindfulness': 'Inner Peace and Clarity'
        }
        
        benefit = benefit_mapping.get(niche.primary_keyword.lower(), 'Personal Growth')
        
        # Use unique angle if provided
        if unique_angle:
            return f"{unique_angle} for {target_audience.title()}"
        
        return template.format(
            benefit=benefit,
            area=niche.primary_keyword.title(),
            goal='Success',
            audience=target_audience.title()
        )
    
    def _generate_opening_hook(self, niche: Niche, target_audience: str, book_type: str) -> str:
        """Generate compelling opening hook."""
        hooks = [
            f"Transform your {niche.primary_keyword} with this comprehensive {book_type} designed specifically for {target_audience}.",
            f"Discover the proven strategies that successful {target_audience} use to master {niche.primary_keyword}.",
            f"Are you ready to take your {niche.primary_keyword} to the next level? This {book_type} is your roadmap to success."
        ]
        return random.choice(hooks)
    
    def _generate_benefits_section(self, niche: Niche, target_audience: str, book_type: str) -> str:
        """Generate benefits section."""
        benefits = [
            f"• Proven strategies for improving your {niche.primary_keyword}",
            f"• Step-by-step guidance tailored for {target_audience}",
            f"• Practical exercises and actionable insights",
            f"• Real-world examples and case studies"
        ]
        
        return "What you'll gain from this " + book_type + ":\n\n" + "\n".join(benefits)
    
    def _generate_features_section(self, features: List[str]) -> str:
        """Generate features section."""
        formatted_features = [f"✓ {feature}" for feature in features]
        return "Key Features:\n\n" + "\n".join(formatted_features)
    
    def _generate_default_features(self, book_type: str) -> List[str]:
        """Generate default features based on book type."""
        feature_mapping = {
            'journal': [
                "Daily reflection prompts",
                "Goal tracking pages",
                "Progress monitoring sections",
                "Inspirational quotes"
            ],
            'workbook': [
                "Interactive exercises",
                "Worksheets and templates",
                "Self-assessment tools",
                "Action planning guides"
            ],
            'guide': [
                "Step-by-step instructions",
                "Expert tips and strategies",
                "Common pitfalls to avoid",
                "Success stories and examples"
            ],
            'planner': [
                "Daily planning pages",
                "Weekly and monthly overviews",
                "Goal setting templates",
                "Progress tracking charts"
            ]
        }
        
        return feature_mapping.get(book_type, feature_mapping['guide'])
    
    def _generate_audience_section(self, target_audience: str) -> str:
        """Generate target audience section."""
        return f"Perfect for {target_audience} who want to achieve more and create lasting positive change in their lives."
    
    def _generate_call_to_action(self, keyword: str, book_type: str) -> str:
        """Generate call to action."""
        ctas = [
            f"Start your {keyword} transformation today!",
            f"Get your copy now and begin your journey to success!",
            f"Don't wait - transform your {keyword} starting today!"
        ]
        return random.choice(ctas)
    
    def _clean_redundant_words(self, title: str) -> str:
        """Remove redundant words from title."""
        words = title.split()
        cleaned_words = []
        seen_words = set()
        
        for word in words:
            word_lower = word.lower().strip(':-')
            if word_lower not in seen_words:
                cleaned_words.append(word)
                seen_words.add(word_lower)
        
        return ' '.join(cleaned_words)
    
    def _is_duplicate_keyword(self, new_keyword: str, existing_keywords: List[str]) -> bool:
        """Check if a keyword is essentially a duplicate of existing ones."""
        new_words = set(new_keyword.lower().split())
        
        for existing in existing_keywords:
            existing_words = set(existing.lower().split())
            # If 80% or more words overlap, consider it a duplicate
            overlap = len(new_words.intersection(existing_words))
            if overlap / max(len(new_words), len(existing_words)) >= 0.8:
                return True
        
        return False
    
    def _generate_benefits_list(self, niche: Niche, target_audience: str, book_type: str) -> List[str]:
        """Generate list of benefits for HTML formatting."""
        return [
            f"Proven strategies for improving your {niche.primary_keyword}",
            f"Step-by-step guidance tailored for {target_audience}",
            f"Practical exercises and actionable insights",
            f"Real-world examples and case studies"
        ]


class SEOOptimizer:
    """SEO optimization for book listings."""
    
    def calculate_seo_score(self, listing_data: Dict[str, Any]) -> float:
        """Calculate SEO score for a listing."""
        score = 0.0
        max_score = 100.0
        
        title = listing_data.get('title', '')
        description = listing_data.get('description', '')
        keywords = listing_data.get('keywords', [])
        primary_keyword = listing_data.get('primary_keyword', '')
        
        # Title optimization (30 points)
        title_score = self._score_title_seo(title, primary_keyword)
        score += title_score * 0.3
        
        # Description optimization (25 points)
        desc_score = self._score_description_seo(description, primary_keyword, keywords)
        score += desc_score * 0.25
        
        # Keyword optimization (25 points)
        keyword_score = self._score_keywords_seo(keywords, primary_keyword)
        score += keyword_score * 0.25
        
        # Content quality (20 points)
        quality_score = self._score_content_quality(title, description)
        score += quality_score * 0.2
        
        return min(max_score, max(0, score))
    
    def optimize_title_for_seo(self, title: str, primary_keyword: str, 
                              secondary_keywords: List[str]) -> str:
        """Optimize title for SEO."""
        # Ensure primary keyword is at the beginning
        if not title.lower().startswith(primary_keyword.lower()):
            title = f"{primary_keyword.title()}: {title}"
        
        # Add secondary keywords if space allows
        for keyword in secondary_keywords[:2]:
            if keyword.lower() not in title.lower() and len(title) < 180:
                title = f"{title} - {keyword.title()}"
        
        return title[:200]  # Amazon limit
    
    def optimize_description_for_seo(self, description: str, primary_keyword: str,
                                   secondary_keywords: List[str]) -> str:
        """Optimize description for SEO."""
        # Ensure primary keyword appears in first paragraph
        if primary_keyword.lower() not in description[:200].lower():
            description = f"Master {primary_keyword} with this comprehensive guide. {description}"
        
        # Add secondary keywords naturally
        for keyword in secondary_keywords[:3]:
            if keyword.lower() not in description.lower():
                description += f" Perfect for anyone interested in {keyword}."
        
        return description
    
    def suggest_improvements(self, listing_data: Dict[str, Any]) -> List[str]:
        """Suggest SEO improvements."""
        suggestions = []
        
        title = listing_data.get('title', '')
        description = listing_data.get('description', '')
        keywords = listing_data.get('keywords', [])
        primary_keyword = listing_data.get('primary_keyword', '')
        
        # Title suggestions
        if primary_keyword.lower() not in title.lower():
            suggestions.append("Include primary keyword in title")
        
        if len(title) < 50:
            suggestions.append("Consider lengthening title for better keyword coverage")
        
        # Description suggestions
        keyword_density = self.calculate_keyword_density(description, primary_keyword)
        if keyword_density < 1.0:
            suggestions.append("Increase primary keyword density in description")
        elif keyword_density > 3.0:
            suggestions.append("Reduce keyword density to avoid over-optimization")
        
        # Keywords suggestions
        if len(keywords) < 5:
            suggestions.append("Add more relevant keywords")
        
        return suggestions
    
    def calculate_keyword_density(self, text: str, keyword: str) -> float:
        """Calculate keyword density percentage."""
        if not text or not keyword:
            return 0.0
        
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Count keyword occurrences
        keyword_count = text_lower.count(keyword_lower)
        
        # Count total words
        words = re.findall(r'\b\w+\b', text_lower)
        total_words = len(words)
        
        if total_words == 0:
            return 0.0
        
        return (keyword_count / total_words) * 100
    
    def optimize_against_competitors(self, primary_keyword: str, competitor_titles: List[str],
                                   book_type: str) -> str:
        """Generate title optimized against competitors."""
        # Analyze competitor patterns
        common_words = self._analyze_competitor_patterns(competitor_titles)
        
        # Generate differentiated title
        differentiators = ['Ultimate', 'Complete', 'Essential', 'Advanced', 'Practical']
        differentiator = random.choice([d for d in differentiators if d.lower() not in ' '.join(competitor_titles).lower()])
        
        title = f"The {differentiator} {primary_keyword.title()} {book_type.title()}"
        
        # Add unique angle
        unique_angles = ['Step-by-Step Guide', 'Proven Strategies', 'Daily Practices', '30-Day Challenge']
        angle = random.choice([a for a in unique_angles if a.lower() not in ' '.join(competitor_titles).lower()])
        
        title += f": {angle}"
        
        return title
    
    def _score_title_seo(self, title: str, primary_keyword: str) -> float:
        """Score title SEO optimization."""
        score = 0.0
        
        if primary_keyword.lower() in title.lower():
            score += 40
            
            # Bonus for keyword at beginning
            if title.lower().startswith(primary_keyword.lower()):
                score += 20
        
        # Length optimization
        if 50 <= len(title) <= 150:
            score += 20
        elif 30 <= len(title) <= 200:
            score += 10
        
        # Readability
        if ':' in title or '-' in title:
            score += 10  # Good structure
        
        # Avoid keyword stuffing
        keyword_count = title.lower().count(primary_keyword.lower())
        if keyword_count > 2:
            score -= 20
        
        return min(100, score)
    
    def _score_description_seo(self, description: str, primary_keyword: str, keywords: List[str]) -> float:
        """Score description SEO optimization."""
        score = 0.0
        
        # Primary keyword presence
        if primary_keyword.lower() in description.lower():
            score += 30
            
            # Keyword density
            density = self.calculate_keyword_density(description, primary_keyword)
            if 1.0 <= density <= 2.5:
                score += 20
            elif 0.5 <= density <= 3.0:
                score += 10
        
        # Secondary keywords
        secondary_count = sum(1 for kw in keywords[1:5] if kw.lower() in description.lower())
        score += min(25, secondary_count * 5)
        
        # Length
        if 200 <= len(description) <= 2000:
            score += 15
        elif 100 <= len(description) <= 3000:
            score += 10
        
        # Structure (paragraphs, bullets)
        if '•' in description or '✓' in description:
            score += 10
        
        return min(100, score)
    
    def _score_keywords_seo(self, keywords: List[str], primary_keyword: str) -> float:
        """Score keywords SEO optimization."""
        score = 0.0
        
        # Primary keyword included
        if primary_keyword in keywords:
            score += 30
        
        # Keyword count
        if 5 <= len(keywords) <= 7:
            score += 25
        elif 3 <= len(keywords) <= 8:
            score += 15
        
        # Keyword variety (different lengths)
        lengths = [len(kw.split()) for kw in keywords]
        if len(set(lengths)) >= 2:
            score += 20
        
        # Long-tail keywords
        long_tail_count = sum(1 for kw in keywords if len(kw.split()) >= 3)
        score += min(25, long_tail_count * 5)
        
        return min(100, score)
    
    def _score_content_quality(self, title: str, description: str) -> float:
        """Score overall content quality."""
        score = 0.0
        
        # Title quality
        if len(title.split()) >= 4:
            score += 20
        
        # Description quality
        if len(description.split()) >= 50:
            score += 20
        
        # Readability
        if description.count('.') >= 3:  # Multiple sentences
            score += 15
        
        # Professional language
        professional_words = ['proven', 'comprehensive', 'essential', 'ultimate', 'complete']
        if any(word in description.lower() for word in professional_words):
            score += 15
        
        # Call to action
        cta_words = ['start', 'begin', 'transform', 'achieve', 'discover']
        if any(word in description.lower() for word in cta_words):
            score += 15
        
        # Avoid excessive punctuation
        if description.count('!') <= 3:
            score += 15
        
        return min(100, score)
    
    def _analyze_competitor_patterns(self, competitor_titles: List[str]) -> List[str]:
        """Analyze common patterns in competitor titles."""
        all_words = []
        for title in competitor_titles:
            words = re.findall(r'\b\w+\b', title.lower())
            all_words.extend(words)
        
        # Count word frequency
        word_count = {}
        for word in all_words:
            word_count[word] = word_count.get(word, 0) + 1
        
        # Return most common words
        return sorted(word_count.keys(), key=lambda x: word_count[x], reverse=True)[:10]


class ContentAnalyzer:
    """Analyze content for gaps and opportunities."""
    
    def analyze_content_gaps(self, competitor_descriptions: List[str], niche_keywords: List[str]) -> List[str]:
        """Analyze content gaps in competitor descriptions."""
        gaps = []
        
        # Check for missing keywords
        for keyword in niche_keywords:
            mentioned_count = sum(1 for desc in competitor_descriptions if keyword.lower() in desc.lower())
            coverage = mentioned_count / len(competitor_descriptions) if competitor_descriptions else 0
            
            if coverage < 0.3:  # Less than 30% coverage
                gaps.append(f"Underutilized keyword: {keyword}")
        
        # Check for missing content themes
        content_themes = [
            'step-by-step', 'beginner', 'advanced', 'daily', 'weekly',
            'practical', 'proven', 'case studies', 'examples', 'templates'
        ]
        
        for theme in content_themes:
            mentioned_count = sum(1 for desc in competitor_descriptions if theme in desc.lower())
            coverage = mentioned_count / len(competitor_descriptions) if competitor_descriptions else 0
            
            if coverage < 0.2:  # Less than 20% coverage
                gaps.append(f"Missing content theme: {theme}")
        
        return gaps[:10]  # Return top 10 gaps
    
    def extract_content_themes(self, descriptions: List[str]) -> List[str]:
        """Extract common content themes from descriptions."""
        themes = []
        
        # Common themes to look for
        theme_patterns = {
            'step-by-step': r'\bstep[- ]by[- ]step\b',
            'daily practices': r'\bdaily\b',
            'proven strategies': r'\bproven\b',
            'beginner friendly': r'\bbeginner\b',
            'advanced techniques': r'\badvanced\b',
            'practical tips': r'\bpractical\b',
            'real examples': r'\bexample\b',
            'case studies': r'\bcase stud\w+\b'
        }
        
        for theme_name, pattern in theme_patterns.items():
            count = sum(1 for desc in descriptions if re.search(pattern, desc.lower()))
            if count > 0:
                themes.append(theme_name)
        
        return themes
    
    def analyze_audience_language(self, target_audience: str, competitor_content: List[str]) -> Dict[str, Any]:
        """Analyze language patterns for target audience."""
        audience_terms = {
            'professionals': ['professional', 'career', 'workplace', 'business'],
            'students': ['student', 'study', 'academic', 'learning'],
            'entrepreneurs': ['entrepreneur', 'startup', 'business owner', 'venture'],
            'parents': ['parent', 'family', 'children', 'parenting']
        }
        
        # Find relevant terms for audience
        relevant_terms = audience_terms.get(target_audience.lower(), [])
        
        # Analyze usage in competitor content
        term_usage = {}
        for term in relevant_terms:
            usage_count = sum(1 for content in competitor_content if term in content.lower())
            term_usage[term] = usage_count
        
        # Extract pain points and benefits
        pain_point_indicators = ['struggle', 'difficult', 'challenge', 'problem', 'frustration']
        benefit_indicators = ['achieve', 'success', 'improve', 'transform', 'master']
        
        pain_points = []
        benefits = []
        
        for content in competitor_content:
            content_lower = content.lower()
            for indicator in pain_point_indicators:
                if indicator in content_lower:
                    # Extract surrounding context
                    sentences = content.split('.')
                    for sentence in sentences:
                        if indicator in sentence.lower():
                            pain_points.append(sentence.strip())
                            break
            
            for indicator in benefit_indicators:
                if indicator in content_lower:
                    sentences = content.split('.')
                    for sentence in sentences:
                        if indicator in sentence.lower():
                            benefits.append(sentence.strip())
                            break
        
        return {
            'common_terms': list(term_usage.keys()),
            'tone_indicators': {
                'professional': sum(1 for content in competitor_content if 'professional' in content.lower()),
                'casual': sum(1 for content in competitor_content if any(word in content.lower() for word in ['easy', 'simple', 'fun']))
            },
            'audience_pain_points': pain_points[:5],
            'promised_benefits': benefits[:5]
        }
    
    def generate_unique_angles(self, niche: str, competitor_angles: List[str]) -> List[str]:
        """Generate unique angles not used by competitors."""
        all_angles = [
            'science-based approach',
            'minimalist method',
            '30-day challenge',
            'habit stacking',
            'micro-habits',
            'visual learning',
            'storytelling approach',
            'gamification',
            'mindfulness integration',
            'data-driven method'
        ]
        
        # Filter out angles already used by competitors
        competitor_text = ' '.join(competitor_angles).lower()
        unique_angles = []
        
        for angle in all_angles:
            if not any(word in competitor_text for word in angle.split()):
                unique_angles.append(angle)
        
        return unique_angles[:5]
    
    def calculate_content_quality_score(self, content: Dict[str, Any]) -> float:
        """Calculate overall content quality score."""
        score = 0.0
        
        title = content.get('title', '')
        description = content.get('description', '')
        keywords = content.get('keywords', [])
        
        # Title quality (25 points)
        if len(title) >= 30:
            score += 10
        if len(title.split()) >= 5:
            score += 10
        if ':' in title or '-' in title:
            score += 5
        
        # Description quality (50 points)
        if len(description) >= 200:
            score += 15
        if description.count('.') >= 3:
            score += 10
        if '•' in description or '✓' in description:
            score += 10
        if any(word in description.lower() for word in ['proven', 'step-by-step', 'comprehensive']):
            score += 10
        if description.count('!') <= 2:
            score += 5
        
        # Keywords quality (25 points)
        if len(keywords) >= 5:
            score += 10
        if any(len(kw.split()) >= 3 for kw in keywords):
            score += 10
        if len(set(len(kw.split()) for kw in keywords)) >= 2:
            score += 5
        
        return min(100, score)


# Utility functions for listing generation

async def generate_optimized_listing(niche: Niche, target_audience: str, book_type: str,
                                   competitor_analysis: bool = False, seo_optimization: bool = True,
                                   unique_angle: Optional[str] = None) -> Dict[str, Any]:
    """Generate a complete optimized listing."""
    generator = ListingGenerator()
    
    # Generate basic listing
    listing = generator.generate_complete_listing(niche, target_audience, book_type, unique_angle=unique_angle)
    
    result = {
        'listing': listing,
        'optimization_suggestions': [],
        'seo_analysis': {},
        'competitor_analysis': {}
    }
    
    # Add SEO optimization
    if seo_optimization:
        seo_optimizer = SEOOptimizer()
        suggestions = seo_optimizer.suggest_improvements(listing)
        result['optimization_suggestions'] = suggestions
        
        result['seo_analysis'] = {
            'seo_score': listing['seo_score'],
            'keyword_density': seo_optimizer.calculate_keyword_density(
                listing['description'], niche.primary_keyword
            ),
            'title_optimization': 'Good' if niche.primary_keyword.lower() in listing['title'].lower() else 'Needs improvement'
        }
    
    # Add competitor analysis if requested
    if competitor_analysis:
        # This would integrate with actual competitor data
        result['competitor_analysis'] = {
            'differentiation_score': random.uniform(60, 90),
            'unique_elements': ['Comprehensive approach', 'Step-by-step guidance'],
            'competitive_advantages': ['More detailed content', 'Better organization']
        }
    
    return result

# Main function for MCP agent integration
async def generate_kdp_listing(niche: Dict[str, Any], target_audience: str, book_type: str = "journal",
                             keepa_client=None, cache_manager=None,
                             unique_angle: Optional[str] = None,
                             price_range: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Generate KDP listing for MCP agent integration."""
    try:
        # Convert niche dict to Niche object if needed
        if isinstance(niche, dict):
            niche_obj = Niche(
                primary_keyword=niche.get('primary_keyword', niche.get('keyword', '')),
                category=niche.get('category', 'Self-Help'),
                keywords=niche.get('keywords', []),
                profitability_score_numeric=niche.get('profitability_score_numeric', 0.0),
                competition_score_numeric=niche.get('competition_score_numeric', 0.0),
                market_size_score=niche.get('market_size_score', 0.0),
                confidence_score=niche.get('confidence_score', 0.0)
            )
        else:
            niche_obj = niche
        
        # Generate optimized listing
        result = await generate_optimized_listing(
            niche=niche_obj,
            target_audience=target_audience,
            book_type=book_type,
            competitor_analysis=True,
            seo_optimization=True,
            unique_angle=unique_angle
        )
        
        # Format for MCP response
        listing = result['listing']
        
        return {
            'generated_listing': {
                'title': listing['title'],
                'description': listing['description'],
                'html_description': listing['html_description'],
                'keywords': listing['keywords'],
                'categories': listing['categories'],
                'seo_score': listing['seo_score'],
                'character_counts': listing['character_counts'],
                'metadata': listing['metadata']
            },
            'optimization_data': {
                'seo_analysis': result.get('seo_analysis', {}),
                'optimization_suggestions': result.get('optimization_suggestions', []),
                'competitor_analysis': result.get('competitor_analysis', {})
            },
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            'error': f"Listing generation failed: {str(e)}",
            'generated_listing': None,
            'optimization_data': {},
            'success': False,
            'timestamp': datetime.now().isoformat()
        }