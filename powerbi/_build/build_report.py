"""Generate the RxAnalytics Power BI report (PBIR) and its theme.

    python powerbi/_build/build_report.py

Writes powerbi/RxAnalytics.Report, powerbi/RxAnalytics.pbip and powerbi/theme/rx-plum-gold.json.
The semantic model (powerbi/RxAnalytics.SemanticModel/definition) is authored with the Power BI
modelling MCP server and exported as TMDL; this script only adds its PBIP wrapper files.
Close Power BI Desktop before running: an open Desktop overwrites the files on save.
"""

from __future__ import annotations

import copy
import pathlib

from pbir_lib import (
    PLATFORM_SCHEMA,
    Page,
    build_report,
    card,
    categorical_filter,
    col,
    color,
    labels_on,
    mea,
    nav_button,
    slicer,
    sort_by,
    text,
    topn_filter,
    write,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAME = "RxAnalytics"

# ------------------------------------------------------------------ design tokens
# Data colours validated with the dataviz skill's palette checker on the ivory canvas and on white
# cards: lightness band, chroma floor, colour-blind separation (worst adjacent dE 24) and >= 3:1.
PLUM, GOLD, LAVENDER, BRONZE = "#6A3B98", "#B57D00", "#A07AD6", "#8A5A12"
OTHER = "#8C8494"
# Decorative (never used for data)
AUBERGINE = "#2E1A47"   # header band
GOLD_RULE = "#C9A227"   # thin rule under the header
CANVAS = "#F7F4EF"      # warm ivory page
CARD = "#FFFFFF"
BORDER = "#E7E1D8"
GRID = "#EDE8E1"
INK = "#241B2F"         # primary text
INK_2 = "#5E556A"       # secondary text
INK_ON_DARK = "#F3EDF9"
MUTED_ON_DARK = "#CDBDE3"
SERIF, SANS, SANS_BOLD = "Georgia", "Segoe UI", "Segoe UI Semibold"


def theme() -> dict:
    axis = {"labelColor": {"solid": {"color": INK_2}}, "fontSize": 9, "fontFamily": SANS,
            "titleColor": {"solid": {"color": INK_2}}, "titleFontSize": 9}
    return {
        "name": "Rx Plum & Gold",
        "dataColors": [PLUM, GOLD, LAVENDER, BRONZE, OTHER, "#C9B6E4", "#E3C77A", "#4A2970"],
        "foreground": INK, "foregroundNeutralSecondary": INK_2, "foregroundNeutralTertiary": OTHER,
        "background": CARD, "backgroundLight": CANVAS, "backgroundNeutral": BORDER,
        "tableAccent": PLUM,
        "good": "#2E7D4F", "neutral": GOLD, "bad": "#B3261E",
        "maximum": "#4A2970", "center": "#B9A3DA", "minimum": "#F3EDF9",
        "textClasses": {
            "callout": {"fontSize": 24, "fontFace": SANS_BOLD, "color": INK},
            "title": {"fontSize": 12, "fontFace": SANS_BOLD, "color": INK},
            "header": {"fontSize": 11, "fontFace": SANS_BOLD, "color": INK},
            "label": {"fontSize": 10, "fontFace": SANS, "color": INK_2},
        },
        "visualStyles": {
            "*": {"*": {
                "background": [{"show": True, "color": {"solid": {"color": CARD}}, "transparency": 0}],
                "border": [{"show": True, "color": {"solid": {"color": BORDER}}, "radius": 8}],
                "dropShadow": [{"show": False}],
                "title": [{"show": True, "fontFamily": SANS_BOLD, "fontSize": 12,
                           "fontColor": {"solid": {"color": INK}}}],
                "subTitle": [{"show": False}],
                "padding": [{"top": 10, "bottom": 8, "left": 12, "right": 12}],
                "valueAxis": [{**axis, "gridlineColor": {"solid": {"color": GRID}}, "gridlineStyle": "solid",
                               "showAxisTitle": False}],
                "categoryAxis": [{**axis, "showAxisTitle": False, "gridlineShow": False}],
                "legend": [{"labelColor": {"solid": {"color": INK_2}}, "fontSize": 9, "position": "Top",
                            "showTitle": False}],
                "lineStyles": [{"strokeWidth": 2, "showMarker": False}],
                "labels": [{"color": {"solid": {"color": INK_2}}, "fontSize": 9}],
            }},
            "page": {"*": {"background": [{"color": {"solid": {"color": CANVAS}}, "transparency": 0}],
                           "outspace": [{"color": {"solid": {"color": CANVAS}}, "transparency": 0}]}},
            "card": {"*": {"labels": [{"color": {"solid": {"color": INK}}, "fontSize": 22, "fontFamily": SANS_BOLD}],
                           "categoryLabels": [{"color": {"solid": {"color": INK_2}}, "fontSize": 10, "fontFamily": SANS}]}},
            "tableEx": {"*": {"columnHeaders": [{"fontColor": {"solid": {"color": "#4A2970"}},
                                                 "backColor": {"solid": {"color": "#F3EDF9"}}, "fontFamily": SANS_BOLD}],
                              "values": [{"fontColorPrimary": {"solid": {"color": INK}}, "fontSize": 9,
                                          "backColorSecondary": {"solid": {"color": "#FBF9FD"}}}],
                              "grid": [{"gridHorizontalColor": {"solid": {"color": GRID}}, "outlineColor": {"solid": {"color": BORDER}}}]}},
            "pivotTable": {"*": {"columnHeaders": [{"fontColor": {"solid": {"color": "#4A2970"}},
                                                    "backColor": {"solid": {"color": "#F3EDF9"}}, "fontFamily": SANS_BOLD}],
                                 "rowHeaders": [{"fontColor": {"solid": {"color": INK}}, "fontSize": 9}],
                                 "values": [{"fontColorPrimary": {"solid": {"color": INK}}, "fontSize": 9}],
                                 "grid": [{"gridHorizontalColor": {"solid": {"color": GRID}}}]}},
            "slicer": {"*": {"header": [{"fontColor": {"solid": {"color": INK_2}}, "textSize": 9}],
                             "items": [{"fontColor": {"solid": {"color": INK}}, "textSize": 10}]}},
        },
    }


# ------------------------------------------------------------------ page chrome
PAGES = [("overview", "Overview"), ("regions", "Regions"), ("medicines", "Medicines"),
         ("savings", "Generic Savings"), ("quality", "Data Quality")]
TITLES = {
    "overview": ("Executive overview", "Volume, cost and generic prescribing at a glance"),
    "regions": ("Regional variation", "Prescribing rates per 1,000 registered patients by region, ICB and deprivation"),
    "medicines": ("Medicines & BNF drill-down", "Where the items and the money go, chapter to presentation"),
    "savings": ("Generic vs branded", "The savings opportunity where a generic is available"),
    "quality": ("Data quality & pipeline health", "What the pipeline found, fixed and loaded"),
}


def header(page: Page, key: str) -> None:
    title, sub = TITLES[key]
    text(page, 0, 0, 1280, 66, [
        [("Prescribing Analytics  ·  ", 11, MUTED_ON_DARK, SANS), (title, 20, INK_ON_DARK, SERIF)],
        [(f"{sub}.  Synthetic NHS England primary-care data, 2023–2025.", 9, MUTED_ON_DARK, SANS)],
    ], bg=AUBERGINE)
    text(page, 0, 66, 1280, 3, [[(" ", 1, GOLD_RULE, SANS)]], bg=GOLD_RULE)
    x = 1280 - 24 - len(PAGES) * 112
    for name, label in PAGES:
        active = name == key
        nav_button(page, x, 18, 108, 30, name, label, fg=GOLD_RULE if active else MUTED_ON_DARK,
                   hover="#4A2E66", size=10, font=SANS_BOLD if active else SANS, align="center")
        x += 112


def slicers(page: Page, which: list[str], y: int = 80) -> None:
    spec = {"year": ("Date", "Year", "Year"), "region": ("Practice", "Region", "Region"),
            "chapter": ("Medicine", "BNF Chapter", "BNF chapter")}
    x = 24
    for key in which:
        entity, prop, label = spec[key]
        w = 300 if key == "chapter" else 190
        slicer(page, x, y, w, 46, entity, prop, label)
        x += w + 12


def kpi(page, x, y, w, h, measure, label, size=22):
    card(page, x, y, w, h, measure, label, value_color=INK, label_color=INK_2, size=size, font=SANS_BOLD)


def kpi_row(page, y, h, items, size=22, x0=24, width=1232, gap=12):
    w = (width - gap * (len(items) - 1)) / len(items)
    for i, (measure, label) in enumerate(items):
        if measure:
            kpi(page, round(x0 + i * (w + gap)), y, round(w), h, measure, label, size)


def chart(page, vtype, x, y, w, h, title, query, objects=None, sort=None, filters=None):
    return page.add(vtype, x, y, w, h, query=query, objects=objects, title=title, sort=sort, filters=filters)


def series_color(c):
    return {"dataPoint": [{"properties": {"fill": color(c)}}]}


# ------------------------------------------------------------------ pages
def overview() -> Page:
    p = Page("overview", "Overview")
    header(p, "overview")
    slicers(p, ["year", "region", "chapter"])
    text(p, 880, 84, 376, 40, [[("Rates are monthly averages per 1,000 registered patients. "
                                 "Change figures compare with the same period a year earlier.", 8, INK_2, SANS)]])
    kpi_row(p, 136, 84, [("Total Items", "Items dispensed"), ("Total Cost", "Net ingredient cost"),
                         ("Cost per Item", "Cost per item"), ("Items per 1,000 Patients", "Items per 1,000 patients / month"),
                         ("Generic %", "Generic prescribing rate")])
    kpi_row(p, 226, 46, [("Items YoY %", "vs prior year"), ("Cost YoY %", "vs prior year"), (None, None), (None, None),
                         ("Generic % Change vs PY", "vs prior year")], size=12)
    month = col("Date", "Month Start", "Month")
    chart(p, "lineChart", 24, 284, 608, 210, "Items dispensed per month",
          {"Category": [month], "Y": [mea("Total Items", "Items")]})
    chart(p, "lineChart", 644, 284, 612, 210, "Net ingredient cost, rolling 12 months",
          {"Category": [month], "Y": [mea("Cost Rolling 12M", "Cost (rolling 12 months)")]}, objects=series_color(GOLD))
    chapter = col("Medicine", "BNF Chapter", "BNF chapter")
    items = mea("Total Items", "Items")
    chart(p, "clusteredBarChart", 24, 506, 608, 190, "Items by BNF chapter",
          {"Category": [chapter], "Y": [items]}, objects=labels_on(), sort=sort_by(items))
    chart(p, "lineChart", 644, 506, 612, 190, "Generic prescribing rate per month",
          {"Category": [month], "Y": [mea("Generic %", "Generic prescribing rate")]})
    return p


def regions() -> Page:
    p = Page("regions", "Regions")
    header(p, "regions")
    slicers(p, ["year", "chapter"])
    kpi_row(p, 136, 80, [("Items per 1,000 Patients", "Items per 1,000 patients / month"),
                         ("Cost per 1,000 Patients", "Cost per 1,000 patients / month"),
                         ("Antibacterial Items per 1,000 Patients", "Antibacterial items per 1,000 / month"),
                         ("Registered Patients", "Registered patients (panel)")])
    rate = mea("Items per 1,000 Patients", "Items per 1,000 patients")
    chart(p, "clusteredBarChart", 24, 228, 400, 222, "Items per 1,000 patients by NHS region",
          {"Category": [col("Practice", "Region")], "Y": [rate]}, objects=labels_on(), sort=sort_by(rate))
    quint = col("Practice", "Deprivation Quintile", "Deprivation quintile")
    chart(p, "clusteredColumnChart", 24, 462, 400, 234, "Items per 1,000 patients by practice deprivation",
          {"Category": [quint], "Y": [rate]}, objects=labels_on(), sort=sort_by(quint, desc=False))
    chart(p, "map", 436, 228, 360, 468, "Practices by postcode district (bubble = items)",
          {"Category": [col("Practice", "Postcode District")], "Size": [mea("Total Items", "Items")],
           "Tooltips": [rate]}, objects={"dataPoint": [{"properties": {"defaultColor": color(PLUM)}}]})
    chart(p, "pivotTable", 808, 228, 448, 468, "Region and ICB comparison",
          {"Rows": [col("Practice", "Region"), col("Practice", "ICB")],
           "Values": [mea("Items per 1,000 Patients", "Items /1k"), mea("Cost per 1,000 Patients", "Cost /1k"),
                      mea("Antibacterial Items per 1,000 Patients", "Antibacterial /1k"), mea("Generic %", "Generic %")]},
          sort=sort_by(mea("Items per 1,000 Patients", "Items /1k")))
    return p


def medicines() -> Page:
    p = Page("medicines", "Medicines")
    header(p, "medicines")
    slicers(p, ["year", "region", "chapter"])
    kpi_row(p, 136, 80, [("Total Items", "Items dispensed"), ("Total Cost", "Net ingredient cost"),
                         ("Cost per Item", "Cost per item"), ("Generic %", "Generic prescribing rate")])
    cost = mea("Total Cost", "Cost")
    chart(p, "pivotTable", 24, 228, 620, 468, "BNF drill-down (expand rows: chapter > section > paragraph > chemical > presentation)",
          {"Rows": [col("Medicine", "BNF Chapter", "BNF chapter"), col("Medicine", "BNF Section", "Section"),
                    col("Medicine", "BNF Paragraph", "Paragraph"), col("Medicine", "Chemical Substance", "Chemical"),
                    col("Medicine", "Presentation")],
           "Values": [mea("Total Items", "Items"), cost, mea("Cost per Item", "Cost / item"), mea("Generic %", "Generic %")]},
          sort=sort_by(cost))
    chem = col("Medicine", "Chemical Substance", "Chemical substance")
    chart(p, "clusteredBarChart", 656, 228, 600, 260, "Top 15 chemical substances by cost",
          {"Category": [chem], "Y": [cost]}, objects=labels_on(), sort=sort_by(cost),
          filters=[topn_filter("top15chem", "Medicine", "Chemical Substance", "Total Cost", 15)])
    chart(p, "clusteredColumnChart", 656, 500, 600, 196, "Seasonal profile: items by calendar month",
          {"Category": [col("Date", "Month Short", "Month")], "Y": [mea("Total Items", "Items")]},
          sort=sort_by(col("Date", "Month Short", "Month"), desc=False))
    return p


def savings() -> Page:
    p = Page("savings", "Generic Savings")
    header(p, "savings")
    slicers(p, ["year", "region", "chapter"])
    kpi_row(p, 136, 80, [("Potential Generic Saving", "Potential saving"), ("Generic %", "Generic prescribing rate"),
                         ("Branded Items Where Generic Available", "Branded items with a generic"),
                         ("Saving % of Branded Cost", "Saving as % of that branded cost")])
    chart(p, "columnChart", 24, 228, 400, 230, "Generic vs branded items where a generic exists",
          {"Category": [col("Date", "Year")],
           "Y": [mea("Generic Items Where Available", "Generic"), mea("Branded Items Where Generic Available", "Branded")]},
          objects=labels_on())
    chart(p, "lineChart", 24, 470, 400, 226, "Generic prescribing rate, rolling 12 months",
          {"Category": [col("Date", "Month Start", "Month")], "Y": [mea("Generic % Rolling 12M", "Generic % (rolling 12 months)")]})
    saving = mea("Potential Generic Saving", "Potential saving")
    chart(p, "clusteredBarChart", 436, 228, 820, 230, "Top 10 chemical substances by potential saving",
          {"Category": [col("Medicine", "Chemical Substance", "Chemical substance")], "Y": [saving]},
          objects={**labels_on(), **series_color(GOLD)}, sort=sort_by(saving),
          filters=[topn_filter("top10save", "Medicine", "Chemical Substance", "Potential Generic Saving", 10)])
    chart(p, "tableEx", 436, 470, 820, 226, "Branded presentations that have a generic equivalent",
          {"Values": [col("Medicine", "Presentation", "Branded presentation"), col("Medicine", "Generic Equivalent"),
                      mea("Total Items", "Items"), mea("Total Cost", "Cost"), saving]},
          sort=sort_by(saving),
          filters=[categorical_filter("branded", "Medicine", "Generic or Branded", ["Branded"]),
                   categorical_filter("hasgeneric", "Medicine", "Generic Available", ["true"])])
    return p


def quality() -> Page:
    p = Page("quality", "Data Quality")
    header(p, "quality")
    kpi_row(p, 82, 78, [("Last EL Run Status", "Last EL run"), ("Last EL Run", "Last EL run started (UTC)"),
                        ("Hours Since Last EL Run", "Hours since last EL run"), ("EL Success Rate", "EL run success rate"),
                        ("Rows Loaded (Latest Run)", "Rows loaded, latest run")], size=18)
    kpi_row(p, 172, 64, [("Duplicate Submissions Removed", "Duplicates removed"), ("Late Arrival %", "Late-arriving lines"),
                         ("Imputed Cost Lines", "Lines with imputed cost"), ("Restated Lines", "Restated lines"),
                         ("Credit Lines", "Credit lines")], size=16)
    chart(p, "tableEx", 24, 248, 700, 220, "Data-quality checks and how the pipeline handles them",
          {"Values": [col("Data Quality Checks", "Check"), col("Data Quality Checks", "Entity"),
                      col("Data Quality Checks", "Affected Rows"), col("Data Quality Checks", "Affected Share"),
                      col("Data Quality Checks", "Handling")]})
    lines = mea("Prescription Lines", "Lines")
    chart(p, "clusteredColumnChart", 736, 248, 520, 220, "Lines by days from dispensing to arrival",
          {"Category": [col("Prescriptions", "Arrival Lag Band", "Arrival lag")], "Y": [lines]},
          objects=labels_on(), sort=sort_by(col("Prescriptions", "Arrival Lag Band", "Arrival lag"), desc=False))
    chart(p, "tableEx", 24, 480, 700, 216, "Incremental loads of prescription lines (latest first)",
          {"Values": [col("Pipeline Runs", "Started At"), col("Pipeline Runs", "Status"), col("Pipeline Runs", "Load Mode"),
                      col("Pipeline Runs", "Full Refresh"), col("Pipeline Runs", "Rows Loaded"),
                      col("Pipeline Runs", "Watermark After"), col("Pipeline Runs", "Duration (s)")]},
          sort=sort_by(col("Pipeline Runs", "Started At")),
          filters=[categorical_filter("itemtable", "Pipeline Runs", "Table", ["prescription_item"])])
    chart(p, "lineChart", 736, 480, 520, 216, "Late-arriving share by dispensing month",
          {"Category": [col("Date", "Month Start", "Month")], "Y": [mea("Late Arrival %", "Late-arriving share")]},
          objects=series_color(GOLD))
    return p


def main() -> None:
    t = theme()
    write(ROOT / "theme" / "rx-plum-gold.json", copy.deepcopy(t))
    build_report(ROOT, NAME, [overview(), regions(), medicines(), savings(), quality()], t, "rx-plum-gold.json")

    # PBIP wrapper files for the MCP-authored semantic model
    sm = ROOT / f"{NAME}.SemanticModel"
    write(sm / "definition.pbism", {"version": "4.2", "settings": {}})
    write(sm / ".platform", {"$schema": PLATFORM_SCHEMA, "metadata": {"type": "SemanticModel", "displayName": NAME},
                             "config": {"version": "2.0", "logicalId": "4f3d2a8e-6b1c-4e7a-9d55-0c2b7a9e1f10"}})
    if not (sm / ".pbi" / "editorSettings.json").exists():
        write(sm / ".pbi" / "editorSettings.json", {"version": "1.0", "autodetectRelationships": False,
                                                    "parallelQueryLoading": True, "typeDetectionEnabled": True,
                                                    "relationshipImportEnabled": False})
    print("report written:", ROOT / f"{NAME}.pbip")


if __name__ == "__main__":
    main()
