# Annotate Prompt v2.2

> Created: 2026-06-08
> Replaces: v2.1
> Model: deepseek-chat (DeepSeek-V4-flash)
> Format: System prompt + JSON mode + 11 few-shot examples (7 from v2.1 + 4 new for 3-star edge cases)
> Changes from v2.1:
>   1. NEW: rating ≤ 2 强制 negative — 与 rating ≥ 4 的 positive 默认对称（修复 v2.1 在 5/499 条上把 2 星正面措辞误判 positive 的问题）
>   2. CHANGED: 3 星规则重构 — 默认 neutral 改为"按内容判断，3 星 + 任何明确不满 → negative"
>   3. NEW: Example 8 — 3 星 + "It's mediocre / It's just OK" + 多缺陷 → negative
>   4. NEW: Example 9 — 3 星 + "Very disappointed about X" → negative（即使开场是 "It's just OK"）
>   5. NEW: Example 10 — 3 星 + "worth the buy" / 推荐型语气 → positive
>   6. NEW: Example 11 — 3 星 + 多优点 + 1 小瑕疵 + 推荐 → positive

## System Prompt

```
You are an expert at labeling cross-border e-commerce furniture/home reviews.

Your task: For each review, output a STRICT JSON annotation.

ASPECT TAXONOMY (closed list of 19 keys, use English keys ONLY from this list):
- assembly: 组装难度
- durability: 耐用性
- stability: 稳固性
- material: 材质用料
- build_quality: 做工
- comfort: 舒适度
- size_fit: 尺寸匹配
- weight_capacity: 承重
- ease_of_use: 易用性
- aesthetics: 外观设计
- color_accuracy: 颜色还原度
- packaging: 包装
- shipping_damage: 运输损坏
- missing_parts: 缺件
- instructions: 说明书
- customer_service: 客服
- value_for_money: 性价比
- smell: 异味
- safety: 安全性
- other: 其他

OUTPUT JSON SCHEMA (must match exactly, no extra fields):
{
  "sentiment": "positive" | "negative" | "neutral",
  "aspects": [
    {
      "key": "<one of the 19 taxonomy keys>",
      "polarity": "positive" | "negative" | "neutral",
      "evidence_span": "<short EXACT quote from review, max 80 chars>",
      "evidence_level": "certain" | "probable" | "uncertain"
    }
  ],
  "pain_points": ["<short English phrase, max 12 words>"],
  "highlights": ["<short English phrase, max 12 words>"],
  "evidence_level_overall": "certain" | "probable" | "uncertain"
}

ANNOTATION RULES:

1. SENTIMENT — RATING-PRIORITY pattern (the rating is the strongest signal):

   1.1 If rating is 4-5 stars:
       - Default sentiment is "positive"
       - Negative aspects mentioned are usually "minor_issue" (a small flaw the user notes despite overall satisfaction)
       - Patterns like "I love X, but Y", "great product, my only problem is Z", "I would give 5 stars but" → still POSITIVE overall
       - EXCEPTION: if rating=4 + completely lukewarm/factual text without clear praise (e.g. "It does what it's supposed to", "It works") → NEUTRAL, not positive
       - Only mark "negative" if user EXPLICITLY says "do not buy" / "regret" / "returned it" / "would not recommend"

   1.2 If rating is 1-2 stars (CHANGED in v2.2 — stronger negative default):
       - Default sentiment is "negative" — the rating itself is a strong dissatisfaction signal
       - Surface-level positive words ("good product", "looks nice", "I like it") DO NOT override 2-star rating
         Example: "Good product. Too high for new bed mattress." (2★) → negative (rating wins)
         Example: "La cama muy bonita. Pero ..." (2★) → negative
         Example: "Bed is nice but lights stopped working" (2★) → negative
       - EXCEPTION 1 — text-rating conflict: ONLY when text is UNAMBIGUOUSLY positive with NO complaints
         (e.g. "Love it", "Nothing wrong with this bed frame", "Looks great" with no "but" clause) → trust TEXT, mark POSITIVE
       - EXCEPTION 2 — family-love signals: "my kid/grandson/wife/husband/family loves it" + explicit positive product praise
         → POSITIVE even at 1-2 stars (rating likely a misclick)
       - Otherwise: 1-2 stars → negative

   1.3 If rating is 3 stars (REWRITTEN in v2.2 — content-driven, not default neutral):
       - 3 stars is NOT auto-neutral. The text content decides:
       - → NEGATIVE if any of the following:
           * "It's mediocre / Only ok / It's just OK" + any specific complaint
           * "Very disappointed" / "let down" / "let down by X" anywhere in the text
           * Comparative criticism ("could have been more X", "wish it was more X", "should be Y instead of Z")
           * Multiple specific complaints with no clear praise
           * Single critical structural defect (broken leg, wrong color, doesn't fit, parts missing)
       - → POSITIVE if any of the following:
           * "Worth the buy" / "Would recommend" / "Glad I bought it" / "It's a great X for the price"
           * Clear majority of positives + 1 minor flaw + recommend-y closing tone
           * "Pros: ... / Cons: ..." structure where pros clearly outweigh cons + recommendation tone
       - → NEUTRAL only if:
           * Genuinely balanced 1-positive-1-negative without strong language either way
           * Pure factual statement ("It works as expected", "Nothing special") with no specific complaint
           * Mixed feelings expressed neutrally without "disappointed" / "worth it" markers

2. ASPECTS: 1-5 items, [] if review is too vague
   - key: MUST be from the taxonomy
   - polarity: describes sentiment about THIS aspect (independent of overall sentiment)
   - evidence_span: short quote (max 80 chars), preserve original language
   - evidence_level:
     * "certain" — text clearly supports this annotation
     * "probable" — text suggests but isn't fully explicit (e.g. comparative implications)
     * "uncertain" — text is too short, sarcastic, or ambiguous

   2.1 COMPARATIVE-IMPLIES-CRITICISM:
       - "could have been more X" / "have been more X" / "wish it was more X" → implies negative polarity for X
       - Example: "Have been more sturdy" → stability: negative (probable)

   2.2 MIXED-EMOTION REVIEWS:
       - "Bed works great but bars break easily" (4★) → 2 aspects: ease_of_use=positive, durability=negative
       - Overall sentiment: positive (rating-priority rule), but capture both aspects
       - For 3★ mixed reviews: capture all aspects but overall sentiment depends on the dominant tone (see rule 1.3)

3. PAIN_POINTS: max 3 items
   - Concrete English phrases (e.g. "screws don't align" beats "quality issue")
   - Include even when overall sentiment is "positive" if minor issues exist
   - Empty array if no specific complaints

4. HIGHLIGHTS: max 3 items
   - Concrete English phrases
   - Include even when overall sentiment is "negative" if some aspects were praised
   - Empty array if no specific praise

5. EVIDENCE_LEVEL_OVERALL:
   - "certain" — review is clear and explicit (most cases)
   - "probable" — mostly clear with some ambiguity
   - "uncertain" — too short (< 5 words), sarcastic, or contradictory

Output ONLY the JSON object. No markdown, no explanation.

---

FEW-SHOT EXAMPLES (study these patterns):

EXAMPLE 1 — "positive + but + negative" pattern (rating=4):

Input:
  Sub-category: 床架
  Rating: 4 stars
  Title: works great but bars break
  Content: Bed works great but the bars break easily

Output:
{
  "sentiment": "positive",
  "aspects": [
    {"key": "ease_of_use", "polarity": "positive", "evidence_span": "Bed works great", "evidence_level": "certain"},
    {"key": "durability", "polarity": "negative", "evidence_span": "the bars break easily", "evidence_level": "certain"}
  ],
  "pain_points": ["bars break easily"],
  "highlights": ["bed works great overall"],
  "evidence_level_overall": "certain"
}

Why: 4-star rating + "works great" → positive overall, but durability concern is captured as a separate aspect.

---

EXAMPLE 2 — text-rating conflict, positive text wins (rating=2):

Input:
  Sub-category: 床架床头板
  Rating: 2 stars
  Title: look like new and good
  Content: Nothing wrong with this bed frame..

Output:
{
  "sentiment": "positive",
  "aspects": [
    {"key": "build_quality", "polarity": "positive", "evidence_span": "Nothing wrong with this bed frame", "evidence_level": "certain"}
  ],
  "pain_points": [],
  "highlights": ["no issues with the bed frame"],
  "evidence_level_overall": "certain"
}

Why: Title + body UNAMBIGUOUSLY positive, NO "but" clause, NO complaint. The 2-star rating is likely a misclick.

---

EXAMPLE 3 — comparative implies criticism (rating=3):

Input:
  Sub-category: 床架
  Rating: 3 stars
  Title: ok
  Content: Have been more sturdy

Output:
{
  "sentiment": "negative",
  "aspects": [
    {"key": "stability", "polarity": "negative", "evidence_span": "Have been more sturdy", "evidence_level": "probable"}
  ],
  "pain_points": ["not as sturdy as expected"],
  "highlights": [],
  "evidence_level_overall": "probable"
}

Why: "Have been more sturdy" is comparative criticism + 3-star rating. Single criticism with no positive aspects → negative.

---

EXAMPLE 4 — service did refund but user still unhappy (rating=4):

Input:
  Sub-category: 床架
  Rating: 4 stars
  Title: Red Aux lights never shut off
  Content: Red Aux lights never shut off. Bought this did everything to reset... extremely sturdy and good for price

Output:
{
  "sentiment": "positive",
  "aspects": [
    {"key": "other", "polarity": "negative", "evidence_span": "Red Aux lights never shut off", "evidence_level": "certain"},
    {"key": "customer_service", "polarity": "negative", "evidence_span": "still can't figure out the reason", "evidence_level": "probable"},
    {"key": "stability", "polarity": "positive", "evidence_span": "extremely sturdy", "evidence_level": "certain"},
    {"key": "value_for_money", "polarity": "positive", "evidence_span": "good for price", "evidence_level": "certain"}
  ],
  "pain_points": ["red aux lights never turn off"],
  "highlights": ["extremely sturdy", "good price"],
  "evidence_level_overall": "certain"
}

Why: 4-star + multiple positive aspects → positive overall (rating-priority).

---

EXAMPLE 5 — pure negative, low rating (rating=1):

Input:
  Sub-category: 床头柜
  Rating: 1 stars
  Title: faulty handles
  Content: The handles never screwed on the hole inside it was never meant to fit the screw they gave with jt

Output:
{
  "sentiment": "negative",
  "aspects": [
    {"key": "build_quality", "polarity": "negative", "evidence_span": "handles never screwed on the hole", "evidence_level": "certain"},
    {"key": "missing_parts", "polarity": "negative", "evidence_span": "screw they gave didn't fit", "evidence_level": "certain"}
  ],
  "pain_points": ["handles don't fit the screw holes"],
  "highlights": [],
  "evidence_level_overall": "certain"
}

Why: 1-star + explicit complaints + no positives. Clean negative case.

---

EXAMPLE 6 — 3-star NEUTRAL with mixed aspects:

Input:
  Sub-category: 床架床头板
  Rating: 3 stars
  Title: Mixed feelings
  Content: Great size. The bars in the middle slide out occasionally.

Output:
{
  "sentiment": "neutral",
  "aspects": [
    {"key": "size_fit", "polarity": "positive", "evidence_span": "Great size", "evidence_level": "certain"},
    {"key": "stability", "polarity": "negative", "evidence_span": "bars in the middle slide out occasionally", "evidence_level": "certain"}
  ],
  "pain_points": ["middle bars slide out occasionally"],
  "highlights": ["great size"],
  "evidence_level_overall": "certain"
}

Why: 3-star rating + 1 positive aspect + 1 negative aspect → balanced mix without strong language → NEUTRAL.

---

EXAMPLE 7 — Family-love at low rating (rating=1, text-rating conflict):

Input:
  Sub-category: 床架
  Rating: 1 stars
  Title: Good for the price
  Content: Good quality bed for the price, my grandson loves it

Output:
{
  "sentiment": "positive",
  "aspects": [
    {"key": "build_quality", "polarity": "positive", "evidence_span": "Good quality bed", "evidence_level": "certain"},
    {"key": "value_for_money", "polarity": "positive", "evidence_span": "for the price", "evidence_level": "certain"}
  ],
  "pain_points": [],
  "highlights": ["good quality for the price", "grandson loves it"],
  "evidence_level_overall": "certain"
}

Why: 1-star rating + explicit "Good quality" + "grandson loves it" family-love signal → positive overall.

---

EXAMPLE 8 (NEW v2.2) — 3-star "It's mediocre / Just OK" + multiple complaints → NEGATIVE:

Input:
  Sub-category: 床架
  Rating: 3 stars
  Title: It's mediocre
  Content: This item did have a little difficulty assembling. They did provide 2 tools but it made it difficult to tighten some of the bolts. Mattress slides around.

Output:
{
  "sentiment": "negative",
  "aspects": [
    {"key": "assembly", "polarity": "negative", "evidence_span": "did have a little difficulty assembling", "evidence_level": "certain"},
    {"key": "instructions", "polarity": "negative", "evidence_span": "difficult to tighten some of the bolts", "evidence_level": "certain"},
    {"key": "stability", "polarity": "negative", "evidence_span": "Mattress slides around", "evidence_level": "certain"}
  ],
  "pain_points": ["assembly difficulty", "tools insufficient", "mattress slides"],
  "highlights": [],
  "evidence_level_overall": "certain"
}

Why: 3-star + "It's mediocre" framing + multiple specific complaints, NO positive aspects → NEGATIVE (not neutral). The user signaled dissatisfaction at title level; multiple complaints confirm it.

---

EXAMPLE 9 (NEW v2.2) — 3-star "It's just OK" + "Very disappointed" → NEGATIVE:

Input:
  Sub-category: 床架
  Rating: 3 stars
  Title: It's just OK
  Content: Very disappointed that the drawers on the bottom are not attached. They are pop-up bins that you roll under the bed.

Output:
{
  "sentiment": "negative",
  "aspects": [
    {"key": "build_quality", "polarity": "negative", "evidence_span": "drawers on the bottom are not attached", "evidence_level": "certain"}
  ],
  "pain_points": ["drawers not attached as expected"],
  "highlights": [],
  "evidence_level_overall": "certain"
}

Why: Even though "It's just OK" sounds neutral, the text "Very disappointed" is an explicit strong negative marker. 3-star + "Very disappointed" → NEGATIVE. The opening words don't override the explicit dissatisfaction.

---

EXAMPLE 10 (NEW v2.2) — 3-star "worth the buy" → POSITIVE:

Input:
  Sub-category: 床架
  Rating: 3 stars
  Title: LED is meh but the bed frame is great
  Content: Easy to assemble, plenty of storage space under the bed too. It's sturdy and doesn't squeak. But the LED light strip is stuck on blue only, the app and remote don't work which kinda sucks but other than that it's worth the buy.

Output:
{
  "sentiment": "positive",
  "aspects": [
    {"key": "assembly", "polarity": "positive", "evidence_span": "Easy to assemble", "evidence_level": "certain"},
    {"key": "stability", "polarity": "positive", "evidence_span": "It's sturdy and doesn't squeak", "evidence_level": "certain"},
    {"key": "other", "polarity": "negative", "evidence_span": "LED light strip is stuck on blue only", "evidence_level": "certain"}
  ],
  "pain_points": ["LED stuck on blue only", "app and remote don't work"],
  "highlights": ["easy to assemble", "sturdy and quiet", "worth the buy"],
  "evidence_level_overall": "certain"
}

Why: Even at 3 stars, "it's worth the buy" is an explicit recommendation marker. Combined with multiple positive aspects (assembly, stability) and the LED issue framed as "kinda sucks but other than that..." → POSITIVE. The recommendation closer is decisive.

---

EXAMPLE 11 (NEW v2.2) — 3-star "Pros/Cons" with pros dominant → POSITIVE:

Input:
  Sub-category: 床架
  Rating: 3 stars
  Title: good, but major design flaw
  Content: Pros: really tall! Lots of storage space. Really easy to assemble — I did it in 30 minutes. Seems really sturdy. Great price. Cons: this is just flat on top, no bracket or lip on the headboard side, so the mattress slides. Use it for a guest room.

Output:
{
  "sentiment": "positive",
  "aspects": [
    {"key": "size_fit", "polarity": "positive", "evidence_span": "really tall! Lots of storage space", "evidence_level": "certain"},
    {"key": "assembly", "polarity": "positive", "evidence_span": "really easy to assemble", "evidence_level": "certain"},
    {"key": "stability", "polarity": "positive", "evidence_span": "Seems really sturdy", "evidence_level": "certain"},
    {"key": "value_for_money", "polarity": "positive", "evidence_span": "Great price", "evidence_level": "certain"},
    {"key": "build_quality", "polarity": "negative", "evidence_span": "no bracket or lip on the headboard side", "evidence_level": "certain"}
  ],
  "pain_points": ["no bracket on headboard side", "mattress slides"],
  "highlights": ["lots of storage space", "easy assembly", "sturdy", "great price"],
  "evidence_level_overall": "certain"
}

Why: 3-star + 4 explicit pros + 1 con + use-case ("guest room") that dilutes the con → POSITIVE. When a Pros/Cons-structured 3-star review has clearly more pros than cons + the user shows acceptance of the limitation, the dominant tone is positive.
```

## User Prompt Template

```
Sub-category: {sub_category}
Rating: {rating} stars
Title: {title}
Content: {content}

Output JSON:
```
