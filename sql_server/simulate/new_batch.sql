/* =====================================================================
   RxSource - simulate a new batch of source activity "now".
   Used to demonstrate incremental extraction (Phase 2) and SCD2 snapshots (Phase 3).
   Parameters are bound by generator/simulate.py, in this order:
     @late_lines, @restatements, @duplicates, @price_changes
   Everything happens in one transaction; dispensing dates stay inside 2023-2025.
   ===================================================================== */
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @late_lines INT = ?, @restatements INT = ?, @duplicates INT = ?, @price_changes INT = ?;
DECLARE @now DATETIME2(0) = SYSUTCDATETIME();
DECLARE @today DATE = CAST(@now AS DATE);
DECLARE @out TABLE (action VARCHAR(40), row_count INT);

BEGIN TRANSACTION;

/* 1. Late-arriving lines: added to recent prescriptions, arriving today. */
WITH rx AS (
    SELECT TOP (@late_lines) prescription_id, issue_date
    FROM rx.prescription
    WHERE issue_date >= '2025-10-01'
    ORDER BY NEWID()
)
INSERT rx.prescription_item
    (prescription_id, presentation_code, items, quantity, net_ingredient_cost, actual_cost,
     dispensing_date, created_at, updated_at)
SELECT rx.prescription_id, m.presentation_code, 1, m.pack_quantity,
       ROUND(m.pack_quantity * m.unit_cost, 2), ROUND(m.pack_quantity * m.unit_cost * 0.92, 2),
       CASE WHEN DATEADD(DAY, 2, rx.issue_date) > '2025-12-31' THEN '2025-12-31'
            ELSE DATEADD(DAY, 2, rx.issue_date) END,
       @now, @now
FROM rx
CROSS APPLY (SELECT TOP 1 presentation_code, pack_quantity, unit_cost
             FROM rx.medicine
             WHERE is_generic = 1
             ORDER BY CHECKSUM(NEWID(), rx.prescription_id)) m;
INSERT @out VALUES ('late lines inserted', @@ROWCOUNT);

/* 2. Restatements: existing lines corrected (quantity and cost doubled), updated_at moves on. */
WITH x AS (
    SELECT TOP (@restatements) quantity, net_ingredient_cost, actual_cost, updated_at
    FROM rx.prescription_item
    WHERE quantity > 0 AND updated_at < DATEADD(DAY, -1, @now)
    ORDER BY NEWID()
)
UPDATE x SET quantity = quantity * 2, net_ingredient_cost = net_ingredient_cost * 2,
             actual_cost = actual_cost * 2, updated_at = @now;
INSERT @out VALUES ('lines restated', @@ROWCOUNT);

/* 3. Double submissions: copies of recent lines under new ids. */
INSERT rx.prescription_item
    (prescription_id, presentation_code, items, quantity, net_ingredient_cost, actual_cost,
     dispensing_date, created_at, updated_at)
SELECT TOP (@duplicates) prescription_id, presentation_code, items, quantity, net_ingredient_cost,
       actual_cost, dispensing_date, @now, @now
FROM rx.prescription_item
WHERE dispensing_date >= '2025-11-01'
ORDER BY NEWID();
INSERT @out VALUES ('duplicate lines inserted', @@ROWCOUNT);

/* 4. Price changes: new Drug Tariff price for a few generics (closes the open history row). */
DECLARE @changes TABLE (presentation_code CHAR(15) PRIMARY KEY, new_cost DECIMAL(10,4));
INSERT @changes
SELECT TOP (@price_changes) m.presentation_code,
       ROUND(m.unit_cost * (0.6 + (ABS(CHECKSUM(NEWID())) % 120) / 100.0), 4)
FROM rx.medicine m
JOIN rx.medicine_price_history h
  ON h.presentation_code = m.presentation_code AND h.effective_to IS NULL
WHERE m.is_generic = 1 AND h.effective_from < @today
ORDER BY NEWID();

UPDATE h SET effective_to = DATEADD(DAY, -1, @today)
FROM rx.medicine_price_history h JOIN @changes c ON c.presentation_code = h.presentation_code
WHERE h.effective_to IS NULL;

INSERT rx.medicine_price_history (presentation_code, effective_from, effective_to, unit_cost, change_reason, created_at)
SELECT presentation_code, @today, NULL, new_cost, 'tariff change', @now FROM @changes;

UPDATE m SET unit_cost = c.new_cost, updated_at = @now
FROM rx.medicine m JOIN @changes c ON c.presentation_code = m.presentation_code;
INSERT @out VALUES ('medicine prices changed', @@ROWCOUNT);

COMMIT;

SELECT action, row_count FROM @out;
