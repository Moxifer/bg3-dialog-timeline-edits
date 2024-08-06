from dataclasses import dataclass, field
import xml.etree.ElementTree as ET
from typing import Self
from typing import TypeAlias, Literal
from base_objects import NewAttribute, BaseNode, create_comment, NewNode, NewBaseNode, Guid, EffectComponentChildType, EffectComponentType,emotions_labels,known_effect_component_child_type, known_effect_component_types
from timeline_parser import EffectComponentNode, EffectComponentChildNode, TimelineTree



SplatterType: TypeAlias = Literal["Blood", "Dirt", "Bruise", "Sweat"]
SplatterTypeIndex = [
    "Blood",
    "Dirt",
    "Bruise",
    "Sweat",
]

@dataclass
class SplatterData:
    time_str: str
    value: str | None

def create_splatter_channels(splatter_data: dict[SplatterType, list[SplatterData]]) -> NewNode:
    splatter_channels = []
    for i, splatter_type in enumerate(SplatterTypeIndex):
        splatter_type_children = []
        if splatter_type in splatter_data:
            for c in splatter_data[splatter_type]:
                time_attribute = NewAttribute(id_str="Time", type_str="float", value=c.time_str, is_relative_timestamp_attribute=True)
                attributes = [time_attribute, NewAttribute(id_str="InterpolationType", type_str="uint8", value="2")]
                if  c.value is not None:
                    attributes.append(NewAttribute(id_str="Value", type_str="float", value=c.value))
                splatter_type_children.append(
                    NewNode(node_id="Key", attributes=attributes)
                )
        splatter_channels.append(
            NewNode(node_id="Channel", 
                    attributes=[NewAttribute(id_str="SplatterType", type_str="uint8", value=str(i))],  
                    children=[NewNode(node_id="Keys", children=splatter_type_children)] if len(splatter_type_children) > 0 else []))
    return NewNode(
                node_id="Channels",
                children=splatter_channels
            )

Vector4Float = tuple[float, float, float, float]


glowdata_parameters = [
    "EmissiveMult", # 1.25, 10
    "Fresnel_Power", # 1.62, 0.5, 0, 20
    "SphereMask_Intensity", # 1
    "Fresnel_Power_Emissive", # 10
    "OneMinus_Fresnel_Emissive", # 1
    "_Use_ColorGradient", # 1
    "Color_Max", # 1
    "Color_Mid", # 1
    "Color_Min", # 1, 0.4, 0.2
    "Mid_Max_Exponent", # 1
    "Mid_Position", #0.1
    "Min_Mid_Exponent", #1 
    "Color", 
    "DynamicParameter",
    "VisibilityChannel", # bool

]

@dataclass
class GlowData:
    # 0 to 255
    color: Vector4Float = (25, 0, 0, 1)
    dynamic_parameter: Vector4Float = (3, 0, 0, 0)

    @classmethod
    def create_parameter_children(cls, value: Vector4Float) -> list[NewNode]:
        return [NewNode(node_id="MaterialParameter", children=[
                NewNode(node_id="Keys", children=[
                    NewNode(node_id="Key", attributes=[
                        NewAttribute(id_str="Time", type_str="float", value="0", is_relative_timestamp_attribute=True),
                        NewAttribute(id_str="InterpolationType", type_str="uint8", value="2"),
                        NewAttribute(id_str="Value", type_str="float", value=x),
                    ])
                ])
            ]) for x in value]

    def create_color_parameters(self) -> list[NewNode]:
        return GlowData.create_parameter_children(value=self.color)


    def create_dynamic_parameters(self) -> list[NewNode]:
        return GlowData.create_parameter_children(value=self.dynamic_parameter)


eye_glow_id = "9caf0fad-81da-4469-9e61-2c1e17393d18" # TODO

def create_glow_node(node_uuid: str, actor_uuid: str, glow_data: GlowData) -> NewNode:
    glow_group_id = "f281ed2c-96b2-4269-a1ce-c7990311dc08"
    attributes = [
        NewAttribute(id_str="ID", type_str="guid", value=node_uuid),
        NewAttribute(id_str="Type", type_str="LSString", value="TLMaterial"),
        NewAttribute(id_str="GroupId", type_str="guid", value=glow_group_id),
        NewAttribute(id_str="IsContinuous", type_str="bool", value="True"),
        NewAttribute(id_str="IsOverlay", type_str="bool", value="True"),
        NewAttribute(id_str="IsSnappedToEnd", type_str="bool", value="True"),
    ]

    color_node = NewNode(
        node_id="Node",
        attributes=[
            NewAttribute(id_str="Dimensions", type_str="int32", value="4"),
            NewAttribute(id_str="MaterialParameterName", type_str="FixedString", value="Color")
        ],
        children=glow_data.create_color_parameters()
    )

    dynamic_param_node = NewNode(
        node_id="Node",
        attributes=[
            NewAttribute(id_str="Dimensions", type_str="int32", value="4"),
            NewAttribute(id_str="MaterialParameterName", type_str="FixedString", value="DynamicParameter")
        ],
        children=glow_data.create_dynamic_parameters()
    )

    visibility_node = NewNode(
        node_id="VisibilityChannel",
        children=[
            NewNode(node_id="Keys", children=[
                NewNode(node_id="Key", attributes=[
                    NewAttribute(id_str="Time", type_str="float", value="0", is_relative_timestamp_attribute=True),
                    NewAttribute(id_str="Value", type_str="bool", value="True")
                ])
            ])
        ]
    )

    children = [
        NewNode(node_id="Actor", attributes=[
            NewAttribute(id_str="UUID", type_str="guid", value=actor_uuid),
        ]),
        NewNode(node_id="MaterialParameter", children=[color_node, dynamic_param_node]),
        visibility_node,
    ]

    return NewNode(
        node_id="EffectComponent",
        attributes=attributes,
        children=children
    )







# ================ Creation Data Classes ================

@dataclass
class NodePathingData:
    node_id: str
    node_child_index: int

@dataclass
class AddAttributeToNode:
    node_uuid: str
    type_str: str
    pathing: list[NodePathingData]
    attribute: NewAttribute

    def add_attribute(self, effect_component: EffectComponentNode) -> None:
        next_node: EffectComponentChildNode | EffectComponentNode = effect_component
        for pathing in self.pathing:
            next_node = next_node.get_children_nodes(child_type=pathing.node_id)[pathing.node_child_index]
        next_node._add_or_update_attribute_node(attr=self.attribute)
                

@dataclass
class AddChildNodeToNode:
    node_uuid: str
    type_str: str
    pathing: list[NodePathingData]
    child_index: int
    node_to_add: NewNode

    def add_node(self, effect_component: EffectComponentNode) -> None:
        next_node: EffectComponentChildNode | EffectComponentNode = effect_component
        for pathing in self.pathing:
            children = next_node.get_children_nodes(child_type=pathing.node_id)
            assert len(children) > pathing.node_child_index, f"Number of children {len(children)} too little for child inedx {pathing.node_child_index}, {pathing}, {effect_component.uuid}"
            next_node = next_node.get_children_nodes(child_type=pathing.node_id)[pathing.node_child_index]
        
        next_node.add_child_node(node=self.node_to_add.create_element(
            phase_index=effect_component.phase_index,
            is_effect_component=False,
            start_time=effect_component.start_time,
            end_time=effect_component.end_time
        ), child_index=self.child_index, debug_comment=self.node_to_add.debug_comment)



# ================ Edit data summary ================

@dataclass
class SceneExtensionData:
    adjustment_amount: float #in seconds
    new_subduration_nodes: list[NewNode]
    extend_end_time_for_subdurations: list[str]

@dataclass
class SceneEditData:
    phase_index: int
    scene_extension_datas: list[SceneExtensionData] # a list so you can repeatedly extend
    new_effect_component_nodes: list[NewNode]
    attribute_changes: list[AddAttributeToNode]
    child_nodes_to_add: list[AddChildNodeToNode]

def run_scene_edits(tree: TimelineTree, edits: list[SceneEditData]):
    for edit in edits:
        print(f"Running edits for phase {edit.phase_index}...")
        for extension in edit.scene_extension_datas:
            print(f"    Extending phase by {extension.adjustment_amount} seconds, adding {len(extension.new_subduration_nodes)} new EffectComponent nodes to newly extended duration")
            tree.extend_phase_duration(
                phase_index=edit.phase_index, 
                adjustment_amount=extension.adjustment_amount, 
                new_nodes_for_subduration=extension.new_subduration_nodes, 
                extend_subdurations_of_types=extension.extend_end_time_for_subdurations)
        print(f"    Adding {len( edit.new_effect_component_nodes)} EffectComponent full duration nodes")
        for n in edit.new_effect_component_nodes:
            tree.content.effect.effect_component_phases[edit.phase_index].full_duration_nodes.append_new_node(new_node=n)

        print(f"    Adding/Updating {len(edit.attribute_changes)} attribute nodes")

        for change in edit.attribute_changes:
            phase = tree.content.effect.effect_component_phases[edit.phase_index]
            found_node = phase.get_node_by_uuid(node_uuid=change.node_uuid, node_type_str=change.type_str)
            change.add_attribute(effect_component=found_node)

        print(f"    Adding {len(edit.child_nodes_to_add)} child nodes")
        for add in edit.child_nodes_to_add:
            phase = tree.content.effect.effect_component_phases[edit.phase_index]
            found_node = phase.get_node_by_uuid(node_uuid=add.node_uuid, node_type_str=add.type_str)
            add.add_node(effect_component=found_node)
