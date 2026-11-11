import json
import os
from copy import deepcopy
from typing import Dict

import matplotlib.pyplot as plt
import networkx as nx

from amlparser.amlparser import AMLParser
from amlparser.amlquery import AMLQuery
from pyutils.logger_utility.logger import logger


class DiagramPositioner:
    def __init__(self, diagram_id: str, diagram_json: Dict, aml_parser: "AMLParser", aml_query: "AMLQuery"):
        """
        Class for diagram positioning.
        :param diagram_id: The diagram/model ID
        :param diagram_json: The diagram JSON from SPM (Signavio Process Manager)
        :param amlparser: AMLParser instance (passed from main)
        :param aml_query: Instance of AMLQuery (passed from main)
        :param spm_client: Instance of SPMClient (passed from main)
        """
        self.diagram_json = diagram_json
        self.aml_parser = aml_parser
        self.aml_query = aml_query
        self.diagram_id = diagram_id

        self.model_data = self.__get_model_by_guid()
        self.scale_factor = self.model_data.get("scale", 100) / 25 if self.model_data else 4.0
        self.pool_origin = (0, 0)  # ARIS global pool origin, set during __recursive_apply_bpmn_coords
        self.pool_canvas_ul = (50, 50)  # Signavio canvas position where pool is placed (always 50,50)
        self.lane_origin_x = 0  # min ARIS x of all lane occs, used for docker waypoint conversion
        self.lane_origin_y = 0  # min ARIS y of all lane occs, used for docker waypoint conversion
        self.diagram_shapes_flattened = {}
        self.__recursive_traverse_and_provide_flattened_dict_of_elements(self.diagram_json)

    def __get_model_by_guid(self):
        model = list(filter(lambda m: m.get("guid") == self.diagram_id, self.aml_query.models.values()))
        if len(model) > 0:
            return model[0]
        else:
            logger.error(f"Model with guid {self.diagram_id} not found in AMLQuery.")
            return None

    def _get_model_data_via_query(self):
        """
        Retrieves the model data for the current diagram/model ID using AMLQuery.
        Falls back to AMLParser if not found in AMLQuery.
        """
        # Try to get model via AMLQuery (more robust, supports filtering etc.)
        model = self.aml_query.models.get(self.diagram_id)
        if model:
            return model
        # Fallback: try AMLParser
        model = self.aml_parser.models.get(self.diagram_id)
        if model:
            return model
        return None

    def build_graph_from_aris_model(
        self, visualize: bool = True, show_id: bool = False, scale_size: bool = False, show_plot: bool = False
    ):
        """
        Build a directed graph from ARIS model data using networkx.
        Nodes: Object Occurrences (ObjOcc)
        Edges: Connections from outgoing_cxns and incoming_cxns
        If visualize=True, display the graph using matplotlib.
        Returns: nx.DiGraph
        """

        G = nx.DiGraph()

        if not self.model_data:
            return G

        occs = self.model_data.get("occs", {})
        # Add nodes, mark pools and lanes for grouping
        pool_ids = set()
        lane_ids = set()
        for occ_id, occ in occs.items():
            occ_type = occ.get("symbol", "").lower()
            occ_def = self.aml_parser.defs.get(occ.get("def"), {})
            name = occ_def.get("name", occ_id)
            label = f"{occ_type.capitalize()} ({name})"
            if show_id:
                label += f" [{occ_id}]"
            if "pool" in occ_type:
                pool_ids.add(occ_id)
            if "lane" in occ_type:
                lane_ids.add(occ_id)
            G.add_node(occ_id, label=label, type=occ_type)

        # Add edges using outgoing_cxns from ObjOccs, skip pools and lanes
        for occ_id, occ in occs.items():
            if occ_id in pool_ids or occ_id in lane_ids:
                continue
            outgoing_cxns = occ.get("outgoing_cxns", {})
            for target_id, cxn_list in outgoing_cxns.items():
                if target_id in pool_ids or target_id in lane_ids:
                    continue
                for cxn in cxn_list:
                    cxn_def_id = cxn.get("cxn_def_id")
                    # Get connection type from amlparser
                    cxn_type = self.aml_parser.cxns.get(cxn_def_id, {}).get("type", "")
                    G.add_edge(occ_id, target_id, label=cxn_type)

        # Add edges from incoming_cxns that are not yet in the graph, skip pools and lanes
        for occ_id, occ in occs.items():
            if occ_id in pool_ids or occ_id in lane_ids:
                continue
            incoming_cxns = occ.get("incoming_cxns", {})
            for source_id, cxn_list in incoming_cxns.items():
                if source_id in pool_ids or source_id in lane_ids:
                    continue
                # Skip if the target is a pool or lane
                if occ_id in pool_ids or occ_id in lane_ids:
                    continue
                for cxn in cxn_list:
                    cxn_def_id = cxn.get("cxn_def_id")
                    cxn_type = self.aml_parser.cxns.get(cxn_def_id, {}).get("type", "")
                    # Check if the edge already exists
                    if not G.has_edge(source_id, occ_id):
                        G.add_edge(source_id, occ_id, label=cxn_type)

        if visualize:
            # Fixed coordinates and sizes from ObjOcc
            pos = {}
            sizes = {}
            labels = {}
            for occ_id, occ in occs.items():
                position = occ.get("position")
                size = occ.get("size")
                # Default coordinates if not present
                x = float(position.get("x", 0)) if position else 0.0
                y = float(position.get("y", 0)) if position else 0.0
                pos[occ_id] = (x, y)
                # Default size if not present
                radius = max(float(size.get("dx", 40)), float(size.get("dy", 40))) if size else 40.0
                sizes[occ_id] = radius * 10 if scale_size else radius
                occ_type = occ.get("symbol", "").lower()
                occ_def = self.aml_parser.defs.get(occ.get("def"), {})
                name = occ_def.get("name", occ_id)
                label = f"{occ_type.capitalize()} ({name})"
                if show_id:
                    label += f" [{occ_id}]"
                labels[occ_id] = label

            plt.figure(figsize=(16, 12))
            # Draw nodes as rectangles with fixed positions and sizes
            for occ_id, (x, y) in pos.items():
                width = float(sizes[occ_id]) / 100
                height = float(sizes[occ_id]) / 100
                rect = plt.Rectangle(
                    (x - width / 2, y - height / 2), width, height, color="lightblue", ec="blue", alpha=0.7
                )
                plt.gca().add_patch(rect)
                plt.text(x, y, labels[occ_id], ha="center", va="center", fontsize=8, weight="normal")

            # Draw edges: iterate over all ObjOccs and their outgoing_cxns/incoming_cxns
            for occ_id, occ in occs.items():
                # Skip pools and lanes as source
                if occ_id in pool_ids or occ_id in lane_ids:
                    continue
                # Outgoing connections
                outgoing_cxns = occ.get("outgoing_cxns", {})
                for target_id, cxn_list in outgoing_cxns.items():
                    # Skip pools and lanes as target
                    if target_id in pool_ids or target_id in lane_ids:
                        continue
                    for cxn in cxn_list:
                        cxn_def_id = cxn.get("cxn_def_id")
                        # Get position data from self.aml_parser.cxns
                        start_point = pos.get(occ_id, (0, 0))
                        end_point = pos.get(target_id, (0, 0))
                        docker = []
                        if "position" in cxn and cxn["position"]:
                            if isinstance(cxn["position"], list):
                                positions = cxn["position"]
                                if len(positions) > 2:
                                    # Only use inner points as docker points
                                    docker = [
                                        (float(p.get("x", 0)), float(p.get("y", 0)))
                                        for i, p in enumerate(positions)
                                        if p and i != 0 and i != len(positions) - 1
                                    ]
                                # If only two positions, treat as start/end only
                            elif isinstance(cxn["position"], dict):
                                # Only one position, treat as direct connection
                                pass
                        points = [start_point] + docker + [end_point]
                        xs, ys = zip(*points)
                        plt.plot(xs, ys, color="gray", linewidth=2, alpha=0.7)
                # Incoming connections (optional, if you want bidirectional visualization)
                # incoming_cxns = occ.get('incoming_cxns', {})
                # for source_id, cxn_list in incoming_cxns.items():
                #     ... same as outgoing ...

            plt.axis("equal")
            plt.title("ARIS Model Graph (ObjOcc positions and sizes)")
            plt.xlabel("X")
            plt.ylabel("Y")
            plt.tight_layout()

            # Save plot as PNG in output folder
            output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
            os.makedirs(output_dir, exist_ok=True)

            # Clean filename (remove/replace problematic chars)
            safe_name = "".join(
                c if c.isalnum() or c in (" ", "_", "-") else "_"
                for c in f"{self.model_data.get('name', '')}_{self.diagram_id}"
            )
            file_path = os.path.join(output_dir, f"aris_model_graph_{safe_name}.png")
            plt.savefig(file_path, format="png")
            print(f"Graph image saved to: {file_path}")
            if show_plot:
                plt.show()
                input("Press Enter to close the plot and continue...")

        return G

    """
    The following methods are for applying coordinates for VCD.
    """

    def __recursive_traverse_and_update_coords_vcd(self, shape):
        """
        Recursively traverse the diagram JSON for VCD and update coordinates based on ARIS model data.
        """
        # Recursive traversal
        for child in shape["childShapes"]:
            self.__recursive_traverse_and_update_coords_vcd(child)
        current_occ_id = shape.get("resourceId")
        current_occ_id = current_occ_id.replace("ObjOcc", "ObjOcc.")
        if current_occ_id and current_occ_id in self.model_data.get("occs", {}):
            occ = self.model_data["occs"][current_occ_id]
            position = occ.get("position", {})
            size = occ.get("size", {})
            position_x = position.get("x")
            position_dx = size.get("dx")
            position_y = position.get("y")
            position_dy = size.get("dy")
            if position_x and position_y and position_dx and position_dy:
                shape["bounds"] = {
                    "lowerRight": {
                        "x": int(position.get("x", 0)) + int(size.get("dx")),
                        "y": int(position.get("y", 0)) + int(size.get("dy")),
                    },
                    "upperLeft": {"x": position.get("x", 0), "y": position.get("y", 0)},
                }
            else:
                logger.warning(f"POSITION MISSING VCD - occ_id <{current_occ_id}> | aris_guid <{self.diagram_id}>")

    def apply_coords_for_vcd(self):
        """
        Apply coordinates from ARIS model VCD to the diagram JSON VCD for Signavio.
        """
        # Check if model_data is available
        if not self.model_data:
            logger.error(f"Model data not available. Cannot apply coordinates for VCD with guid <{self.diagram_id}>.")
            return self.diagram_json
        else:
            # recursively traverse diagram_json and update coordinates
            self.__recursive_traverse_and_update_coords_vcd(self.diagram_json)
            return self.diagram_json

    """
    The following methods are for applying coordinates for BPMN.
    """

    def __recursive_traverse_and_built_bpmn_graph(self, shape, parent_id=None):
        """
        Recursively traverse the diagram JSON for BPMN and extract built a graph to identify shapes in the lowest level.
        """
        current_occ_id = shape.get("resourceId")
        for child in shape["childShapes"]:
            self.__recursive_traverse_and_built_bpmn_graph(shape=child, parent_id=current_occ_id)
        # Add current shape / parent relationship
        if current_occ_id not in self.bpmn_graph:
            self.bpmn_graph[current_occ_id] = parent_id if parent_id else "root"
        if current_occ_id not in self.diagram_objects:
            # clone objec with deepcopy to avoid modifying the original and to empty childShapes for later use
            shape_copy = deepcopy(shape)
            shape_copy["childShapes"] = []
            self.diagram_objects[current_occ_id] = shape_copy

    def __recursive_traverse_and_sort_in_shape(self, shape, shape_to_sort_in, lane_id):
        """
        Recursively traverse the shape and sort it into the correct lane based on its coordinates.
        """
        for child in shape["childShapes"]:
            if self.__recursive_traverse_and_sort_in_shape(child, shape_to_sort_in, lane_id):
                return True
        # Add current shape to childShapes of the lane
        if lane_id == shape["resourceId"]:
            shape["childShapes"].append(deepcopy(shape_to_sort_in))
            return True
        return False

    def sort_in_additional_shapes_to_correct_lane(self, additional_shapes):
        """
        Sort additional shapes (e.g. TextAnnotations) into the correct lane based on their coordinates.
        """
        # Find all lanes with their original coordinates
        lane_positions = {}
        for lane_id, lane in self.lanes.items():
            current_occ_id = lane['properties'].get('meta-occId', '')
            # current_occ_id = lane_id.replace("ObjOcc", "ObjOcc.")
            if current_occ_id and current_occ_id in self.model_data.get("occs", {}):
                occ = self.model_data["occs"][current_occ_id]
                position = occ.get("position", {})
                size = occ.get("size", {})
                position_x = position.get("x")
                position_dx = size.get("dx")
                position_y = position.get("y")
                position_dy = size.get("dy")
                if position_x and position_y and position_dx and position_dy:
                    lane_positions[lane_id] = {
                        "bounds": {
                            "upperLeft": {
                                "x": int(position_x),
                                "y": int(position_y),
                            },
                            "lowerRight": {
                                "x": int(position_x) + int(position_dx),
                                "y": int(position_y) + int(position_dy),
                            },
                        }
                    }
            else:
                # No direct ARIS occ for the lane — derive bounds from its child shapes' positions
                child_ids = [sid for sid, pid in self.bpmn_graph.items() if pid == lane_id]
                xs, ys, x2s, y2s = [], [], [], []
                for child_id in child_ids:
                    child_occ_id = child_id.replace("ObjOcc", "ObjOcc.").replace("CxnOcc", "CxnOcc.")
                    child_occ = self.model_data.get("occs", {}).get(child_occ_id)
                    if child_occ:
                        cp = child_occ.get("position", {})
                        cs = child_occ.get("size", {})
                        cx, cy, cdx, cdy = cp.get("x"), cp.get("y"), cs.get("dx"), cs.get("dy")
                        if cx is not None and cy is not None and cdx is not None and cdy is not None:
                            xs.append(int(cx))
                            ys.append(int(cy))
                            x2s.append(int(cx) + int(cdx))
                            y2s.append(int(cy) + int(cdy))
                if xs:
                    lane_positions[lane_id] = {
                        "bounds": {
                            "upperLeft": {"x": min(xs), "y": min(ys)},
                            "lowerRight": {"x": max(x2s), "y": max(y2s)},
                        }
                    }
                else:
                    logger.warning(
                        f"POSITION MISSING LANE - occ_id <{current_occ_id}> | aris_guid <{self.diagram_id}>, "
                        f"could not derive bounds from child shapes, additional shapes might be sorted into the fallback lane."
                    )
        # For each additional shape, check which lane it belongs to based on its coordinates and add it to the childShapes of the correct lane
        for shape_id, shape in additional_shapes.items():
            current_occ_id = shape_id.replace("ObjOcc", "ObjOcc.").replace("CxnOcc", "CxnOcc.")
            if current_occ_id.startswith("ObjOcc"):
                if current_occ_id and current_occ_id in self.model_data.get("occs", {}):
                    occ = self.model_data["occs"][current_occ_id]
                    position = occ.get("position", {})
                    size = occ.get("size", {})
                    position_x = int(position.get("x", 0))
                    position_y = int(position.get("y", 0))
                    sorted_in_to_lane = False
                    if lane_positions:
                        for lane_id, lane_position in lane_positions.items():
                            # check if upperleft shape coordinates are within the lane
                            if (
                                position_x >= lane_position["bounds"]["upperLeft"]["x"]
                                and position_x <= lane_position["bounds"]["lowerRight"]["x"]
                                and position_y >= lane_position["bounds"]["upperLeft"]["y"]
                                and position_y <= lane_position["bounds"]["lowerRight"]["y"]
                            ):
                                # add shape to childShapes of the lane, to do this, find lane recursively with lane_id
                                if self.__recursive_traverse_and_sort_in_shape(self.diagram_json, shape, lane_id):
                                    sorted_in_to_lane = True
                                    break
                    else:
                        for lane_id in self.lanes.keys():
                            logger.warning(
                                f"NO LANE POSITIONS AVAILABLE - aris_guid <{self.diagram_id}>, "
                                f"additional shapes will be sorted into the lane with the occ id <{lane_id}>."
                            )
                            if self.__recursive_traverse_and_sort_in_shape(self.diagram_json, shape, lane_id):
                                break
                    if not sorted_in_to_lane:
                        # add to canvas if no lane found, means coordinates are outside of all lanes
                        self.diagram_json["childShapes"].append(deepcopy(shape))

            elif current_occ_id.startswith("CxnOcc"):
                # Add connection to first childShapes as all connections are globally defined
                self.diagram_json["childShapes"].append(deepcopy(shape))
            else:
                logger.warning(f"UNKNOWN OCCURRENCE ID - occ_id <{current_occ_id}> | "
                               f"aris_guid <{self.diagram_id}>, shape will be added as is.")

    def __get_occ_id_for_shape(self, shape: dict) -> str:
        """
        Resolve the ARIS occ id for a shape.
        Lanes store it in meta-occId; other shapes encode it in the resourceId.
        """
        occ_id = shape.get("properties", {}).get("meta-occId", "")
        if occ_id:
            return occ_id
        resource_id = shape.get("resourceId", "")
        return resource_id.replace("ObjOcc", "ObjOcc.").replace("CxnOcc", "CxnOcc.")

    def __recursive_apply_bpmn_coords(self, shape, parent_origin_x: int = 0, parent_origin_y: int = 0):
        """
        Recursively walk the nested diagram JSON and overwrite bounds with ARIS coordinates.

        All ARIS values are divided by self.scale_factor (= Scale / 25) to convert to
        Signavio pixels. scale_factor defaults to 4.0 (Scale=100).

        Coordinate rules (mirrors how Signavio expects them):
        - Canvas:   no bounds change, traverse children with origin (0, 0).
        - Pool:     global ARIS position / scale → absolute bounds; pass scaled pool
                    origin down. Also stores pool_origin for docker conversion.
        - Lane:     ARIS y relative to pool / scale → pool-relative y bounds.
                    UL.x is always pinned to 30 (Signavio lane label column);
                    width comes from ARIS dx / scale.
                    Pass lane ARIS global origin down to children.
        - Task/Gateway/Event/etc.:
                    ARIS position minus lane origin, divided by scale → lane-relative px.
                    Gateways/events use scaled ARIS center + fixed Signavio default size.
        - SequenceFlow: bounds unused; skip.
        """
        sf = self.scale_factor
        stencil_id = shape.get("stencil", {}).get("id", "")
        stencil_lower = stencil_id.lower()
        occs = self.model_data.get("occs", {})

        # SequenceFlows: skip bounds, no children to recurse into
        if "flow" in stencil_lower or "association" in stencil_lower:
            return

        if stencil_lower == "pool":
            occ_id = self.__get_occ_id_for_shape(shape)
            if occ_id in occs:
                occ = occs[occ_id]
                position = occ.get("position", {})
                size = occ.get("size", {})
                px, py = position.get("x"), position.get("y")
                pdx, pdy = size.get("dx"), size.get("dy")
                if px is not None and py is not None and pdx and pdy:
                    px, py, pdx, pdy = int(px), int(py), int(pdx), int(pdy)
                    # Always pin pool to canvas (50, 50) — ARIS absolute position is irrelevant for canvas placement
                    pcx, pcy = self.pool_canvas_ul
                    shape["bounds"] = {
                        "upperLeft": {"x": pcx, "y": pcy},
                        "lowerRight": {"x": pcx + round(pdx / sf), "y": pcy + round(pdy / sf)},
                    }
                    self.pool_origin = (px, py)
                    # Compute lane origins: min ARIS x/y across all lane occs for docker waypoint conversion
                    lane_xs, lane_ys = [], []
                    for child in shape["childShapes"]:
                        child_stencil = child.get("stencil", {}).get("id", "").lower()
                        if child_stencil == "lane":
                            child_occ_id = self.__get_occ_id_for_shape(child)
                            if child_occ_id in occs:
                                lp = occs[child_occ_id].get("position", {})
                                lx, ly = lp.get("x"), lp.get("y")
                                if lx is not None:
                                    lane_xs.append(int(lx))
                                if ly is not None:
                                    lane_ys.append(int(ly))
                    self.lane_origin_x = min(lane_xs) if lane_xs else px
                    self.lane_origin_y = min(lane_ys) if lane_ys else py
                    for child in shape["childShapes"]:
                        self.__recursive_apply_bpmn_coords(child, px, py)
                    return
                else:
                    logger.warning(f"POSITION MISSING POOL - occ_id <{occ_id}> | aris_guid <{self.diagram_id}>")
            # fallback: traverse with unchanged origin
            for child in shape["childShapes"]:
                self.__recursive_apply_bpmn_coords(child, parent_origin_x, parent_origin_y)
            return

        if stencil_lower == "lane":
            occ_id = self.__get_occ_id_for_shape(shape)
            if occ_id in occs:
                occ = occs[occ_id]
                position = occ.get("position", {})
                size = occ.get("size", {})
                lx, ly = position.get("x"), position.get("y")
                ldx, ldy = size.get("dx"), size.get("dy")
                if lx is not None and ly is not None and ldx and ldy:
                    lx, ly, ldx, ldy = int(lx), int(ly), int(ldx), int(ldy)
                    # y is pool-relative and scaled; x is always 30 (Signavio label column)
                    rel_y = round((ly - parent_origin_y) / sf)
                    lane_w = round(ldx / sf)
                    lane_h = round(ldy / sf)
                    shape["bounds"] = {
                        "upperLeft": {"x": 30, "y": rel_y},
                        "lowerRight": {"x": 30 + lane_w, "y": rel_y + lane_h},
                    }
                    for child in shape["childShapes"]:
                        self.__recursive_apply_bpmn_coords(child, lx, ly)
                    return
                else:
                    logger.warning(f"POSITION MISSING LANE - occ_id <{occ_id}> | aris_guid <{self.diagram_id}>")
            # fallback: traverse with unchanged origin
            for child in shape["childShapes"]:
                self.__recursive_apply_bpmn_coords(child, parent_origin_x, parent_origin_y)
            return

        # Regular shape (task, gateway, event, annotation, …)
        occ_id = self.__get_occ_id_for_shape(shape)
        if occ_id in occs:
            occ = occs[occ_id]
            position = occ.get("position", {})
            size = occ.get("size", {})
            sx, sy = position.get("x"), position.get("y")
            sdx, sdy = size.get("dx"), size.get("dy")
            if sx is not None and sy is not None and sdx and sdy:
                sx, sy, sdx, sdy = int(sx), int(sy), int(sdx), int(sdy)
                rel_x = round((sx - parent_origin_x) / sf)
                rel_y = round((sy - parent_origin_y) / sf)
                default_size = self.__get_signavio_default_size(stencil_id)
                if default_size:
                    mid_x = rel_x + round(sdx / sf) // 2
                    mid_y = rel_y + round(sdy / sf) // 2
                    half_w = default_size[0] // 2
                    half_h = default_size[1] // 2
                    shape["bounds"] = {
                        "upperLeft": {"x": mid_x - half_w, "y": mid_y - half_h},
                        "lowerRight": {"x": mid_x + half_w, "y": mid_y + half_h},
                    }
                else:
                    shape["bounds"] = {
                        "upperLeft": {"x": rel_x, "y": rel_y},
                        "lowerRight": {"x": rel_x + round(sdx / sf), "y": rel_y + round(sdy / sf)},
                    }
            else:
                logger.warning(
                    f"POSITION MISSING BPMN - occ_id <{occ_id}> | "
                    f"aris_guid <{self.diagram_id}>, shape will keep its existing bounds."
                )
        # Recurse into children (e.g. sub-processes) passing own ARIS global origin unchanged
        for child in shape["childShapes"]:
            self.__recursive_apply_bpmn_coords(child, parent_origin_x, parent_origin_y)

    # Default Signavio sizes (width, height) per stencil category.
    # Gateways and events have fixed sizes in Signavio regardless of ARIS dimensions.
    _GATEWAY_STENCIL_IDS = {"exclusive_databased_gateway", "parallelgateway", "inclusivegateway"}
    _END_EVENT_STENCIL_IDS = {"endnoneevent", "endmessageevent", "enderrorevent", "endescalationevent",
                              "endcancelevent", "endcompensationevent", "endmultipleevent", "endterminateevent"}
    _EVENT_STENCIL_IDS = {"startnoneevent", "startmessageevent", "starttimerevent", "starterrorevent",
                          "startcompensationevent", "startparallelmultipleevent", "startescalationevent",
                          "startconditionalevent", "startmultipleevent",
                          "intermediateevent", "intermediatetimerevent", "intermediatemessageevent",
                          "intermediatelinkeventcatching", "intermediatelinkeventthrowing",
                          "eventsubprocess", "collapsedeventsubprocess"}
    _SIGNAVIO_DEFAULT_SIZE = {
        "gateway": (40, 40),
        "end_event": (28, 28),
        "event": (30, 30),
    }

    def __get_signavio_default_size(self, stencil_id: str):
        """
        Return the fixed Signavio (width, height) for gateway/event stencils, or None for other shapes.
        """
        sid = stencil_id.lower()
        if sid in self._GATEWAY_STENCIL_IDS:
            return self._SIGNAVIO_DEFAULT_SIZE["gateway"]
        if sid in self._END_EVENT_STENCIL_IDS:
            return self._SIGNAVIO_DEFAULT_SIZE["end_event"]
        if sid in self._EVENT_STENCIL_IDS:
            return self._SIGNAVIO_DEFAULT_SIZE["event"]
        return None

    def __check_if_shape_is_connection(self, shape):
        """
        Check if a shape is a connection based on its stencil id.
        """
        connection_keywords = ["flow", "association"]
        for conn in connection_keywords:
            if conn in shape.get("stencil", {}).get("id", "").lower():
                return True
        return False

    def __recursive_traverse_and_provide_flattened_dict_of_elements(self, shape):
        """
        Recursively traverse the diagram JSON and flatten the list of elements to get all shapes in one list.
        """
        # Recursive traversal
        for child in shape["childShapes"]:
            self.__recursive_traverse_and_provide_flattened_dict_of_elements(child)
        self.diagram_shapes_flattened[shape["resourceId"]] = shape

    def __add_cnxs_to_diagram_json(self):
        """
        Add connections to the diagram JSON for BPMN based on the ARIS model connections.
        """
        possible_connection_ids = [shape for shape, parent in self.bpmn_graph.items() if parent == "canvas"]
        connection_shapes = {
            shape_id: shape_obj
            for shape_id, shape_obj in self.diagram_objects.items()
            if shape_id in possible_connection_ids and self.__check_if_shape_is_connection(shape_obj)
        }
        # Iterate connection shapes and add to diagram_json with coordinates from ARIS model
        for shape_id, shape in connection_shapes.items():
            shape['labels'] = []
            current_cnx_occ_id = shape_id.replace("CxnOcc", "CxnOcc.")
            if current_cnx_occ_id and current_cnx_occ_id in self.model_data.get("cxn_occs", {}):
                positions = self.model_data["cxn_occs"][current_cnx_occ_id]
                # Get start and end shape
                start_shape = list(filter(lambda x: shape_id in json.dumps(x), self.diagram_shapes_flattened.values()))[0]
                end_id = shape["target"]["resourceId"] if shape.get("target") else None
                # get shapes from flattened dict to access bounds/coordinates
                end_shape = self.diagram_shapes_flattened.get(end_id)
                # calculate first and last docker
                start_start_x = start_shape.get("bounds", {}).get("upperLeft", {}).get("x")
                start_start_y = start_shape.get("bounds", {}).get("upperLeft", {}).get("y")
                start_end_x = start_shape.get("bounds", {}).get("lowerRight", {}).get("x")
                start_end_y = start_shape.get("bounds", {}).get("lowerRight", {}).get("y")
                end_start_x = end_shape.get("bounds", {}).get("upperLeft", {}).get("x")
                end_start_y = end_shape.get("bounds", {}).get("upperLeft", {}).get("y")
                end_end_x = end_shape.get("bounds", {}).get("lowerRight", {}).get("x")
                end_end_y = end_shape.get("bounds", {}).get("lowerRight", {}).get("y")
                # calculate size of elements to set dockers in the middle of the connection line
                size_start_x_half = abs(int(start_end_x) - int(start_start_x)) / 2
                size_start_y_half = abs(int(start_end_y) - int(start_start_y)) / 2
                size_end_x_half = abs(int(end_end_x) - int(end_start_x)) / 2
                size_end_y_half = abs(int(end_end_y) - int(end_start_y)) / 2
                # init empty dockers list
                dockers = []
                # check lenght of dockers in positions
                if len(positions) == 2:
                    dockers.append({"x": size_start_x_half, "y": size_start_y_half})
                    dockers.append({"x": size_end_x_half, "y": size_end_y_half})
                    shape["dockers"] = dockers
                else:
                    if len(positions) > 2:
                        dockers.append({"x": size_start_x_half, "y": size_start_y_half})
                        sf = self.scale_factor
                        pcx, pcy = self.pool_canvas_ul
                        for p in positions[1:-1]:
                            # Intermediate waypoints must be Signavio canvas-absolute coordinates.
                            # x: subtract lane's min ARIS x, scale, add pool canvas left + 30px label column.
                            # y: subtract lane's min ARIS y, scale, add pool canvas top.
                            abs_x = pcx + 30 + round((float(p.get("x", 0)) - self.lane_origin_x) / sf)
                            abs_y = pcy + round((float(p.get("y", 0)) - self.lane_origin_y) / sf)
                            dockers.append({"x": abs_x, "y": abs_y})
                        dockers.append({"x": size_end_x_half, "y": size_end_y_half})
                        shape["dockers"] = dockers
                    else:
                        logger.warning(
                            f"POSITIONS MISSING FOR CONNECTION - occ_id <{current_cnx_occ_id}> | "
                            f"aris_guid <{self.diagram_id}>, connection won't be added."
                        )
                self.diagram_json["childShapes"].append(deepcopy(shape))

    def __built_bpnm_with_aris_coords(self):
        # self.diagram_json is the full nested canvas from DiagramForge (pool→lane→shapes intact).
        # Walk it and overwrite bounds in-place with ARIS coordinates.
        for child in self.diagram_json["childShapes"]:
            self.__recursive_apply_bpmn_coords(child)
        self.diagram_shapes_flattened = {}
        self.__recursive_traverse_and_provide_flattened_dict_of_elements(self.diagram_json)
        self.__add_cnxs_to_diagram_json()

    def apply_coords_for_bpmn(self, **kwargs):
        """
        Apply coordinates from ARIS model BPMN to the diagram JSON BPMN for Signavio.
        """
        # Check if model_data is available
        if not self.model_data:
            logger.error(f"Model data not available. Cannot apply coordinates for BPMN with guid <{self.diagram_id}>.")
            return self.diagram_json
        else:
            # Prepare standard self attributes for BPMN processing
            self.diagram_objects = {}
            self.bpmn_graph = {}
            self.all_additional_shapes = {}
            self.__recursive_traverse_and_built_bpmn_graph(self.diagram_json)
            self.lanes = {
                shape_id: shape
                for shape_id, shape in self.diagram_objects.items()
                if "lane" in shape.get("stencil", {}).get("id", "").lower()
            }
            # Check kwargs for additional shapes, e.g. TextAnnotations, Groups, ...
            if kwargs:
                self.found_additional_shape_keys = []
                for key, value in kwargs.items():
                    if value is None:
                        continue
                setattr(self, key, value)
                self.found_additional_shape_keys.append(key)
                # Add additional shapes from **kwargs to diagram_json childShapes, coordinates will be added later
                for key in self.found_additional_shape_keys:
                    self.sort_in_additional_shapes_to_correct_lane(getattr(self, key))
                    items = getattr(self, key)
                    if items:
                        for item_id, item in items.items():
                            self.all_additional_shapes[item_id] = item
            # Rerun recursive traverse to sort in additional shapes to correct lane based on coordinates from ARIS model
            self.diagram_objects = {}
            self.bpmn_graph = {}
            self.__recursive_traverse_and_built_bpmn_graph(self.diagram_json)
            if 'ObjOcc-4fP5aq6AMR4-u-L--3oXqLRDeaHu-x-L-33-c' in self.diagram_objects:
                logger.info(f"Shape with id 'ObjOcc-4fP5aq6AMR4-u-L--3oXqLRDeaHu-x-L-33-c' found in diagram_objects, "
                            f"this is a TextAnnotation and will be sorted into the correct lane based on its coordinates.")
            # Built the BPMN diagram with coordinates from ARIS model
            self.__built_bpnm_with_aris_coords()
            return self.diagram_json
