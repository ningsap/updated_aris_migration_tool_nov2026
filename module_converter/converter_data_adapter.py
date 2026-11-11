# External
import json
import copy

# Modules
from vc_model_builder.vc_model_builder import ModelBuilder
from diagramforge.diagramforge import DiagramForge
from alloy.task_watch.task_watch import TaskWatch
from alloy.file_handler.json_files import read_json_file, write_json_file
from alloy.logging.logger_utility import logger


class ConverterDataAdapter():
    def __init__(self, cfg, file_tracker: TaskWatch, dictionary_tracker: TaskWatch):
        self.FT_Models = file_tracker
        self.template_signavio_shape_data = read_json_file("template_signavio_shape_data.json", "input")
        self.json_converted_models_file_path = cfg.get('file_path_converted_models_json')
        self.diagram_language = cfg.get('default_workspace_language')
        self.dictionary_tracker = dictionary_tracker

        try:
            with open(self.json_converted_models_file_path, 'r') as json_file:
                self.models = json.load(json_file)
        except:
            logger.error(f'ModelCreator Import: {self.json_converted_models_file_path} does not exist')
        
        
        # Prepare signavio_id to aris_guid mapping from dictionary_tracker
        self.dictionary_signavio_to_aris_guid = {}

        for record, data in self.dictionary_tracker.yield_filtered_records():
            signavio_id = data.get("signavio_id")
            aris_guid = record.id
            if signavio_id and aris_guid:
                self.dictionary_signavio_to_aris_guid[signavio_id] = aris_guid

        # Write the mapping to a JSON file
        if self.dictionary_signavio_to_aris_guid:
            write_json_file(self.dictionary_signavio_to_aris_guid, 'dictionary_signavio_to_aris_guid_mapping.json', 'output')


    def find_lane_for_shape(self, shape: dict, model_data: dict, visited_shapes: set = None) -> str:
        """
        Recursively find appropriate lane for a shape by checking both predecessors and successors.

        Args:
            shape: The shape to find a lane for
            model_data: Complete model data containing all shapes
            visited_shapes: Set of already visited shape IDs to prevent infinite loops

        Returns:
            str: Lane ID or 'Fallback_Lane' if no appropriate lane found
        """
        if visited_shapes is None:
            visited_shapes = set()

        shape_id = shape.get('resourceId', '')
        if shape_id in visited_shapes:
            return 'Fallback_Lane'
        visited_shapes.add(shape_id)

        # If shape already has a valid parent lane, return it
        parent = shape.get('parent', '')
        shape_type = shape.get('stencil', {}).get('id')
        if parent and 'Event' not in shape_type and 'Gateway' not in shape_type and 'SequenceFlow' != shape_type:
            return parent
        # if parent and parent != 'Fallback_Lane':
        #    return parent

        shapes = model_data.get('shapes', {})

        # Check predecessors first
        incoming_flows = shape.get('predecessor', [])
        for incoming_key in incoming_flows:
            source_shape = shapes.get(incoming_key)
            if source_shape:
                lane_id = self.find_lane_for_shape(source_shape, model_data, visited_shapes)
                if lane_id and lane_id != 'Fallback_Lane':
                    return lane_id

        # If no lane found through predecessors, check successors
        outgoings = shape.get('outgoing', [])
        for outgoing_key in outgoings:
            outgoing_key = outgoing_key.get('resourceId')
            target_shape = shapes.get(outgoing_key)
            if target_shape:
                lane_id = self.find_lane_for_shape(target_shape, model_data, visited_shapes)
                if lane_id and lane_id != 'Fallback_Lane':
                    return lane_id

        return 'Fallback_Lane'

    def convert_to_bpmn_model_json(self, model_data):
        # convert converter data into signavio format canvas and respective childshapes
        # for events, gateways if there is no parent assigned,
        # put the shape in the same lane as the first sucessor with a parent
        # get pool
        shapes = model_data.get('shapes', {})
        text_annotations_and_connections = {}

        # extra keys to remove
        list_of_extra_keys = ["type", "aris_id", "aris_guid", "name", "predecessor", "def_id", "aris_symbol_type", "parent"]
        if shapes:
            pools = list(filter(lambda shape_key: shapes[shape_key].get('stencil', {}).get('id', '') == 'Pool', shapes))
            check = list(filter(lambda shape_key: shapes[shape_key].get('stencil', {}).get('id', '') == 'ProcessCollapsed', shapes))
            if len(check) > 0:
                print(check)
            if len(pools) > 0:
                pool = shapes[pools[0]]
            else:
                pool = shapes.get('Pool', None)
                if pool == None:
                    pool = copy.deepcopy(self.template_signavio_shape_data.get('Pool'))
                    pool["resourceId"] = 'MissingPoolFromSourceData'
                    pool["properties"]['name'] = 'MissingPoolFromSourceData'
            sequence_flows = list(filter(lambda shape_key: shapes[shape_key].get('stencil', {}).get('id', '') == 'SequenceFlow', shapes))

            lanes = list(filter(lambda shape_key: shapes[shape_key].get('stencil', {}).get('id', '') == 'Lane', shapes))

            # Get keys of text annotations
            text_annotation_keys = [shape_key for shape_key in shapes if shapes[shape_key].get('stencil', {}).get('id', '') == 'TextAnnotation']
            for key in text_annotation_keys:
                # Save the text annotation shape
                text_annotations_and_connections[key] = copy.deepcopy(shapes[key])
                outgoings = shapes[key].get('outgoing', [])
                for outgoing in outgoings:
                    conn_key = outgoing.get('resourceId', '')
                    conn_shape = shapes.get(conn_key)
                    text_annotations_and_connections[key] = copy.deepcopy(conn_shape)
                    if conn_shape:
                        outgoings_of_conn = conn_shape.get('outgoing', [])
                        # check outgoing shapes and remove the connection key from the predecessor of the shape
                        for out in outgoings_of_conn:
                            target_key = out.get('resourceId', '')
                            target_shape = shapes.get(target_key)
                            if target_shape:
                                # remove the conn_key from the predecessor of shape.get(target_key)
                                predecessor_list = target_shape.get('predecessor', [])
                                predecessor_list = [p for p in predecessor_list if p != conn_key]
                                target_shape['predecessor'] = predecessor_list

                        # delete the target connection
                        shapes.pop(conn_key, None)
                # delete the text annotation
                shapes.pop(key, None)

            for lane_key in lanes:
                # get shapes belong to lane
                child_shapes = list(filter(lambda shape_key: shapes[shape_key].get('stencil', {}).get(
                    'id', '') not in ('Pool', 'Lane', 'SequenceFlow') and shapes[shape_key].get('parent', '') == lane_key, shapes))
                if child_shapes:
                    child_shape_objs = [shapes[key] for key in child_shapes]
                    shapes[lane_key]["childShapes"] = copy.deepcopy(child_shape_objs)

            # create fallback lane
            fallback_lane = copy.deepcopy(self.template_signavio_shape_data.get('Lane'))
            fallback_lane["resourceId"] = 'Fallback_Lane'
            fallback_lane["properties"]['name'] = 'Unassigned'

            # check remaining shapes without parent
            # for events, gateways, check successor and put it into same lane
            shapes_without_lane = list(filter(lambda shape_key: shapes[shape_key].get('parent', '') in ['', 'Fallback_Lane'] and shapes[shape_key].get(
                'stencil', {}).get('id', '') not in ['SequenceFlow', 'Lane', 'Pool'], shapes))
            fallback_shapes = []
            for shape_key in shapes_without_lane:
                # check shape type
                shape = shapes.get(shape_key)
                lane_id = self.find_lane_for_shape(shape, model_data)

                if lane_id == 'Fallback_Lane':
                    fallback_shapes.append(shape_key)
                else:
                    shapes[lane_id]['childShapes'].append(copy.deepcopy(shape))

            # Add remaining shapes to fallback lane
            for shape_key in fallback_shapes:
                for key in list_of_extra_keys:
                    shapes[shape_key].pop(key, None)
                fallback_lane['childShapes'].append(copy.deepcopy(shapes[shape_key]))

            lanes = list(filter(lambda shape_key: shapes[shape_key].get('stencil', {}).get(
                'id', '') == 'Lane' and len(shapes[shape_key]["childShapes"]) > 0, shapes))
            lane_objects = []
            for lane_key in lanes:
                lane_obj = shapes[lane_key]
                # Remove unwanted keys from lane itself
                for key in list_of_extra_keys:
                    lane_obj.pop(key, None)
                # Remove unwanted keys from child shapes
                for child in lane_obj.get('childShapes', []):
                    for key in list_of_extra_keys:
                        child.pop(key, None)
                lane_objects.append(copy.deepcopy(lane_obj))

            pool['childShapes'] = lane_objects
            if len(fallback_lane['childShapes']) > 0:
                pool['childShapes'].append(copy.deepcopy(fallback_lane))

            # remove extra keys from shapes
            for key in list_of_extra_keys:
                pool.pop(key, None)

            model_data['childShapes'].append(copy.deepcopy(pool))
            sequenceflow_objects = [shapes[key] for key in sequence_flows]
            for obj in sequenceflow_objects:
                for key in list_of_extra_keys:
                    obj.pop(key, None)

            model_data['childShapes'] += copy.deepcopy(sequenceflow_objects)

        if "meta-diagramnotes_en_us" in model_data.get('properties',{}):
            model_data["properties"]["meta-notes"] =  copy.deepcopy(model_data["properties"]["meta-diagramnotes_en_us"])
            model_data["properties"].pop("meta-diagramnotes_en_us", None)

        
        # add language
        model_data["language"] = self.diagram_language
        for key in list_of_extra_keys:
            model_data.pop(key, None)
        # delete shapes from model_data
        del model_data['shapes']

        return model_data, text_annotations_and_connections

    
    def convert_to_vc_model_json(self, model_data):
        list_of_extra_keys = ["type", "aris_id", "aris_guid", "name", "predecessor", "def_id", "aris_symbol_type", "parent"]
        shapes = model_data.get('shapes')

        text_annotations_and_connections = {}
        # Get keys of text annotations
        text_annotation_keys = [shape_key for shape_key in shapes if shapes[shape_key].get('stencil', {}).get('id', '') == 'TextAnnotation']
        for key in text_annotation_keys:
            # Save the text annotation shape
            text_annotations_and_connections[key] = copy.deepcopy(shapes[key])
            outgoings = shapes[key].get('outgoing', [])
            for outgoing in outgoings:
                conn_key = outgoing.get('resourceId', '')
                conn_shape = shapes.get(conn_key)
                text_annotations_and_connections[key] = copy.deepcopy(conn_shape)
                if conn_shape:
                    outgoings_of_conn = conn_shape.get('outgoing', [])
                    # check outgoing shapes and remove the connection key from the predecessor of the shape
                    for out in outgoings_of_conn:
                        target_key = out.get('resourceId', '')
                        target_shape = shapes.get(target_key)
                        if target_shape:
                            # remove the conn_key from the predecessor of shape.get(target_key)
                            predecessor_list = target_shape.get('predecessor', [])
                            predecessor_list = [p for p in predecessor_list if p != conn_key]
                            target_shape['predecessor'] = predecessor_list

                    # delete the target connection
                    shapes.pop(conn_key, None)
            # delete the text annotation
            shapes.pop(key, None)

        child_shape_objs = [shapes[key] for key in shapes]

        for shape in child_shape_objs:
            for key in list_of_extra_keys:
                shape.pop(key, None)
        model_data['childShapes'] += copy.deepcopy(child_shape_objs)

        # add language
        model_data["language"] = self.diagram_language
        for key in list_of_extra_keys:
            model_data.pop(key, None)
        
        if "meta-diagramnotes_en_us" in model_data.get('properties',{}):
            model_data["properties"]["meta-notes"] =  copy.deepcopy(model_data["properties"]["meta-diagramnotes_en_us"])
            model_data["properties"].pop("meta-diagramnotes_en_us", None)


        # delete shapes from model_data
        del model_data['shapes']

        return model_data, text_annotations_and_connections

    def build_signavio_data(self):

        for key, model in self.models.items():

            aris_guid = model.get('aris_guid')
            #if aris_guid not in ['c4f18ec1-d7cc-11ef-4bbc-2e79ce7bec12', "c86f89b1-a57e-11ef-180f-5232495bb7aa"]:
            #    continue
            data_exists, data = self.FT_Models.is_task_done(id=aris_guid)

            if data_exists:
                final_transformed_data = {}
                text_annotations_and_connections = {}
                shapes = model.get('shapes', {})
                #if 'transformed_model_json' in data:
                #    continue
                if len(shapes) > 0:
                    diagram_type = model.get('type')
                    if diagram_type == 'bpmn':
                        converted_model_data, text_annotations_and_connections = self.convert_to_bpmn_model_json(model)
                        converted_model_data = self.update_diagrams_with_risk_management(converted_model_data)
                        # write_json_file(converted_model_data, 'test.json', 'output')
                        try:
                            diagram_forge = DiagramForge(converted_model_data)
                            final_transformed_data = diagram_forge.to_spm_json()
                        except:
                            logger.error(
                                f'Diagram ID: <{aris_guid}> Diagram Type : BPMN is not created via diagramforge. Check the diagram data')
                    else:  # value chain
                        try:
                            converted_model_data, text_annotations_and_connections = self.convert_to_vc_model_json(model)
                            converted_model_data = self.update_diagrams_with_risk_management(converted_model_data)
                            model_builder = ModelBuilder(converted_model_data)
                            final_transformed_data = model_builder.to_spm_json()
                        except:
                            logger.error(
                                f'Diagram ID: <{aris_guid}> Diagram Type : Value Chain is not created via VC Model Builder. Check the diagram data')
                else:
                    # add language
                    model["language"] = self.diagram_language
                    for key in ["type", "aris_id", "aris_guid", "name"]:
                        model.pop(key, None)
                    final_transformed_data = model

                # Save transformed data to FileTracker
                # update existing data with transformed model json key and value
                if final_transformed_data:
                    data['transformed_model_json'] = final_transformed_data
                    data['text_annotations_and_connections'] = text_annotations_and_connections
                    self.FT_Models.save_task_results(id=aris_guid, data=data, try_update=True)
                else:

                    logger.error(f'Diagram ID: <{aris_guid}> cannot be created')


    def update_diagrams_with_risk_management(self, model_json):
        # get all records from DB

        # model_json = data.get('json', {})
        # get risks controls
        diagram_risks = model_json.get('properties', {}).get('meta-risksonly', [])
        diagram_controls = model_json.get('properties', {}).get('meta-controls', [])
        risk_management_attribute, controls_added = self.create_risk_management_attribute(diagram_risks, diagram_controls)

        # add risk management attribute to model_json
        if risk_management_attribute['totalCount'] > 0:
            model_json['properties']['meta-risks'] = copy.deepcopy(risk_management_attribute)

        # Remove meta-risks and meta-controls from properties
        if 'meta-risksonly' in model_json.get('properties', {}):
            del model_json['properties']['meta-risksonly']
        if 'meta-controls' in model_json.get('properties', {}):
            controls_added = list(controls_added)
            for control_id in controls_added:
                model_json['properties']['meta-controls'].remove(control_id)

        # update shapes with risk-management attributes
        self.update_shapes_with_risk_management(model_json)

        return model_json

    def update_shapes_with_risk_management(self, model_data):
        # check shape elements Tasks
        child_shapes = model_data.get("childShapes", "")

        if child_shapes and len(child_shapes) != 0:
            # check Tasks
            tasks = list(filter(lambda a: a['stencil']['id'] == 'Task', child_shapes))
            for task in tasks:
                task_risks = task.get('properties', {}).get('meta-risksonly', [])
                task_controls = task.get('properties', {}).get('meta-controls', [])
                risk_management_attribute, controls_added = self.create_risk_management_attribute(task_risks, task_controls)
               # add risk management attribute to model_json
                if risk_management_attribute['totalCount'] > 0:
                    task['properties']['meta-risks'] = copy.deepcopy(risk_management_attribute)

                # Remove meta-risks and meta-controls from task properties
                if 'meta-risksonly' in task.get('properties', {}):
                    del task['properties']['meta-risksonly']
                if 'meta-controls' in task.get('properties', {}):
                    controls_added = list(controls_added)
                    for control_id in controls_added:
                        task['properties']['meta-controls'].remove(control_id)
                    #del task['properties']['meta-controls']

            if len(child_shapes) > 0:
                for child in child_shapes:
                    self.update_shapes_with_risk_management(child)

    def transform_metaDataValues(self, input_data):
        # adds /glssary/ before id and removes unrequired data
        output_data = {}

        for key, value in input_data.items():
            if isinstance(value, dict):
                if 'id' in value:
                    output_data[key] = f"/glossary/{value['id']}"
                else:
                    output_data[key] = value
            elif isinstance(value, list):
                output_data[key] = []
                for item in value:
                    if isinstance(item, dict) and 'id' in item:
                        output_data[key].append(f"/glossary/{item['id']}")
                    else:
                        output_data[key].append(item)
            else:
                output_data[key] = value

        return output_data

    def create_risk_management_attribute(self, risks, controls):
        risk_management_attribute = {"totalCount": 0, 'items': []}
        control_added = set()
        for risk_id in risks:
            # get risk data
            aris_guid = self.dictionary_signavio_to_aris_guid.get(risk_id, '')
            data_exists, data_dictionary = self.dictionary_tracker.is_task_done(id=aris_guid)
            if not data_exists:
                logger.error(f'Risk ID: <{risk_id}> does not exist.')
            else:
                # check controls of the risk
                # check controls of the diagram
                risk_attached_controls = data_dictionary.get("json", {}).get('metaDataValues', {}).get('meta-controls', [])

                new_risk = {}
                new_risk_metadata = data_dictionary.get("json", {}).get('metaDataValues', {})
                new_risk = self.transform_metaDataValues(new_risk_metadata)
                new_risk['itemHref'] = data_dictionary.get("signavio_id", "")
                new_risk['attachments'] = ''
                new_risk["riskname"] = data_dictionary.get("json", {}).get('title', '')
                new_risk['description'] = data_dictionary.get("json", {}).get('description', '')
                new_risk["controls"] = {"totalCount": 0, 'items': []}
                for risk_attached_control in risk_attached_controls:
                    # if control exists in model & risk_attached_controls then add it
                    control_glossary_href = '/glossary/' + risk_attached_control.get('id', '')
                    if control_glossary_href in controls:
                        # control_glossary_data, data_exists = self.dictionary_tracker.is_task_done(
                        #    id=risk_attached_control.get('id', '').replace('/glossary/', ''))
                        aris_guid = self.dictionary_signavio_to_aris_guid.get(control_glossary_href, '')
                        data_exists, control_glossary_data = self.dictionary_tracker.is_task_done(id=aris_guid)
                        if not data_exists:
                            logger.error(f"Contol ID: <{risk_attached_control.get('id', '').replace('/glossary/', '')}> does not exist.")
                        else:
                            control_added.add(control_glossary_href)
                            new_control = {}
                            new_control_metadata = control_glossary_data.get("json", {}).get('metaDataValues', {})
                            new_control = self.transform_metaDataValues(new_control_metadata)
                            # control_category = control_glossary_data.get("json", {}).get('rep', {}).get('category', '')
                            new_control['itemHref'] = control_glossary_data.get("signavio_id", '')
                            new_control['attachments'] = ''
                            new_control["name"] = control_glossary_data.get("json", {}).get('title', '')
                            new_control['description'] = control_glossary_data.get("json", {}).get('description', '')

                            new_risk["controls"]['items'].append(new_control)
                    else:
                        logger.error(
                            f'Control is attached to risk but not available as control to model: {control_glossary_href} , Risk id: <{risk_id}>')

                new_risk["controls"]['totalCount'] = len(new_risk["controls"]['items'])
                risk_management_attribute['items'].append(new_risk)
        # log error
        if len(controls) > len(control_added):
            logger.warning(f'Control is not attached: Controls<{controls}> ')
        risk_management_attribute['totalCount'] = len(risk_management_attribute['items'])
        return risk_management_attribute, control_added