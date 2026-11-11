from diagramforge.SETUP import forge_logger


class DisallowedChildShape(Exception):
    def __init__(self, disallowed_child_shape, parent_resource_id):
        self.parent_resource_id = parent_resource_id
        disallowed_shape_resource_id = getattr(disallowed_child_shape, "resource_id", None)

        shape_repr = str(disallowed_child_shape)
        if len(shape_repr) > 100:
            shape_repr = f"{shape_repr[:100]}...[TRUNCATED]"

        self.disallowed_child_shape = f"{shape_repr} (Resource ID: {disallowed_shape_resource_id})"
        self.shape_output = f"<{self.disallowed_child_shape}> of class <{disallowed_child_shape.__class__.__name__}>"

    def log_and_return_message(self, container_type):
        message = (
            f"{container_type} (Resource ID: {self.parent_resource_id}) contains disallowed shape: {self.shape_output}"
        )
        forge_logger.error(message)
        return message


class DiagramDisallowedChildShape(DisallowedChildShape):
    def __str__(self):
        return self.log_and_return_message("Diagram")


class PoolDisallowedChildShape(DisallowedChildShape):
    def __str__(self):
        return self.log_and_return_message("Pool")


class LaneDisallowedChildShape(DisallowedChildShape):
    def __str__(self):
        return self.log_and_return_message("Lane")


class CollapsedPoolNoChildShapesAllowed(Exception):
    def __init__(self, resource_id):
        self.resource_id = resource_id

    def __str__(self):
        message = f"CollapsedPool (Resource ID: {self.resource_id}) cannot have child shapes."
        forge_logger.error(message)
        return message
