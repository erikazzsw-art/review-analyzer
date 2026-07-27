-- Migration 059: Add normalized comment review date
-- 创建时间: 2026-07-27
-- 说明:
--   1. Adds nullable comments.review_date DATE while preserving raw comments.date for display/export.
--   2. Backfills supported raw formats:
--      - YYYY-MM-DD, including timestamps containing that prefix/date token
--      - Amazon strings such as "Reviewed in the United States on July 1, 2026"
--   3. Leaves unsupported dates as NULL; inspect the verification query before prod rollout.

-- ========== UP ==========

ALTER TABLE comments
    ADD COLUMN IF NOT EXISTS review_date DATE;

COMMENT ON COLUMN comments.review_date IS
    'Normalized review date parsed from raw comments.date/date_iso-compatible sources. Raw comments.date is retained for display.';

WITH parsed AS (
    SELECT
        id,
        regexp_match(date, '([0-9]{4})-([0-9]{2})-([0-9]{2})') AS parts
    FROM comments
    WHERE review_date IS NULL
      AND date ~ '[0-9]{4}-[0-9]{2}-[0-9]{2}'
),
iso_parts AS (
    SELECT
        id,
        (parts[1])::int AS year_num,
        (parts[2])::int AS month_num,
        (parts[3])::int AS day_num
    FROM parsed
    WHERE parts IS NOT NULL
),
normalized AS (
    SELECT
        id,
        make_date(year_num, month_num, day_num) AS parsed_date
    FROM iso_parts
    WHERE month_num BETWEEN 1 AND 12
      AND day_num BETWEEN 1 AND CASE
          WHEN month_num IN (1, 3, 5, 7, 8, 10, 12) THEN 31
          WHEN month_num IN (4, 6, 9, 11) THEN 30
          WHEN month_num = 2
               AND (year_num % 400 = 0 OR (year_num % 4 = 0 AND year_num % 100 <> 0)) THEN 29
          WHEN month_num = 2 THEN 28
          ELSE 0
      END
)
UPDATE comments c
SET review_date = n.parsed_date
FROM normalized n
WHERE c.id = n.id
  AND n.parsed_date IS NOT NULL;

WITH parsed AS (
    SELECT
        id,
        regexp_match(
            date,
            '(January|February|March|April|May|June|July|August|September|October|November|December)\s+([0-9]{1,2}),\s*([0-9]{4})',
            'i'
        ) AS parts
    FROM comments
    WHERE review_date IS NULL
      AND date ~* '(January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-9]{1,2},\s*[0-9]{4}'
),
month_parts AS (
    SELECT
        id,
        (parts[3])::int AS year_num,
        CASE lower(parts[1])
            WHEN 'january' THEN 1
            WHEN 'february' THEN 2
            WHEN 'march' THEN 3
            WHEN 'april' THEN 4
            WHEN 'may' THEN 5
            WHEN 'june' THEN 6
            WHEN 'july' THEN 7
            WHEN 'august' THEN 8
            WHEN 'september' THEN 9
            WHEN 'october' THEN 10
            WHEN 'november' THEN 11
            WHEN 'december' THEN 12
        END AS month_num,
        (parts[2])::int AS day_num
    FROM parsed
    WHERE parts IS NOT NULL
),
normalized AS (
    SELECT
        id,
        make_date(year_num, month_num, day_num) AS parsed_date
    FROM month_parts
    WHERE month_num IS NOT NULL
      AND day_num BETWEEN 1 AND CASE
          WHEN month_num IN (1, 3, 5, 7, 8, 10, 12) THEN 31
          WHEN month_num IN (4, 6, 9, 11) THEN 30
          WHEN month_num = 2
               AND (year_num % 400 = 0 OR (year_num % 4 = 0 AND year_num % 100 <> 0)) THEN 29
          WHEN month_num = 2 THEN 28
          ELSE 0
      END
)
UPDATE comments c
SET review_date = n.parsed_date
FROM normalized n
WHERE c.id = n.id
  AND n.parsed_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_comments_user_session_id_desc
    ON comments(user_id, session_id, id DESC);

CREATE INDEX IF NOT EXISTS idx_comments_user_product_review_date_id_desc
    ON comments(user_id, product_id, review_date DESC, id DESC)
    WHERE review_date IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_comments_user_product_variant_review_date_id_desc
    ON comments(user_id, product_id, source_variant_asin, review_date DESC, id DESC)
    WHERE source_variant_asin IS NOT NULL
      AND review_date IS NOT NULL;

-- Dev/prod verification query after running UP:
-- SELECT
--     COUNT(*) AS total_comments,
--     COUNT(*) FILTER (WHERE review_date IS NOT NULL) AS normalized_comments,
--     COUNT(*) FILTER (WHERE review_date IS NULL AND COALESCE(date, '') <> '') AS unparsed_raw_date_comments,
--     COUNT(*) FILTER (WHERE COALESCE(date, '') = '') AS blank_raw_date_comments
-- FROM comments;

-- ========== DOWN ==========
-- DROP INDEX IF EXISTS idx_comments_user_product_variant_review_date_id_desc;
-- DROP INDEX IF EXISTS idx_comments_user_product_review_date_id_desc;
-- DROP INDEX IF EXISTS idx_comments_user_session_id_desc;
-- ALTER TABLE comments DROP COLUMN IF EXISTS review_date;
