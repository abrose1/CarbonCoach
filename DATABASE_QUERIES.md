# CarbonCoach Database Queries

A collection of useful SQL queries for analyzing CarbonCoach data on Railway PostgreSQL.

## Connection
```bash
railway connect postgres
```

## User Analytics

### Get All User Names and Completion Percentages
```sql
SELECT DISTINCT
    s.session_id,
    s.progress_pct,
    ur.response_value as user_name
FROM sessions s
LEFT JOIN user_responses ur ON s.session_id = ur.session_id 
WHERE ur.question_key = 'name'
ORDER BY s.progress_pct DESC, ur.response_value;
```

### User Completion Summary
```sql
SELECT 
    CASE 
        WHEN s.progress_pct = 100 THEN 'Completed (100%)'
        WHEN s.progress_pct >= 50 THEN 'Partial (50-99%)'
        WHEN s.progress_pct >= 20 THEN 'Started (20-49%)'
        ELSE 'Just Started (0-19%)'
    END as completion_category,
    COUNT(*) as user_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT session_id) FROM user_responses WHERE question_key = 'name'), 1) as percentage
FROM sessions s
JOIN user_responses ur ON s.session_id = ur.session_id
WHERE ur.question_key = 'name'
GROUP BY completion_category
ORDER BY MIN(s.progress_pct) DESC;
```

## Reference Data Counts

### Database Overview
```sql
SELECT 'sessions' as table_name, COUNT(*) as record_count FROM sessions
UNION ALL
SELECT 'user_responses', COUNT(*) FROM user_responses
UNION ALL
SELECT 'carbon_calculations', COUNT(*) FROM carbon_calculations
UNION ALL
SELECT 'recommendations', COUNT(*) FROM recommendations
UNION ALL
SELECT 'dsire_federal_programs', COUNT(*) FROM dsire_federal_programs
UNION ALL
SELECT 'dsire_state_programs', COUNT(*) FROM dsire_state_programs
UNION ALL
SELECT 'vehicle_mpg', COUNT(*) FROM vehicle_mpg
UNION ALL
SELECT 'emission_factors', COUNT(*) FROM emission_factors
UNION ALL
SELECT 'electricity_rates', COUNT(*) FROM electricity_rates;
```

### DSIRE Programs by State
```sql
SELECT state, COUNT(*) as program_count
FROM dsire_state_programs
GROUP BY state
ORDER BY program_count DESC
LIMIT 10;
```

## Session Analysis

### Sessions by Creation Date
```sql
SELECT 
    DATE(created_at) as date,
    COUNT(*) as sessions_created
FROM sessions
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Average Progress by Section
```sql
SELECT 
    current_section,
    COUNT(*) as sessions,
    ROUND(AVG(progress_pct), 1) as avg_progress
FROM sessions
GROUP BY current_section
ORDER BY avg_progress DESC;
```

## Response Data Analysis

### Most Common User Locations
```sql
SELECT 
    ur_state.response_value as state,
    ur_city.response_value as city,
    COUNT(*) as user_count
FROM user_responses ur_state
JOIN user_responses ur_city ON ur_state.session_id = ur_city.session_id
WHERE ur_state.question_key = 'state' 
    AND ur_city.question_key = 'city'
GROUP BY ur_state.response_value, ur_city.response_value
ORDER BY user_count DESC
LIMIT 10;
```

### Vehicle Distribution
```sql
SELECT 
    CONCAT(
        SUBSTRING(response_value FROM 'make:\s*([^,]+)'),
        ' ',
        SUBSTRING(response_value FROM 'model:\s*([^,}]+)')
    ) as vehicle,
    COUNT(*) as count
FROM user_responses
WHERE question_key IN ('vehicle_make', 'vehicle_model')
    AND response_value IS NOT NULL
GROUP BY vehicle
HAVING COUNT(*) > 1
ORDER BY count DESC;
```

## Carbon Footprint Analysis

### Average Emissions by Component
```sql
SELECT 
    ROUND(AVG(home_emissions), 0) as avg_home_kg,
    ROUND(AVG(transport_emissions), 0) as avg_transport_kg,
    ROUND(AVG(consumption_emissions), 0) as avg_consumption_kg,
    ROUND(AVG(total_annual_co2_kg), 0) as avg_total_kg
FROM carbon_calculations;
```

### Footprint Distribution
```sql
SELECT 
    CASE 
        WHEN total_annual_co2_kg < 5000 THEN 'Low (< 5 tons)'
        WHEN total_annual_co2_kg < 10000 THEN 'Medium (5-10 tons)'
        WHEN total_annual_co2_kg < 16000 THEN 'High (10-16 tons)'
        ELSE 'Very High (> 16 tons)'
    END as footprint_category,
    COUNT(*) as user_count
FROM carbon_calculations
GROUP BY footprint_category
ORDER BY MIN(total_annual_co2_kg);
```

## Maintenance Queries

### Clear User Data (for fresh launch)
```sql
-- Clear in dependency order (child tables first)
DELETE FROM calculation_breakdowns;
DELETE FROM conversation_logs;
DELETE FROM recommendations;
DELETE FROM carbon_calculations;  
DELETE FROM user_responses;
DELETE FROM sessions;
```

### Verify Clean State
```sql
SELECT 'User data cleared' as status,
    (SELECT COUNT(*) FROM sessions) as sessions,
    (SELECT COUNT(*) FROM user_responses) as responses,
    (SELECT COUNT(*) FROM carbon_calculations) as calculations;
```