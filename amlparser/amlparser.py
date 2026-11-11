import copy
import datetime
import os.path
import pickle
import re

import lxml.etree as ET
import html
import yaml
import time


class AMLParser:
    def __init__(self):
        self.cxns = {}
        self.defs = {}
        self.txt_defs = {}
        self.models = {}
        self.def_to_models = {}
        self.path = []
        self.info = {}
        self.groups = {}
        self.cxn_occs = {}

        # read yaml file language codes
        language_codes_path = 'amlparser/language_codes.yaml'
        self.language_codes = self.read_config(language_codes_path)

    def read_config(self, file_path):
        with open(file_path) as file:
            cfg = yaml.load(file, Loader=yaml.FullLoader)
        return cfg

    def parse_aml(self, aml_filename, force_parse=True):
        pickle_filename = f"{os.path.splitext(aml_filename)[0]}.pickle"

        if not force_parse and os.path.exists(pickle_filename):
            
            print(f"Loading cached data from '{pickle_filename}' ...")
            with open(pickle_filename, "rb") as f:
                data = pickle.load(f)
            self.cxns = data["cxns"]
            self.defs = data["defs"]
            self.def_to_models = data.get("def_to_models", {})
            self.models = data["models"]
            self.groups = data["groups"]
            self.txt_defs = data.get("txt_defs", {})
            modified_time = os.path.getmtime(pickle_filename)
            print(f"Data File Info: {data.get('info', {})} (last modified: {time.ctime(modified_time)})")
            return data
        
        print(f"Parsing AML file '{aml_filename}' ...")

        context = ET.iterparse(aml_filename, ("start", "end"), huge_tree=True)
        self.low_memory_iter(context)

        data = {
            "cxns": self.cxns,
            "defs": self.defs,
            # mapping of each def the models it's assigned to
            "def_to_models": self.def_to_models,
            "models": self.models,
            "groups": self.groups,
            "txt_defs": self.txt_defs,
            "info": {
                "GeneratedFrom": aml_filename,
                "Created": datetime.datetime.now().isoformat(),
                "Counts": {
                    "Models": len(self.models),
                    "Defs": len(self.defs),
                    "Cxns": len(self.cxns),
                },
            }
        }

        print(f"Writing '{pickle_filename}' ...")
        with open(pickle_filename, "wb") as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

        return data

    def parse_attr_defs(self, item):
        attrs = {}
        attrs['styles'] = {}
        attr_defs = item.findall("AttrDef")
        for attr in attr_defs:
            plain_text = attr.findall(".//PlainText")

            def traverse(element, result):
                if element is None:
                    return
                for child in element:
                    if child.tag == 'PlainText':
                        text_value = child.attrib.get('TextValue', '')
                        attr_text.append(text_value)
                        if 'Enumeration_Type' in current_styles:
                            if current_styles['Enumeration_Type'] == 'ORDERED':
                                text_value = '<li>' + text_value + '</li>'
                            elif current_styles['Enumeration_Type'] == 'UNORDERED':
                                text_value = '<li>' + text_value + '</li>'
                        result.append(text_value)
                    elif child.tag == 'StyledElement':
                        traverse(child, result)
                    elif child.tag == 'Enumeration':
                        current_styles['Enumeration_Type'] = child.attrib.get('Type', 'Unknown')
                        if current_styles['Enumeration_Type'] == 'ORDERED':
                            result.append('<ol>')
                        elif current_styles['Enumeration_Type'] == 'UNORDERED':
                            result.append('<ul>')
                        elif current_styles['Enumeration_Type'] == 'UNORDERED':
                            result.append('<ul>')
                    elif child.tag == 'Paragraph':
                        current_styles['Paragraph_Alignment'] = child.attrib.get('Alignment', 'Unknown')
                    elif child.tag == 'Bold':
                        current_styles['Bold'] = True
                        if current_styles['Bold']:
                            result.append('<b>')
                    elif child.tag == 'Italic':
                        current_styles['Italic'] = True
                        if current_styles['Italic']:
                            result.append('<i>')

                if element.tag == 'StyledElement':
                    check_enum = element.find('Enumeration')
                    if check_enum is not None:
                        enum_type = check_enum.attrib.get('Type', 'Unknown')
                        if enum_type == 'ORDERED':
                            result.append('</ol>')
                            current_styles.pop('Enumeration_Type', None)  # Remove after handling
                        elif enum_type == 'UNORDERED':
                            result.append('</ul>')
                            current_styles.pop('Enumeration_Type', None)  # Remove after handling
                    check_bold = element.find('Bold')
                    if check_bold is not None:
                        result.append('</b>')
                        current_styles.pop('Bold', None)  # Remove after handling
                    check_italic = element.find('Italic')
                    if check_italic is not None:
                        result.append('</i>')
                        current_styles.pop('Italic', None)  # Remove after handling
                    check_paragraph = element.find('Paragraph')
                    if check_paragraph is not None:
                        # result.append('<br>')
                        current_styles.pop('Paragraph', None)  # Remove after handling
                        result.append('\n')
                        attr_text.append('\n')

            attr_vals = attr.findall("AttrValue")
            for attr_val in attr_vals:
                attr_text = []
                locale_id = attr_val.get('LocaleId', None)
                if locale_id:
                    locale_id = int(locale_id)

                current_styles = {}
                result = []
                traverse(attr_val, result)
                result_styled_text = ''.join(result)
                attr_text = "".join([val for val in attr_text if val])
                result_styled_text = html.unescape(result_styled_text)
                attr_text = html.unescape(attr_text)
                non_printable_pattern = re.compile(r'[^\x20-\x7E\xA0-\xFF\u0100-\u017F\n\r]')
                result_styled_text = non_printable_pattern.sub('', result_styled_text)
                attr_text = non_printable_pattern.sub('', attr_text)

                if attr.get("AttrDef.Type") not in attrs:
                    attrs[attr.get("AttrDef.Type")] = {}

                if attr.get("AttrDef.Type") not in attrs['styles']:
                    attrs['styles'][attr.get("AttrDef.Type")] = {}

                if attr_text:
                    attrs[attr.get("AttrDef.Type")][self.language_codes.get(locale_id, '')] = attr_text.strip()

                else:
                    attr_value = attr.find(".//AttrValue")
                    if attr_value is not None and attr_value.text is not None:
                        attrs[attr.get("AttrDef.Type")][self.language_codes.get(locale_id, '')] = attr_value.text.strip()

                    else:
                        attrs[attr.get("AttrDef.Type")][self.language_codes.get(locale_id, '')] = ""

                attrs['styles'][attr.get("AttrDef.Type")][self.language_codes.get(locale_id, '')] = result_styled_text

        return attrs

    def parse_cxn_occs(self, item):
        occ_cxns = {}

        cxn_occs = item.findall("CxnOcc")
        for cxn in cxn_occs:
            connected_to = cxn.get("ToObjOcc.IdRef")
            occ_id = cxn.get("CxnOcc.ID")

            position = cxn.findall("Position") if cxn.findall("Position") is not None else []
            if position:
                position = [{'x': pos.get('Pos.X'), 'y': pos.get('Pos.Y')} for pos in cxn.findall("Position")]
                if len(position) == 1:
                    position = position[0]
            
            occ_cxns.setdefault(connected_to, []).append(
                {
                    'cxn_def_id': cxn.get("CxnDef.IdRef"),
                    'cxn_occ_id': occ_id,
                    'position': position
                }
            )
            # occ_cxns[connected_to] = cxn.get("CxnDef.IdRef")
            cxn_def_id = cxn.get("CxnDef.IdRef")
            # self.cxn_occs[cxn_def_id] = occ_id
            if cxn_def_id in self.cxn_occs:
                self.cxn_occs[cxn_def_id].append(
                    {
                        'cxn_occ_id': occ_id,
                        'connected_to_obj': connected_to,
                        'position': position
                    }
                )
            else:
                self.cxn_occs[cxn_def_id] = [
                    {
                        'cxn_occ_id': occ_id,
                        'connected_to_obj': connected_to,
                        'position': position
                    }
                ]

        return occ_cxns

    def parse_obj_occs(self, item):
        occs = {}
        cnxn_occs = {}

        obj_occs = item.findall("ObjOcc")
        for occ in obj_occs:
            id = occ.get("ObjOcc.ID")
            occ_cxns = self.parse_cxn_occs(occ)
            for key, values in occ_cxns.items():
                for value in values:
                    cnxn_occs[value['cxn_occ_id']] = value['position']
            symbol_GUID = occ.find("SymbolGUID")

            position = occ.findall("Position") if occ.findall("Position") is not None else []
            size = occ.findall("Size") if occ.findall("Size") is not None else []

            if position:
                position = [{'x': pos.get('Pos.X'), 'y': pos.get('Pos.Y')} for pos in occ.findall("Position")]
                if len(position) == 1:
                    position = position[0]
            if size:
                size = [{'dx': sze.get('Size.dX'), 'dy': sze.get('Size.dY')} for sze in occ.findall("Size")]
                if len(size) == 1:
                    size = size[0]

            new_values = {
                "id": id,
                "def": occ.get("ObjDef.IdRef", ""),
                "outgoing_cxns": occ_cxns,
                "path": "/".join(self.path),
                "model_id": item.get("Model.ID"),
                "aris_type": "ObjOcc",
                "position": position,
                "size": size
            }

            if symbol_GUID is not None:
                new_values["symbol"] = symbol_GUID.text
                new_values["derived_symbol"] = occ.get("SymbolNum", "")
            else:
                new_values["symbol"] = occ.get("SymbolNum", "")

            if id in occs:
                occs[id].update(new_values)
            else:
                occs[id] = new_values

            for obj_occ_id, cxn_def_ids in occ_cxns.items():
                occs.setdefault(obj_occ_id, {}).setdefault(
                    "incoming_cxns", {})[id] = cxn_def_ids

        return occs, cnxn_occs

    def parse_txt_occs(self, item):
        txt_occs = {}

        fftext_occs = item.findall("FFTextOcc")
        for occ in fftext_occs:
            id = occ.get("FFTextDef.IdRef")
            if id and id not in txt_occs:
                txt_occs[id] = {
                    "def_id": occ.get("FFTextDef.IdRef"),
                    "occ_id": occ.get("FFTextOcc.ID")
                }

        return txt_occs

    def parse_txt_defs(self, item):
        txt_defs = {}

        id = item.get("FFTextDef.ID")
        guid = item.find("GUID")
        if guid:
            guid = guid.text
        else:
            guid = ''
        attrs = self.parse_attr_defs(item)

        new_values = {
            "id": id,
            "name": attrs.get("AT_NAME", ""),
            "guid": guid,
            "attrs": attrs,
            "path": "/".join(self.path),
            "aris_type": "FFTextDef",
        }
        if id:
            if id in self.txt_defs:
                self.txt_defs[id].update(new_values)
            else:
                self.txt_defs[id] = new_values

        return txt_defs

    def parse_cxn_defs(self, item):
        obj_cxns = {}

        cxn_defs = item.findall("CxnDef")
        for cxn in cxn_defs:
            id = cxn.get("CxnDef.ID")
            connected_to = cxn.get("ToObjDef.IdRef")
            attrs = self.parse_attr_defs(cxn)
            obj_cxns[connected_to] = {
                "id": id,
                "type": cxn.get("CxnDef.Type"),
            }

            self.cxns[id] = {
                "def": item.get("ObjDef.ID"),
                "type": cxn.get("CxnDef.Type"),
                "connected_to": connected_to,
                "attrs": attrs
            }

        return obj_cxns

    def parse_obj_defs(self, item):
        obj_defs = item.findall("ObjDef")
        for obj in obj_defs:
            id = obj.get("ObjDef.ID")
            guid = obj.find("GUID").text
            linked_models = re.sub(
                "\s+", " ", obj.get("LinkedModels.IdRefs", "")).strip().split()
            attrs = self.parse_attr_defs(obj)
            def_cxns = self.parse_cxn_defs(obj)

            new_values = {
                "id": id,
                "name": attrs.get("AT_NAME", ""),
                "guid": guid,
                "type": obj.get("TypeNum", ""),
                "symbol": obj.get("SymbolNum", ""),
                "attrs": attrs,
                "linked_models": linked_models,
                "outgoing_cxns": def_cxns,
                "path": "/".join(self.path),
                "aris_type": "ObjDef",
            }
            if id in self.defs:
                self.defs[id].update(new_values)
            else:
                self.defs[id] = new_values

            self.def_to_models.setdefault(id, []).extend(linked_models)

            for obj_def_id, cxn_def_type in def_cxns.items():
                self.defs.setdefault(obj_def_id, {}).setdefault(
                    "incoming_cxns", {})[id] = cxn_def_type

    def parse_models(self, item):
        obj_models = item.findall("Model")
        for model in obj_models:
            id = model.get("Model.ID")
            attrs = self.parse_attr_defs(model)
            occs, cxn_occs = self.parse_obj_occs(model)
            txt_occs = self.parse_txt_occs(model)
            guid = model.find("GUID").text
            creator = model.get("Creator")
            # TODO make this nicer
            try:
                derived_type = model.find("TypeGUID").text
            except:
                derived_type = None
            parent_element = model.getparent()
            if len(parent_element) != 0:
                parent_id = parent_element.get("Group.ID")
            else:
                parent_id = ""
            self.models[id] = {
                "id": id,
                "name": attrs.get("AT_NAME", ""),
                "guid": guid,
                "type": model.get("Model.Type"),
                "derived_type": derived_type,
                "parent_id": parent_id,
                "attrs": attrs,
                "occs": occs,
                "txt_occs": txt_occs,
                "path": "/".join(self.path),
                "aris_type": "Model",
                "model_creator": creator,
                "cxn_occs": cxn_occs,
                "scale": int(model.get("Scale", 100)),
            }

    def parse_groups(self, item):
        obj_groups = item.xpath('//Group')
        for group in obj_groups:
            id = group.get("Group.ID")
            if id != "Group.Root" and id is not None:
                attrs = self.parse_attr_defs(group)
                if id not in self.groups:
                    guid = group.find("GUID")
                    if guid is not None:
                        guid = group.find("GUID").text
                    else:
                        guid = ''
                        print(f'ERROR: GUID not available for Group {id}')
                    parent_element = group.getparent()
                    child_folder = group.findall('.//Group')
                    child_model = group.findall('.//Model')
                    has_child = False
                    if len(child_folder) != 0 or len(child_model) != 0:
                        has_child = True
                    if len(parent_element) != 0:
                        parent_id = parent_element.get("Group.ID")
                    else:
                        parent_id = ""
                    self.groups[id] = {
                        "id": id,
                        "name": attrs.get("AT_NAME", ""),
                        "guid": guid,
                        "attrs": attrs,
                        "parent_id": parent_id,
                        "has_child": has_child,
                        "aris_type": "Group",
                    }
                elif id in self.groups and self.groups.get(id, {}).get("name", '') == '' and attrs.get('AT_NAME', '') != '':
                    guid = group.find("GUID")
                    if guid is not None:
                        guid = group.find("GUID").text
                    else:
                        guid = ''
                        print(f'ERROR: GUID not available for Group {id}')
                    parent_element = group.getparent()
                    child_folder = group.findall('.//Group')
                    child_model = group.findall('.//Model')
                    has_child = False

                    if len(child_folder) != 0 or len(child_model) != 0:
                        has_child = True
                    if len(parent_element) != 0:
                        parent_id = parent_element.get("Group.ID")
                    else:
                        parent_id = ""

                    if self.groups[id].get('guid', '') == '':
                        self.groups[id]["guid"] = guid
                    if self.groups[id].get('name', '') == '':
                        self.groups[id]["name"] = attrs.get("AT_NAME", "")
                        self.groups[id]["attrs"] = attrs
                    if self.groups[id].get('parent_id', '') == '':
                        self.groups[id]["parent_id"] = parent_id
                    if self.groups[id].get('has_child', '') is False and has_child:
                        self.groups[id]["has_child"] = has_child

    def low_memory_iter(self, context):
        in_group_start = False

        for event, element in context:
            # if event == "start" and element.tag == "Group" and element.get("Group.ID") == "Group.Root":
            # self.parse_groups(element)

            if event == "start" and element.tag == "Group" and element.get("Group.ID") != "Group.Root":
                in_group_start = True
                # self.parse_groups(element)

            if in_group_start and event == "end" and element.tag == "AttrDef":
                parent = element.getparent()
                attr = self.parse_attr_defs(parent)
                at_name = attr.get("AT_NAME", {})
                current_path = next(iter(at_name.values()), "") if isinstance(at_name, dict) else at_name
                self.path.append(current_path)
                self.parse_groups(parent)
                in_group_start = False

            if event == "end" and element.tag == 'FFTextDef':
                self.parse_txt_defs(element)

            if event == "end" and element.tag == "Group":
                self.parse_obj_defs(element)
                self.parse_models(element)

                if len(self.path) > 0:
                    self.path.pop()

                element.clear()

                for ancestor in element.xpath("ancestor-or-self::*"):
                    if ancestor.tag == "AML":
                        continue

                    while ancestor.getprevious() is not None:
                        del ancestor.getparent()[0]
        del context