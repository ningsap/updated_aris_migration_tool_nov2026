import os.path
import pickle
import sys
import time

from amlparser.amlparser import AMLParser


class AMLQuery:
    def __init__(self, aml_filename, force_parse=False):
        data = {}
        pickle_filename = f"{os.path.splitext(aml_filename)[0]}.pickle"

        if force_parse:
            AMLParser().parse_aml(aml_filename)

        try:
            with open(pickle_filename, "rb") as f:
                data = pickle.load(f)

            modified_time = os.path.getmtime(pickle_filename)
            date_time = time.ctime(modified_time)

            from_aml_filename = data.get("info", {}).get("GeneratedFrom")
            if from_aml_filename == aml_filename:
                print(
                    f"Opened '{pickle_filename}' (last modified: {date_time})")
                print(f"Data File Info: {data.get('info', {})}")
            else:
                raise SystemExit(
                    f"Error: Existing '{pickle_filename}' was generated from a diffirent AML file: '{from_aml_filename}'. "
                    "Pass 'force_parse=True' to AMLQuery init to overwrite the existing data file "
                    f"or provide correct '{pickle_filename}' file.")
        except FileNotFoundError:
            try:
                data = AMLParser().parse_aml(aml_filename)

                modified_time = os.path.getmtime(pickle_filename)
                date_time = time.ctime(modified_time)

                print(
                    f"Opened '{pickle_filename}' (last modified: {date_time})")
                print(f"Data File Info: {data.get('info', {})}")
            except Exception as e:
                print(e)
                raise SystemExit(
                    f"Error: No valid AML filename provided and did not find an existing '{pickle_filename}' file to open")
        finally:
            if data:
                self.__set_data(data)

    def __open_data_file(self, aml_filename):
        data = None

    def __set_data(self, data):
        self.cxns = data["cxns"]
        self.defs = data["defs"]
        self.models = data["models"]
        self.def_to_models = data["def_to_models"]
        self.groups = data["groups"]

    def parse_aml(self, aml_filename):
        AMLParser().parse_aml(aml_filename)

    def get_attr(self, item, attr):
        if item.get("aris_type") in ["Model", "ObjDef"]:
            return item.get("attrs", {}).get(attr, "")
        elif item.get("aris_type") == "ObjOcc":
            return self.get_obj_def(item).get("attrs", {}).get(attr, "")

    def get_obj_def(self, occ):
        return self.defs.get(occ["def"], {})

    def get_occ_name(self, occ):
        return self.get_obj_def(occ).get("name", "")

    def get_superior_defs(self, model_id):
        superior_defs = {}

        for obj_def_id, models in self.def_to_models.items():
            if model_id in models:
                superior_defs[obj_def_id] = self.defs[obj_def_id]

        return superior_defs

    def get_assigned_models(self, item, model_types=None):
        if item.get("aris_type") == "ObjDef":
            obj_def = item
        else:
            obj_def = self.get_obj_def(item)

        if model_types is None:
            return [self.models[model_id] for model_id in obj_def.get("linked_models", []) if model_id in self.models]
        else:
            model_types = model_types if isinstance(
                model_types, list) else [model_types]
            return [self.models[model_id] for model_id in obj_def.get("linked_models", []) if self.models.get(model_id, {}).get("type") in model_types]

    # gets the assigned FAD's func occ
    def get_fad_func_occ(self, func_occ, symbols=None, fad_type="MT_FUNC_ALLOC_DGM"):
        fads = self.get_assigned_models(func_occ, fad_type)

        fad_func_occ = {}
        if fads:
            fad = fads[0]
            fad_func_occs = self.filter_occs_by_symbol(fad, symbols)
            fad_func_occs = [
                occ for occ in fad_func_occs if occ["def"] == func_occ["def"]]
            if fad_func_occs:
                fad_func_occ = fad_func_occs[0]

        return fad_func_occ

    def get_connections(self, item, direction="both"):
        if direction == "in":
            return item.get("incoming_cxns", {})
        elif direction == "out":
            return item.get("outgoing_cxns", {})
        else:
            return item.get("incoming_cxns", {}) | item.get("outgoing_cxns", {})

    def get_connected_occs(self, occ, symbols=None, direction="both"):
        connected_occs = []

        model = self.models.get(occ.get("model_id"))
        if model:
            occs = model.get("occs", {})
        else:
            occs = {}

        occ_cxns = self.get_connections(occ, direction)
        connected_occs = [occs[occ_id]
                          for occ_id in occ_cxns.keys() if occ_id in occs]

        if symbols is None:
            return connected_occs
        else:
            symbols = symbols if isinstance(symbols, list) else [symbols]
            return [occ for occ in connected_occs if occ.get("symbol") in symbols]

    def find_models(self, model_types=None):
        if model_types is None:
            return self.models
        else:
            model_types = model_types if isinstance(
                model_types, list) else [model_types]
            return {model_id: model_data for model_id, model_data in self.models.items() if model_data.get("type") in model_types}

    # can take multiple func occs and filter by connected symbol type and connection type (eg. func on EPC and FAD with their connected symbols by connection type)
    def filter_occs_by_cxn(self, func_occs, occs_to_filter, symbols=None):
        if symbols is None:
            return occs_to_filter
        else:
            func_occs = func_occs if isinstance(
                func_occs, list) else [func_occs]
            symbols = symbols if isinstance(symbols, list) else [symbols]

            filtered_occs = []

            for in_occ in occs_to_filter:
                occ_cxns = self.get_connections(in_occ)

                for func_occ in func_occs:
                    func_id = func_occ["id"]

                    if func_id in occ_cxns:
                        for connection in occ_cxns[func_id]:
                            cxn_def_id = connection.get('cxn_def_id')
                            cxn_def = self.cxns.get(cxn_def_id)
                            if cxn_def.get("type") in symbols:
                                filtered_occs.append(in_occ)

            return filtered_occs

    def filter_occs_by_symbol(self, item_or_occs, symbols=None):
        if isinstance(item_or_occs, dict):
            if item_or_occs.get("aris_type") in ["Model", "ObjDef"]:
                occs = item_or_occs.get("occs", {}).values()
            else:
                occs = []
        else:
            occs = item_or_occs

        if symbols is None:
            return occs
        else:
            symbols = symbols if isinstance(symbols, list) else [symbols]
            return [occ for occ in occs if occ.get("symbol") in symbols]
