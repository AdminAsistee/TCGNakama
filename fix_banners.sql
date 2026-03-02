-- Check current banner data
SELECT id, title, image_path, is_active, display_order 
FROM banners 
ORDER BY display_order;

-- Option 1: Reset all banners to use gradients (set image_path to NULL)
-- Uncomment the lines below to execute:
-- UPDATE banners SET image_path = NULL WHERE id IN (1, 2, 3);

-- Option 2: Update specific banner with correct image path
-- Example: UPDATE banners SET image_path = 'banners/one-piece.jpg' WHERE id = 1;

-- After updating, verify the changes:
-- SELECT id, title, image_path, is_active FROM banners ORDER BY display_order;
