# Initial Mock Data Blueprint

This document outlines the structure and sample data intended for initializing the database for development and testing purposes. It complements the `database/sample_data.sql` script.

**Workflow to Populate Face Embeddings:**

1.  **Start Services:** Ensure your Docker containers, especially the `db` (PostgreSQL) and `deepface` (Face Recognition) services, are running:
    ```powershell
    docker-compose up -d
    ```
2.  **Activate Environment (If Applicable):** If you use a Python virtual environment for running utility scripts locally, activate it.
3.  **Run Generation Script:** Execute the embedding generation script from your project's root directory. This script contacts the running `deepface` service via `http://localhost:5001` and appends SQL `UPDATE` statements to `database/sample_data.sql`.
    ```powershell
    python api/utils/generate_embeddings_for_sample_data.py
    ```
4.  **Reset Database & Apply Changes:** To apply the *initial* employee inserts (with NULL embeddings) *and* the *newly appended* `UPDATE` statements for embeddings, you must reset the database volume and restart the containers. This ensures PostgreSQL runs the complete `sample_data.sql` file on initialization.
    ```powershell
    docker-compose down -v
    docker-compose up -d --build api db # Rebuild db to ensure init scripts run
    ```

**Note:** The `sample_data.sql` script initially inserts employees with `NULL` for `face_embedding` and uses the `photo_url` values listed below. The workflow above populates the `face_embedding` field.

## Employees

This table defines the core employee data. The `id` is derived from the Supabase URL provided.

| id (UUID)                                  | name             | rfid_tag | role             | email                       | photo_url (Supabase)                                                                                                                                 | active | face_embedding | last_verified | verification_count |
| :----------------------------------------- | :--------------- | :------- | :--------------- | :-------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------- | :----- | :------------- | :------------ | :----------------- |
| `296c37de-8dbb-4479-a12a-90f59a91a54b`     | Sebastian Galvez | EMP001   | Security Officer | sebastian.galvez@acme.local | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_296c37de-8dbb-4479-a12a-90f59a91a54b_profile_1745411696.jpg` | true   | `NULL`         | `NOW()`       | 0                  |
| `841a532c-6904-45a7-b3fe-b719bf9588f1`     | Luke Reynolds    | EMP002   | Security Officer | luke.reynolds@acme.local    | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_841a532c-6904-45a7-b3fe-b719bf9588f1_profile_1745411327.jpg` | true   | `NULL`         | `NOW()`       | 1                  |
| `56637754-b86c-436d-80da-f2b09433ceba`     | Anthony Hailey   | EMP003   | Administrator    | anthony.hailey@acme.local   | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_56637754-b86c-436d-80da-f2b09433ceba_profile_1745411012.jpg` | true   | `NULL`         | `NOW()`       | 2                  |
| `57f478ed-d79d-4874-b255-327f1868db88`     | Dakota Dietz     | EMP005   | Security Officer | dakota.dietz@acme.local     | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_57f478ed-d79d-4874-b255-327f1868db88_profile_1745411126.jpg` | true   | `NULL`         | `NOW()`       | 3                  |
| `efd6d697-9c09-446e-b486-3441f25040fc`     | Manuel Fermento  | EMP006   | Administrator    | manuel.fermento@acme.local  | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_efd6d697-9c09-446e-b486-3441f25040fc_profile_1745411618.jpg` | true   | `NULL`         | `NOW()`       | 0                  |
| `e9d1edfd-c778-4aee-96e4-cde9ca3f191e`     | Robert Ackerman  | EMP007   | Security Officer | robert.ackerman@acme.local  | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_e9d1edfd-c778-4aee-96e4-cde9ca3f191e_profile_1745411653.jpg` | true   | `NULL`         | `NOW()`       | 1                  |
| `fcb7cf71-654d-4d6e-b1e8-a0d4d9f00b8f`     | Santiago Zambrano| EMP008   | Security Officer | santiago.zambrano@acme.local| `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_fcb7cf71-654d-4d6e-b1e8-a0d4d9f00b8f_profile_1745411673.jpg` | true   | `NULL`         | `NOW()`       | 2                  |
| `2a9ddfb4-cb07-43f3-96c5-4ede0bf9467b`     | Kyle Holliday    | EMP020   | Engineer         | kyle@acme.local             | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_2a9ddfb4-cb07-43f3-96c5-4ede0bf9467b_profile.jpg`       | true   | `NULL`         | `NOW()`       | 3                  |
| `f9941e45-5897-405c-8ec6-8e337a5ded49`     | Kaleb Cole       | EMP021   | Security         | kaleb.i.cole@acme.local     | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_f9941e45-5897-405c-8ec6-8e337a5ded49_profile.jpg`       | true   | `NULL`         | `NOW()`       | 0                  |
| `868e5428-adf6-46c2-b2cb-7f04e6f4ee0a`     | Griffin Holbert  | EMP022   | Engineer         | griffin@acme.local          | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/employees/employee_868e5428-adf6-46c2-b2cb-7f04e6f4ee0a_profile.jpg`       | true   | `NULL`         | `NOW()`       | 0                  |


<!-- Access Log Scenarios -->



## Access Logs Scenarios (Generated from Mock Images)
| Scenario Description                | Employee Name     | Verification Method        | Initial Status | Access Granted | Confidence | `session_id` (Example)                 |
| :---------------------------------- | :---------------- | :------------------------- | :------------- | :------------- | :--------- | :------------------------------------- |
| AnthonyHailey BOTH approved granted 0.91 | Anthony Hailey    | BOTH                       | approved       | Granted        | 0.91       | `589f712d-db65-45c1-a799-ab14b83a08b4` |
| GriffinHolbert FACE ONLY PENDING REVIEW pending NA NA | Griffin Holbert   | FACE_ONLY_PENDING_REVIEW   | pending        | Na             | NA         | `83d1d49f-852c-4180-9ab9-de95d7b60d73` |
| KalebCole FACE approved granted 0.96 | Kaleb Cole        | FACE                       | approved       | Granted        | 0.96       | `44a5721c-e4f4-4854-a5d3-27fe84e5c5eb` |
| KyleHolliday BOTH approved granted 0.99 | Kyle Holliday     | BOTH                       | approved       | Granted        | 0.99       | `df071cb7-d479-4fff-bb33-302d641ecf88` |
| LukeReynolds RFID ONLY PENDING REVIEW pending NA NA | Luke Reynolds     | RFID_ONLY_PENDING_REVIEW   | pending        | Na             | NA         | `c675b315-ae87-4e9b-a440-22fe2d8f3ff9` |
| SantiagoZambrano FACE approved granted 0.97 | Santiago Zambrano | FACE                       | approved       | Granted        | 0.97       | `02fe63be-ff2d-4dea-959a-7f48fb82f0f0` |

## Verification Images (Generated from Mock Images)
| `session_id` (Example)                 | Captured Image URL (Supabase)                                                    | Associated Scenario                |
| :------------------------------------- | :------------------------------------------------------------------------------- | :--------------------------------- |
| `589f712d-db65-45c1-a799-ab14b83a08b4` | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/verification_images/session_589f712d-db65-45c1-a799-ab14b83a08b4.png` | AnthonyHailey BOTH approved granted 0.91 |
| `83d1d49f-852c-4180-9ab9-de95d7b60d73` | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/verification_images/session_83d1d49f-852c-4180-9ab9-de95d7b60d73.png` | GriffinHolbert FACE ONLY PENDING REVIEW pending NA NA |        
| `44a5721c-e4f4-4854-a5d3-27fe84e5c5eb` | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/verification_images/session_44a5721c-e4f4-4854-a5d3-27fe84e5c5eb.png` | KalebCole FACE approved granted 0.96 |
| `df071cb7-d479-4fff-bb33-302d641ecf88` | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/verification_images/session_df071cb7-d479-4fff-bb33-302d641ecf88.png` | KyleHolliday BOTH approved granted 0.99 |
| `c675b315-ae87-4e9b-a440-22fe2d8f3ff9` | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/verification_images/session_c675b315-ae87-4e9b-a440-22fe2d8f3ff9.png` | LukeReynolds RFID ONLY PENDING REVIEW pending NA NA |
| `02fe63be-ff2d-4dea-959a-7f48fb82f0f0` | `https://icaqsnveqjmzyawjdffw.supabase.co/storage/v1/object/public/Campus-Security-and-Evacuation-System/verification_images/session_02fe63be-ff2d-4dea-959a-7f48fb82f0f0.png` | SantiagoZambrano FACE approved granted 0.97 |
---------------------------------------------