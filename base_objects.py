from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
from typing import Self
from typing import TypeAlias, Literal

# ================ TypeAliases ================
Guid: TypeAlias = str
EffectComponentType: TypeAlias = str
EffectComponentChildType: TypeAlias = str

# ================ Constants ================
known_effect_component_types = [
    "TLVoice",
    "TLAttitudeEvent",
    "TLShot",
    "TLSwitchStageEvent",
    "TLSoundEvent",
    "TLShowVisual",
    "TLLookAtEvent",
    "TLEmotionEvent",
    "TLTransform",
    "TLCameraFoV",
    "TLShowWeapon",
    "TLShowPeanuts",
    "TLShowArmor",
    "TLPhysics",
    "TLAnimation",
    "TLHandsIK",
    "TLPlayEffectEvent",
    "TLMaterial",
    "TLSwitchLocationEvent",
    "TLCameraDoF",
    "TLShapeShift",
    "TimelineActorPropertiesReflection",
    "TLSplatter",
    "TLEffectPhaseEvent",
    "TLSprings",
]
known_effect_component_child_type = [
    "Actor", 
    "Keys", 
    "TransformChannels", 
    "Key", 
    "TransformChannel",   
    "CameraContainer",
    "Channels",
    "MaterialParameter",
    "VisibilityChannel",
    "TargetTransform",
]

emotions_labels = {
    1: "neutral",
    2: "happy",
    4: "thinking",
    8: "angry",
    16: "fear",
    32: "sad",
    64: "surprised",
    128: "disgust",
    256: "sleeping",
    512: "dead",
    1024: "confusion",
    2048: "pain"
}


# ================ Helper Methods ================

def create_comment(msg: str) -> ET.Element:
    return ET.Comment(text=f"Edited - {msg}")



@dataclass
class NewAttribute:
    id_str: str
    type_str: str
    value: str
    is_relative_timestamp_attribute: bool = False
    debug_comment: str | None = None
    write_value_as_handle: bool = False

    def create_attribute_element(self) -> ET.Element:
        if self.write_value_as_handle:
            attributes = {
                    "id": self.id_str,
                    "type": self.type_str,
                    "handle": self.value,
                    "version": "1",
                }
        else:
            attributes = {
                    "id": self.id_str,
                    "type": self.type_str,
                    "value": self.value
                }
        return ET.Element("attribute", attrib=attributes)

# existing node
@dataclass
class BaseNode:
    _node: ET.Element
    _attribute_elements: dict[str, ET.Element]
    _children_element_container: ET.Element | None

    def __init__(self, element: ET.Element) -> None:
        assert isinstance(element, ET.Element), f"Wrong type {type(element)}"
        self._node = element
        attributes = element.findall("attribute") or []
        self._attribute_elements = { x.attrib["id"]: x for x in attributes}
        self._children_element_container = element.find("children")

    def add_child_node(self, node: ET.Element, child_index: int, debug_comment: str | None = None) -> None:
        if self._children_element_container is None:
            self._children_element_container = ET.Element("children")
            self._node.append(self._children_element_container)

        if child_index == -1:
            self._children_element_container.append(node)
        elif child_index < 0:
            child_index += len(list(self._children_element_container))
            self._children_element_container.insert(child_index, node)
        else:
            self._children_element_container.insert(child_index, node)
        comment_str = "Added child node"
        if debug_comment is not None:
            comment_str = f"{debug_comment} - {comment_str}"
        if child_index == -1:
            self._children_element_container.append(create_comment(comment_str))
        else:
            self._children_element_container.insert(child_index, create_comment(comment_str))

    def get_attribute_value_nonnil(self, name: str) -> str:
        element = self._attribute_elements.get(name)
        assert element is not None, f"element cannot be found for name {name} in node {self._node.attrib}"
        attribs = element.attrib
        if "value" in attribs:
            return attribs["value"]
        return element.attrib["handle"]
    
    def get_attribute_value(self, name: str) -> str | None:
        element = self._attribute_elements.get(name)
        if element is None:
            return None
        return element.attrib["value"]

    def _get_attribute_node(self, name: str) -> ET.Element | None:
        element = self._attribute_elements.get(name)
        return element 

    def _add_or_update_attribute_node(self, attr: NewAttribute) -> None:
        existing = self._get_attribute_node(name=attr.id_str)
        if existing is not None:
            self.update_value_for_attribute(name=attr.id_str, new_value=attr.value, debug_comment=attr.debug_comment)
        else:
            new_element = attr.create_attribute_element()
            any_element = list(self._attribute_elements.values())[0]
            any_element_index = list(self._node).index(any_element)
            self._node.insert(any_element_index + 1, new_element)
            comment_str = "Added new attribute"
            if attr.debug_comment is not None:
                comment_str = f"{attr.debug_comment} - {comment_str}"
            self._node.insert(any_element_index + 1, create_comment(comment_str))
            self._attribute_elements[attr.id_str] = new_element

    def _delete_child(self, child_element: ET.Element) -> None:
        child_index = list(self._children_element_container).index(child_element)
        self._children_element_container.remove(child_element)
        self._children_element_container.insert(child_index+1, create_comment(msg=f"Deleted child element {child_element.attrib}"))

    def _num_children(self) -> int:
        return len(list(self._children_element_container))
    
    def _get_children_elements(self, child_type: str | None = None) -> list[ET.Element]:
        if self._children_element_container is None:
            return []
        return [x for x in self._children_element_container if child_type is None or child_type == x.attrib.get("id", "")]
    
    def update_value_for_attribute(self, name: str, new_value: str, debug_comment: str | None = None) -> None:
        attribute_node = self._get_attribute_node(name=name)
        old_value = attribute_node.attrib["value"]
        attribute_node.attrib["value"] = new_value

        attribute_node_index = list(self._node).index(attribute_node)
        comment_str = f"Updated attribute {name} value from {old_value} to {new_value}"
        if debug_comment is not None:
            comment_str = f"{debug_comment} - {comment_str}"
        self._node.insert(attribute_node_index, create_comment(comment_str))
        self._attribute_elements[name] = attribute_node


# creation of a new node
@dataclass
class NewBaseNode:
    def create(self) -> ET.Element:
        assert False, "Should be overriden"

    def create_element(self, node_id: str | None, node_key: str | None = None, attributes: list[NewAttribute] = [], children: list[Self | ET.Element] = []) -> ET.Element:
        node_attr = {}
        if node_id is not None:
            node_attr["id"] = node_id
        if node_key is not None:
            node_attr["key"] = node_key

        node = ET.Element("node", node_attr)
        for attrib in attributes:
            attrib_node = attrib.create_attribute_element()
            node.append(attrib_node)
        
        if len(children) > 0:
            children_container = ET.Element("children")
            node.append(children_container)
            for child in children:
                if isinstance(child, ET.Element):
                    children_container.append(child)
                else:
                    child_element = child.create()
                    children_container.append(child_element)
        return node

@dataclass
class NewPhasesNode(NewBaseNode):
    duration: str
    dialog_node_id: Guid
    def create_element(self) -> ET.Element:
        return super().create_element(node_id="Phase", attributes=[
            NewAttribute(id_str="Duration", type_str="float", value= self.duration),
            NewAttribute(id_str="PlayCount", type_str="int32", value="1"),
            NewAttribute(id_str="DialogNodeId", type_str="guid", value=self.dialog_node_id),
        ],children=[ET.Element("node", attrib={"id": "QuestionHoldAutomation"})])

@dataclass
class NewTimelinePhasesNode(NewBaseNode):
    map_key: Guid
    map_value: int
    def create_element(self) -> ET.Element:
        return super().create_element(node_id="Object", node_key="MapKey", attributes=[
            NewAttribute(id_str="MapKey", type_str="guid", value= self.map_key),
            NewAttribute(id_str="MapValue", type_str="uint64", value=str(self.map_value)),
        ])

# new phase component node
@dataclass
class NewNode(NewBaseNode):
    node_id: str | None
    attributes: list[NewAttribute] = field(default_factory=list)
    children: list["NewNode"] = field(default_factory=list)
    debug_comment: str | None = None

    def create_element(self, phase_index: int, is_effect_component: bool, start_time: float | None = None, end_time: float | None = None) -> ET.Element:
        all_attributes = self.attributes.copy()

        if is_effect_component:
            all_attributes.append(
                NewAttribute(id_str="PhaseIndex", type_str="int64", value=str(phase_index))
            )          
            if start_time is not None:
                all_attributes.append(
                    NewAttribute(id_str="StartTime", type_str="float", value=str(start_time))
                )
            if end_time is not None:
                all_attributes.append(
                    NewAttribute(id_str="EndTime", type_str="float", value=str(end_time))
                )
        for a in all_attributes:
            if a.is_relative_timestamp_attribute and start_time is not None:
                current_time = float(a.value)
                if end_time is not None:
                    assert current_time + start_time <= end_time, f"{current_time=} {start_time=} {end_time=}"
                a.value = str(current_time + start_time)

        return super().create_element(node_id=self.node_id, attributes=all_attributes,children=[x.create_element(phase_index=phase_index, is_effect_component=False, start_time=start_time, end_time=end_time) for x in self.children])

