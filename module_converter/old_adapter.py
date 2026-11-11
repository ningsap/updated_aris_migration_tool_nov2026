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
    def __init__(self, cfg, file_tracker: TaskWatch):
        self.FT_Models = file_tracker
        self.template_signavio_shape_data = read_json_file("template_signavio_shape_data.json", "input")
        self.json_converted_models_file_path = cfg.get('file_path_converted_models_json')
        self.diagram_language = cfg.get('default_workspace_language')

        try:
            with open(self.json_converted_models_file_path, 'r') as json_file:
                self.models = json.load(json_file)
        except:
            logger.error(f'ModelCreator Import: {self.json_converted_models_file_path} does not exist')

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
            fallback_lane["properties"]['name'] = 'Fallback_Lane'

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
        # delete shapes from model_data
        del model_data['shapes']

        return model_data, text_annotations_and_connections

    def build_signavio_data(self):

        for key, model in self.models.items():

            aris_guid = model.get('aris_guid')
            # if aris_guid not in ['386a6dc1-951b-11f0-4b6b-001dd8b71e0b']:
            #    continue
            data_exists, data = self.FT_Models.is_task_done(id=aris_guid)

            if data_exists:
                final_transformed_data = {}
                text_annotations_and_connections = {}
                shapes = model.get('shapes', {})
                if len(shapes) > 0:
                    diagram_type = model.get('type')
                    if diagram_type == 'bpmn':
                        converted_model_data, text_annotations_and_connections = self.convert_to_bpmn_model_json(model)
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
