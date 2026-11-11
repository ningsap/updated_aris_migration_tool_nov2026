from typing import List, Union

from diagramforge.exceptions.flow_positioning import RelativePositionCouldNotBeDetermined
from diagramforge.helpers.STATICS import CARDINAL_DIRECTIONS as CD
from diagramforge.rendering.flows.global_grid_lookup import GlobalGridLookup
from diagramforge.rendering.flows.port_connection import PortConnection
from diagramforge.schema.shapes import Event, Gateway, Task
from diagramforge.SETUP import forge_logger


class PortAdapter:
    """
    Responsible for assigning a node's connected edges to respective input/output ports
    and managing the edges' port docking order.

    Attributes:
        bound_shape (Union[Task, Event, Gateway]): The shape bound to this adapter.
        global_grid_lookup (GlobalGridLookup): Utility for grid-based position lookups.
        all_outgoing_connections (List[PortConnection]): List of all outgoing port connections.
        north_port_connections (List[PortConnection]): Connections assigned to the NORTH port.
        east_port_connections (List[PortConnection]): Connections assigned to the EAST port.
        south_port_connections (List[PortConnection]): Connections assigned to the SOUTH port.
    """

    def __init__(
        self,
        bound_shape: Union[Task, Event, Gateway],
        global_grid_lookup: GlobalGridLookup,
        all_outgoing_connections: List[PortConnection] = [],
    ) -> None:
        """
        Initializes the PortAdapter with the bound shape, grid lookup, and outgoing connections.

        Args:
            bound_shape (Union[Task, Event, Gateway]): The shape to bind to this adapter.
            global_grid_lookup (GlobalGridLookup): Grid lookup utility instance.
            all_outgoing_connections (List[PortConnection], optional): Outgoing port connections. Defaults to [].
        """

        self.bound_shape: Union[Task, Event, Gateway] = bound_shape
        self.all_outgoing_connections: List[PortConnection] = all_outgoing_connections
        self.global_grid_lookup: GlobalGridLookup = global_grid_lookup

        # Port connections (outgoing)
        self.north_port_connections: List[PortConnection] = []
        self.east_port_connections: List[PortConnection] = []
        self.south_port_connections: List[PortConnection] = []
        self.special_connections: List[PortConnection] = []

        # Only incoming connections
        self.west_port_connections: List[PortConnection] = []

        # Sort the connections into the respective ports
        self.__sort_connections_into_ports()

        # Assign an order to each connection in the respective port relative to the source shape
        self.__assign_order_to_outgoing_connections()

    def __sort_connections_into_ports(self):
        """
        Sorts outgoing connections into their respective ports based on their relative positions.

        Raises:
            RelativePositionCouldNotBeDetermined: If the relative position of a connection cannot be determined.
        """

        forge_logger.debug(f"Sorting connections for shape {self.bound_shape.resource_id}")

        for connection in self.all_outgoing_connections:
            _log_string = f"Association with ID {connection.association.resource_id} ({connection.source} -> {connection.target}) assigned to"

            if connection.relative_position_to_source in [CD.NORTH, CD.NORTHWEST]:
                self.north_port_connections.append(connection)
                forge_logger.debug(f"{_log_string} NORTH port.")

            elif connection.relative_position_to_source in [CD.NORTHEAST, CD.EAST, CD.SOUTHEAST]:
                self.east_port_connections.append(connection)
                forge_logger.debug(f"{_log_string} EAST port.")

            elif connection.relative_position_to_source in [CD.SOUTH, CD.SOUTHWEST, CD.WEST]:
                self.south_port_connections.append(connection)
                forge_logger.debug(f"{_log_string} SOUTH port.")
            elif connection.relative_position_to_source in [
                CD.SOURCE_COLLAPSED_POOL,
                CD.SOURCE_AND_TARGET_COLLAPSED_POOLS,
            ]:
                self.special_connections.append(connection)
                forge_logger.debug(f"{_log_string} SPECIAL port (collapsed pool).")

            else:
                raise RelativePositionCouldNotBeDetermined(connection.source, connection.target)

    def __assign_order_to_outgoing_connections(self):
        """
        Assigns an order to outgoing connections within each port based on their branching points.
        """

        # ------------------------------ NORTH PORT ------------------------------
        # Assign order to connections in the NORTH port (covers N and NW)
        # Order: First branching point is the furthest col and row distance from the source node.
        # Inside the column: Iterating over the rows of a column from furthest to closest first
        # Then changing to the second furthest column and iterating over the rows from furthest to closest and so on
        forge_logger.debug(f"Assigning order of NORTH port connections for shape {self.bound_shape.resource_id}")

        # Sort self.north_port_connections in place first by col_distance and then by row_distance
        self.north_port_connections.sort(key=lambda x: (x.col_distance, x.row_distance))
        for idx, connection in enumerate(self.north_port_connections):
            connection.order = idx + 1
            forge_logger.debug(
                f"Order {idx + 1} | Connection {connection.association.resource_id} | NORTH Port | ({connection.source} -> {connection.target})"
            )

        # ------------------------------ EAST PORT -------------------------------
        # Assign order to connections in the EAST port
        # This port covers connections in the E, SE and NE directions
        # The special case is the E direction, where the order could be 0, as it's a direct connection to the target node without any branching or
        # nodes in between. This is the only case where the association does not need any dockers.

        forge_logger.debug(f"Assigning order of EAST port connections for shape {self.bound_shape.resource_id}")

        ne_direction_connections_sorted = sorted(
            [
                connection
                for connection in self.east_port_connections
                if connection.relative_position_to_source == CD.NORTHEAST
            ],
            key=lambda x: (x.col_distance_abs, x.row_distance_abs),
        )

        e_direction_connections_sorted = sorted(
            [
                connection
                for connection in self.east_port_connections
                if connection.relative_position_to_source == CD.EAST
            ],
            key=lambda x: x.col_distance_abs,
            reverse=True,
        )

        se_direction_connections_sorted = sorted(
            [
                connection
                for connection in self.east_port_connections
                if connection.relative_position_to_source == CD.SOUTHEAST
            ],
            key=lambda x: (x.col_distance_abs, -x.row_distance_abs),
            reverse=True,
        )

        # Check for direct connection in the E direction
        for e_connection in e_direction_connections_sorted:
            if not self.global_grid_lookup.is_a_node_in_between_on_row(e_connection.source, e_connection.target):
                e_connection.is_straight_direct_connection = True
                forge_logger.debug(
                    f"Straight Direct Connection | Connection {e_connection.association.resource_id} | EAST Port | ({e_connection.source} -> {e_connection.target})"
                )
                break

        e_port_order = 0

        # NE connections first
        for connection in ne_direction_connections_sorted:
            connection.order = int(e_port_order)
            forge_logger.debug(
                f"Order {e_port_order} | Connection {connection.association.resource_id} | EAST Port | ({connection.source} -> {connection.target})"
            )
            e_port_order += 1

        # E connections second
        for connection in e_direction_connections_sorted:
            if connection.is_straight_direct_connection:
                continue
            connection.order = int(e_port_order)
            forge_logger.debug(
                f"Order {e_port_order} | Connection {connection.association.resource_id} | EAST Port | ({connection.source} -> {connection.target})"
            )
            e_port_order += 1

        # SE connections last
        for connection in se_direction_connections_sorted:
            connection.order = int(e_port_order)
            forge_logger.debug(
                f"Order {e_port_order} | Connection {connection.association.resource_id} | EAST Port | ({connection.source} -> {connection.target})"
            )
            e_port_order += 1

        # ------------------------------ SOUTH PORT ------------------------------
        # Assign order to connections in the SOUTH port (covers S, SW and W)
        # Order: First branching point is
        #   1. W direction: Closest col of the same row as the source node, then the next closest col and so on
        #   2. SW direction: Furthest col + row distance from the source node, moving inside the col from furthest to closest row, then next col
        #   3. S direction: Furthest row of the same col as the source node, then the next furthest row and so on
        forge_logger.debug(f"Assigning order of SOUTH port connections for shape {self.bound_shape.resource_id}")

        w_direction_connections_sorted = sorted(
            [
                connection
                for connection in self.south_port_connections
                if connection.relative_position_to_source == CD.WEST
            ],
            key=lambda x: x.col_distance_abs,
        )

        sw_direction_connections_sorted = sorted(
            [
                connection
                for connection in self.south_port_connections
                if connection.relative_position_to_source == CD.SOUTHWEST
            ],
            key=lambda x: (x.col_distance_abs, x.row_distance_abs),
        )

        s_direction_connections_sorted = sorted(
            [
                connection
                for connection in self.south_port_connections
                if connection.relative_position_to_source == CD.SOUTH
            ],
            key=lambda x: x.row_distance_abs,
            reverse=True,
        )

        all_south_connections_sorted = (
            w_direction_connections_sorted + sw_direction_connections_sorted + s_direction_connections_sorted
        )

        for idx, connection in enumerate(all_south_connections_sorted):
            connection.order = idx + 1
            forge_logger.debug(
                f"Order {idx + 1} | Connection {connection.association.resource_id} | SOUTH Port | ({connection.source} -> {connection.target})"
            )
