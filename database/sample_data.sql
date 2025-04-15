-- Clear existing data
-- TODO: Comment out or remove the following TRUNCATE commands for demo purposes
-- if you want sample data to persist across database rebuilds.
TRUNCATE TABLE verification_images CASCADE;
TRUNCATE TABLE access_logs CASCADE;
TRUNCATE TABLE employees CASCADE;

-- Use the same photo_url for all employees
-- Photo URL:
-- https://www.google.com/imgres?q=free%20image%20of%20a%20person%20url&imgurl=https%3A%2F%2Fimages.pexels.com%2Fphotos%2F1681010%2Fpexels-photo-1681010.jpeg%3Fcs%3Dsrgb%26dl%3Dpexels-creationhill-1681010.jpg%26fm%3Djpg&imgrefurl=https%3A%2F%2Fwww.pexels.com%2Fsearch%2Fperson%2F&docid=lrXLklXghG-NqM&tbnid=2KHSwyuP4mTCiM&vet=12ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA..i&w=3456&h=5184&hcb=2&ved=2ahUKEwiqssr05c6MAxVSGFkFHRNdOIwQM3oECHgQAA

-- Insert updated employee data with correct names and image paths
INSERT INTO employees (name, rfid_tag, role, email, face_embedding, active, last_verified, verification_count, photo_url)
VALUES
  ('Test Employee', 'EMP001', 'Test Role', 'test.emp@acme.local', NULL, true, NOW(), 0,
   '/static/images/employees/EMP001.jpg'),
  ('Sebastian Galvez', 'EMP002', 'Security Officer', 'sebastian.galvez@acme.local', NULL, true, NOW(), 0,
   '/static/images/employees/EMP002.jpg'),
  ('Luke Reynolds', 'EMP003', 'Security Officer', 'luke.reynolds@acme.local', NULL, true, NOW(), 1,
   '/static/images/employees/EMP003.jpg'),
  ('Anthony Hailey', 'EMP004', 'Administrator', 'anthony.hailey@acme.local', NULL, true, NOW(), 2,
   '/static/images/employees/EMP004.jpg'),
  ('Martin Fermento', 'EMP005', 'Security Officer', 'martin.fermento@acme.local', NULL, true, NOW(), 1,
   '/static/images/employees/EMP005.jpg'),
  ('Dakota Dietz', 'EMP006', 'Security Officer', 'dakota.dietz@acme.local', NULL, true, NOW(), 3,
   '/static/images/employees/EMP006.jpg'),
  ('Manuel Fermento', 'EMP007', 'Administrator', 'manuel.fermento@acme.local', NULL, true, NOW(), 0,
   '/static/images/employees/EMP007.jpg'),
  ('Robert Ackerman', 'EMP008', 'Security Officer', 'robert.ackerman@acme.local', NULL, true, NOW(), 1,
   '/static/images/employees/EMP008.jpg'),
  ('Santiago Zambrano', 'EMP009', 'Security Officer', 'santiago.zambrano@acme.local', NULL, true, NOW(), 2,
   '/static/images/employees/EMP009.jpg');
-- Insert sample access_logs data
INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_confidence, verification_image_path, review_status)
SELECT id, true, 'FACE', uuid_generate_v4(), 0.95,
       '/static/images/verifications/officer_face_' || CAST(id AS TEXT) || '.jpg', -- Placeholder path
       'approved'
FROM employees
WHERE role = 'Security Officer'
LIMIT 3;

INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, review_status)
SELECT id, true, 'RFID', uuid_generate_v4(),
       'approved'
FROM employees
WHERE role = 'Security Officer'
LIMIT 3;

INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_confidence, verification_image_path, review_status)
SELECT id, true, 'BOTH', uuid_generate_v4(), 0.98,
       '/static/images/verifications/admin_both_' || CAST(id AS TEXT) || '.jpg', -- Placeholder path
       'approved'
FROM employees
WHERE role = 'Administrator'
LIMIT 2;

INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_confidence, review_status)
SELECT id, false, 'FACE', uuid_generate_v4(), 0.45,
       'denied'
FROM employees
LIMIT 2;

-- Insert sample verification_images data
INSERT INTO verification_images (session_id, image_data, processed, confidence, matched_employee_id, device_id)
SELECT
    al.session_id, -- Use session_id from corresponding access_logs
    '\xDEADBEEF'::bytea, -- Placeholder dummy bytea data for the image
    true,
    al.verification_confidence,
    al.employee_id,
    'esp32-cam-simulator' -- Example device ID
FROM access_logs al
WHERE al.verification_method IN ('FACE', 'BOTH') AND al.verification_confidence IS NOT NULL
LIMIT 5; -- Limit how many images we create samples for


-- Example: RFID_ONLY_PENDING_REVIEW
-- Noah Tucker (EMP002) used RFID, but no face was detected in the image.
INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_image_path, review_status)
SELECT id, false, 'RFID_ONLY_PENDING_REVIEW', 'a1a1a1a1-b1b1-c1c1-d1d1-e1e1e1e1e1e1', -- Specific UUID for testing
       '/static/images/EMP002.jpg',
       'pending'
FROM employees
WHERE rfid_tag = 'EMP002';
-- Add corresponding verification image for this session
INSERT INTO verification_images (session_id, image_data, device_id, processed)
VALUES ('a1a1a1a1-b1b1-c1c1-d1d1-e1e1e1e1e1e1', '\x0FACE0FF'::bytea, 'esp32-cam-simulator', false); -- No face detected, so not processed for embedding

-- Example: FACE_ONLY_PENDING_REVIEW
-- A face was detected, but no RFID was presented. Employee ID is NULL initially.
INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_image_path, review_status)
VALUES (NULL, false, 'FACE_ONLY_PENDING_REVIEW', 'a2a2a2a2-b2b2-c2c2-d2d2-e2e2e2e2e2e2', -- Specific UUID
        '/static/images/EMP003.jpg', -- Dummy image path
        'pending');
-- Add corresponding verification image
INSERT INTO verification_images (session_id, image_data, device_id, processed, confidence)
VALUES ('a2a2a2a2-b2b2-c2c2-d2d2-e2e2e2e2e2e2', '\xBEEFFACE'::bytea, 'esp32-cam-simulator', true, 0.88); -- Face detected and processed

-- Example: FACE_VERIFICATION_FAILED
-- Triston Stover (EMP003) used RFID, face was detected, but confidence was too low.
INSERT INTO access_logs (employee_id, access_granted, verification_method, session_id, verification_confidence, verification_image_path, review_status)
SELECT id, false, 'FACE_VERIFICATION_FAILED', 'a3a3a3a3-b3b3-c3c3-d3d3-e3e3e3e3e3e3', -- Specific UUID
       0.55, -- Low confidence score example
       '/static/images/EMP006.jpg',
       'pending'
FROM employees
WHERE rfid_tag = 'EMP003';
-- Add corresponding verification image
INSERT INTO verification_images (session_id, image_data, device_id, processed, confidence, matched_employee_id)
SELECT 'a3a3a3a3-b3b3-c3c3-d3d3-e3e3e3e3e3e3', '\xFA17FACE'::bytea, 'esp32-cam-simulator', true, 0.55, id
FROM employees WHERE rfid_tag = 'EMP003';