ALTER TABLE products ADD COLUMN IF NOT EXISTS scraped_title TEXT;

COMMENT ON COLUMN products.scraped_title IS 'API抓取的原始产品标题（Rainforest/AliExpress等），与用户填写的name字段区分';
