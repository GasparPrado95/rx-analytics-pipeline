/* =====================================================================
   RxSource - row counts, referential integrity and data-quality profile.
   Runs standalone in SSMS/sqlcmd, or via: python -m generator.check

   category = rowcount   : informational, compared to expected ranges in Python
   category = integrity  : MUST be 0 (orphans, untrusted constraints, broken invariants)
   category = dq_profile : deliberate defects the dbt layer must handle (expected > 0)
   ===================================================================== */
USE RxSource;
SET NOCOUNT ON;

DECLARE @r TABLE (category VARCHAR(12), check_name VARCHAR(80), value BIGINT);

/* ---------- Row counts ---------- */
INSERT @r SELECT 'rowcount', 'rx.' + t.name, SUM(p.rows)
FROM sys.tables t
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
WHERE t.schema_id = SCHEMA_ID('rx')
GROUP BY t.name;

/* ---------- Constraints are enabled and trusted (bcp skips checks; loader re-validates) ---------- */
INSERT @r SELECT 'integrity', 'foreign keys disabled or untrusted', COUNT(*)
FROM sys.foreign_keys WHERE schema_id = SCHEMA_ID('rx') AND (is_disabled = 1 OR is_not_trusted = 1);
INSERT @r SELECT 'integrity', 'check constraints disabled or untrusted', COUNT(*)
FROM sys.check_constraints WHERE schema_id = SCHEMA_ID('rx') AND (is_disabled = 1 OR is_not_trusted = 1);

/* ---------- Orphans (explicit, independent of the FK metadata) ---------- */
INSERT @r SELECT 'integrity', 'icb -> region orphans', COUNT(*)
FROM rx.icb c LEFT JOIN rx.region r ON r.region_code = c.region_code WHERE r.region_code IS NULL;
INSERT @r SELECT 'integrity', 'practice -> icb orphans', COUNT(*)
FROM rx.practice p LEFT JOIN rx.icb c ON c.icb_code = p.icb_code WHERE c.icb_code IS NULL;
INSERT @r SELECT 'integrity', 'prescriber -> practice orphans', COUNT(*)
FROM rx.prescriber s LEFT JOIN rx.practice p ON p.practice_code = s.practice_code WHERE p.practice_code IS NULL;
INSERT @r SELECT 'integrity', 'patient -> practice orphans', COUNT(*)
FROM rx.patient s LEFT JOIN rx.practice p ON p.practice_code = s.practice_code WHERE p.practice_code IS NULL;
INSERT @r SELECT 'integrity', 'medicine -> chemical orphans', COUNT(*)
FROM rx.medicine m LEFT JOIN rx.bnf_chemical c ON c.chemical_code = m.chemical_code WHERE c.chemical_code IS NULL;
INSERT @r SELECT 'integrity', 'chemical -> paragraph -> section -> chapter broken', COUNT(*)
FROM rx.bnf_chemical c
LEFT JOIN rx.bnf_paragraph p ON p.paragraph_code = c.paragraph_code
LEFT JOIN rx.bnf_section s ON s.section_code = p.section_code
LEFT JOIN rx.bnf_chapter h ON h.chapter_code = s.chapter_code
WHERE h.chapter_code IS NULL;
INSERT @r SELECT 'integrity', 'prescription -> patient/prescriber/practice orphans', COUNT(*)
FROM rx.prescription x
LEFT JOIN rx.patient pt ON pt.patient_id = x.patient_id
LEFT JOIN rx.prescriber pr ON pr.prescriber_id = x.prescriber_id
LEFT JOIN rx.practice pc ON pc.practice_code = x.practice_code
WHERE pt.patient_id IS NULL OR pr.prescriber_id IS NULL OR pc.practice_code IS NULL;
INSERT @r SELECT 'integrity', 'prescription_item -> prescription orphans', COUNT(*)
FROM rx.prescription_item i LEFT JOIN rx.prescription x ON x.prescription_id = i.prescription_id
WHERE x.prescription_id IS NULL;
INSERT @r SELECT 'integrity', 'prescription_item -> medicine orphans', COUNT(*)
FROM rx.prescription_item i LEFT JOIN rx.medicine m ON m.presentation_code = i.presentation_code
WHERE m.presentation_code IS NULL;

/* ---------- Business invariants ---------- */
INSERT @r SELECT 'integrity', 'prescription practice <> prescriber practice', COUNT(*)
FROM rx.prescription x JOIN rx.prescriber pr ON pr.prescriber_id = x.prescriber_id
WHERE pr.practice_code <> x.practice_code;
INSERT @r SELECT 'integrity', 'prescription practice <> patient registered practice', COUNT(*)
FROM rx.prescription x JOIN rx.patient pt ON pt.patient_id = x.patient_id
WHERE pt.practice_code <> x.practice_code;
INSERT @r SELECT 'integrity', 'branded generic_equivalent_code not a generic', COUNT(*)
FROM rx.medicine b JOIN rx.medicine g ON g.presentation_code = b.generic_equivalent_code
WHERE g.is_generic = 0 OR g.chemical_code <> b.chemical_code;
INSERT @r SELECT 'integrity', 'medicines without exactly one open price row', COUNT(*)
FROM rx.medicine m
OUTER APPLY (SELECT COUNT(*) AS n FROM rx.medicine_price_history h
             WHERE h.presentation_code = m.presentation_code AND h.effective_to IS NULL) o
WHERE o.n <> 1;
INSERT @r SELECT 'integrity', 'medicine.unit_cost <> open price row', COUNT(*)
FROM rx.medicine m JOIN rx.medicine_price_history h
  ON h.presentation_code = m.presentation_code AND h.effective_to IS NULL
WHERE h.unit_cost <> m.unit_cost;
INSERT @r SELECT 'integrity', 'price history gaps or overlaps', COUNT(*)
FROM (SELECT effective_to,
             LEAD(effective_from) OVER (PARTITION BY presentation_code ORDER BY effective_from) AS next_from
      FROM rx.medicine_price_history) h
WHERE h.next_from IS NOT NULL AND DATEADD(DAY, 1, h.effective_to) <> h.next_from;
INSERT @r SELECT 'integrity', 'dispensing_date outside 2023-01-01..2025-12-31', COUNT(*)
FROM rx.prescription_item WHERE dispensing_date NOT BETWEEN '2023-01-01' AND '2025-12-31';
INSERT @r SELECT 'integrity', 'dispensed before issue', COUNT(*)
FROM rx.prescription_item i JOIN rx.prescription x ON x.prescription_id = i.prescription_id
WHERE i.dispensing_date < x.issue_date;
INSERT @r SELECT 'integrity', 'updated_at earlier than created_at', COUNT(*)
FROM rx.prescription_item WHERE updated_at < created_at;

/* ---------- Data-quality profile (deliberate; handled in dbt staging) ---------- */
INSERT @r SELECT 'dq_profile', 'item lines with NULL actual_cost', COUNT(*) FROM rx.prescription_item WHERE actual_cost IS NULL;
INSERT @r SELECT 'dq_profile', 'item lines with NULL quantity', COUNT(*) FROM rx.prescription_item WHERE quantity IS NULL;
INSERT @r SELECT 'dq_profile', 'item lines with NULL net_ingredient_cost', COUNT(*) FROM rx.prescription_item WHERE net_ingredient_cost IS NULL;
INSERT @r SELECT 'dq_profile', 'credit lines (negative quantity)', COUNT(*) FROM rx.prescription_item WHERE quantity < 0;
INSERT @r SELECT 'dq_profile', 'duplicate item lines (same natural key)', SUM(n - 1)
FROM (SELECT COUNT(*) AS n FROM rx.prescription_item
      GROUP BY prescription_id, presentation_code, dispensing_date, items, quantity, net_ingredient_cost
      HAVING COUNT(*) > 1) d;
INSERT @r SELECT 'dq_profile', 'late arrivals (created > 30 days after dispensing)', COUNT(*)
FROM rx.prescription_item WHERE created_at > DATEADD(DAY, 30, CAST(dispensing_date AS DATETIME2(0)));
INSERT @r SELECT 'dq_profile', 'restated lines (updated_at > created_at)', COUNT(*)
FROM rx.prescription_item WHERE updated_at > created_at;
INSERT @r SELECT 'dq_profile', 'patients with NULL imd_decile', COUNT(*) FROM rx.patient WHERE imd_decile IS NULL;
INSERT @r SELECT 'dq_profile', 'patients with non-standard sex code', COUNT(*)
FROM rx.patient WHERE sex COLLATE Latin1_General_CS_AS NOT IN ('F', 'M');
INSERT @r SELECT 'dq_profile', 'practices with NULL postcode_district', COUNT(*) FROM rx.practice WHERE postcode_district IS NULL;
INSERT @r SELECT 'dq_profile', 'practices with non-standard rural_urban', COUNT(*)
FROM rx.practice WHERE rural_urban COLLATE Latin1_General_CS_AS NOT IN ('Urban', 'Rural');

SELECT category, check_name, ISNULL(value, 0) AS value FROM @r ORDER BY category, check_name;
