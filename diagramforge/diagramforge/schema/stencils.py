from enum import Enum


class ContainerStencil(str, Enum):
    BPMNDiagram = "BPMNDiagram"
    Pool = "Pool"
    CollapsedPool = "CollapsedPool"
    Lane = "Lane"


class TaskStencil(str, Enum):
    TASK = "Task"
    COLLAPSED_SUBPROCESS = "CollapsedSubprocess"
    EVENT_SUBPROCESS = "EventSubprocess"
    COLLAPSED_EVENT_SUBPROCESS = "CollapsedEventSubprocess"
    SUBPROCESS = "Subprocess"


class EventStencil(str, Enum):
    START_NONE = "StartNoneEvent"
    START_MESSAGE = "StartMessageEvent"
    START_TIMER = "StartTimerEvent"
    START_ERROR = "StartErrorEvent"
    START_COMPENSATION = "StartCompensationEvent"
    START_PARALLEL_MULTIPLE = "StartParallelMultipleEvent"
    START_ESCALATION = "StartEscalationEvent"
    START_CONDITIONAL = "StartConditionalEvent"
    START_MULTIPLE = "StartMultipleEvent"
    END_NONE = "EndNoneEvent"
    END_ESCALATION = "EndEscalationEvent"
    END_MESSAGE = "EndMessageEvent"
    END_ERROR = "EndErrorEvent"
    END_CANCEL = "EndCancelEvent"
    END_COMPENSATION = "EndCompensationEvent"
    END_SIGNAL = "EndSignalEvent"
    END_MULTIPLE = "EndMultipleEvent"
    END_TERMINATE = "EndTerminateEvent"
    INTERMEDIATE_PARALLEL_MULTIPLE_CATCHING = "IntermediateParallelMultipleEventCatching"
    INTERMEDIATE_ESCALATION = "IntermediateEscalationEvent"
    INTERMEDIATE_MESSAGE_CATCHING = "IntermediateMessageEventCatching"
    INTERMEDIATE_TIMER = "IntermediateTimerEvent"
    INTERMEDIATE_ERROR = "IntermediateErrorEvent"
    INTERMEDIATE_CANCEL = "IntermediateCancelEvent"
    INTERMEDIATE_CONDITIONAL = "IntermediateConditionalEvent"
    INTERMEDIATE_SIGNAL_CATCHING = "IntermediateSignalEventCatching"
    INTERMEDIATE_MULTIPLE_CATCHING = "IntermediateMultipleEventCatching"
    INTERMEDIATE_LINK_CATCHING = "IntermediateLinkEventCatching"
    INTERMEDIATE_COMPENSATION_CATCHING = "IntermediateCompensationEventCatching"
    INTERMEDIATE_ESCALATION_THROWING = "IntermediateEscalationEventThrowing"
    INTERMEDIATE = "IntermediateEvent"
    INTERMEDIATE_MESSAGE_THROWING = "IntermediateMessageEventThrowing"
    INTERMEDIATE_COMPENSATION_THROWING = "IntermediateCompensationEventThrowing"
    INTERMEDIATE_SIGNAL_THROWING = "IntermediateSignalEventThrowing"
    INTERMEDIATE_MULTIPLE_THROWING = "IntermediateMultipleEventThrowing"
    INTERMEDIATE_LINK_THROWING = "IntermediateLinkEventThrowing"


class GatewayStencil(str, Enum):
    EXCLUSIVE_DATABASED = "Exclusive_Databased_Gateway"
    PARALLEL = "ParallelGateway"
    INCLUSIVE = "InclusiveGateway"
    COMPLEX = "ComplexGateway"
    EVENTBASED = "EventbasedGateway"


class AssociationStencil(str, Enum):
    ASSOCIATION_UNDIRECTED = "Association_Undirected"
    ASSOCIATION_UNIDIRECTIONAL = "Association_Unidirectional"
    MESSAGE_FLOW = "MessageFlow"
    ASSOCIATION_BIDIRECTIONAL = "Association_Bidirectional"
    SEQUENCE_FLOW = "SequenceFlow"


class ArtifactStencil(str, Enum):
    TEXT_ANNOTATION = "TextAnnotation"
