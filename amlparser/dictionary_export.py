import csv
import os

from amlquery import AMLQuery

amlquery = AMLQuery('../input/ARISAMLExportExample.xml', force_parse=True)

model_types = [
    "MT_ENTERPRISE_BPMN_COLLABORATION",
    "MT_ENTERPRISE_BPMN_PROCESS",
    "MT_VAL_ADD_CHN_DGM",
    "MT_BPMN_COLLABORATION_DIAGRAM",
]
excluded_obj_types = ["OT_EVT", "OT_RULE"]


# These system attributes are not parsed as standard
# "AT_CREATOR", "AT_CREAT_TIME_STMP", "AT_LAST_CHNG_2", "AT_LUSER"


symbol_dict = {}

for model_id, model_data in amlquery.models.items():
    if model_data["type"] in model_types:
        for occ_id, occ_data in model_data["occs"].items():
            occ_def = amlquery.get_obj_def(occ_data)

            if occ_def["type"] not in excluded_obj_types:
                occ_def_attrs = {
                    k: v for k, v in occ_def["attrs"].items() if k != "AT_NAME"
                }

                if occ_data["symbol"] in symbol_dict:
                    symbol_dict[occ_data["symbol"]]["columns"].update(occ_def_attrs)
                    symbol_dict[occ_data["symbol"]]["defs"][occ_def["guid"]] = {
                        k: v
                        for k, v in occ_def.items()
                        if k in ["name", "path", "attrs"]
                    }
                else:
                    symbol_dict[occ_data["symbol"]] = {
                        "derived_symbol": occ_data.get("derived_symbol"),
                        "columns": set(occ_def_attrs),
                        "defs": {
                            occ_def["guid"]: {
                                k: v
                                for k, v in occ_def.items()
                                if k in ["name", "path", "attrs"]
                            }
                        },
                    }

for symbol, data in symbol_dict.items():
    columns = sorted(data["columns"])
    table = [["Name", "Group Path", "GUID", "Derived Symbol"] + columns]

    occ_defs = dict(sorted(data["defs"].items(), key=lambda x: x[1]["name"]))
    for guid, def_data in occ_defs.items():
        row = [
            def_data["name"],
            def_data["path"],
            guid,
            data["derived_symbol"],
        ]
        for col in columns:
            row.append(def_data["attrs"].get(col, ""))

        table.append(row)

    os.makedirs("output", exist_ok=True)
    with open(f"output/{symbol}.csv", "w", newline="") as f:
        writer = csv.writer(f, delimiter="|", dialect="excel", quoting=csv.QUOTE_ALL)
        writer.writerows(table)
