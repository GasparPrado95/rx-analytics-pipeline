/* =====================================================================
   RxSource - 01: tables
   Normalised OLTP-style schema. Every table carries created_at / updated_at
   so the EL layer can extract incrementally on a high-watermark.
   ===================================================================== */
USE RxSource;
GO

/* ---------- Organisation hierarchy: region -> ICB -> practice ---------- */

CREATE TABLE rx.region (
    region_code      CHAR(3)        NOT NULL,   -- NHS England region code, e.g. Y56
    ons_code         CHAR(9)        NOT NULL,   -- ONS code, e.g. E40000003
    region_name      NVARCHAR(60)   NOT NULL,
    created_at       DATETIME2(0)   NOT NULL CONSTRAINT df_region_created DEFAULT SYSUTCDATETIME(),
    updated_at       DATETIME2(0)   NOT NULL CONSTRAINT df_region_updated DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_region PRIMARY KEY (region_code),
    CONSTRAINT uq_region_ons UNIQUE (ons_code)
);

CREATE TABLE rx.icb (
    icb_code         CHAR(3)        NOT NULL,   -- ODS code, e.g. QOP
    icb_name         NVARCHAR(120)  NOT NULL,
    region_code      CHAR(3)        NOT NULL,
    created_at       DATETIME2(0)   NOT NULL CONSTRAINT df_icb_created DEFAULT SYSUTCDATETIME(),
    updated_at       DATETIME2(0)   NOT NULL CONSTRAINT df_icb_updated DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_icb PRIMARY KEY (icb_code),
    CONSTRAINT fk_icb_region FOREIGN KEY (region_code) REFERENCES rx.region (region_code)
);

CREATE TABLE rx.practice (
    practice_code     CHAR(6)        NOT NULL,  -- ODS-style code, e.g. P84012
    practice_name     NVARCHAR(120)  NOT NULL,
    icb_code          CHAR(3)        NOT NULL,
    postcode_district VARCHAR(4)     NULL,      -- e.g. M14 (nullable: source has gaps)
    list_size         INT            NOT NULL,  -- registered patients
    rural_urban       VARCHAR(10)    NOT NULL,  -- free text in source: Urban / Rural (inconsistent casing)
    imd_decile        TINYINT        NOT NULL,  -- deprivation of practice area, 1 = most deprived
    opened_date       DATE           NOT NULL,
    created_at        DATETIME2(0)   NOT NULL CONSTRAINT df_practice_created DEFAULT SYSUTCDATETIME(),
    updated_at        DATETIME2(0)   NOT NULL CONSTRAINT df_practice_updated DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_practice PRIMARY KEY (practice_code),
    CONSTRAINT fk_practice_icb FOREIGN KEY (icb_code) REFERENCES rx.icb (icb_code),
    CONSTRAINT ck_practice_list_size CHECK (list_size > 0),
    CONSTRAINT ck_practice_imd CHECK (imd_decile BETWEEN 1 AND 10)
);

/* ---------- Prescribers ---------- */

CREATE TABLE rx.prescriber_type (
    prescriber_type_code CHAR(2)       NOT NULL,  -- GP / NP / PH
    prescriber_type_name NVARCHAR(40)  NOT NULL,
    CONSTRAINT pk_prescriber_type PRIMARY KEY (prescriber_type_code)
);

CREATE TABLE rx.prescriber (
    prescriber_id        INT           NOT NULL,
    prescriber_code      CHAR(8)       NOT NULL,  -- synthetic professional registration number
    prescriber_type_code CHAR(2)       NOT NULL,
    practice_code        CHAR(6)       NOT NULL,
    first_name           NVARCHAR(60)  NOT NULL,  -- Faker-generated, not real people
    last_name            NVARCHAR(60)  NOT NULL,
    start_date           DATE          NOT NULL,
    created_at           DATETIME2(0)  NOT NULL CONSTRAINT df_prescriber_created DEFAULT SYSUTCDATETIME(),
    updated_at           DATETIME2(0)  NOT NULL CONSTRAINT df_prescriber_updated DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_prescriber PRIMARY KEY (prescriber_id),
    CONSTRAINT uq_prescriber_code UNIQUE (prescriber_code),
    CONSTRAINT fk_prescriber_type FOREIGN KEY (prescriber_type_code) REFERENCES rx.prescriber_type (prescriber_type_code),
    CONSTRAINT fk_prescriber_practice FOREIGN KEY (practice_code) REFERENCES rx.practice (practice_code)
);

/* ---------- BNF hierarchy: chapter -> section -> paragraph -> chemical -> presentation ---------- */

CREATE TABLE rx.bnf_chapter (
    chapter_code   CHAR(2)        NOT NULL,
    chapter_name   NVARCHAR(100)  NOT NULL,
    CONSTRAINT pk_bnf_chapter PRIMARY KEY (chapter_code)
);

CREATE TABLE rx.bnf_section (
    section_code   CHAR(4)        NOT NULL,
    section_name   NVARCHAR(120)  NOT NULL,
    chapter_code   CHAR(2)        NOT NULL,
    CONSTRAINT pk_bnf_section PRIMARY KEY (section_code),
    CONSTRAINT fk_bnf_section_chapter FOREIGN KEY (chapter_code) REFERENCES rx.bnf_chapter (chapter_code)
);

CREATE TABLE rx.bnf_paragraph (
    paragraph_code CHAR(6)        NOT NULL,
    paragraph_name NVARCHAR(120)  NOT NULL,
    section_code   CHAR(4)        NOT NULL,
    CONSTRAINT pk_bnf_paragraph PRIMARY KEY (paragraph_code),
    CONSTRAINT fk_bnf_paragraph_section FOREIGN KEY (section_code) REFERENCES rx.bnf_section (section_code)
);

CREATE TABLE rx.bnf_chemical (
    chemical_code  CHAR(9)        NOT NULL,
    chemical_name  NVARCHAR(120)  NOT NULL,
    paragraph_code CHAR(6)        NOT NULL,
    CONSTRAINT pk_bnf_chemical PRIMARY KEY (chemical_code),
    CONSTRAINT fk_bnf_chemical_paragraph FOREIGN KEY (paragraph_code) REFERENCES rx.bnf_paragraph (paragraph_code)
);

CREATE TABLE rx.medicine (
    presentation_code         CHAR(15)       NOT NULL,  -- 15-char BNF-style code
    presentation_name         NVARCHAR(200)  NOT NULL,
    chemical_code             CHAR(9)        NOT NULL,
    is_generic                BIT            NOT NULL,
    brand_name                NVARCHAR(80)   NULL,      -- NULL for generics
    generic_equivalent_code   CHAR(15)       NULL,      -- branded -> its generic presentation, if one exists
    form                      VARCHAR(30)    NOT NULL,  -- tablet, capsule, inhaler, oral solution...
    strength                  VARCHAR(40)    NOT NULL,
    unit_of_measure           VARCHAR(20)    NOT NULL,  -- tablet, capsule, ml, gram, dose, device
    pack_quantity             INT            NOT NULL,  -- typical quantity per item
    unit_cost                 DECIMAL(10,4)  NOT NULL,  -- CURRENT price per unit (GBP); history in medicine_price_history
    created_at                DATETIME2(0)   NOT NULL CONSTRAINT df_medicine_created DEFAULT SYSUTCDATETIME(),
    updated_at                DATETIME2(0)   NOT NULL CONSTRAINT df_medicine_updated DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_medicine PRIMARY KEY (presentation_code),
    CONSTRAINT fk_medicine_chemical FOREIGN KEY (chemical_code) REFERENCES rx.bnf_chemical (chemical_code),
    CONSTRAINT fk_medicine_generic_equiv FOREIGN KEY (generic_equivalent_code) REFERENCES rx.medicine (presentation_code),
    CONSTRAINT ck_medicine_unit_cost CHECK (unit_cost > 0),
    CONSTRAINT ck_medicine_brand CHECK (
        (is_generic = 1 AND brand_name IS NULL AND generic_equivalent_code IS NULL)
        OR (is_generic = 0 AND brand_name IS NOT NULL))
);

-- Drug Tariff-style price history. One open row (effective_to IS NULL) per medicine.
CREATE TABLE rx.medicine_price_history (
    presentation_code  CHAR(15)       NOT NULL,
    effective_from     DATE           NOT NULL,
    effective_to       DATE           NULL,
    unit_cost          DECIMAL(10,4)  NOT NULL,
    change_reason      VARCHAR(40)    NOT NULL,  -- initial / price concession / tariff reduction / annual uplift
    created_at         DATETIME2(0)   NOT NULL CONSTRAINT df_mph_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_medicine_price_history PRIMARY KEY (presentation_code, effective_from),
    CONSTRAINT fk_mph_medicine FOREIGN KEY (presentation_code) REFERENCES rx.medicine (presentation_code),
    CONSTRAINT ck_mph_dates CHECK (effective_to IS NULL OR effective_to > effective_from)
);

/* ---------- Patients (synthetic, banded: no PII) ---------- */

CREATE TABLE rx.patient (
    patient_id        INT           NOT NULL,
    practice_code     CHAR(6)       NOT NULL,  -- registered practice
    age_band          VARCHAR(5)    NOT NULL,  -- 0-4, 5-14, ..., 85+
    sex               VARCHAR(1)    NOT NULL,  -- F / M / U (source casing is inconsistent)
    imd_decile        TINYINT       NULL,      -- nullable: source has gaps
    registered_date   DATE          NOT NULL,
    created_at        DATETIME2(0)  NOT NULL CONSTRAINT df_patient_created DEFAULT SYSUTCDATETIME(),
    updated_at        DATETIME2(0)  NOT NULL CONSTRAINT df_patient_updated DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_patient PRIMARY KEY (patient_id),
    CONSTRAINT fk_patient_practice FOREIGN KEY (practice_code) REFERENCES rx.practice (practice_code),
    CONSTRAINT ck_patient_imd CHECK (imd_decile IS NULL OR imd_decile BETWEEN 1 AND 10)
);

/* ---------- Transactions: prescription (header) -> prescription_item (line) ---------- */

CREATE TABLE rx.prescription (
    prescription_id  BIGINT        NOT NULL,
    patient_id       INT           NOT NULL,
    prescriber_id    INT           NOT NULL,
    practice_code    CHAR(6)       NOT NULL,
    issue_date       DATE          NOT NULL,
    created_at       DATETIME2(0)  NOT NULL,
    updated_at       DATETIME2(0)  NOT NULL,
    CONSTRAINT pk_prescription PRIMARY KEY (prescription_id),
    CONSTRAINT fk_prescription_patient FOREIGN KEY (patient_id) REFERENCES rx.patient (patient_id),
    CONSTRAINT fk_prescription_prescriber FOREIGN KEY (prescriber_id) REFERENCES rx.prescriber (prescriber_id),
    CONSTRAINT fk_prescription_practice FOREIGN KEY (practice_code) REFERENCES rx.practice (practice_code)
);

-- IDENTITY so later inserts (e.g. new monthly batches) get keys from the database.
-- The generator bulk-loads its own ids with bcp -E (keep identity) for reproducibility.
CREATE TABLE rx.prescription_item (
    item_line_id         BIGINT IDENTITY(1,1) NOT NULL,
    prescription_id      BIGINT         NOT NULL,
    presentation_code    CHAR(15)       NOT NULL,
    items                SMALLINT       NOT NULL,
    quantity             DECIMAL(10,2)  NULL,      -- nullable: source has gaps; a few credits are negative
    net_ingredient_cost  DECIMAL(12,2)  NULL,
    actual_cost          DECIMAL(12,2)  NULL,
    dispensing_date      DATE           NOT NULL,
    created_at           DATETIME2(0)   NOT NULL,  -- when the line reached this system (late arrivals lag by months)
    updated_at           DATETIME2(0)   NOT NULL,  -- bumped on corrections: the incremental watermark
    CONSTRAINT pk_prescription_item PRIMARY KEY (item_line_id),
    CONSTRAINT fk_item_prescription FOREIGN KEY (prescription_id) REFERENCES rx.prescription (prescription_id),
    CONSTRAINT fk_item_medicine FOREIGN KEY (presentation_code) REFERENCES rx.medicine (presentation_code),
    CONSTRAINT ck_item_items CHECK (items > 0)
);
GO
