-- Clear existing data
TRUNCATE TABLE verification_images CASCADE;
TRUNCATE TABLE access_logs CASCADE;
TRUNCATE TABLE employees CASCADE;

-- Use the same photo_url for all employees
-- Photo URL:
-- https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA

INSERT INTO employees (name, rfid_tag, role, email, face_embedding, active, last_verified, verification_count, photo_url)
VALUES
  ('Noah Tucker', 'NT2025001', 'Security Officer', 'noah.tucker@acme.local', NULL, true, NOW(), 0,
   'https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA'),
  ('Triston Stover', 'TS2025002', 'Security Officer', 'triston.stover@acme.local', NULL, true, NOW(), 1,
   'https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA'),
  ('Patrick Hilbert', 'PH2025003', 'Administrator', 'patrick.hilbert@acme.local', NULL, true, NOW(), 2,
   'https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA'),
  ('Anthony Biley', 'AB2025004', 'Security Officer', 'anthony.biley@acme.local', NULL, true, NOW(), 1,
   'https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA'),
  ('Sam Miller', 'SM2025005', 'Security Officer', 'sam.miller@acme.local', NULL, true, NOW(), 3,
   'https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA'),
  ('Dakota Dietz', 'DD2025006', 'Administrator', 'dakota.dietz@acme.local', NULL, true, NOW(), 0,
   'https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA'),
  ('Santiago Zambraano', 'SZ2025007', 'Security Officer', 'santiago.zambraano@acme.local', NULL, true, NOW(), 1,
   'https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA'),
  ('Anthony Hailey', 'AH2025008', 'Security Officer', 'anthony.hailey@acme.local', NULL, true, NOW(), 2,
   'https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA');

-- Insert sample access_logs data
INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_confidence, verification_image_path)
SELECT id, true, 'FACE', 'INIT_SESSION_' || CAST(FLOOR(RANDOM() * 1000) AS TEXT), 0.95,
       'https://storage.example.com/verifications/' || LOWER(REPLACE(name, ' ', '_')) || '_init.jpg'
FROM employees
WHERE role = 'Security Officer'
LIMIT 3;

INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id)
SELECT id, true, 'RFID', 'TEST_SESSION_' || CAST(FLOOR(RANDOM() * 1000) AS TEXT)
FROM employees
WHERE role = 'Security Officer'
LIMIT 3;

INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_confidence, verification_image_path)
SELECT id, true, 'BOTH', 'TEST_SESSION_2FA_' || CAST(FLOOR(RANDOM() * 1000) AS TEXT), 0.98,
       'https://storage.example.com/verifications/' || LOWER(REPLACE(name, ' ', '_')) || '_2fa.jpg'
FROM employees
WHERE role = 'Administrator'
LIMIT 2;

INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_confidence)
SELECT id, false, 'FACE', 'TEST_SESSION_FAILED_' || CAST(FLOOR(RANDOM() * 1000) AS TEXT), 0.45
FROM employees
LIMIT 2;

-- Insert sample verification_images data
INSERT INTO verification_images (session_id, image_data, processed, confidence, matched_employee_id, device_id)
SELECT 'TEST_SESSION_' || CAST(FLOOR(RANDOM() * 1000) AS TEXT),
       '\x0123456789ABCDEF'::bytea,
       true,
       0.95,
       id,
       'esp32-cam-01'
FROM employees
LIMIT 3;
