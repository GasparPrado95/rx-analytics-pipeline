"""PBIR report helpers (Power BI enhanced report format). Adapted from the author's dashboard builder.

The semantic model itself is authored with the Power BI modelling MCP server and exported to TMDL;
this module only writes the report definition (pages, visuals, theme) next to it.
"""
import json
import pathlib
import shutil
import uuid

SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
VC_SCHEMA = f"{SCH}/visualContainer/2.13.0/schema.json"
PLATFORM_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json"
BASE_THEME = pathlib.Path(__file__).resolve().parent / "Fluent2-CY26SU09.json"
MEAS = "_Measures"


def write(path, content):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(content, str):
        content = json.dumps(content, indent=2, ensure_ascii=False)
    path.write_text(content, encoding="utf-8")


# ------------------------------------------------------------------ report primitives
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def color(c):
    return {"solid": {"color": lit(f"'{c}'")}}


def s(text):
    return lit("'" + text.replace("'", "''") + "'")


def col(entity, prop, display=None):
    p = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
         "queryRef": f"{entity}.{prop}", "nativeQueryRef": display or prop}
    if display:
        p["displayName"] = display
    return p


def mea(prop, display=None):
    p = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": MEAS}}, "Property": prop}},
         "queryRef": f"{MEAS}.{prop}", "nativeQueryRef": display or prop}
    if display:
        p["displayName"] = display
    return p


def sort_by(proj, desc=True):
    return {"sort": [{"field": proj["field"], "direction": "Descending" if desc else "Ascending"}], "isDefaultSort": True}


def labels_on():
    return {"labels": [{"properties": {"show": lit("true")}}]}


class Page:
    def __init__(self, name, display, background=None):
        self.name, self.display, self.background = name, display, background
        self.visuals = []

    def add(self, vtype, x, y, w, h, query=None, objects=None, title=None, container=None, sort=None, filters=None):
        n = len(self.visuals) + 1
        v = {"visualType": vtype}
        if query:
            v["query"] = {"queryState": {role: {"projections": projs} for role, projs in query.items()}}
            if sort:
                v["query"]["sortDefinition"] = sort
        if objects:
            v["objects"] = objects
        vco = dict(container or {})
        if title is not None:
            vco.setdefault("title", [{"properties": {"show": lit("true"), "text": s(title)}}])
        vco.setdefault("subTitle", [{"properties": {"show": lit("false")}}])   # base theme (Fluent 2) repeats the title as a subtitle
        v["visualContainerObjects"] = vco
        v["drillFilterOtherVisuals"] = True
        body = {"$schema": VC_SCHEMA, "name": f"{self.name}{n:02d}",
                "position": {"x": x, "y": y, "z": n * 1000, "height": h, "width": w, "tabOrder": n * 1000}, "visual": v}
        if filters:
            body["filterConfig"] = {"filters": filters}
        self.visuals.append(body)
        return body


def no_chrome(bg=None):
    c = {"title": [{"properties": {"show": lit("false")}}], "dropShadow": [{"properties": {"show": lit("false")}}],
         "border": [{"properties": {"show": lit("false")}}], "visualHeader": [{"properties": {"show": lit("false")}}],
         "padding": [{"properties": {"top": lit("0D"), "bottom": lit("0D"), "left": lit("0D"), "right": lit("0D")}}]}
    c["background"] = ([{"properties": {"show": lit("true"), "color": color(bg), "transparency": lit("0D")}}] if bg
                       else [{"properties": {"show": lit("false")}}])
    return c


def text(page, x, y, w, h, paragraphs, bg=None, align="left"):
    """paragraphs: list of paragraphs; each a list of (text, size_pt, color, font)."""
    paras = [{"textRuns": [{"value": t, "textStyle": {"fontFamily": f, "fontSize": f"{sz}pt", "color": c}} for t, sz, c, f in para],
              "horizontalTextAlignment": align} for para in paragraphs]
    return page.add("textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": paras}}]}, container=no_chrome(bg))


def card(page, x, y, w, h, measure, label, value_color=None, label_color=None, size=None, font=None, container=None, show_label=True):
    objs = {}
    lab = {}
    if value_color:
        lab["color"] = color(value_color)
    if size:
        lab["fontSize"] = lit(f"{size}D")
    if font:
        lab["fontFamily"] = s(font)
    if lab:
        objs["labels"] = [{"properties": lab}]
    cl = {"show": lit("true" if show_label else "false")}
    if label_color:
        cl["color"] = color(label_color)
    objs["categoryLabels"] = [{"properties": cl}]
    return page.add("card", x, y, w, h, query={"Values": [mea(measure, label)]}, objects=objs,
                    container=container or {"title": [{"properties": {"show": lit("false")}}]})


def image(page, x, y, w, h, resource, scaling="Fit", bg=None):
    """Image visual showing a file registered with build_report(images=...)."""
    objs = {"image": [{"properties": {"sourceFile": {"image": {
        "name": s(resource),
        "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": resource}}},
        "scaling": s(scaling)}}}}]}
    return page.add("image", x, y, w, h, objects=objs, container=no_chrome(bg))


def nav_button(page, x, y, w, h, target_page, label, fg, bg=None, hover=None, size=11, font="Segoe UI Semibold", align="left"):
    """Button that navigates to another page (Ctrl+click in Desktop edit mode, plain click when published)."""
    fill = [{"properties": {"show": lit("true" if (bg or hover) else "false")}}]
    if bg:
        fill.append({"properties": {"fillColor": color(bg), "transparency": lit("0D")}, "selector": {"id": "default"}})
    elif hover:
        fill.append({"properties": {"fillColor": color(hover), "transparency": lit("100D")}, "selector": {"id": "default"}})
    if hover:
        fill.append({"properties": {"fillColor": color(hover), "transparency": lit("0D")}, "selector": {"id": "hover"}})
    objs = {
        "icon": [{"properties": {"show": lit("false")}}],
        "text": [{"properties": {"show": lit("true")}},
                 {"properties": {"text": s(label), "fontColor": color(fg), "fontSize": lit(f"{size}D"), "fontFamily": s(font),
                                 "horizontalAlignment": s(align), "leftMargin": lit("8D")}, "selector": {"id": "default"}}],
        "fill": fill,
        "outline": [{"properties": {"show": lit("false")}}],
    }
    container = no_chrome()
    container["visualLink"] = [{"properties": {"show": lit("true"), "type": s("PageNavigation"), "navigationSection": s(target_page)}}]
    return page.add("actionButton", x, y, w, h, objects=objs, container=container)


def slicer(page, x, y, w, h, entity, prop, label, mode="Dropdown"):
    objs = {"data": [{"properties": {"mode": s(mode)}}], "header": [{"properties": {"show": lit("true"), "text": s(label)}}]}
    if mode == "Dropdown":
        objs["selection"] = [{"properties": {"selectAllCheckboxEnabled": lit("true")}}]
    page.add("slicer", x, y, w, h, query={"Values": [col(entity, prop, label)]}, objects=objs,
             container={"title": [{"properties": {"show": lit("false")}}],
                        "padding": [{"properties": {"top": lit("4D"), "bottom": lit("4D"), "left": lit("10D"), "right": lit("10D")}}]})


def finalize_theme(theme):
    """Use measure format strings as-is (no automatic K/M display units, which also follow the Desktop UI language)
    and drop the base theme's donut centre total, which gets truncated."""
    vs = theme.setdefault("visualStyles", {})
    star = vs.setdefault("*", {}).setdefault("*", {})
    for key in ("valueAxis", "labels"):
        entries = star.setdefault(key, [{}])
        for e in entries:
            e["labelDisplayUnits"] = 1
    card = vs.setdefault("card", {}).setdefault("*", {})
    for e in card.setdefault("labels", [{}]):
        e["labelDisplayUnits"] = 1
    donut = vs.setdefault("donutChart", {}).setdefault("*", {})
    donut["centerValue"] = [{"show": False}]
    return theme


def build_report(out_dir, name, pages, theme, theme_file, images=None):
    theme = finalize_theme(theme)
    root = pathlib.Path(out_dir) / f"{name}.Report"
    for sub in ("definition", "StaticResources"):
        if (root / sub).exists():
            shutil.rmtree(root / sub)
    d = root / "definition"
    write(root / "StaticResources" / "RegisteredResources" / theme_file, theme)
    reg_items = [{"name": theme_file, "path": theme_file, "type": "CustomTheme"}]
    for res_name, src in (images or []):
        shutil.copy(src, root / "StaticResources" / "RegisteredResources" / res_name)
        reg_items.append({"name": res_name, "path": res_name, "type": "Image"})
    (root / "StaticResources" / "SharedResources" / "BaseThemes").mkdir(parents=True, exist_ok=True)
    shutil.copy(BASE_THEME, root / "StaticResources" / "SharedResources" / "BaseThemes" / BASE_THEME.name)
    ver = {"visual": "2.13.0", "report": "3.4.0", "page": "2.3.1"}
    write(d / "report.json", {
        "$schema": f"{SCH}/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": BASE_THEME.stem, "reportVersionAtImport": ver, "type": "SharedResources"},
                            "customTheme": {"name": theme_file, "reportVersionAtImport": ver, "type": "RegisteredResources"}},
        "objects": {"section": [{"properties": {"verticalAlignment": s("Top")}}],
                    "outspacePane": [{"properties": {"expanded": lit("false")}}]},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": BASE_THEME.stem, "path": f"BaseThemes/{BASE_THEME.name}", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": reg_items}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True}})
    write(d / "version.json", {"$schema": f"{SCH}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    write(d / "pages" / "pages.json", {"$schema": f"{SCH}/pagesMetadata/1.1.0/schema.json",
                                       "pageOrder": [p.name for p in pages], "activePageName": pages[0].name})
    for p in pages:
        pj = {"$schema": f"{SCH}/page/2.1.0/schema.json", "name": p.name, "displayName": p.display,
              "displayOption": "FitToPage", "height": 720, "width": 1280}
        if p.background:
            pj["objects"] = {"background": [{"properties": {"color": color(p.background), "transparency": lit("0D")}}],
                             "outspace": [{"properties": {"color": color(p.background), "transparency": lit("0D")}}]}
        write(d / "pages" / p.name / "page.json", pj)
        for v in p.visuals:
            write(d / "pages" / p.name / "visuals" / v["name"] / "visual.json", v)
    write(root / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{name}.SemanticModel"}}})
    write(root / ".platform", {"$schema": PLATFORM_SCHEMA, "metadata": {"type": "Report", "displayName": name},
                               "config": {"version": "2.0", "logicalId": str(uuid.uuid5(uuid.NAMESPACE_URL, f"pbip/{name}/report"))}})
    write(pathlib.Path(out_dir) / f"{name}.pbip", {"version": "1.0", "artifacts": [{"report": {"path": f"{name}.Report"}}],
                                                   "settings": {"enableAutoRecovery": True}})


# ------------------------------------------------------------------ visual-level filters
def _col_expr(source, prop):
    return {"Column": {"Expression": {"SourceRef": {"Source": source}}, "Property": prop}}


def categorical_filter(name, entity, prop, values):
    """Keep only rows whose column is in values (strings are quoted, booleans/numbers passed as 'true' / '1')."""
    lits = [[{"Literal": {"Value": v if isinstance(v, str) and v in ("true", "false") else f"'{v}'"}}] for v in values]
    return {"name": name, "type": "Categorical",
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "filter": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [_col_expr("t", prop)], "Values": lits}}}]}}


def topn_filter(name, entity, prop, measure, n):
    """Top N members of entity[prop] ranked by a measure of the _Measures table."""
    return {"name": name, "type": "TopN",
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "filter": {"Version": 2,
                       "From": [{"Name": "subquery", "Type": 2, "Expression": {"Subquery": {"Query": {
                           "Version": 2,
                           "From": [{"Name": "t", "Entity": entity, "Type": 0}, {"Name": "m", "Entity": MEAS, "Type": 0}],
                           "Select": [{**_col_expr("t", prop), "Name": "field"}],
                           "OrderBy": [{"Direction": 2, "Expression": {"Measure": {
                               "Expression": {"SourceRef": {"Source": "m"}}, "Property": measure}}}],
                           "Top": n}}}},
                                {"Name": "t", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [_col_expr("t", prop)],
                                                       "Table": {"SourceRef": {"Source": "subquery"}}}}}]}}
