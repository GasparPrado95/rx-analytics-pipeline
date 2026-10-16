"""Reference data: NHS geography and a curated BNF-style medicine catalogue.

Region and ICB names/codes follow the public NHS England structure (2022+).
BNF chapter/section/paragraph names follow the legacy BNF layout used by the
English Prescribing Dataset. Chemical and presentation codes are generated in
the EPD *format* (9 and 15 characters) but are synthetic and do not match real
codes. Costs are illustrative, not Drug Tariff prices.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# Geography
# --------------------------------------------------------------------------

# region_code, ons_code, name, prescribing rate factor, antibacterial factor,
# share of rural practices, mean practice IMD decile, ODS letters for practice codes
REGIONS = [
    ("Y56", "E40000003", "London", 0.84, 0.88, 0.00, 4.6, "EFH"),
    ("Y59", "E40000005", "South East", 0.95, 0.95, 0.25, 7.0, "GHJK"),
    ("Y58", "E40000006", "South West", 1.02, 0.97, 0.38, 6.4, "LJ"),
    ("Y61", "E40000007", "East of England", 0.99, 1.00, 0.32, 6.4, "DE"),
    ("Y60", "E40000008", "Midlands", 1.06, 1.06, 0.22, 5.0, "MCY"),
    ("Y63", "E40000009", "North East and Yorkshire", 1.16, 1.14, 0.20, 4.3, "ABC"),
    ("Y62", "E40000010", "North West", 1.13, 1.12, 0.15, 4.2, "NP"),
]

# icb_code, name, region_code, population (millions, approximate), postcode areas
ICBS = [
    ("QHM", "NHS North East and North Cumbria ICB", "Y63", 3.0, ["NE", "SR", "DH", "TS", "DL", "CA"]),
    ("QOQ", "NHS Humber and North Yorkshire ICB", "Y63", 1.7, ["HU", "YO", "DN", "HG"]),
    ("QF7", "NHS South Yorkshire ICB", "Y63", 1.4, ["S", "DN"]),
    ("QWO", "NHS West Yorkshire ICB", "Y63", 2.4, ["LS", "BD", "WF", "HD", "HX"]),
    ("QE1", "NHS Lancashire and South Cumbria ICB", "Y62", 1.8, ["PR", "BB", "FY", "LA"]),
    ("QOP", "NHS Greater Manchester ICB", "Y62", 3.0, ["M", "BL", "OL", "SK", "WN"]),
    ("QYG", "NHS Cheshire and Merseyside ICB", "Y62", 2.7, ["L", "CH", "CW", "WA"]),
    ("QJ2", "NHS Derby and Derbyshire ICB", "Y60", 1.1, ["DE", "S"]),
    ("QK1", "NHS Leicester, Leicestershire and Rutland ICB", "Y60", 1.2, ["LE"]),
    ("QJM", "NHS Lincolnshire ICB", "Y60", 0.8, ["LN", "PE", "NG"]),
    ("QPM", "NHS Northamptonshire ICB", "Y60", 0.8, ["NN"]),
    ("QT1", "NHS Nottingham and Nottinghamshire ICB", "Y60", 1.1, ["NG"]),
    ("QOC", "NHS Shropshire, Telford and Wrekin ICB", "Y60", 0.5, ["SY", "TF"]),
    ("QNC", "NHS Staffordshire and Stoke-on-Trent ICB", "Y60", 1.2, ["ST", "WS", "DE"]),
    ("QHL", "NHS Birmingham and Solihull ICB", "Y60", 1.3, ["B"]),
    ("QUA", "NHS Black Country ICB", "Y60", 1.3, ["WV", "DY", "WS", "B"]),
    ("QWU", "NHS Coventry and Warwickshire ICB", "Y60", 1.0, ["CV", "B"]),
    ("QGH", "NHS Herefordshire and Worcestershire ICB", "Y60", 0.8, ["HR", "WR", "DY"]),
    ("QHG", "NHS Bedfordshire, Luton and Milton Keynes ICB", "Y61", 1.0, ["MK", "LU", "SG"]),
    ("QUE", "NHS Cambridgeshire and Peterborough ICB", "Y61", 0.95, ["CB", "PE"]),
    ("QM7", "NHS Hertfordshire and West Essex ICB", "Y61", 1.6, ["AL", "SG", "WD", "CM", "EN"]),
    ("QH8", "NHS Mid and South Essex ICB", "Y61", 1.2, ["CM", "SS", "RM"]),
    ("QMM", "NHS Norfolk and Waveney ICB", "Y61", 1.1, ["NR"]),
    ("QJG", "NHS Suffolk and North East Essex ICB", "Y61", 1.0, ["IP", "CO"]),
    ("QMF", "NHS North East London ICB", "Y56", 2.1, ["E", "IG", "RM"]),
    ("QMJ", "NHS North Central London ICB", "Y56", 1.6, ["N", "NW", "EN"]),
    ("QRV", "NHS North West London ICB", "Y56", 2.7, ["W", "NW", "HA", "UB", "TW"]),
    ("QKK", "NHS South East London ICB", "Y56", 2.0, ["SE", "BR", "DA"]),
    ("QWE", "NHS South West London ICB", "Y56", 1.6, ["SW", "KT", "SM", "CR"]),
    ("QU9", "NHS Buckinghamshire, Oxfordshire and Berkshire West ICB", "Y59", 1.9, ["OX", "HP", "RG", "MK"]),
    ("QXU", "NHS Surrey Heartlands ICB", "Y59", 1.1, ["GU", "KT", "RH"]),
    ("QNX", "NHS Sussex ICB", "Y59", 1.8, ["BN", "RH", "TN", "PO"]),
    ("QKS", "NHS Kent and Medway ICB", "Y59", 1.9, ["ME", "CT", "TN", "DA"]),
    ("QRL", "NHS Hampshire and Isle of Wight ICB", "Y59", 1.9, ["SO", "PO", "GU"]),
    ("QNQ", "NHS Frimley ICB", "Y59", 0.8, ["GU", "SL"]),
    ("QOX", "NHS Bath and North East Somerset, Swindon and Wiltshire ICB", "Y58", 0.95, ["BA", "SN", "SP"]),
    ("QUY", "NHS Bristol, North Somerset and South Gloucestershire ICB", "Y58", 1.0, ["BS"]),
    ("QT6", "NHS Cornwall and the Isles of Scilly ICB", "Y58", 0.6, ["TR", "PL"]),
    ("QJK", "NHS Devon ICB", "Y58", 1.25, ["EX", "PL", "TQ"]),
    ("QVV", "NHS Dorset ICB", "Y58", 0.8, ["BH", "DT"]),
    ("QR1", "NHS Gloucestershire ICB", "Y58", 0.67, ["GL"]),
    ("QSL", "NHS Somerset ICB", "Y58", 0.6, ["TA", "BA"]),
]

# --------------------------------------------------------------------------
# BNF hierarchy (legacy BNF chapters 1-13)
# --------------------------------------------------------------------------

BNF_CHAPTERS = {
    "01": "Gastro-Intestinal System",
    "02": "Cardiovascular System",
    "03": "Respiratory System",
    "04": "Central Nervous System",
    "05": "Infections",
    "06": "Endocrine System",
    "07": "Obstetrics, Gynaecology and Urinary-Tract Disorders",
    "08": "Malignant Disease and Immunosuppression",
    "09": "Nutrition and Blood",
    "10": "Musculoskeletal and Joint Diseases",
    "11": "Eye",
    "12": "Ear, Nose and Oropharynx",
    "13": "Skin",
}

BNF_SECTIONS = {
    "0101": "Dyspepsia and gastro-oesophageal reflux disease",
    "0102": "Antispasmodics and other drugs altering gut motility",
    "0103": "Antisecretory drugs and mucosal protectants",
    "0104": "Acute diarrhoea",
    "0106": "Laxatives",
    "0202": "Diuretics",
    "0204": "Beta-adrenoceptor blocking drugs",
    "0205": "Hypertension and heart failure",
    "0206": "Nitrates, calcium-channel blockers and other antianginal drugs",
    "0208": "Anticoagulants and protamine",
    "0209": "Antiplatelet drugs",
    "0212": "Lipid-regulating drugs",
    "0301": "Bronchodilators",
    "0302": "Corticosteroids (respiratory)",
    "0303": "Cromoglicate, leukotriene and phosphodiesterase type-4 inhibitors",
    "0304": "Antihistamines, hyposensitisation and allergic emergencies",
    "0307": "Mucolytics",
    "0401": "Hypnotics and anxiolytics",
    "0402": "Drugs used in psychoses and related disorders",
    "0403": "Antidepressant drugs",
    "0404": "CNS stimulants and drugs used for ADHD",
    "0406": "Drugs used in nausea and vertigo",
    "0407": "Analgesics",
    "0408": "Antiepileptic drugs",
    "0409": "Drugs used in parkinsonism and related disorders",
    "0410": "Drugs used in substance dependence",
    "0411": "Drugs for dementia",
    "0501": "Antibacterial drugs",
    "0502": "Antifungal drugs",
    "0503": "Antiviral drugs",
    "0601": "Drugs used in diabetes",
    "0602": "Thyroid and antithyroid drugs",
    "0603": "Corticosteroids and other hormones",
    "0604": "Sex hormones",
    "0606": "Drugs affecting bone metabolism",
    "0703": "Contraceptives",
    "0704": "Drugs for genito-urinary disorders",
    "0801": "Cytotoxic drugs",
    "0802": "Drugs affecting the immune response",
    "0803": "Sex hormones and hormone antagonists in malignant disease",
    "0901": "Anaemias and some other blood disorders",
    "0905": "Minerals",
    "0906": "Vitamins",
    "1001": "Drugs used in rheumatic diseases and gout",
    "1002": "Drugs used in neuromuscular disorders",
    "1103": "Anti-infective eye preparations",
    "1106": "Treatment of glaucoma",
    "1108": "Preparations for tear deficiency and ocular lubricants",
    "1202": "Drugs acting on the nose",
    "1203": "Drugs acting on the oropharynx",
    "1302": "Emollient and barrier preparations",
    "1304": "Topical corticosteroids",
    "1310": "Anti-infective skin preparations",
}

BNF_PARAGRAPHS = {
    "010102": "Compound alginates and proprietary indigestion preparations",
    "010200": "Antispasmodics and other drugs altering gut motility",
    "010305": "Proton pump inhibitors",
    "010402": "Antimotility drugs",
    "010602": "Stimulant laxatives",
    "010604": "Osmotic laxatives",
    "020201": "Thiazides and related diuretics",
    "020202": "Loop diuretics",
    "020203": "Potassium-sparing diuretics and aldosterone antagonists",
    "020400": "Beta-adrenoceptor blocking drugs",
    "020505": "Drugs affecting the renin-angiotensin system",
    "020601": "Nitrates",
    "020602": "Calcium-channel blockers",
    "020802": "Oral anticoagulants",
    "020900": "Antiplatelet drugs",
    "021200": "Lipid-regulating drugs",
    "030101": "Selective beta2 agonists",
    "030102": "Antimuscarinic bronchodilators",
    "030200": "Corticosteroids (respiratory)",
    "030302": "Leukotriene receptor antagonists",
    "030401": "Antihistamines",
    "030403": "Allergic emergencies",
    "030700": "Mucolytics",
    "040101": "Hypnotics",
    "040102": "Anxiolytics",
    "040201": "Antipsychotic drugs",
    "040301": "Tricyclic and related antidepressant drugs",
    "040303": "Selective serotonin re-uptake inhibitors",
    "040304": "Other antidepressant drugs",
    "040400": "CNS stimulants and drugs used for ADHD",
    "040600": "Drugs used in nausea and vertigo",
    "040701": "Non-opioid analgesics and compound preparations",
    "040702": "Opioid analgesics",
    "040703": "Antimigraine drugs",
    "040801": "Control of epilepsy",
    "040901": "Dopaminergic drugs used in parkinsonism",
    "041002": "Nicotine dependence",
    "041100": "Drugs for dementia",
    "050101": "Penicillins",
    "050102": "Cephalosporins and other beta-lactams",
    "050103": "Tetracyclines",
    "050105": "Macrolides",
    "050108": "Sulfonamides and trimethoprim",
    "050113": "Urinary-tract infections",
    "050200": "Antifungal drugs",
    "050302": "Herpesvirus infections",
    "050304": "Influenza",
    "060101": "Insulins",
    "060102": "Antidiabetic drugs",
    "060201": "Thyroid hormones",
    "060202": "Antithyroid drugs",
    "060302": "Glucocorticoid therapy",
    "060401": "Female sex hormones and their modulators",
    "060602": "Bisphosphonates and other drugs affecting bone metabolism",
    "070301": "Combined hormonal contraceptives and systems",
    "070302": "Progestogen-only contraceptives",
    "070401": "Drugs for urinary retention",
    "070402": "Drugs for urinary frequency, enuresis and incontinence",
    "070405": "Drugs for erectile dysfunction",
    "080103": "Antimetabolites",
    "080202": "Other immunomodulating drugs",
    "080304": "Hormone antagonists",
    "090101": "Iron-deficiency anaemias",
    "090102": "Drugs used in megaloblastic anaemias",
    "090501": "Calcium and magnesium",
    "090604": "Vitamin D",
    "100101": "Non-steroidal anti-inflammatory drugs",
    "100104": "Drugs used to treat gout",
    "100202": "Skeletal muscle relaxants",
    "110301": "Antibacterials (eye)",
    "110600": "Treatment of glaucoma",
    "110801": "Tear deficiency, ocular lubricants and astringents",
    "120201": "Drugs used in nasal allergy",
    "120302": "Oropharyngeal anti-infective drugs",
    "130201": "Emollient and barrier preparations",
    "130400": "Topical corticosteroids",
    "131001": "Antibacterial preparations (skin)",
    "131002": "Antifungal preparations (skin)",
}

# --------------------------------------------------------------------------
# Medicine catalogue
# --------------------------------------------------------------------------

# form -> unit of measure used for quantity and unit cost
FORM_UNITS = {
    "tablet": "tablet",
    "dispersible tablet": "tablet",
    "gastro-resistant tablet": "tablet",
    "modified-release tablet": "tablet",
    "chewable tablet": "tablet",
    "capsule": "capsule",
    "gastro-resistant capsule": "capsule",
    "modified-release capsule": "capsule",
    "oral solution": "ml",
    "oral suspension": "ml",
    "oral powder sachet": "sachet",
    "pressurised inhaler": "inhaler",
    "dry powder inhaler": "inhaler",
    "auto-injector": "device",
    "pre-filled pen": "pen",
    "transdermal patch": "patch",
    "sublingual spray": "device",
    "nasal spray": "device",
    "eye drops": "ml",
    "eye gel": "gram",
    "eye ointment": "gram",
    "cream": "gram",
    "gel": "gram",
}


@dataclass(frozen=True)
class Form:
    form: str
    strengths: tuple[str, ...]
    pack: int  # typical quantity per item, in the form's unit
    costs: tuple[float, ...]  # generic (or reference) cost per unit, one per strength


@dataclass(frozen=True)
class Chemical:
    name: str
    paragraph: str
    popularity: float  # relative share of prescription lines
    forms: tuple[Form, ...]
    brands: tuple[str, ...] = ()
    brand_premium: float = 6.0  # brand unit cost / generic unit cost
    brand_share: float = 0.10  # share of lines on brands at the start of the period
    brand_share_end: float | None = None  # defaults to a 45% relative decline
    generic: bool = True  # False: brand-only (patent protected / biosimilar brands)
    season: str = "flat"
    trend: float = 0.0  # annual growth in volume
    profile: str = "all"  # patient age/sex profile, see config.AGE_PROFILES


def F(form: str, strengths: str, pack: int, *costs: float) -> Form:
    """Compact Form constructor: strengths are '|'-separated; one cost applies to all."""
    s = tuple(strengths.split("|"))
    c = costs if len(costs) == len(s) else tuple([costs[0]] * len(s))
    return Form(form, s, pack, c)


C = Chemical

CATALOGUE: tuple[Chemical, ...] = (
    # ---------------- 01 Gastro-intestinal ----------------
    C("Sodium alginate with potassium bicarbonate", "010102", 6, (F("oral suspension", "500mg/100mg per 5ml", 500, 0.0105),), ("Gaviscon Advance",), 1.0, 0.6, profile="older"),
    C("Mebeverine hydrochloride", "010200", 6, (F("tablet", "135mg", 100, 0.045),), ("Colofac",), 4.0, 0.08),
    C("Hyoscine butylbromide", "010200", 3, (F("tablet", "10mg", 56, 0.08),), ("Buscopan",), 2.5, 0.25),
    C("Omeprazole", "010305", 85, (F("gastro-resistant capsule", "10mg|20mg|40mg", 28, 0.035, 0.04, 0.06),), ("Losec",), 12.0, 0.02, profile="older"),
    C("Lansoprazole", "010305", 50, (F("capsule", "15mg|30mg", 28, 0.035, 0.04),), ("Zoton FasTab",), 9.0, 0.03, profile="older"),
    C("Esomeprazole", "010305", 9, (F("gastro-resistant tablet", "20mg|40mg", 28, 0.07, 0.09),), ("Nexium",), 8.0, 0.08),
    C("Pantoprazole", "010305", 7, (F("gastro-resistant tablet", "20mg|40mg", 28, 0.04, 0.05),), ("Protium",), 7.0, 0.03),
    C("Loperamide hydrochloride", "010402", 4, (F("capsule", "2mg", 30, 0.035),), ("Imodium",), 3.0, 0.05),
    C("Senna", "010602", 10, (F("tablet", "7.5mg", 60, 0.025),), ("Senokot",), 3.0, 0.06, profile="older"),
    C("Bisacodyl", "010602", 3, (F("gastro-resistant tablet", "5mg", 60, 0.035),), ("Dulcolax",), 3.0, 0.08, profile="older"),
    C("Macrogol compound", "010604", 18, (F("oral powder sachet", "13.8g", 30, 0.16),), ("Laxido Orange", "Movicol"), 1.6, 0.55, profile="older"),
    C("Lactulose", "010604", 7, (F("oral solution", "3.35g/5ml", 500, 0.0065),), ("Duphalac",), 2.0, 0.06, profile="older"),
    # ---------------- 02 Cardiovascular ----------------
    C("Bendroflumethiazide", "020201", 10, (F("tablet", "2.5mg", 28, 0.03),), trend=-0.06, profile="older"),
    C("Indapamide", "020201", 9, (F("tablet", "2.5mg", 28, 0.04), F("modified-release tablet", "1.5mg", 28, 0.06)), ("Natrilix SR",), 3.0, 0.10, profile="older"),
    C("Furosemide", "020202", 25, (F("tablet", "20mg|40mg", 28, 0.022, 0.024),), profile="older"),
    C("Spironolactone", "020203", 9, (F("tablet", "25mg|50mg", 28, 0.045, 0.06),), ("Aldactone",), 4.0, 0.04, profile="older"),
    C("Bisoprolol fumarate", "020400", 45, (F("tablet", "1.25mg|2.5mg|5mg|10mg", 28, 0.03, 0.03, 0.035, 0.04),), ("Cardicor",), 4.0, 0.02, profile="older"),
    C("Atenolol", "020400", 14, (F("tablet", "25mg|50mg|100mg", 28, 0.025, 0.025, 0.03),), ("Tenormin",), 6.0, 0.02, trend=-0.08, profile="older"),
    C("Propranolol hydrochloride", "020400", 12, (F("tablet", "10mg|40mg", 28, 0.035, 0.045),), ("Inderal",), 5.0, 0.03),
    C("Ramipril", "020505", 45, (F("capsule", "1.25mg|2.5mg|5mg|10mg", 28, 0.03, 0.032, 0.04, 0.05),), ("Tritace",), 6.0, 0.03, profile="older"),
    C("Lisinopril", "020505", 14, (F("tablet", "5mg|10mg|20mg", 28, 0.025, 0.025, 0.03),), ("Zestril",), 6.0, 0.02, profile="older"),
    C("Losartan potassium", "020505", 25, (F("tablet", "25mg|50mg|100mg", 28, 0.035, 0.035, 0.05),), ("Cozaar",), 7.0, 0.03, trend=0.04, profile="older"),
    C("Candesartan cilexetil", "020505", 12, (F("tablet", "4mg|8mg|16mg", 28, 0.045, 0.055, 0.07),), ("Amias",), 6.0, 0.03, profile="older"),
    C("Sacubitril with valsartan", "020505", 3, (F("tablet", "24mg/26mg|49mg/51mg|97mg/103mg", 56, 1.63),), ("Entresto",), 1.0, 1.0, generic=False, trend=0.25, profile="older"),
    C("Glyceryl trinitrate", "020601", 6, (F("sublingual spray", "400micrograms/dose", 1, 3.50),), ("GTN Pump Spray",), 1.4, 0.35, profile="older"),
    C("Isosorbide mononitrate", "020601", 6, (F("modified-release tablet", "60mg", 28, 0.12),), ("Monomax XL",), 2.0, 0.30, trend=-0.05, profile="older"),
    C("Amlodipine", "020602", 75, (F("tablet", "5mg|10mg", 28, 0.022, 0.028),), ("Istin",), 12.0, 0.01, profile="older"),
    C("Felodipine", "020602", 6, (F("modified-release tablet", "5mg|10mg", 28, 0.08, 0.11),), ("Plendil",), 2.0, 0.25, profile="older"),
    C("Diltiazem hydrochloride", "020602", 4, (F("modified-release capsule", "120mg|180mg", 28, 0.26, 0.31),), ("Adizem-XL", "Tildiem LA"), 1.3, 0.70, profile="older"),
    C("Warfarin sodium", "020802", 9, (F("tablet", "1mg|3mg|5mg", 28, 0.03, 0.03, 0.035),), trend=-0.14, profile="older"),
    C("Apixaban", "020802", 35, (F("tablet", "2.5mg|5mg", 56, 0.95),), ("Eliquis",), 1.0, 1.0, generic=False, trend=0.16, profile="older"),
    C("Rivaroxaban", "020802", 12, (F("tablet", "10mg|15mg|20mg", 28, 1.80),), ("Xarelto",), 1.0, 1.0, generic=False, trend=0.04, profile="older"),
    C("Edoxaban", "020802", 8, (F("tablet", "30mg|60mg", 28, 1.75),), ("Lixiana",), 1.0, 1.0, generic=False, trend=0.35, profile="older"),
    C("Aspirin", "020900", 35, (F("dispersible tablet", "75mg", 28, 0.03),), ("Nu-Seals",), 5.0, 0.03, trend=-0.06, profile="older"),
    C("Clopidogrel", "020900", 18, (F("tablet", "75mg", 28, 0.045),), ("Plavix",), 15.0, 0.01, profile="older"),
    C("Ticagrelor", "020900", 3, (F("tablet", "60mg|90mg", 56, 1.04),), ("Brilique",), 1.0, 1.0, generic=False, profile="older"),
    C("Atorvastatin", "021200", 100, (F("tablet", "10mg|20mg|40mg|80mg", 28, 0.03, 0.032, 0.04, 0.06),), ("Lipitor",), 12.0, 0.01, trend=0.05, profile="older"),
    C("Simvastatin", "021200", 25, (F("tablet", "10mg|20mg|40mg", 28, 0.022, 0.025, 0.03),), ("Zocor",), 10.0, 0.01, trend=-0.08, profile="older"),
    C("Rosuvastatin calcium", "021200", 12, (F("tablet", "5mg|10mg|20mg", 28, 0.045, 0.05, 0.065),), ("Crestor",), 12.0, 0.04, trend=0.12, profile="older"),
    C("Ezetimibe", "021200", 9, (F("tablet", "10mg", 28, 0.075),), ("Ezetrol",), 12.0, 0.03, trend=0.06, profile="older"),
    # ---------------- 03 Respiratory ----------------
    C("Salbutamol", "030101", 55, (F("pressurised inhaler", "100micrograms/dose", 1, 1.50), F("dry powder inhaler", "100micrograms/dose", 1, 3.31)), ("Ventolin Evohaler", "Salamol"), 1.0, 0.55, season="mild_winter", trend=-0.03),
    C("Tiotropium", "030102", 7, (F("dry powder inhaler", "18micrograms", 1, 33.50), F("pressurised inhaler", "2.5micrograms/dose", 1, 23.00)), ("Spiriva", "Braltus"), 1.0, 1.0, generic=False, season="mild_winter", profile="older"),
    C("Beclometasone dipropionate", "030200", 20, (F("pressurised inhaler", "100micrograms/dose|200micrograms/dose", 1, 7.42, 16.17),), ("Clenil Modulite",), 1.0, 0.70, season="mild_winter"),
    C("Budesonide with formoterol", "030200", 14, (F("dry powder inhaler", "200micrograms/6micrograms|400micrograms/12micrograms", 1, 28.00),), ("Symbicort Turbohaler", "DuoResp Spiromax"), 1.0, 1.0, generic=False, season="mild_winter", trend=0.08),
    C("Fluticasone propionate with salmeterol", "030200", 8, (F("pressurised inhaler", "125micrograms/25micrograms|250micrograms/25micrograms", 1, 29.32),), ("Seretide", "Sirdupla"), 1.0, 1.0, generic=False, season="mild_winter", trend=-0.05),
    C("Montelukast", "030302", 14, (F("tablet", "10mg", 28, 0.06), F("chewable tablet", "4mg|5mg", 28, 0.10)), ("Singulair",), 15.0, 0.02, season="mild_winter"),
    C("Cetirizine hydrochloride", "030401", 16, (F("tablet", "10mg", 30, 0.025),), ("Zirtek",), 6.0, 0.03, season="summer"),
    C("Loratadine", "030401", 9, (F("tablet", "10mg", 30, 0.025),), ("Clarityn",), 7.0, 0.03, season="summer"),
    C("Fexofenadine hydrochloride", "030401", 12, (F("tablet", "120mg|180mg", 30, 0.09, 0.11),), ("Telfast",), 5.0, 0.04, season="summer", trend=0.06),
    C("Chlorphenamine maleate", "030401", 4, (F("tablet", "4mg", 28, 0.05),), ("Piriton",), 2.0, 0.10, season="summer"),
    C("Adrenaline", "030403", 3, (F("auto-injector", "300micrograms|150micrograms", 1, 26.45),), ("EpiPen", "Jext"), 1.0, 1.0, generic=False, profile="young"),
    C("Carbocisteine", "030700", 8, (F("capsule", "375mg", 120, 0.045),), season="winter", profile="older"),
    # ---------------- 04 Central nervous system ----------------
    C("Zopiclone", "040101", 10, (F("tablet", "3.75mg|7.5mg", 28, 0.035, 0.04),), profile="older"),
    C("Melatonin", "040101", 6, (F("modified-release tablet", "2mg", 30, 0.52),), ("Circadin", "Slenyto"), 1.0, 0.55, trend=0.10, profile="young"),
    C("Diazepam", "040102", 10, (F("tablet", "2mg|5mg|10mg", 28, 0.025, 0.025, 0.03),)),
    C("Quetiapine", "040201", 10, (F("tablet", "25mg|100mg|200mg", 60, 0.035, 0.05, 0.08),), ("Seroquel",), 15.0, 0.02),
    C("Olanzapine", "040201", 8, (F("tablet", "5mg|10mg", 28, 0.035, 0.045),), ("Zyprexa",), 20.0, 0.01),
    C("Risperidone", "040201", 5, (F("tablet", "1mg|2mg", 60, 0.03, 0.04),), ("Risperdal",), 15.0, 0.01),
    C("Amitriptyline hydrochloride", "040301", 35, (F("tablet", "10mg|25mg|50mg", 28, 0.045, 0.045, 0.07),)),
    C("Sertraline hydrochloride", "040303", 50, (F("tablet", "50mg|100mg", 28, 0.03, 0.04),), ("Lustral",), 15.0, 0.01, trend=0.06),
    C("Citalopram", "040303", 30, (F("tablet", "10mg|20mg|40mg", 28, 0.025, 0.03, 0.04),), ("Cipramil",), 12.0, 0.01, trend=-0.03),
    C("Fluoxetine", "040303", 25, (F("capsule", "20mg", 30, 0.035), F("oral solution", "20mg/5ml", 70, 0.15)), ("Prozac",), 10.0, 0.02),
    C("Mirtazapine", "040304", 25, (F("tablet", "15mg|30mg|45mg", 28, 0.05, 0.06, 0.08),), ("Zispin SolTab",), 8.0, 0.02),
    C("Venlafaxine", "040304", 12, (F("modified-release capsule", "75mg|150mg", 28, 0.13, 0.18),), ("Efexor XL", "Vensir XL"), 3.0, 0.20),
    C("Duloxetine", "040304", 8, (F("gastro-resistant capsule", "30mg|60mg", 28, 0.055, 0.065),), ("Cymbalta",), 15.0, 0.02, trend=0.05),
    C("Methylphenidate hydrochloride", "040400", 6, (F("modified-release tablet", "18mg|36mg", 30, 1.05, 1.20),), ("Concerta XL", "Xaggitin XL", "Delmosart"), 1.0, 1.0, generic=False, trend=0.22, profile="young"),
    C("Lisdexamfetamine dimesylate", "040400", 3, (F("capsule", "30mg|50mg|70mg", 28, 2.10),), ("Elvanse",), 1.0, 1.0, generic=False, trend=0.28, profile="young"),
    C("Prochlorperazine maleate", "040600", 5, (F("tablet", "5mg", 28, 0.045),), ("Stemetil",), 3.0, 0.05),
    C("Cyclizine hydrochloride", "040600", 3, (F("tablet", "50mg", 100, 0.06),), ("Valoid",), 2.0, 0.05),
    C("Ondansetron", "040600", 3, (F("tablet", "4mg|8mg", 10, 0.10, 0.12),), ("Zofran",), 25.0, 0.01),
    C("Paracetamol", "040701", 40, (F("tablet", "500mg", 100, 0.016), F("oral suspension", "120mg/5ml", 100, 0.009)), ("Panadol",), 2.0, 0.02),
    C("Co-codamol", "040701", 30, (F("tablet", "8mg/500mg|30mg/500mg", 100, 0.025, 0.042),), ("Zapain", "Solpadol"), 2.2, 0.08, profile="older"),
    C("Codeine phosphate", "040702", 12, (F("tablet", "15mg|30mg", 28, 0.05, 0.06),), profile="older"),
    C("Tramadol hydrochloride", "040702", 10, (F("capsule", "50mg", 100, 0.032),), ("Zydol",), 4.0, 0.03, trend=-0.05, profile="older"),
    C("Morphine sulfate", "040702", 6, (F("oral solution", "10mg/5ml", 100, 0.019),), ("Oramorph",), 1.0, 0.85, profile="older"),
    C("Buprenorphine", "040702", 6, (F("transdermal patch", "5micrograms/hour|10micrograms/hour", 4, 4.35, 7.80),), ("Butec", "BuTrans", "Reletrans"), 1.0, 1.0, generic=False, profile="older"),
    C("Oxycodone hydrochloride", "040702", 4, (F("modified-release tablet", "10mg|20mg", 56, 0.40, 0.80),), ("OxyContin", "Longtec"), 1.3, 0.55, profile="older"),
    C("Sumatriptan", "040703", 5, (F("tablet", "50mg|100mg", 6, 0.27, 0.32),), ("Imigran",), 20.0, 0.01, profile="female_repro"),
    C("Gabapentin", "040801", 18, (F("capsule", "100mg|300mg|400mg", 100, 0.032, 0.05, 0.065),), ("Neurontin",), 12.0, 0.01, trend=-0.04),
    C("Pregabalin", "040801", 22, (F("capsule", "25mg|75mg|150mg", 56, 0.05, 0.06, 0.08),), ("Lyrica",), 15.0, 0.02),
    C("Levetiracetam", "040801", 6, (F("tablet", "250mg|500mg|1g", 60, 0.07, 0.09, 0.16),), ("Keppra",), 10.0, 0.04),
    C("Lamotrigine", "040801", 7, (F("tablet", "25mg|50mg|100mg", 56, 0.04, 0.05, 0.06),), ("Lamictal",), 10.0, 0.04),
    C("Sodium valproate", "040801", 4, (F("gastro-resistant tablet", "200mg|500mg", 100, 0.06, 0.11),), ("Epilim",), 1.0, 0.75, trend=-0.06),
    C("Carbamazepine", "040801", 3, (F("tablet", "200mg", 84, 0.08),), ("Tegretol",), 1.2, 0.60),
    C("Co-careldopa", "040901", 4, (F("tablet", "25mg/100mg", 100, 0.26),), ("Sinemet",), 2.5, 0.10, profile="older"),
    C("Nicotine", "041002", 4, (F("transdermal patch", "21mg/24hours|14mg/24hours", 7, 1.32),), ("NiQuitin", "Nicorette Invisi"), 1.0, 1.0, generic=False, season="new_year", trend=-0.04),
    C("Donepezil hydrochloride", "041100", 6, (F("tablet", "5mg|10mg", 28, 0.035, 0.045),), ("Aricept",), 25.0, 0.01, profile="older"),
    C("Memantine hydrochloride", "041100", 4, (F("tablet", "10mg|20mg", 28, 0.055, 0.08),), ("Ebixa",), 15.0, 0.01, profile="older"),
    # ---------------- 05 Infections ----------------
    C("Amoxicillin", "050101", 40, (F("capsule", "250mg|500mg", 21, 0.04, 0.05), F("oral suspension", "125mg/5ml|250mg/5ml", 100, 0.012, 0.016)), ("Amoxil",), 5.0, 0.01, season="winter", profile="acute"),
    C("Phenoxymethylpenicillin", "050101", 12, (F("tablet", "250mg", 28, 0.055), F("oral solution", "250mg/5ml", 100, 0.045)), season="winter", profile="acute"),
    C("Flucloxacillin", "050101", 10, (F("capsule", "250mg|500mg", 28, 0.065, 0.085),), ("Floxapen",), 4.0, 0.02, season="winter", profile="acute"),
    C("Co-amoxiclav", "050101", 8, (F("tablet", "250mg/125mg|500mg/125mg", 21, 0.13, 0.17),), ("Augmentin",), 3.0, 0.03, season="winter", profile="acute"),
    C("Cefalexin", "050102", 6, (F("capsule", "250mg|500mg", 28, 0.06, 0.09),), ("Keflex",), 3.0, 0.03, season="winter", profile="acute"),
    C("Doxycycline", "050103", 18, (F("capsule", "100mg", 8, 0.11),), ("Vibramycin-D",), 6.0, 0.02, season="winter", profile="acute"),
    C("Lymecycline", "050103", 5, (F("capsule", "408mg", 28, 0.13),), ("Tetralysal",), 3.0, 0.08, profile="young"),
    C("Clarithromycin", "050105", 12, (F("tablet", "250mg|500mg", 14, 0.13, 0.20),), ("Klaricid",), 6.0, 0.02, season="winter", profile="acute"),
    C("Azithromycin", "050105", 4, (F("tablet", "250mg|500mg", 6, 0.30, 0.38),), ("Zithromax",), 6.0, 0.02, season="winter", profile="acute"),
    C("Erythromycin", "050105", 2, (F("gastro-resistant tablet", "250mg", 28, 0.11),), ("Erythrocin",), 3.0, 0.05, season="winter", profile="acute"),
    C("Trimethoprim", "050108", 10, (F("tablet", "100mg|200mg", 14, 0.035, 0.045),), profile="female_older"),
    C("Nitrofurantoin", "050113", 14, (F("modified-release capsule", "100mg", 14, 0.56),), ("Macrobid",), 1.2, 0.20, trend=0.04, profile="female_older"),
    C("Fluconazole", "050200", 6, (F("capsule", "50mg|150mg", 7, 0.10, 0.45),), ("Diflucan",), 8.0, 0.02, profile="female_repro"),
    C("Aciclovir", "050302", 5, (F("tablet", "200mg|400mg|800mg", 25, 0.05, 0.08, 0.15),), ("Zovirax",), 10.0, 0.01),
    C("Oseltamivir", "050304", 2, (F("capsule", "30mg|75mg", 10, 1.54),), ("Tamiflu",), 1.0, 0.75, season="flu", profile="older"),
    # ---------------- 06 Endocrine ----------------
    C("Insulin glargine", "060101", 6, (F("pre-filled pen", "100units/ml 3ml", 5, 6.94),), ("Lantus SoloStar", "Abasaglar KwikPen", "Semglee"), 1.0, 1.0, generic=False, profile="older"),
    C("Insulin aspart", "060101", 4, (F("pre-filled pen", "100units/ml 3ml", 5, 6.10),), ("NovoRapid FlexPen", "Trurapi"), 1.0, 1.0, generic=False),
    C("Metformin hydrochloride", "060102", 60, (F("tablet", "500mg|850mg|1g", 56, 0.022, 0.03, 0.05), F("modified-release tablet", "500mg", 56, 0.07)), ("Glucophage",), 4.0, 0.03, trend=0.04, profile="older"),
    C("Gliclazide", "060102", 18, (F("tablet", "40mg|80mg", 28, 0.03, 0.035),), ("Diamicron",), 5.0, 0.02, trend=-0.03, profile="older"),
    C("Sitagliptin", "060102", 9, (F("tablet", "50mg|100mg", 28, 0.30),), ("Januvia",), 5.5, 0.85, brand_share_end=0.15, trend=0.04, profile="older"),
    C("Dapagliflozin", "060102", 12, (F("tablet", "5mg|10mg", 28, 1.31),), ("Forxiga",), 1.0, 1.0, generic=False, trend=0.25, profile="older"),
    C("Empagliflozin", "060102", 12, (F("tablet", "10mg|25mg", 28, 1.31),), ("Jardiance",), 1.0, 1.0, generic=False, trend=0.30, profile="older"),
    C("Levothyroxine sodium", "060201", 70, (F("tablet", "25micrograms|50micrograms|100micrograms", 28, 0.032, 0.034, 0.036),), ("Eltroxin",), 1.8, 0.04, profile="female_older"),
    C("Carbimazole", "060202", 2, (F("tablet", "5mg|20mg", 100, 0.06, 0.16),), profile="female_older"),
    C("Prednisolone", "060302", 12, (F("tablet", "1mg|5mg", 28, 0.03, 0.035),), season="mild_winter", profile="older"),
    C("Hydrocortisone", "060302", 2, (F("tablet", "10mg", 30, 0.30),), ("Hydrocortone",), 1.5, 0.10),
    C("Estradiol", "060401", 10, (F("tablet", "1mg|2mg", 84, 0.055, 0.06), F("gel", "0.06% (750micrograms/actuation)", 80, 0.26)), ("Oestrogel Pump-Pack", "Elleste Solo"), 1.2, 0.45, trend=0.20, profile="female_midlife"),
    C("Alendronic acid", "060602", 10, (F("tablet", "70mg", 4, 0.31),), ("Fosamax Once Weekly",), 20.0, 0.01, profile="female_older"),
    # ---------------- 07 Obstetrics, gynaecology, urinary ----------------
    C("Levonorgestrel with ethinylestradiol", "070301", 7, (F("tablet", "150micrograms/30micrograms", 63, 0.045),), ("Microgynon 30", "Rigevidon", "Levest"), 1.2, 0.85, profile="female_repro"),
    C("Desogestrel", "070302", 9, (F("tablet", "75micrograms", 84, 0.025),), ("Cerelle", "Cerazette"), 1.8, 0.25, trend=0.03, profile="female_repro"),
    C("Tamsulosin hydrochloride", "070401", 22, (F("modified-release capsule", "400micrograms", 30, 0.055),), ("Flomaxtra XL",), 5.0, 0.04, profile="male_older"),
    C("Finasteride", "070401", 8, (F("tablet", "5mg", 28, 0.045),), ("Proscar",), 12.0, 0.01, profile="male_older"),
    C("Solifenacin succinate", "070402", 7, (F("tablet", "5mg|10mg", 30, 0.055, 0.08),), ("Vesicare",), 9.0, 0.05, profile="older"),
    C("Oxybutynin hydrochloride", "070402", 3, (F("tablet", "2.5mg|5mg", 56, 0.045, 0.05),), ("Ditropan",), 3.0, 0.05, trend=-0.08, profile="older"),
    C("Mirabegron", "070402", 5, (F("modified-release tablet", "25mg|50mg", 30, 0.97),), ("Betmiga",), 1.0, 1.0, generic=False, trend=0.10, profile="older"),
    C("Sildenafil", "070405", 5, (F("tablet", "25mg|50mg|100mg", 4, 0.30, 0.40, 0.55),), ("Viagra",), 20.0, 0.01, profile="male_older"),
    C("Tadalafil", "070405", 4, (F("tablet", "5mg|10mg|20mg", 4, 0.40, 0.45, 0.55),), ("Cialis",), 15.0, 0.02, profile="male_older"),
    # ---------------- 08 Malignant disease and immunosuppression ----------------
    C("Methotrexate", "080103", 3, (F("tablet", "2.5mg", 28, 0.11),), ("Maxtrex",), 1.5, 0.15, profile="older"),
    C("Azathioprine", "080202", 2, (F("tablet", "25mg|50mg", 56, 0.06, 0.08),), ("Imuran",), 3.0, 0.05),
    C("Tamoxifen", "080304", 2, (F("tablet", "20mg", 30, 0.075),), profile="female_midlife"),
    C("Anastrozole", "080304", 3, (F("tablet", "1mg", 28, 0.045),), ("Arimidex",), 30.0, 0.01, profile="female_older"),
    C("Letrozole", "080304", 3, (F("tablet", "2.5mg", 14, 0.07),), ("Femara",), 25.0, 0.01, profile="female_older"),
    C("Bicalutamide", "080304", 2, (F("tablet", "50mg", 28, 0.055),), ("Casodex",), 20.0, 0.01, profile="male_older"),
    # ---------------- 09 Nutrition and blood ----------------
    C("Ferrous sulfate", "090101", 12, (F("tablet", "200mg", 28, 0.025),), profile="female_repro"),
    C("Ferrous fumarate", "090101", 8, (F("tablet", "210mg", 84, 0.03),), ("Fersaday",), 1.5, 0.20, profile="female_repro"),
    C("Folic acid", "090102", 20, (F("tablet", "400micrograms|5mg", 28, 0.03, 0.025),), profile="female_repro"),
    C("Cyanocobalamin", "090102", 3, (F("tablet", "50micrograms", 50, 0.10),), ("Cytacon",), 1.5, 0.30, profile="older"),
    C("Calcium carbonate with colecalciferol", "090501", 18, (F("chewable tablet", "1.5g/400unit", 112, 0.06),), ("Adcal-D3", "Accrete D3", "Calcichew-D3 Forte"), 1.3, 0.80, profile="female_older"),
    C("Colecalciferol", "090604", 55, (F("capsule", "800unit|1000unit|20000unit", 30, 0.10, 0.10, 0.30),), ("Fultium-D3", "Invita D3", "Stexerol-D3"), 1.4, 0.60, season="mild_winter", trend=0.05),
    # ---------------- 10 Musculoskeletal ----------------
    C("Naproxen", "100101", 22, (F("tablet", "250mg|500mg", 56, 0.045, 0.06),), ("Naprosyn",), 6.0, 0.01),
    C("Ibuprofen", "100101", 14, (F("tablet", "200mg|400mg", 84, 0.035), F("gel", "5%", 100, 0.05)), ("Brufen",), 3.0, 0.03),
    C("Diclofenac sodium", "100101", 6, (F("gastro-resistant tablet", "50mg", 84, 0.035), F("gel", "1.16%", 100, 0.07)), ("Voltarol",), 3.0, 0.05, trend=-0.12),
    C("Allopurinol", "100104", 18, (F("tablet", "100mg|300mg", 28, 0.025, 0.035),), ("Zyloric",), 4.0, 0.02, profile="male_older"),
    C("Colchicine", "100104", 5, (F("tablet", "500micrograms", 28, 0.11),), profile="male_older"),
    C("Baclofen", "100202", 4, (F("tablet", "10mg", 84, 0.045),), ("Lioresal",), 5.0, 0.03),
    # ---------------- 11 Eye ----------------
    C("Chloramphenicol", "110301", 8, (F("eye drops", "0.5%", 10, 0.25), F("eye ointment", "1%", 4, 0.45)), season="mild_winter", profile="acute"),
    C("Latanoprost", "110600", 7, (F("eye drops", "50micrograms/ml", 2, 1.20),), ("Xalatan",), 8.0, 0.03, profile="older"),
    C("Timolol maleate", "110600", 3, (F("eye drops", "0.25%|0.5%", 5, 0.45, 0.50),), ("Timoptol",), 3.0, 0.08, profile="older"),
    C("Carbomer 980", "110801", 6, (F("eye gel", "0.2%", 10, 0.16),), ("Viscotears", "Clinitas"), 1.2, 0.45, profile="older"),
    C("Hypromellose", "110801", 7, (F("eye drops", "0.3%", 10, 0.11),), ("Tears Naturale",), 2.5, 0.10, profile="older"),
    # ---------------- 12 Ear, nose and oropharynx ----------------
    C("Beclometasone dipropionate (nasal)", "120201", 6, (F("nasal spray", "50micrograms/dose", 1, 2.10),), ("Beconase Aqueous",), 2.0, 0.10, season="summer"),
    C("Fluticasone propionate (nasal)", "120201", 6, (F("nasal spray", "50micrograms/dose", 1, 3.55),), ("Flixonase Aqueous",), 3.0, 0.10, season="summer"),
    C("Mometasone furoate (nasal)", "120201", 9, (F("nasal spray", "50micrograms/dose", 1, 2.50),), ("Nasonex",), 3.5, 0.05, season="summer", trend=0.04),
    C("Nystatin", "120302", 3, (F("oral suspension", "100,000units/ml", 30, 0.07),), ("Nystan",), 2.0, 0.10, profile="child"),
    # ---------------- 13 Skin ----------------
    C("Liquid paraffin with white soft paraffin", "130201", 25, (F("cream", "6.3%/15%", 500, 0.012),), ("Zerobase", "Diprobase", "Epimax", "Cetraben"), 1.9, 0.75, season="mild_winter"),
    C("Hydrocortisone (topical)", "130400", 8, (F("cream", "1%", 30, 0.07),), ("Dioderm",), 2.0, 0.05),
    C("Clobetasone butyrate", "130400", 6, (F("cream", "0.05%", 30, 0.13),), ("Eumovate",), 1.6, 0.30),
    C("Betamethasone valerate", "130400", 5, (F("cream", "0.1%", 100, 0.045),), ("Betnovate",), 1.6, 0.35),
    C("Clobetasol propionate", "130400", 4, (F("cream", "0.05%", 30, 0.11),), ("Dermovate",), 1.6, 0.30),
    C("Fusidic acid", "131001", 6, (F("cream", "2%", 30, 0.16),), ("Fucidin",), 1.4, 0.25, profile="child"),
    C("Clotrimazole", "131002", 8, (F("cream", "1%", 20, 0.10),), ("Canesten",), 1.8, 0.20),
)

# --------------------------------------------------------------------------
# Price events (Drug Tariff-style changes during the period)
# --------------------------------------------------------------------------
# kind: "concession"  -> temporary multiplier between start and end, then back to baseline
#       "reduction"   -> permanent multiplier from start (generic competition / Category M)
#       "uplift"      -> permanent multiplier on ALL branded presentations from start
PRICE_EVENTS = [
    ("concession", "Amoxicillin", "2023-01-01", "2023-04-30", 2.6),  # winter Strep A demand
    ("concession", "Sertraline hydrochloride", "2023-03-01", "2023-08-31", 3.2),
    ("concession", "Amlodipine", "2024-01-01", "2024-03-31", 2.0),
    ("concession", "Co-codamol", "2024-06-01", "2024-11-30", 1.8),
    ("concession", "Levothyroxine sodium", "2025-02-01", "2025-05-31", 1.6),
    ("reduction", "Pregabalin", "2023-10-01", None, 0.70),
    ("reduction", "Sitagliptin", "2024-04-01", None, 0.45),
    ("reduction", "Tadalafil", "2025-01-01", None, 0.60),
    ("uplift", None, "2024-04-01", None, 1.030),
    ("uplift", None, "2025-04-01", None, 1.025),
]
