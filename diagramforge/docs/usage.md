# Usage

This is a guide on how to use the Diagram Forge package the way it was intended. Here, "using" the package mainly means addresses the data input and its generation. There are two main ways to feed data to the Diagram Forge:

- **SPM Diagram JSON**: Primarily, this option should be used if there is a diagram in SPM already that needs to be downloaded and optimized with this package.
  
- **Diagram Model Representation**: This option is supposed to be the more approachable way during data creation, for instance, when creating a diagram from scratch or when working with a diagram in a different format during a migration.

Both options will yield the same result. The following is a guide on how to use the Model Representation option and why it is the better choice for most cases.

### Table of Contents

- [What is the "Model Representation"?](#what-is-the-model-representation)
- [Why is this package using Pydantic models?](#why-is-this-package-using-pydantic-models)
- [How to use the schema?](#how-to-use-the-schema)
  - [Example: Build a Diagram](#example-build-a-diagram)
- [Why is this the better choice?](#why-is-this-the-better-choice)

## What is the "Model Representation"?

The model, not to be confused with "diagram", is a Pydantic model that represents the structure of a BPMN diagram. In other words, it is an assortment of Python objects that can be created and manipulated in code. These objects are nothing more than Python classes on steroids, with the ability to validate their own data and to be converted to and from JSON. These objects are part of the schema module which you can find under [`diagramforge.schema`](../diagramforge/schema/).

## Why is this package using Pydantic models?

The main reason for using Pydantic models is that they provide a way to validate the data that is fed into the package. This is important because the package relies on the data being structured in a certain way. If the data is not structured correctly, the package will not be able to optimize the diagram. Pydantic models ensure that and provide precise error messages if the data is not structured correctly.

Additionally, it is very easy to mess up the JSON structure for SPM without knowing what went wrong. The Pydantic models try to mitigate the risk of hours of debugging.

### Note <!-- omit in toc -->
The Pydantic models are not perfect in any regard. There are some static values that needs to be updated as well as spots that would need some more validation or error handling. However, the models are a good starting point and can be improved over time.

## How to use the schema?

The schema module contains all BPMN diagram elements that are accepted in this package. The following elements (or shapes) are available and are always associated with their respective proprietary stencils from SPM:

- `Diagram`: The main class that contains all the elements of the diagram. Stencil: [`ContainerStencil.BPMNDiagram`](../diagramforge/schema/stencils.py).
- `Pool`: Represents a BPMN Pool. Stencil: [`ContainerStencil.POOL`](../diagramforge/schema/stencils.py)
- `Lane`: Represents a BPMN Lane. Stencil: [`ContainerStencil.Lane`](../diagramforge/schema/stencils.py)
- `Task`: Represents all types of BPMN Tasks. All Stencils enumerated in the [`TaskStencil`](../diagramforge/schema/stencils.py) class.
- `Event`: Represents a BPMN Event. All Stencils enumerated in the [`EventStencil`](../diagramforge/schema/stencils.py) class.
- `Gateway`: Represents a BPMN Gateway. All Stencils enumerated in the [`GatewayStencil`](../diagramforge/schema/stencils.py) class.
- `Association`: Represents a BPMN Association. All Stencils enumerated in the [`AssociationStencil`](../diagramforge/schema/stencils.py) class.

> ⚠️ Please mind that stencils that are not listed in [`stencils.py`](../diagramforge/schema/stencils.py) are not supported and will raise validation errors.
> 
In addition to these diagram elements, there are some more useful sub-elements in [`diagramforge.schema.base`](../diagramforge/schema/base.py):

- `Stencil`: Represents a BPMN stencil.
- `Coordinates`: Represents x and y coordinates. ***NOTE: The logic in the package takes care of this!***
- `Bounds`: Encapsulates the upper-left and lower-right bounds of a shape. ***NOTE: The logic in the package takes care of this!***
- `Target`: Represents a target shape by resource ID.
- `Properties`: Represents a collection of properties for a shape.
- `AssociationLabel`: Represents label data for an association relationship.
- `GatewayLabel`: Represents label data for a Gateway shape.

> ⚠️ Before diving into an example, please keep in mind that all custom properties (dictionary keys basically) within the data structures are considered aliases. This means that you can add any property to any shape as long as it is a valid JSON key. However, the package will not be able to validate these properties. Furthermore, to suit the format of SPM, all keys will be converted from snake_case to camelCase.

> ⚠️ META ATTRIBUTES: Custom attributes, prefixed with "meta-", are also affected by that. You have to use the bracket notation to access/edit these attributes, e.g. `shape.properties["meta-attribute"]` instead of e.g. `shape.properties.name`. Also mind that the meta attribute name will also be converted from snake_case to camelCase (does not affect the hyphen), so might use camelCase directly.

### Example: Build a Diagram

Above are all your building blocks for creating a BPMN diagram. You can create a diagram by instantiating these classes and adding them to the diagram and/or to each other. Here is an example:

```python  
from diagramforge.schema import Diagram, Pool, Lane, Task, Event, Gateway, Association
from diagramforge.schema.base import Coordinates, Bounds, Target, Properties, AssociationLabel, GatewayLabel
from diagramforge.schema.stencils import ContainerStencil, TaskStencil, EventStencil, GatewayStencil, AssociationStencil

# Create a diagram
diagram = Diagram(resource_id="diagram123")

diagram_level_properties = Properties(
    name="My Diagram",
    description="This is a simple diagram",
    ...  # Add more properties here
)

diagram.properties = diagram_level_properties

# Forgot a diagram level property? No problem, either
diagram.properties.responsible = "John Doe"

# or
diagram_level_properties.responsible = "John Doe"

# Create a pool for which you happen to have all properties
lane123 = Pool(
    resource_id="pool123",
    properties=Properties(
        name="My Pool",
        description="This is a simple pool",
        responsible="Jane Doe",
        ...  # Add more properties here
    )
)

# Add the pool to the diagram
diagram.child_shapes.append(pool)

# Create a lane for that you have all properties already in a dictionary called lane_properties
my_lane = Lane(resource_id="lane123", properties=Properties(**lane_properties))

# Add the lane to the pool
pool.child_shapes.append(lane123)

# Create a task
task123 = Task(
    resource_id="task123",
    properties=Properties(...),
    stencil=Stencil(TaskStencil.COLLAPSED_SUBPROCESS), # ... because SPM needs it as { "stencil": {"id": "CollapsedSubprocess"}}
)

# Add the task to the lane
lane123.child_shapes.append(task123)

# And so on...
```

## Why is this the better choice?

Let alone data validation, the main reason for using the Model Representation is that it is much easier to create and manipulate the diagram in code. At any given point in time, you could simply take `lane123` from the example above and append more child shapes or edit its properties. This is much easier than editing a JSON file.

Moreover, to facilitate access to all exiting shapes and elements throughout your code, you could create a dictionary that maps the resource ID to the shape. This way, you can easily access any shape and change it on the spot without having to traverse the entire diagram (unless you copy the elements of course).

Let's say, you have created all Tasks of all Lanes, but you have to update the Accountable role at a later point - maybe because the data is missing for now or just does not make sense in this part of the code. You could simply do this:

```python
# ... creating tasks ...
all_tasks_of_my_diagram = [... each time you create a task, append it here ...]

# or 
all_tasks_of_my_diagram_by_resource_id = {task.resource_id: task} # ... each time you create a task, add it to the dictionary ...

# ... later in the code ...
for task in all_tasks_of_my_diagram:
    task.properties.accountable = "John Doe"

# or respectively
for task in all_tasks_of_my_diagram_by_resource_id.values():
    task.properties.accountable = "John Doe"
```

Admittedly, you could achieve the same benefits by using dictionaries and lists in Python. However, the Pydantic models provide a more structured way of doing so and ensure that the data is structured correctly.