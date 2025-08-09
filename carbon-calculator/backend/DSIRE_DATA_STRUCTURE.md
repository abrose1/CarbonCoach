# DSIRE XML Data Structure Analysis

## Overview
The DSIRE database has been split into multiple XML chunk files for easier processing. This document summarizes the structure, relationships, and filtering criteria for importing residential financial incentive programs into the Carbon Calculator.

## File Structure

### Chunk Files Organization
- **Total programs**: ~4,028 across all chunks
- **Total chunks**: ~50 files (dsire_chunk_aa through dsire_chunk_bl)
- **File naming**: `dsire_chunk_[aa-bl]` (alphabetical sequence)

### Key Tables by Chunk
- **`dsire_chunk_ak/al/am`**: Main program data (`program` table)
- **`dsire_chunk_au/av/aw`**: Technology mappings (`program_technology` table)  
- **`dsire_chunk_as`**: Sector eligibility (`program_sector` table)
- **`dsire_chunk_aw`**: Reference tables (`state`, `program_type`, `sector`)
- **`dsire_chunk_am`**: Reference tables (`program_category`)
- **`dsire_chunk_ay`**: Reference tables (`technology`, `technology_category`)

## Core Data Tables

### Program Table (Main Data)
**Location**: `dsire_chunk_ak`, `dsire_chunk_al`, `dsire_chunk_am`

**Key Fields**:
```xml
<column name="id">program_id</column>
<column name="name">program_name</column>
<column name="code">state_or_federal_code</column>
<column name="summary">detailed_description</column>
<column name="websiteurl">program_website</column>
<column name="program_category_id">1_or_2</column>
<column name="program_type_id">numeric_type_id</column>
<column name="state_id">numeric_state_reference</column>
```

### Program-Technology Mapping
**Location**: `dsire_chunk_au`, `dsire_chunk_av`, `dsire_chunk_aw`

**Structure**:
```xml
<column name="program_id">links_to_program</column>
<column name="technology_id">numeric_tech_id</column>
```

### Program-Sector Mapping (Eligibility)
**Location**: `dsire_chunk_as`

**Structure**:
```xml
<column name="program_id">links_to_program</column>
<column name="sector_id">who_can_apply</column>
```

## Reference Tables

### Program Categories
**Location**: `dsire_chunk_am`
```
ID: 1 -> Financial Incentive ✅ (Import this)
ID: 2 -> Regulatory Policy   ❌ (Skip this)
```

### Program Types (Financial Incentives Only)
**Location**: `dsire_chunk_aw`

**Consumer-Relevant Types**:
```
ID: 31 -> Personal Tax Credit     ✅
ID: 32 -> Personal Tax Deduction  ✅  
ID: 87 -> Grant Program           ✅
ID: 88 -> Rebate Program          ✅
ID: 89 -> Loan Program            ✅
```

**Skip**: Corporate types (18, 19, 21, 49), complex types (13, 85, 91, 92), vague types (68)

### Technology Categories & IDs
**Location**: `dsire_chunk_ay`

**Carbon Calculator Technology Mapping**:
```
DSIRE Category -> Your Category:
1  (Solar Technologies)     -> solar
2  (Geothermal Technologies)-> heat_pumps  
9  (Appliances)            -> appliances
10 (HVAC)                  -> hvac
11 (Lighting)              -> lighting
14 (Building Envelope)     -> insulation
29 (Vehicles)              -> electric_vehicles
```

**Specific Technology IDs to Import**:
```
solar: [7, 2]                    # Solar PV, Solar Water Heat
heat_pumps: [12, 85]             # Geothermal Heat Pumps, Heat Pumps
electric_vehicles: [221, 222, 223] # Passenger EVs, Zero Emission, PHEVs
hvac: [86, 91]                   # Air Conditioners, Programmable Thermostats
appliances: [73, 74, 75, 79, 138] # Washers, Dishwashers, Refrigerators, Water Heaters, Tankless
insulation: [95, 96, 114]        # Building Insulation, Windows, Insulation
lighting: [137]                  # LED Lighting
```

### Sectors (Eligibility)
**Location**: `dsire_chunk_aw`

**Residential Sectors**:
```
Sector  9: 2,965 programs - Residential ✅ (Target this)
Sector 22:     0 programs - Multifamily Residential  
Sector 23:     0 programs - Low Income Residential
Sector 29:     0 programs - Residential (Parent)
```

**Other Major Sectors**:
```
Sector  1: 2,776 programs - Commercial
Sector  3: 1,711 programs - Industrial  
Sector  5: 1,216 programs - Local Government
Sector  6: 1,055 programs - Nonprofit
```

## Federal vs State Classification

### Code Field Pattern
**Location**: Program table `code` field

**Classification Logic**:
```python
if code.startswith('US'):
    return 'federal'  # Examples: "US05R", "US45F"
elif len(code) >= 2 and code[:2].isalpha():
    state = code[:2]  # Examples: "CA115F", "TX12R", "ID07R"
    return 'state', state
```

**Counts**:
- Federal programs: 11 (codes starting with "US")
- State programs: 1,836 (codes starting with state abbreviation)
- All 50 states + DC + territories represented

## Complete Import Filter

### Multi-Step Filtering Process
Programs must meet **ALL** criteria:

1. **Financial Incentives**: `program_category_id = 1`
2. **Consumer Types**: `program_type_id IN [31, 32, 87, 88, 89]`
3. **Residential Eligible**: Has link to `sector_id = 9` in program_sector table
4. **Relevant Technology**: Has link to one of 16 technology IDs in program_technology table
5. **Federal/State**: Classify by code field pattern

### Database Mapping
```python
# DSIRE -> Your Database
program_category_id=1 -> category='financial_incentive'
program_type_id=31    -> program_type='tax_credit'
program_type_id=32    -> program_type='tax_deduction'
program_type_id=87    -> program_type='grant'
program_type_id=88    -> program_type='rebate'  
program_type_id=89    -> program_type='loan'

technology_id -> technology_name + technology_category
code field -> federal_programs or state_programs table
```

## Data Quality Notes

### Good Quality
- Most programs have complete name and summary fields
- Website URLs are generally populated
- Clean numeric IDs throughout

### Requires Processing
- **HTML Cleanup**: Summaries contain HTML tags that need stripping
- **Technology Mapping**: Must map DSIRE technology_id to your category names
- **Cross-Table Joins**: Need to join across 3+ tables for full filtering

## Expected Import Volume

### Rough Estimates
- **Total DSIRE programs**: 4,028
- **After category filter**: ~2,000 (50% are financial incentives)
- **After type filter**: ~400-800 (20-40% are consumer-relevant)
- **After residential filter**: ~200-400 (many programs target multiple sectors)
- **After technology filter**: ~100-300 (subset that match carbon calculator categories)

### Processing Strategy
1. Build lookup tables from reference data first
2. Filter programs by category, type, residential eligibility
3. Check technology mappings for each qualifying program
4. Classify as federal/state and insert into appropriate table

## Usage Notes for Future Sessions

### Key Files to Examine
- **Program data**: `dsire_chunk_ak/al/am` 
- **Technology links**: `dsire_chunk_au/av/aw`
- **Sector links**: `dsire_chunk_as`
- **Reference tables**: `dsire_chunk_aw`, `dsire_chunk_am`, `dsire_chunk_ay`

### Common Patterns
- All XML uses `<![CDATA[value]]>` format
- Program IDs are consistent across tables
- Multiple programs can link to same technology/sector
- Empty fields use `<![CDATA[]]>` (not missing tags)

### Testing Approach
- Start with small sample (first 50 programs)
- Verify all table joins work correctly
- Test federal vs state classification
- Validate technology category mapping
- Check residential sector filtering

---

**Generated**: 2025-01-29 by Claude Code analysis of DSIRE XML chunk files