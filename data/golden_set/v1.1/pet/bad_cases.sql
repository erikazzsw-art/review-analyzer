-- 宠物品类 Bad Cases — 从人工仲裁修正中提取
-- 生成时间: 2026-07-22 13:35
-- Batch ID: pet_deep_review_v1.1
-- 共 38 条 bad case
-- 来源: reviewer_notes 自由文本解析

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 2, 'Puppy love chess things',
  'change_sentiment',
  'neutral', 'positive',
  'Reviewer changed sentiment from neutral to positive',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 3, 'I still find myself having to clean the dogs feet.  I would not purchase again.',
  'add_aspect',
  '(missing)', 'ease_of_use|negative',
  'Added aspect: ease_of_use(negative), evidence: difficult to keep clean',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 3, 'I still find myself having to clean the dogs feet.  I would not purchase again.',
  'add_aspect',
  '(missing)', 'other|negative',
  'Added aspect: other(negative), evidence: 吸水力差',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 5, 'I am totally obsessed with this product! The amount of hair that comes off of my cats is amazing! I ',
  'add_aspect',
  '(missing)', 'grooming_effectiveness|positive',
  'Added aspect [非Taxonomy Key]: grooming_effectiveness(positive), evidence: helped getting the mats off of her pain free',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 5, 'I am totally obsessed with this product! The amount of hair that comes off of my cats is amazing! I ',
  'add_aspect',
  '(missing)', 'gentleness|positive',
  'Added aspect [非Taxonomy Key]: gentleness(positive), evidence: helped getting the mats off of her pain free',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 5, 'I am totally obsessed with this product! The amount of hair that comes off of my cats is amazing! I ',
  'add_aspect',
  '(missing)', 'hair_removal|positive',
  'Added aspect [非Taxonomy Key]: hair_removal(positive), evidence: The amount of hair that comes off of my cats is amazing!',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 5, 'I am totally obsessed with this product! The amount of hair that comes off of my cats is amazing! I ',
  'remove_aspect',
  'palatability|positive', '(removed)',
  'Removed aspect: palatability(positive), evidence: I am totally obsessed with this product',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 5, 'I am totally obsessed with this product! The amount of hair that comes off of my cats is amazing! I ',
  'remove_aspect',
  'ease_of_use|positive', '(removed)',
  'Removed aspect: ease_of_use(positive), evidence: helped getting the mats off of her pain free',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 5, 'I am totally obsessed with this product! The amount of hair that comes off of my cats is amazing! I ',
  'change_aspect',
  'ease_of_use|positive', 'grooming_effectiveness|positive',
  'Changed: ease_of_use|positive → grooming_effectiveness|positive [非Taxonomy Key], evidence: helped getting the mats off of her pain free',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 5, 'I am totally obsessed with this product! The amount of hair that comes off of my cats is amazing! I ',
  'change_aspect',
  'ease_of_use|positive', 'gentleness|positive',
  'Changed: ease_of_use|positive → gentleness|positive [非Taxonomy Key], evidence: helped getting the mats off of her pain free',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 6, 'I have used other brands in the past and these showed up in a search on reorder so I decided to give',
  'add_aspect',
  '(missing)', 'ease_of_use|positive',
  'Added aspect: ease_of_use(positive), evidence: the tape holding the rolls is easy to peel off',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 6, 'I have used other brands in the past and these showed up in a search on reorder so I decided to give',
  'add_aspect',
  '(missing)', 'durability|positive',
  'Added aspect: durability(positive), evidence: The bags a sturdy',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 6, 'I have used other brands in the past and these showed up in a search on reorder so I decided to give',
  'remove_aspect',
  'packaging|positive', '(removed)',
  'Removed aspect: packaging(positive), evidence: The bags a sturdy and the tape holding the rolls',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 11, 'Only worked 3 months for my 10 pound fur baby. It worked when it did, but now I’ve been seeing fleas',
  'add_aspect',
  '(missing)', 'longevity|negative',
  'Added aspect [非Taxonomy Key]: longevity(negative), evidence: Only worked 3 months for my 10 pound fur baby',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 11, 'Only worked 3 months for my 10 pound fur baby. It worked when it did, but now I’ve been seeing fleas',
  'add_aspect',
  '(missing)', 'effectiveness|positive',
  'Added aspect [非Taxonomy Key]: effectiveness(positive), evidence: It worked when it did',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 13, 'I recently started giving my 8 year-old lab,Wuffes Chewable Hip and Joint Support, and I''m thrilled',
  'add_aspect',
  '(missing)', 'price|negative',
  'Added aspect [非Taxonomy Key]: price(negative), evidence: may be more expensive than some other options',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 14, 'Los amo y a mi perro❤️, De Tantos Que Compro Me Deberían Regalar O Darme Descuento 🤭',
  'add_aspect',
  '(missing)', 'value_for_money|neutral',
  'Added aspect: value_for_money(neutral), evidence: De Tantos Que Compro Me Deberían Regalar O Darme Descuento',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 14, 'Los amo y a mi perro❤️, De Tantos Que Compro Me Deberían Regalar O Darme Descuento 🤭',
  'add_aspect',
  '(missing)', 'palatability|positive',
  'Added aspect: palatability(positive), evidence: mi perro❤️',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 19, 'These poop bags are actually really nice—they’re colorful and sturdy, so no worries about rips or le',
  'add_aspect',
  '(missing)', 'packaging|negative',
  'Added aspect: packaging(negative), evidence: there are only 15 bags per roll',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 19, 'These poop bags are actually really nice—they’re colorful and sturdy, so no worries about rips or le',
  'add_aspect',
  '(missing)', 'ease_of_use|negative',
  'Added aspect: ease_of_use(negative), evidence: have to replace rolls more often than I''d like',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 19, 'These poop bags are actually really nice—they’re colorful and sturdy, so no worries about rips or le',
  'remove_aspect',
  'value_for_money|negative', '(removed)',
  'Removed aspect: value_for_money(negative), evidence: there are only 15 bags per roll',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 19, 'These poop bags are actually really nice—they’re colorful and sturdy, so no worries about rips or le',
  'change_aspect',
  'value_for_money|negative', 'packaging|negative',
  'Changed: value_for_money|negative → packaging|negative, evidence: there are only 15 bags per roll',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 29, 'Neither the adult dog nor pup would show any interest.  We tried several different days and differen',
  'add_aspect',
  '(missing)', 'packaging|positive',
  'Added aspect: packaging(positive), evidence: spend the money on the packaging',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 29, 'Neither the adult dog nor pup would show any interest.  We tried several different days and differen',
  'remove_aspect',
  'packaging|negative', '(removed)',
  'Removed aspect: packaging(negative), evidence: disappointing that they spend the money on the packaging',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 37, 'I’m still waiting for this to work. We are starting the 3rd month and my dog is still itchy. Some of',
  'change_sentiment',
  'neutral', 'negative',
  'Reviewer changed sentiment from neutral to negative',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 40, 'My dogs have never been uninterested in these, and never been bored with these (like they have of ot',
  'add_aspect',
  '(missing)', 'appeal|positive',
  'Added aspect [非Taxonomy Key]: appeal(positive), evidence: never been uninterested in these',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 40, 'My dogs have never been uninterested in these, and never been bored with these (like they have of ot',
  'remove_aspect',
  'palatability|positive', '(removed)',
  'Removed aspect: palatability(positive), evidence: never been uninterested in these',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 40, 'My dogs have never been uninterested in these, and never been bored with these (like they have of ot',
  'change_aspect',
  'palatability|positive', 'appeal|positive',
  'Changed: palatability|positive → appeal|positive [非Taxonomy Key], evidence: never been uninterested in these',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 43, 'Perfect for my baby for diapers. So many of them as well. So convenient, and can leave a pack in mul',
  'add_aspect',
  '(missing)', 'ease_of_use|positive',
  'Added aspect: ease_of_use(positive), evidence: convenient, and can leave a pack in multiple places',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 43, 'Perfect for my baby for diapers. So many of them as well. So convenient, and can leave a pack in mul',
  'add_aspect',
  '(missing)', 'value_for_money|positive',
  'Added aspect: value_for_money(positive), evidence: So many of them as well',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 44, 'I''ve bought this 3 times now because it''s my dogs and pups favorite toy but they keep losing it so',
  'add_aspect',
  '(missing)', 'palatability|positive',
  'Added aspect: palatability(positive), evidence: it''s my dogs and pups favorite toy',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 44, 'I''ve bought this 3 times now because it''s my dogs and pups favorite toy but they keep losing it so',
  'remove_aspect',
  'durability|positive', '(removed)',
  'Removed aspect: durability(positive), evidence: it''s my dogs and pups favorite toy',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 44, 'I''ve bought this 3 times now because it''s my dogs and pups favorite toy but they keep losing it so',
  'change_aspect',
  'durability|positive', 'palatability|positive',
  'Changed: durability|positive → palatability|positive, evidence: it''s my dogs and pups favorite toy',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 45, 'These puppy pads work well',
  'add_aspect',
  '(missing)', 'effectiveness|positive',
  'Added aspect [非Taxonomy Key]: effectiveness(positive), evidence: work well',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 46, 'Love this poduct. Excellent for my labradoodle',
  'add_aspect',
  '(missing)', 'effectiveness|positive',
  'Added aspect [非Taxonomy Key]: effectiveness(positive), evidence: Excellent for my labradoodle',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 47, 'Great for puppy training.',
  'add_aspect',
  '(missing)', 'effectiveness|positive',
  'Added aspect [非Taxonomy Key]: effectiveness(positive), evidence: Great for puppy training',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 48, 'Even though these are vitamins, I give him one with breakfast, and one with lunch. His coat is so sh',
  'add_aspect',
  '(missing)', 'effectiveness|positive',
  'Added aspect [非Taxonomy Key]: effectiveness(positive), evidence: Definitely effective',
  'arbitration', '宠物'
);

INSERT INTO bad_cases (batch_id, review_id, content, correction_type, ai_value, reviewer_value, detail, source, sub_category) VALUES (
  'pet_deep_review_v1.1', 48, 'Even though these are vitamins, I give him one with breakfast, and one with lunch. His coat is so sh',
  'remove_aspect',
  'palatability|positive', '(removed)',
  'Removed aspect: palatability(positive), evidence: we''ve become big fans',
  'arbitration', '宠物'
);
