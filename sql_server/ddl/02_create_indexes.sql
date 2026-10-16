/* =====================================================================
   RxSource - 02: secondary indexes
   - FK columns, so joins and FK validation don't scan.
   - Watermark columns (updated_at), so incremental extracts are range seeks.
   ===================================================================== */
USE RxSource;
GO

CREATE INDEX ix_icb_region            ON rx.icb (region_code);
CREATE INDEX ix_practice_icb          ON rx.practice (icb_code);
CREATE INDEX ix_prescriber_practice   ON rx.prescriber (practice_code);
CREATE INDEX ix_medicine_chemical     ON rx.medicine (chemical_code);
CREATE INDEX ix_patient_practice      ON rx.patient (practice_code);

CREATE INDEX ix_prescription_patient    ON rx.prescription (patient_id);
CREATE INDEX ix_prescription_prescriber ON rx.prescription (prescriber_id);
CREATE INDEX ix_prescription_updated    ON rx.prescription (updated_at);

CREATE INDEX ix_item_prescription     ON rx.prescription_item (prescription_id);
CREATE INDEX ix_item_presentation     ON rx.prescription_item (presentation_code);
CREATE INDEX ix_item_updated          ON rx.prescription_item (updated_at) INCLUDE (dispensing_date);
CREATE INDEX ix_item_dispensing_date  ON rx.prescription_item (dispensing_date);
GO
