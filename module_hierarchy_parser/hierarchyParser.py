from alloy.logging.logger_utility import logger

class HierarchyParser:
    def __init__(self, cfg, groups, models):
        self.cfg = cfg
        self.groups = groups
        self.models = models
        self.hierarchy = {}

        # read from config default workspace language
        self.default_workspace_language = self.cfg.get('default_workspace_language')
        if not self.default_workspace_language:
            logger.error('CONFIG MISSING! Please add default_workspace_language config')

    def transform_name(self, data):
        default_key = self.default_workspace_language
        result = {}
        for key, value in data.items():
            if key == default_key:
                result["name"] = value
            else:
                result[f"name_{key}"] = value

        return result

    def parse_hierarchy(self):
        diagram_mapping = self.cfg.get('diagram_mapping')

        # Init
        # Keep all groups that are ancestors of any model (transitive walk up the pid chain) 
        group_parent_index = {v.get('id'): v.get('parent_id') for v in self.groups.values()}
        ancestor_ids = set()
        for model in self.models.values():
            pid = model.get('parent_id')
            while pid and pid not in ancestor_ids:
                ancestor_ids.add(pid)
                pid = group_parent_index.get(pid)
        elements = {k: v for k, v in self.groups.items() if v.get('aris_type') == 'Group' and v.get('id') in ancestor_ids}
        elements.update(self.models)

        # Get library id
        library_id = list(filter(lambda a: elements[a]['name'] == 'Library', elements))
        if library_id:
            library_id = elements[library_id[0]].get("id", "")
        else:
            library_id = ""

        unknown_diagram_types = []
        # Map Directories / Models
        for element_key in elements:
            element = elements.get(element_key)
            aris_type = element.get("aris_type")
            if aris_type == 'Group':
                object_type = 'dir'
            elif aris_type == 'Model':
                diagram_type = element.get("type")
                if diagram_type in diagram_mapping:
                    object_type = diagram_mapping[diagram_type]
                else:
                    if diagram_type != "MT_FUNC_ALLOC_DGM" and diagram_type not in unknown_diagram_types:
                        unknown_diagram_types.append(diagram_type)
                    object_type = diagram_type

            # Filter library and library items
            # Differentiation between directories and library objects by parent_id = library_id
            if element.get("type") != "MT_FUNC_ALLOC_DGM" and element.get("parent_id") != library_id and element.get('id') != library_id:

                # Add object and attributes to hierarchy_dict
                object_id = element.get("id", "")
                if object_id:
                    # get name
                    attr_name = element.get("name", "")
                    # check language
                    if attr_name:
                        attr_name = self.transform_name(attr_name)
                    else:
                        attr_name = {'name': element.get("guid", "")}
                    item = {'guid': element.get("guid", ""),  # globally unique identifier
                            "pid": element.get("parent_id"),
                            "type": object_type,
                            "has_child": element.get("has_child", False)
                            }
                    item = item | attr_name

                    self.hierarchy[object_id] = item
                else:
                    logger.warning(f'HierarchyParser: NO ID --> INVESTIGATE: {str(element)}')

        # self.hierarchy = hierarchy_dict
        logger.error(f'Check for Configuration if any Unknown Diagram Type need to be added for config: {unknown_diagram_types}')
        logger.info(f'Hierarchy Parsing done \n Total Elements (Folders and Models) : {len(self.hierarchy.keys())}')
