## FEATURE:

- Build an AI agent called `KDP Strategist` that helps self-publishers identify profitable book niches, validate those niches using real-world data (BSR, review count, trend trajectory), and generate complete, optimized listings for Amazon KDP.
- Agent should include semantic clustering for niche discovery, use a trend validation tool (Google Trends), and output structured listing components (title, subtitle, bullets, keywords, price, HTML-formatted description).
- Agent should follow the Model Context Protocol (MCP) standard and be deployable within an OpenAgents or LangGraph-based agent runtime.
- Niche outputs must strike a balance between specificity and broad market appeal, avoiding hyper-niches with no proven demand.
- The agent should be tool-callable and expose the following capabilities: `find_profitable_niches`, `analyze_competitor_asin`, `generate_kdp_listing`, `validate_trend`, and `niche_stress_test`.

## EXAMPLES:

No example code is available yet in the `examples/` folder, but base structure should follow this spec:

- Refer to the `kdp_strategist_product_brief.md` document for desired outputs, agent goals, and strategic philosophy.
- When a listing is generated, the returned object should contain: `title`, `subtitle`, `price`, `keywords[]`, `bullets[]`, and `description_html`.
- When a niche is analyzed, return: `niche_name`, `bsr_range`, `review_count`, `trend_score`, `go_no_go`, `rationale`.

Best practice patterns may be found in OpenAgents tool structure or LangGraph agent registration.

## DOCUMENTATION:

- KDP Metadata: https://kdp.amazon.com/en_US/help/topic/G200652170
- KDP Title/Subtitle Rules: https://kdp.amazon.com/en_US/help/topic/G200723950
- Keepa API: https://keepa.com/#!api
- pytrends (Google Trends wrapper): https://github.com/GeneralMills/pytrends
- OpenAgents (MCP-compliant server): https://github.com/OpenGPTs/OpenAgents
- LangGraph: https://github.com/langchain-ai/langgraph
- `kdp-strategist.mcp.json` (defines all tools, I/O schemas, agent persona)
- `kdp_strategist_product_brief.md` (full concept design + reasoning)

## OTHER CONSIDERATIONS:

- The agent must not suggest hyper-specific niches unless demand is validated by both Amazon data (BSR < 100k, <10 serious competitors) and Google Trends.
- Generated listings must follow KDP content and metadata rules — max character limits, no claims or misleading phrases.
- Embeddings used for clustering should be OpenAI’s `text-embedding-3-small` or Instructor-style sentence transformers.
- Listing generation should support multiple tones (educational, empathetic, minimalist, etc.) depending on audience profile.
- The final agent should be testable locally or in OpenAgents with memory via pgvector/Supabase and tool dispatch.