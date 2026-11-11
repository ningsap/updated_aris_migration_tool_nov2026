# fmt: off
import datetime

from openpyxl import Workbook

from amlquery import AMLQuery

amlquery = AMLQuery('ARISAMLExport(Final Migration).xml')

mdlTypes = ["MT_ENTERPRISE_BPMN_COLLABORATION", "MT_ENTERPRISE_BPMN_PROCESS", "MT_VAL_ADD_CHN_DGM", "MT_BPMN_COLLABORATION_DIAGRAM"]

dropdown_values = {
    "1478b9dd-a69d-11e4-4d0d-adcb4d40def0": "Important",
    "1478b9e5-a69d-11e4-4d0d-adcb4d40def0": "Useful",
    "64736d43-a69d-11e4-4d0d-adcb4d40def0": "Vital",
    "e5e979b5-a69c-11e4-4d0d-adcb4d40def0": "Open",
    "e5ebeab7-a69c-11e4-4d0d-adcb4d40def0": "Internal Use",
    "e5ebeabf-a69c-11e4-4d0d-adcb4d40def0": "Confidential",
    "e5ebeac7-a69c-11e4-4d0d-adcb4d40def0": "Secret",
}


func_symbol_type_to_name = {
    "f7b7ddc1-2043-11e8-111c-005056824c5c": "Business Area/Line-of-Business",
    "ST_VAL_ADD_CHN_SML_1": "Business Area/Line-of-Business",
    "e8bb8061-2043-11e8-111c-005056824c5c": "Business Function",
    "ST_VAL_ADD_CHN_SML_2": "Business Function",
    "ST_PRCS_1": "Process",
    "7b36e700-6c51-11de-78c8-9fd61b0df263": "Process",
    "6d2513e1-da30-11e5-45a6-fcf8ae82d10b": "Sub Capability",
    "fee3cc00-f63b-11e0-360d-b4749ff50628": "Sub Capability",
    "87038b71-da30-11e5-45a6-fcf8ae82d10b": "Sub Sub Capability",
    # "ST_BPMN_USER_TASK": "User task",
    # "ST_BPMN_TASK": "Task",
    # "ST_BPMN_SERVICE_TASK": "Service task",
    # "ST_BPMN_SEND_TASK": "Send task",
    # "ST_BPMN_SCRIPT_TASK": "Script task",
    # "ST_BPMN_RECEIVE_TASK": "Receive task",
    # "ST_BPMN_MANUAL_TASK_2": "Manual task",
    # "336f6241-1b88-11e8-111c-005056824c5c": "Manual Function",
    # "ST_FUNC": "Manual Function",
    # "ST_BPMN_CALL_ACTIVITY": "Call activity",
    # "ST_BPMN_SUBPROCESS": "",
    "AVT_BPMN_TASK_TYPE_MANUAL": "Manual",
    "AVT_BPMN_TASK_TYPE_BUSINESS_RULE": "Business Rule",
    "AVT_BPMN_TASK_TYPE_SERVICE": "Service",
    "AVT_BPMN_TASK_TYPE_RECEIVE": "Receive",
    "AVT_BPMN_TASK_TYPE_SEND": "Send",
    "AVT_BPMN_TASK_TYPE_USER": "User",
    "AVT_BPMN_TASK_TYPE_SCRIPT": "Script",
    "AVT_BPMN_TASK_TYPE_ABSTRACT": "Task",
}

func_symbol_types = [
    "ST_BPMN_ADHOC_SUBPROCESS_COLLAPSED",
    "ST_BPMN_ADHOC_SUBPROCESS",
    "ST_VAL_ADD_CHN_SML_1",
    "ST_VAL_ADD_CHN_SML_2",
    "ST_BPMN_BUSINESS_RULE_TASK",
    "ST_BPMN_CALL_ACTIVITY_COLLAPSED",
    "ST_BPMN_CALL_ACTIVITY",
    "ST_FUNC",
    "ST_BPMN_MANUAL_TASK_2",
    "ST_BPMN_RECEIVE_TASK",
    "ST_BPMN_SCRIPT_TASK",
    "ST_BPMN_SEND_TASK",
    "ST_BPMN_SERVICE_TASK",
    "ST_BPMN_SUB_PROCESS_COLLAPSED",
    "ST_BPMN_SUBPROCESS",
    "ST_BPMN_TASK",
    "ST_BPMN_TRANSACTION_COLLAPSED_1",
    "ST_BPMN_TRANSACTION",
    "ST_BPMN_USER_TASK",
    "f7b7ddc1-2043-11e8-111c-005056824c5c",
    "ST_VAL_ADD_CHN_SML_1",
    "e8bb8061-2043-11e8-111c-005056824c5c",
    "ST_VAL_ADD_CHN_SML_2",
    "ST_PRCS_1",
    "7b36e700-6c51-11de-78c8-9fd61b0df263",
    "6d2513e1-da30-11e5-45a6-fcf8ae82d10b",
    "fee3cc00-f63b-11e0-360d-b4749ff50628",
    "87038b71-da30-11e5-45a6-fcf8ae82d10b",
]


ctrlSymbol = "ST_CONTR"

model_attrs = [
    {
        "title": "Path",
        "type": "Path"
    },
    {
        "title": "Model Name",
        "property": "AT_NAME",
    },
    {
        "title": "Model Description",
        "property": "AT_DESC",
    },
    {
        "title": "Model Identifier",
        "property": "AT_ID",
    },
    {
        "title": "Process Owner Historical",
        "property": "AT_AUTH",
    },
    {
        "title": "Department",
        "property": "841b75e1-a0d1-11e6-557d-fcf8ae82d10b",
    },
    {
        "title": "Model Related Documents",
        "titleProperty": ["AT_TITL2", "AT_TITL1", None],
        "linkProperty": ["AT_EXT_2", "AT_EXT_1", "AT_ADS_LINK_1"],
        "type": "DocumentURL"
    },
    {
        "title": "Security Classification",
        "type": "Dropdown",
        "property": "e5cf3af1-a69c-11e4-4d0d-adcb4d40def0",
    },
    {
        "title": "Vital Record Classification",
        "type": "Dropdown",
        "property": "14681801-a69d-11e4-4d0d-adcb4d40def0",
    }
]

node_attrs = [
   {
        "title": "Task Name",
        "property": "AT_NAME",
    },
    {
        "title": "Process/Task Description",
        "property": "AT_DESC",
    },
    {
        "title": "Type(historical)",
        "type": "SymbolName",
        "property": "AT_BPMN_TASK_TYPE_2",
    },
    {
        "title": "Lane",
        "type": "Glossary",
        "property": ["ST_ROLE_LANE", "ST_BPMN_LANE_1", "ST_GROUP_LANE", "ST_AST_LANE", "ST_ORGUNIT_LANE", "ST_POSITION_LANE"]
    },
    {
        "title": "Responsible",
        "property": ["ST_EMPL_TYPE", "ST_POS", "ST_ORG_PIC"],
        "type": "Glossary",
        "filter_by_cxn": ["CT_EXEC_2", "CT_EXEC_1", "CT_IS_RESP_1"]
    },
    {
        "title": "Accountable",
        "property": ["ST_EMPL_TYPE", "ST_POS", "ST_ORG_PIC"],
        "type": "Glossary",
        "filter_by_cxn": "CT_AGREES"
    },
    {
        "title": "Supports",
        "property": ["ST_EMPL_TYPE", "ST_POS", "ST_ORG_PIC"],
        "type": "Glossary",
        "filter_by_cxn": ["CT_SUPPORTS", "CT_SUPP_3"]
    },
    {
        "title": "Consulted",
        "property": ["ST_EMPL_TYPE", "ST_POS", "ST_ORG_PIC"],
        "type": "Glossary",
        "filter_by_cxn": ["CT_HAS_CONSLT_ROLE_IN_2", "CT_HAS_CONSLT_ROLE_IN_1"]
    },
    {
        "title": "Informed",
        "property": ["ST_EMPL_TYPE", "ST_POS", "ST_ORG_PIC"],
        "type": "Glossary",
        "filter_by_cxn": ["CT_MUST_BE_INFO_ABT_2", "CT_MUST_BE_INFO_ABT_1"]
    },
    {
        "title": "Called element",
        "property": "AT_BPMN_CALLED_ELEMENT",
    },
    {
        "title": "Process/Task Related Documents",
        "titleProperty": ["AT_TITL2", "AT_TITL1", "AT_TITL3", "AT_TITL4", "AT_IMAGE_TITL1", None, None, None, "AT_DOCUMENT_TITL1"],
        "linkProperty": ["AT_EXT_2", "AT_EXT_1", "AT_EXT_3", "AT_LINK", "AT_IMAGE_LINK_1", "AT_IMAGE_LINK_2", "AT_IMAGE_LINK_3", "AT_IMAGE_LINK_4", "AT_DOCUMENT_LINK_1"],
        "type": "DocumentURL"
    },
    {
        "title": "KPI",
        "property": "ST_KPI",
        "type": "Glossary"
    },
    {
        "title": "Applications",
        "property": "ST_APPL_SYS_TYPE",
        "type": "Glossary"
    },
    {
        "title": "Screens",
        "property": "ST_SCRN",
        "type": "Glossary"
    },
    {
        "title": "Policies",
        "property": "ST_DOC_KNWLDG_1",
        "type": "Glossary"
    },
    {
        "title": "Input Data",
        "property": ["ST_CLST", "ST_BPMN_DATA_INPUT", "ST_BPMN_DATA_STORE", "ST_ENT_TYPE"],
        "type": "Glossary",
        "filter_by_cxn": ["CT_BELONGS_TO_3", "CT_IS_INP_FOR", "CT_BPMN_IS_ASSOCIATED", "CT_IS_MAN_BY", "CT_LIES_ON", "CT_PROV_INP_FOR_1", "CT_PROV_INP_FOR", "CT_READ_1", "CT_READ_2" "CT_USE_3"]
    },
    {
        "title": "Output Data",
        "property": ["ST_CLST", "ST_BPMN_DATA_INPUT", "ST_BPMN_DATA_STORE", "ST_ENT_TYPE"],
        "type": "Glossary",
        "filter_by_cxn": ["CT_ARCH", "CT_CRT_5", "CT_CRT_OUT_TO", "CT_DISTR", "CT_HAS_OUT"]
    },
    {
        "title": "Input Documents",
        "property": ["ST_DOC", "ST_EMAIL_1"],
        "type": "Glossary",
        "filter_by_cxn": ["CT_BELONGS_TO_3", "CT_IS_INP_FOR", "CT_BPMN_IS_ASSOCIATED", "CT_IS_MAN_BY", "CT_LIES_ON", "CT_PROV_INP_FOR_1", "CT_PROV_INP_FOR", "CT_READ_1", "CT_READ_2", "CT_USE_3"]
    },
    {
        "title": "Output Documents",
        "property": ["ST_DOC", "ST_EMAIL_1"],
        "type": "Glossary",
        "filter_by_cxn": ["CT_ARCH", "CT_CRT_5", "CT_CRT_OUT_TO", "CT_DISTR", "CT_HAS_OUT"]
    },
    {
        "title": "Risk",
        "property": "ST_RISK_1",
        "type": "RiskControl"
    },
    {
        "title": "Objectives",
        "property": "ST_OBJCTV",
        "type": "Glossary"
    },
    {
        "title": "Requirements",
        "property": "ST_REQUIREMENT",
        "type": "Glossary"
    },
    {
        "title": "Has Control Point",
        "property": "e59853e1-1b05-11e5-4d0d-adcb4d40def0",
    },
    {
        "title": "Relevant for SAP",
        "property": "7a4b74a1-1b05-11e5-4d0d-adcb4d40def0",
    },
    {
        "title": "Relevant for WSS",
        "property": "89eaefd1-1b05-11e5-4d0d-adcb4d40def0",
    },
    {
        "title": "Task Sequence",
        "property": "4fc40441-1637-11ea-17e4-0050568c1fd6",
    }
]


def get_headers(items_attributes):
    headers = []
    for item in items_attributes:
        for attr in item:
            if attr.get("type") == "RiskControl":
                headers.append("Risk & Controls")

            headers.append(attr["title"])

            for gItem in attr.get("gloss_attrs", []):
                headers.append(gItem["title"])

            if attr.get("type") == "RiskControl":
                for gItem in attr.get("risk_attrs", []):
                    headers.append(gItem["title"])

                headers.append("Control")

                for gItem in attr.get("control_attrs", []):
                    headers.append(gItem["title"])

    return headers


def get_titles_links(item, c_item):
    urls = []
    for i in range(len(c_item["titleProperty"])):
        titleProp = c_item["titleProperty"][i]
        linkProp = c_item["linkProperty"][i]
        title = ""
        link = ""

        if titleProp is not None:
            title = amlquery.get_attr(item, titleProp)

        if linkProp is not None:
            link = amlquery.get_attr(item, linkProp)

        if title != "" and link != "":
            urls.append(title + " (" + link + ")")
        elif link != "":
            urls.append("(" + link + ")")

    if len(urls) == 0:
        urls.append("")

    return urls


def clean_and_format(input_values):
    def cleaner(value):
        if isinstance(value, list) or isinstance(value, tuple):
            return sorted(list(map(cleaner, value)))
        else:
            return str(value).replace("&amp;", "&").replace(" -> ", "=")

    input_values = map(cleaner, input_values)

    return [
        "|".join(value) if isinstance(value, list) else value for value in input_values
    ]


def get_risks_and_controls(risk_occs, config_item):
    def blank_risk_line():
        return [""] * (
            len(config_item.get("risk_attrs", []))
            + len(config_item.get("control_attrs", []))
            + 3  # risk -> controls, risk names, control names
        )

    risk_and_controls = []
    risks = []
    all_risks_attrs = []
    controls = []
    all_controls_attrs = []

    for risk_item in risk_occs:
        risk_title = amlquery.get_occ_name(risk_item)
        risks.append(risk_title)

        risk_attrs = []
        for gItem in config_item.get("risk_attrs", []):
            risk_attrs.append(amlquery.get_attr(risk_item, gItem.get("property")))

        all_risks_attrs.append(risk_attrs)

        controls_for_risk = []

        control_items = amlquery.get_connected_occs(risk_item, ctrlSymbol)
        if control_items:
            controls_for_risk = [amlquery.get_occ_name(occ) for occ in control_items]

            for control_item in control_items:
                control_attrs = []

                for gItem in config_item.get("control_attrs", []):
                    control_attrs.append(
                        amlquery.get_attr(control_item, gItem.get("property"))
                    )

                all_controls_attrs.append(control_attrs)
        else:
            controls_for_risk.append("")
            all_controls_attrs.append([""] * len(config_item.get("control_attrs", [])))

        controls_for_risk.sort()
        controls.extend(controls_for_risk)
        risk_and_controls.append(f"{risk_title}=({'|'.join(controls_for_risk)})")

    if not risk_and_controls:
        return blank_risk_line()

    all_risks_attrs = matrix_add_lists(all_risks_attrs)
    all_controls_attrs = matrix_add_lists(all_controls_attrs)

    return [
        risk_and_controls,
        risks,
        *all_risks_attrs,
        controls,
        *all_controls_attrs,
    ]


def matrix_add_lists(values_lists):
    # Caution: if any of the sublists are empty, eg. [["a"], []],
    # this function returns [] (because of zip) and all values are lost.
    return list(zip(*values_lists))


def get_model_fad_connected_occs(model):
    connected_occs = {}
    superior_func = amlquery.get_superior_defs(model["id"])

    if superior_func:
        superior_func = list(superior_func.values())[0]
        superior_fad = amlquery.get_assigned_models(superior_func, "MT_FUNC_ALLOC_DGM")

        if superior_fad:
            superior_fad = superior_fad[0]

            high_level_fad_func = amlquery.filter_occs_by_symbol(
                superior_fad, func_symbol_types
            )

            if high_level_fad_func:
                connected_occs = amlquery.get_connected_occs(
                    high_level_fad_func[0], superior_fad
                )

    return connected_occs


def get_func_connected_occs(func_occ):
    connected_occs = amlquery.get_connected_occs(func_occ)
    fad_func_occ = amlquery.get_fad_func_occ(func_occ, func_symbol_types)

    if fad_func_occ:
        fad_connected_occs = amlquery.get_connected_occs(fad_func_occ)
        connected_occs.extend(fad_connected_occs)

    return connected_occs, fad_func_occ


excel_wb = Workbook()
excel_ws = excel_wb.active

headers = get_headers([model_attrs, node_attrs])
excel_ws.append(headers)

models = amlquery.find_models(mdlTypes)

print("Generating report ...")
for model_id, model in models.items():
    funcs = amlquery.filter_occs_by_symbol(model, func_symbol_types)

    for func_occ in funcs:
        func_connected_occs, fad_func_occ = get_func_connected_occs(func_occ)

        row = []

        value = ""
        for item in model_attrs:
            if item.get("type") == "Path":
                value = model["path"]
                row.append(value)
            elif item.get("type") == "DocumentURL":
                values = get_titles_links(model, item)
                value = "|".join(sorted(values))
                row.append(value)
            elif item.get("type") == "Glossary":
                model_fad_connected_occs = get_model_fad_connected_occs(model)
                glossary_occs = amlquery.filter_occs_by_symbol(
                    model_fad_connected_occs, item["property"]
                )

                if glossary_occs:
                    values = [amlquery.get_occ_name(occ) for occ in glossary_occs]
                    value = "|".join(sorted(values))
                    row.append(value)

                    for gItem in item.get("gloss_attrs", []):
                        values = [
                            amlquery.get_attr(occ, gItem.get("property"))
                            for occ in glossary_occs
                        ]
                        value = "|".join(sorted(values))
                        row.append(value)
                else:
                    row.append("")
                    if "gloss_attrs" in item:
                        row.extend([""] * len(item["gloss_attrs"]))
            elif item.get("type") == "Dropdown":
                value = amlquery.get_attr(model, item["property"])
                value = dropdown_values.get(value, "")
                row.append(value)
            else:
                value = amlquery.get_attr(model, item["property"])
                row.append(value)

        for item in node_attrs:
            if item.get("type") == "Glossary":
                glossary_occs = amlquery.filter_occs_by_symbol(
                    func_connected_occs, item.get("property")
                )

                if glossary_occs:
                    if "filter_by_cxn" in item:
                        glossary_occs = amlquery.filter_occs_by_cxn(
                            [func_occ, fad_func_occ],
                            glossary_occs,
                            item.get("filter_by_cxn", ""),
                        )
                    # to print guid for checking
                    # values = [f"{api.get_occ_name(occ)} ({api.get_obj_def(occ).get('guid')})" for occ in glossary_occs]
                    values = [amlquery.get_occ_name(occ) for occ in glossary_occs]
                    value = "|".join(sorted(values))
                    row.append(value)

                    for gItem in item.get("gloss_attrs", []):
                        values = [
                            amlquery.get_attr(occ, gItem.get("property"))
                            for occ in glossary_occs
                        ]
                        value = "|".join(sorted(values))
                        row.append(value)
                else:
                    row.append("")
                    if "gloss_attrs" in item:
                        row.extend([""] * len(item["gloss_attrs"]))
            elif item.get("type") == "RiskControl":
                risk_occs = amlquery.filter_occs_by_symbol(
                    func_connected_occs, item.get("property")
                )
                values = get_risks_and_controls(risk_occs, item)
                value = clean_and_format(values)
                row.extend(value)
            elif item.get("type") == "DocumentURL":
                values = get_titles_links(func_occ, item)
                value = "|".join(sorted(values))
                row.append(value)
            elif item.get("type") == "SymbolName":
                if model['type'] == "MT_VAL_ADD_CHN_DGM":
                    value = func_occ.get("symbol")
                else:
                    value = amlquery.get_attr(func_occ, item.get("property"))
                value = func_symbol_type_to_name.get(value, "")
                row.append(value)
            else:
                value = amlquery.get_attr(func_occ, item.get("property"))
                row.append(value)

        excel_ws.append(row)

# df = pd.DataFrame(data)
# df.to_excel(f"Aris_Report_{timestamp}.xlsx", index=False, header=headers)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
report_filename = f"Aris_Report_{timestamp}.xlsx"
excel_wb.save(report_filename)
excel_wb.close()