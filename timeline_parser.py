import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import TypeAlias, Literal
from timeline_scene_parser import TimelineSceneTree

from base_objects import NewTimelinePhasesNode, NewPhasesNode, NewAttribute, BaseNode, create_comment, NewNode, NewBaseNode, Guid, EffectComponentChildType, EffectComponentType,emotions_labels,known_effect_component_child_type, known_effect_component_types
from dialog_tree_objects import DialogContent
from text_utils import TextEntry, TextKey
VERBOSE = False

@dataclass
class ActorMapContext:
    speaker_map: dict[str, str] = field(default_factory=lambda: {})  # map of actor ids
    peanut_map: dict[str, str] = field(default_factory=lambda: {})
    removed_speakers: list[str] = field(default_factory=lambda: [])
    removed_peanuts: list[str] = field(default_factory=lambda: [])
    custom_speaker_map_for_transform_node: dict[str, str] | None = None


    def has_actor_removal(self) -> bool:
        return len(self.removed_peanuts) > 0 or len(self.removed_speakers) > 0
    
    def should_remove(self, actor_uuid: str) -> bool:
        if actor_uuid in self.removed_speakers:
            return True
        if actor_uuid in self.removed_peanuts:
            return True
        return False
    
    def create_map(self, node_type: str | None) -> dict[str, str]:
        if node_type is not None and self.custom_speaker_map_for_transform_node is not None and node_type == "TLTransform":
            return self.custom_speaker_map_for_transform_node | self.peanut_map
        else:
            return self.speaker_map | self.peanut_map

    
@dataclass
class TimelinePrintInfoContext:
    dialog_text_map: dict[TextKey, TextEntry] | None = None # set to give more info for dialog nodes
    allowed_node_type_strs: list[str] | None = None # set to filter on node type
    allowed_actor_uuids: list[str] | None = None # set to filter on actor
    uuid_labels: dict[str, str] | None = None # provide extra debug labels for any uuids like speaker labels
    camera_id_to_name: dict[str, str] | None = None # camera id to readable name from scene file

@dataclass(frozen=True)
class EmotionData:
    emotion: int
    variation: int


@dataclass
class PhaseNode(BaseNode):
    duration: float
    duration_str: str
    dialog_node_id: Guid
    def __init__(self, element: ET.Element) -> None:
        super().__init__(element)
        self.duration_str = self.get_attribute_value_nonnil("Duration")
        self.duration = float(self.duration_str)
        self.dialog_node_id = self.get_attribute_value_nonnil("DialogNodeId")

    def update_duration(self, adjustment_amount: float) -> None:
        self.duration += adjustment_amount
        self.duration_str = str(self.duration)
        self.update_value_for_attribute(name="Duration", new_value=self.duration_str)

@dataclass
class EffectComponentChildNode(BaseNode):
    child_type: EffectComponentChildType
    def __init__(self, element: ET.Element) -> None:
        super().__init__(element)
        self.child_type = element.attrib.get("id", "")

    def get_children_nodes(self, child_type: str | None) -> list["EffectComponentChildNode"]:
        children_elements = self._get_children_elements(child_type=child_type)
        return [EffectComponentChildNode(element=x) for x in children_elements]
    

    def get_key_nodes(self) -> list["EffectComponentChildNode"]:
        return self.get_children_nodes(child_type="Key")

    def get_channel_nodes(self) -> list["EffectComponentChildNode"]:
        return self.get_children_nodes(child_type="Channel")

    def get_keys_nodes(self) -> list["EffectComponentChildNode"]:
        return self.get_children_nodes(child_type="Keys")
    
    def map_all_guid_children(self, guid_map: dict[Guid, Guid]) -> None:
        # iterate all children and map any attribute that has Guid type and matches existing_guid

        # check all attributes
        for attribute_name, attribute_element in self._attribute_elements.items():
            attr_type = attribute_element.attrib.get("type", "")
            if attr_type == "guid":
                value = attribute_element.attrib["value"]
                if value in guid_map:
                    old = attribute_element.attrib["value"] 
                    attribute_element.attrib["value"] = guid_map[value]
                    if VERBOSE:
                        print(f"Mapped {attribute_name} - {old} to {guid_map[value]}")

        # check all children
        children_elements = [EffectComponentChildNode(x) for x in self._get_children_elements(child_type=None)]
        for child in children_elements:
            child.map_all_guid_children(guid_map=guid_map)

    def shift_all_time_attributes(self, shift_amount: float) -> None:
        # iterate all children and map any attribute that has Guid type and matches existing_guid
        attributes_for_timestamps = [
            "Time"
        ]
        # check all attributes
        for attribute_name, attribute_element in self._attribute_elements.items():
            attr_type = attribute_element.attrib.get("type", "")
            if attribute_name in attributes_for_timestamps and attr_type == "float":
                old_value = float(attribute_element.attrib["value"])
                new_value = str(shift_amount + old_value)
                attribute_element.attrib["value"] = new_value
                if VERBOSE:
                    print(f"Shifted {attribute_name} - {old_value} to {new_value}")

        # check all children
        children_elements = [EffectComponentChildNode(x) for x in self._get_children_elements(child_type=None)]
        for child in children_elements:
            child.shift_all_time_attributes(shift_amount=shift_amount)

    def get_all_guid_children(self) -> list[Guid]:
        # blindly get all guids
        # check all attributes
        ret = []
        for attribute_name, attribute_element in self._attribute_elements.items():
            attr_type = attribute_element.attrib.get("type", "")
            if attr_type == "guid":
                value = attribute_element.attrib["value"]
                ret.append(value)

        # check all children
        children_elements = [EffectComponentChildNode(x) for x in self._get_children_elements(child_type=None)]
        for child in children_elements:
            child_guids = child.get_all_guid_children()
            ret.extend(child_guids)
        return ret
    def get_texture_channel_value(self) -> str | None:
        textures = self.get_children_nodes("TextureChannel")
        assert len(textures) == 1
        return textures[0].get_keys_nodes()[0].get_key_nodes()[0].get_attribute_value("Value")
    


    def get_color_channel_value(self) -> list[list[tuple[str, str]]]:
        color_keys = self.get_children_nodes("MaterialParameter")
        assert len(color_keys) == 4
        ret = []
        for color_node in color_keys:
            key_nodes = color_node.get_keys_nodes()[0].get_key_nodes()
            color_values = []
            for key_node in key_nodes:
                color_value = key_node.get_attribute_value("Value")
                color_time = key_node.get_attribute_value("Time")
                color_values.append((color_time, color_value))
            ret.append(color_values)
        return ret

@dataclass
class EffectComponentNode(EffectComponentChildNode):
    type_str: EffectComponentType
    uuid: Guid
    end_time: float
    end_time_str: str
    start_time: float
    start_time_str: str
    phase_index: int
    def __init__(self, element: ET.Element) -> None:
        super().__init__(element)
        self.type_str = self.get_attribute_value_nonnil("Type")
        self.uuid = self.get_attribute_value_nonnil("ID")
        self.end_time_str = self.get_attribute_value_nonnil("EndTime")
        self.end_time = float(self.end_time_str)
        self.start_time_str = self.get_attribute_value("StartTime") or "0"
        self.start_time = float(self.start_time_str)
        self.phase_index = int(self.get_attribute_value("PhaseIndex") or "0")

    def get_actor_uuid(self) -> Guid | None:
        children = self.get_children_nodes(child_type="Actor")
        if len(children) == 0:
            return None
        assert len(children) == 1, f"UNEXPECTED: {self.uuid} has more than 1 actor"
        return children[0].get_attribute_value("UUID")
    def get_material_parameter_nodes(self) -> dict[str, EffectComponentChildNode]:
        children = self.get_children_nodes(child_type="MaterialParameter")
        if len(children) == 0:
            return []
        assert len(children) == 1
        material_params = children[0].get_children_nodes(child_type="Node")
        ret = {}
        for node in material_params:
            param_type = node.get_attribute_value_nonnil(name="MaterialParameterName")
            ret[param_type] = node
        return ret


    def get_camera_container(self) -> Guid | None:
        children = self.get_children_nodes(child_type="CameraContainer")
        if len(children) == 0:
            return None
        assert len(children) == 1, f"UNEXPECTED: {self.uuid} has more than 1 camera"
        return children[0].get_attribute_value("Object")
    
    def get_transform_channels(self) -> list[EffectComponentChildNode]:
        return self.get_children_nodes(child_type="TransformChannels")

    def get_keys_template_id(self) -> str | None:
        keys = [y for x in self.get_keys()  for y in x.get_key_nodes()]
        for key in keys:
            t = key.get_attribute_value("TemplateId")
            if t is not None:
                return t
        return None
    
    def shift_timestamp(self, shift_amount: float) -> None:
        # start and end times need to be adjusted
        self.start_time += shift_amount
        self.end_time += shift_amount
        self.start_time_str = str(self.start_time)
        self.end_time_str = str(self.end_time)
        self._add_or_update_attribute_node(
            attr=NewAttribute(id_str="StartTime", type_str="float", value=self.start_time_str)
        )
        self.update_value_for_attribute(name="EndTime", new_value=self.end_time_str)

        self.shift_all_time_attributes(shift_amount=shift_amount)

    def get_keys(self) -> list[EffectComponentChildNode]:
        return self.get_children_nodes(child_type="Keys")
    
    def get_time_keys_in_keys(self) -> list[str]:
        keys = self.get_children_nodes(child_type="Keys")
        if len(keys) == 0:
            return []
        assert len(keys) == 1
        key_nodes = keys[0].get_children_nodes("Key")
        ret = []
        for key in key_nodes:
            time_key = key.get_attribute_value("Time")
            if time_key is not None:
                ret.append(time_key)
        return ret
    
    # time, emotion, variation
    def get_emotions_keys(self) -> list[tuple[str | None, str | None, str | None]]:
        if self.type_str != "TLEmotionEvent":
            return []
        keys = self.get_children_nodes(child_type="Keys")
        if len(keys) == 0:
            return []
        assert len(keys) == 1
        key_nodes = keys[0].get_children_nodes("Key")
        ret = []
        for key in key_nodes:
            ret.append((key.get_attribute_value("Time"), key.get_attribute_value("Emotion"), key.get_attribute_value("Variation")))
        return ret
    
    def get_time_keys_in_channel(self) -> list[list[tuple[float | None,float]]]: # lits of chanenls, list of keys, tuple of time and value
        channels = self.get_children_nodes(child_type="Channels")
        if len(channels) == 0:
            return []
        
        channel_nodes = channels[0].get_children_nodes(child_type="Channel")
        channels_result = []
        for channel in channel_nodes:
            channel_result = []
            channels_result.append(channel_result)
            keys = channel.get_children_nodes(child_type="Keys")
            if len(keys) == 0:
                continue
            assert len(keys) == 1
            key_nodes = keys[0].get_children_nodes(child_type="Key")
            for key in key_nodes:
                channel_result.append((key.get_attribute_value(name="Time"), key.get_attribute_value(name="Value")))
        return channels_result
    def map_emotions(self, emotion_map: dict[EmotionData, EmotionData]) -> None:
        if self.type_str != "TLEmotionEvent":
            return []
        keys = self.get_children_nodes(child_type="Keys")
        if len(keys) == 0:
            return []
        assert len(keys) == 1

        key_nodes = keys[0].get_children_nodes("Key")
        for key in key_nodes:
            emotion = key.get_attribute_value("Emotion") or "1"
            variation = key.get_attribute_value("Variation") or "0"
            data = EmotionData(int(emotion), int(variation))
            if data in emotion_map:
                mapped = emotion_map[data]
                key._add_or_update_attribute_node(attr=NewAttribute(id_str="Emotion", type_str="int32", value=str(mapped.emotion), debug_comment="Mapping emotion"))
                key._add_or_update_attribute_node(attr=NewAttribute(id_str="Variation", type_str="int32", value=str(mapped.variation), debug_comment="Mapping emotion"))

        
    def get_time_keys_in_transform_channel(self) -> list[list[tuple[float | None,float]]]: # lits of chanenls, list of keys, tuple of time and value
        channels = self.get_children_nodes(child_type="TransformChannels")
        if len(channels) == 0:
            return []
        
        channel_nodes = channels[0].get_children_nodes(child_type="TransformChannel")
        channels_result = []
        for channel in channel_nodes:
            channel_result = []
            channels_result.append(channel_result)
            keys = channel.get_children_nodes(child_type="Keys")
            if len(keys) == 0:
                continue
            assert len(keys) == 1
            key_nodes = keys[0].get_children_nodes(child_type="Key")
            for key in key_nodes:
                channel_result.append((key.get_attribute_value(name="Time"), key.get_attribute_value(name="Value")))
        return channels_result

    def keys_to_print_str(self, time_keys: list[list[tuple[str,str]]]) -> str:
        if len(time_keys) > 0:
            time_keys_str = ""
            for i, channel in enumerate(time_keys):
                if len(channel) == 0:
                    continue
                time_keys_str += f"\n      channel {i}"
                for key in channel:
                    time_keys_str += f"\n            [{key[0]}] value={key[1]}"
            return time_keys_str
        return ""

    def print_info(self, context: TimelinePrintInfoContext) -> None:
        actor = self.get_actor_uuid()
        time_keys = self.get_time_keys_in_channel()
        keys = self.get_time_keys_in_keys()
        if self.type_str not in known_effect_component_types:
            print(f"FOUND UNKNOWN TYPE {self.type_str}")
        if actor is not None:
            if actor in context.uuid_labels:
                mapped = context.uuid_labels[actor]
                if mapped in context.uuid_labels:
                    mapped += f" {context.uuid_labels[mapped]}"
                actor += f"({mapped})"
        if self.type_str == "TLShot":
            cam_container = self.get_camera_container()
            if cam_container in context.uuid_labels:
                cam_container += f"({context.uuid_labels[cam_container]})"
            print(f"   {self.type_str}={self.uuid} - CameraContainer={cam_container}")
        elif self.type_str == "TLEmotionEvent":
            emotion_keys = self.get_emotions_keys()
            emotion_info = ""
            i = 0
            for time_str, emotion, variation in emotion_keys:
                if emotion is not None:
                    emotion_label = emotions_labels[int(emotion)]
                else:
                    emotion_label = emotions_labels[1]
                emotion_info += f"\n        {i} [{time_str}] {emotion_label} ({variation or 0})"
                i += 1

            print(f"   {self.type_str}={self.uuid} - Actor={actor} Emotions={emotion_info}")
        elif self.type_str == "TLVoice":
            dialog_key = TextKey(
                dialog_node_id=self.get_attribute_value("DialogNodeId"),
                line_id=self.get_attribute_value("ReferenceId")
            )
            dialog_entry = context.dialog_text_map.get(dialog_key, None)
            print(f"   {self.type_str}={self.uuid} - Actor={actor} - Dialog={dialog_entry}")
        elif self.type_str == "TLLookAtEvent":
            keys = self.get_keys()
            key_info = []
            if len(keys) > 0:
                assert len(keys) == 1
                for key in keys[0].get_key_nodes():
                    target = key.get_attribute_value("Target")
                    time = key.get_attribute_value("Time")
                    key_info.append((time, target))

            print(f"   {self.type_str}={self.uuid} - Actor={actor} - Target={key_info}")

        elif self.type_str == "TLTransform":
            transform_time_keys = self.get_time_keys_in_transform_channel()
            print(f"   {self.type_str}={self.uuid} - Actor={actor} - TransformChannels={self.keys_to_print_str(transform_time_keys)}")
        elif self.type_str == "TLMaterial":
            group_id = self.get_attribute_value("GroupId")
            if group_id in context.uuid_labels:
                group_id += f"({context.uuid_labels[group_id]})"
            visibility_child = self.get_children_nodes(child_type="VisibilityChannel")
            keys_info = ""
            material_params = self.get_material_parameter_nodes()
            texture = "none"
            if "ColorRamp" in material_params:
                colorrampnode = material_params["ColorRamp"]
                texture = colorrampnode.get_texture_channel_value()
                if texture is not None:
                    if texture in context.uuid_labels:
                        texture += f"({context.uuid_labels[texture]})"
            color_info = "none"
            if "Color" in material_params:
                color_channels = material_params["Color"].get_color_channel_value()
                color_info = str(color_channels)


            if len(visibility_child) > 0:
                # print keys of visiblity
                child = visibility_child[0]
                all_keys_nodes = keys = child.get_keys_nodes()
                if len(all_keys_nodes) > 0:
                    keys = child.get_keys_nodes()[0].get_key_nodes()
                    keys_info = [f"{x.get_attribute_value(name="Time")} {x.get_attribute_value(name="Value")}" for x in keys]
            print(f"   {self.type_str}={self.uuid} - Actor={actor} GroupId={group_id}) Texture={texture} Color={color_info} Visibility={keys_info}")

        elif self.type_str == "TLAnimation":
            slot = self.get_attribute_value("AnimationSlot")
            group = self.get_attribute_value("AnimationGroup")
            animation_source_id = self.get_attribute_value_nonnil("AnimationSourceId")
            if animation_source_id in context.uuid_labels:
                animation_source_id += f" ({context.uuid_labels[animation_source_id]})"
            print(f"   {self.type_str}={self.uuid} - Actor={actor} AnimationSourceId={animation_source_id} (offset={self.get_attribute_value("AnimationPlayStartOffset") or "none"}) slot={slot} group={group}")
        elif self.type_str == "TLShapeShift":
            template_id = self.get_keys_template_id()
            if template_id is not None:
                print(f"   {self.type_str}={self.uuid} - Actor={actor} {template_id=}")
            else:
                print(f"   {self.type_str}={self.uuid} - Actor={actor} EmptyShapeshift (inherited)")
        else:
            out_str = f"   {self.type_str}={self.uuid}"
            if actor is not None:
                out_str += f" - Actor={actor}"
            if len(time_keys) > 0:
                out_str += f" - Channels={self.keys_to_print_str(time_keys)}"
            if len(keys) > 0:
                out_str += f" - Keys={keys}"
            print(out_str)




@dataclass
class DurationNodes:
    _phase_index: int
    _container_element: ET.Element
    start_time: float
    end_time: float
    nodes_by_type: dict[str, list[EffectComponentNode]]
    def __post_init__(self) -> None:
        self.duration = self.end_time - self.start_time
    
    def remove_all_nodes(self) -> None:
        for _, nodes in self.nodes_by_type.items():
            for node in nodes:
                print(f"Remove {node.uuid} {node.type_str}")
                self._container_element.remove(node._node)
        self.nodes_by_type = {}
        self.end_time = self.start_time
    
    def remove_node(self, node: EffectComponentNode) -> bool:
        if node.type_str not in self.nodes_by_type:
            return False
        if node in self.nodes_by_type[node.type_str]:
            self.nodes_by_type[node.type_str].remove(node)
            return True
        return False

    def append_new_node(self, new_node: NewNode) -> None:
        element = new_node.create_element(phase_index=self._phase_index, is_effect_component=True, start_time=self.start_time, end_time=self.end_time)

        # insert under one of the existing nodes
        existing_node = list(self.nodes_by_type.values())[-1][-1]._node
        existing_node_index = list(self._container_element).index(existing_node)
        self._container_element.insert(existing_node_index + 1, element)
        comment_str = "Added new node"
        if new_node.debug_comment is not None:
            comment_str = f"{new_node.debug_comment} - {comment_str}"
        self._container_element.insert(existing_node_index + 1, create_comment(comment_str))

        new_effect_component = EffectComponentNode(element=element)
        if new_effect_component.type_str not in self.nodes_by_type:
            self.nodes_by_type[new_effect_component.type_str] = [new_effect_component]
        else:
            self.nodes_by_type[new_effect_component.type_str].append(new_effect_component)


    def update_end_time(self, new_end_time: str) -> None:
        self.end_time = float(new_end_time)
        for _, nodes in self.nodes_by_type.items():
            for n in nodes:
                n.end_time = float(new_end_time)
                n.end_time_str = new_end_time
                n.update_value_for_attribute(name="EndTime", new_value=new_end_time)
        self.duration = self.end_time - self.start_time

    def shift_timestamp(self, shift_amount: float) -> None:
        self.start_time += shift_amount
        self.end_time += shift_amount
        for _, nodes in self.nodes_by_type.items():
            for n in nodes:
                n.shift_timestamp(shift_amount=shift_amount)

    def num_nodes(self) -> int:
        return sum([len(x) for x in self.nodes_by_type.values()])
    
    @classmethod
    def create(cls, start_time: float, end_time: float, all_nodes: list[EffectComponentNode], container_element: ET.Element, phase_index: int) -> "DurationNodes":
        nodes_by_type: dict[str, list[EffectComponentNode]] = {}


        for node in all_nodes:
            if node.type_str not in nodes_by_type:
                nodes_by_type[node.type_str] = [node]
            else:
                nodes_by_type[node.type_str].append(node)
        assert len(all_nodes) == sum([len(x) for x in nodes_by_type.values()])
        return DurationNodes(_phase_index=phase_index, _container_element=container_element, start_time=start_time, end_time=end_time, nodes_by_type=nodes_by_type)
    
    def print_info(self, context: TimelinePrintInfoContext) -> None:
        did_print_header = False
        for node_type, nodes in sorted(self.nodes_by_type.items()):
            if context.allowed_node_type_strs is not None:
                if node_type not in context.allowed_node_type_strs:
                    continue

            did_print_subheader = False
            for n in nodes:
                if context.allowed_actor_uuids is not None:
                    actor = n.get_actor_uuid()
                    if actor is not None and actor not in context.allowed_actor_uuids:
                        continue

                if not did_print_header:
                    print(f"[{self.start_time}] - [{self.end_time}] ({self.end_time - self.start_time:.2f}s)")
                    did_print_header = True
                if not did_print_subheader:
                    print(f" {node_type}: {len(nodes)}")
                    did_print_subheader = True
                
                n.print_info(context=context)


    
@dataclass
class EffectComponentPhase:
    _container_element: ET.Element
    phase_index: int
    phase_nodes: list[EffectComponentNode] # only used for init, may not be up to date if stuff gets added to subdurations directly

    full_duration_nodes: DurationNodes = field(init=False)
    sub_duration_nodes: list[DurationNodes] = field(init=False)

    nodes_by_uuid: dict[str, EffectComponentNode] | None = None

    def get_node_by_uuid(self, node_uuid: str, node_type_str: str) -> EffectComponentNode:
        if self.nodes_by_uuid is None:
            self.nodes_by_uuid = {}
            for node in self.phase_nodes:
                assert node.uuid not in self.nodes_by_uuid
                self.nodes_by_uuid[node.uuid] = node
        n =  self.nodes_by_uuid[node_uuid]
        assert n.type_str == node_type_str
        return n
    
    def get_referenced_guids(self) -> list[str]:
        # return uuids used by nodes in this phase
        # for camera container, actor, animation, stage... everything basically
        # TODO can return the guid attribute name if needed
        ret = []
        for node in self.phase_nodes:
            node_guids = node.get_all_guid_children()
            ret.extend(node_guids)
        return ret
    
    def remove_phase_node(self, node: EffectComponentNode) -> None:
        if self.full_duration_nodes.remove_node(node=node):
            if self.nodes_by_uuid is not None:
                del self.nodes_by_uuid[node.uuid]
            self.phase_nodes.remove(node)
            self._container_element.remove(node._node)
            return # removed from full duration
        for sub_duration in self.sub_duration_nodes:
            if sub_duration.remove_node(node=node):
                if self.nodes_by_uuid is not None:
                    del self.nodes_by_uuid[node.uuid]
                self.phase_nodes.remove(node)
                self._container_element.remove(node._node)
                return # removed from subduration
        assert False, "Did not find node"

    def remove_last_subduration(self) -> None:
        # find the subduration that's at the end and remove all nodes in there
        latest_start_time = None
        this_subduration = None
        print(f"There are {len(self.sub_duration_nodes)} subdurations")
        for subduration in self.sub_duration_nodes:
            if subduration.end_time == self.full_duration_nodes.end_time:
                if latest_start_time is None or latest_start_time < subduration.start_time:
                    latest_start_time = subduration.start_time
                    this_subduration = subduration
        assert this_subduration is not None
        print(f"Deleting subduration {this_subduration.start_time} to {this_subduration.end_time}")
        # remove this_subduration
        for _, nodes in this_subduration.nodes_by_type.items():
            for node in nodes:
                self.phase_nodes.remove(node)
        
        this_subduration.remove_all_nodes()
        self.sub_duration_nodes.remove(this_subduration)
        self.nodes_by_uuid = None
       

        # update full duration to be shorter if this removal caused the full length to shorten
        latest_end_time = None
        for subduration in self.sub_duration_nodes:
            if latest_end_time is None or latest_end_time < subduration.end_time:
                latest_end_time = subduration.end_time
        assert latest_end_time is not None
        print(f"Updating end time from {self.full_duration_nodes.end_time} to {latest_end_time}")
        self.full_duration_nodes.update_end_time(new_end_time=str(latest_end_time))
        
    def add_new_subduration(self, subduration_start: float, subduration_end: float, nodes: list[EffectComponentNode]) -> None:
        for s in self.sub_duration_nodes:
            assert not (s.start_time == subduration_start and s.end_time == subduration_end), f"subduration to add already exists, {subduration_start=} {subduration_end=}"
        new_subduration = DurationNodes.create(start_time=subduration_start, end_time=subduration_end, all_nodes=nodes, container_element=self._container_element, phase_index=self.phase_index)
        self.sub_duration_nodes.append(new_subduration)
    
    def extend_end_timestamp(self, adjustment_amount: float, nodes_for_new_subduration: list[NewNode], extend_subdurations_of_types: list[str]) -> None:
        current_end_time = self.full_duration_nodes.end_time
        new_end_time =self.full_duration_nodes.end_time + adjustment_amount

        # extend the full duration
        self.full_duration_nodes.update_end_time(new_end_time=str(new_end_time))

        # we don't extend sub duration nodes automatically. only do it for specific node types
        if len(extend_subdurations_of_types) > 0:
            for subduration in self.sub_duration_nodes:
                if abs(subduration.end_time - current_end_time) < 0.001:
                    # extract types matching what we want and create new subduratin node
                    nodes_to_move: list[EffectComponentNode] = []
                    for type_str in extend_subdurations_of_types:
                        if type_str in subduration.nodes_by_type:
                            nodes_to_move.extend(subduration.nodes_by_type[type_str])
                            del subduration.nodes_by_type[type_str]
                    
                    if len(nodes_to_move) == 0:
                        continue
                    for node in nodes_to_move:
                        node.update_value_for_attribute("EndTime", new_value=str(new_end_time))
                    new_subduration = DurationNodes.create(start_time=subduration.start_time, end_time=new_end_time, all_nodes=[], container_element=self._container_element, phase_index=self.phase_index)
                    self.sub_duration_nodes.append(new_subduration)


        # add a new subduration that starts at the previous end duration
        if len(nodes_for_new_subduration) > 0:
            subduration_start_time = current_end_time
            subduration_end_time = new_end_time
            new_elements = [x.create_element(phase_index=self.phase_index, is_effect_component=True, start_time=subduration_start_time, end_time=subduration_end_time) for x in nodes_for_new_subduration]
            new_nodes = [EffectComponentNode(element=new_element) for new_element in new_elements]
            new_subduration = DurationNodes.create(start_time=subduration_start_time, end_time=subduration_end_time, all_nodes=new_nodes, container_element=self._container_element, phase_index=self.phase_index)
            self.sub_duration_nodes.append(new_subduration)

            last_existing_node = self.phase_nodes[-1]
            self.phase_nodes.extend(new_nodes)

            last_existing_node_index = list(self._container_element).index(last_existing_node._node)
            for n in reversed(new_elements):
                self._container_element.insert(last_existing_node_index+1, n)
                self._container_element.insert(last_existing_node_index + 1, create_comment(f"Added new node for extended duration {adjustment_amount}s"))


    def print_info(self, context:TimelinePrintInfoContext) -> None:
        print(f"Info for EffectComponent: PhaseIndex={self.phase_index}")
        print(f"Full duration: {self.full_duration_nodes.num_nodes()} nodes")
        self.full_duration_nodes.print_info(context=context)
        print(f"Subdurations: {sum([x.num_nodes() for x in self.sub_duration_nodes])} nodes")
        for node in self.sub_duration_nodes:
            node.print_info(context=context)

    def shift_timestamp(self, shift_amount: float) -> None:
        self.full_duration_nodes.shift_timestamp(shift_amount=shift_amount)
        for s in self.sub_duration_nodes:
            s.shift_timestamp(shift_amount=shift_amount)

    def remove_shapeshift_by_template_id(self, template_id: str , actor: str | None) -> None:
        for node in self.phase_nodes:
            if node.type_str == "TLShapeShift":
                this_actor = node.get_actor_uuid()
                if (this_actor is not None and this_actor == actor) or actor is None:
                    keys = node.get_children_nodes(child_type="Keys")
                    if len(keys) > 0:
                        assert len(keys) == 1
                        keys_container = keys[0]
                        key_nodes = keys_container.get_key_nodes()
                        for key in key_nodes:
                            this_template_id = key.get_attribute_value(name="TemplateId")
                            print(f"Found template id {this_template_id}")
                            if this_template_id is not None and this_template_id == template_id:
                                # delete this child
                                print(f"Deleted teimplate {template_id}")
                                keys_container._delete_child(key._node)
                        if keys_container._num_children() == 0:
                            # delete the whole keys
                            node._delete_child(keys_container._node)
    def map_emotions(self, actor: str, emotion_map: dict[EmotionData, EmotionData]) -> None:
        for node in self.phase_nodes:
            if node.type_str == "TLEmotionEvent":
                this_actor = node.get_actor_uuid()
                if actor == this_actor:
                    # map this!
                    node.map_emotions(emotion_map=emotion_map)


    def force_show_armor_to_camp_clothing(self, actor: str, clothing_type: Literal["Camp", "Armor","All", "Naked"]) -> None:
        total_slots = 11
        # channels default to true (armor visible) and inherit the overrides from nodes before them.
        # so empty nodes inherit from previous nodes
        # if channel has no key it means use previous
        interpolation_index = lambda _: 5
        value_fn = lambda _: "True"
        # underwear is 10
        # vanity is 5 and 6
        if clothing_type == "Camp":
            clothing_slots = [5,6]
        elif clothing_type == "Armor":
            clothing_slots = [0, 4, 7]
        elif clothing_type == "Naked":
            clothing_slots = [0, 1, 3, 4, 5, 6,10]
            value_fn = lambda _: "False"
        else:
            clothing_slots = [0, 1, 3, 4, 5, 6,10]
            interpolation_index = lambda _: 2
            value_fn = lambda _: "True"

        for node in self.phase_nodes:
            if node.type_str == "TLShowArmor":
                this_actor = node.get_actor_uuid()
                if this_actor is not None and this_actor != actor:
                    continue

                channels = node.get_children_nodes(child_type="Channels")
                if len(channels) > 0:
                    channel_children = channels[0].get_children_nodes(child_type="")
                    for c in channel_children:
                        channels[0]._delete_child(child_element=c._node)
                    channels_container = channels[0]
                else:
                    new_channels_container = NewNode(node_id="Channels")
                    new_channels_container_element = new_channels_container.create_element(phase_index=self.phase_index, is_effect_component=False, start_time=None, end_time=None)
                    node.add_child_node(node=new_channels_container_element, child_index=-1, debug_comment="Show camp armor channels container")
                    channels_container = EffectComponentChildNode(element=new_channels_container_element)


                armor_slot_nodes = channels_container.get_children_nodes(child_type="")
                for existing_armor_slot_node in armor_slot_nodes:
                    channels_container._delete_child(existing_armor_slot_node._node)

                # add camp slots
                for slot_index in range(total_slots):
                    if slot_index in clothing_slots:
                        this_clothing_interpolation = interpolation_index(slot_index)
                        attributes = [NewAttribute(id_str="InterpolationType", type_str="uint8", value=str(this_clothing_interpolation)),
                                        NewAttribute(id_str="Time", type_str="float", value=str(self.full_duration_nodes.start_time))]
                        value = value_fn(slot_index)
                        if value is not None:
                            attributes.append(NewAttribute(id_str="Value", type_str="bool", value=value))
                        new_slot_key = NewNode(
                            node_id="Key",
                            attributes=attributes,
                        )
                        new_slot_keys = NewNode(
                            node_id="Keys",
                            children=[new_slot_key]
                        )
                        new_slot = NewNode(
                            node_id="",
                            children=[new_slot_keys]
                        )
                    else:
                        new_slot = NewNode(
                            node_id="",
                        )
                    channels_container.add_child_node(node=new_slot.create_element(phase_index=self.phase_index, is_effect_component=False, start_time=None, end_time=None), child_index=-1, debug_comment="Show camp armor")



    def __post_init__(self) -> None:
        # find start and end time ranges
        min_start_time = None
        max_end_time = None
        for node in self.phase_nodes:
            if min_start_time is None or node.start_time < min_start_time:
                min_start_time = node.start_time
            if max_end_time is None or node.end_time > max_end_time:
                max_end_time = node.end_time
        assert min_start_time is not None
        assert max_end_time is not None


        # calculate full duration nodes
        full_duration_nodes_by_type: dict[str, list[EffectComponentNode]] = {}
        # calculate sub duration nodes
        sub_duration_nodes_by_type: dict[tuple[float, float], list[EffectComponentNode]] = {}

        for node in self.phase_nodes:
            if node.start_time == min_start_time and node.end_time == max_end_time:
                # full duration node
                if node.type_str in full_duration_nodes_by_type:
                    full_duration_nodes_by_type[node.type_str].append(node)
                else:
                    full_duration_nodes_by_type[node.type_str] = [node]
            else:
                # sub duration node
                timestamp_tuple = (node.start_time, node.end_time)
                if timestamp_tuple in sub_duration_nodes_by_type:
                    sub_duration_nodes_by_type[timestamp_tuple].append(node)
                else:
                    sub_duration_nodes_by_type[timestamp_tuple] = [node]
        
        self.full_duration_nodes = DurationNodes(_phase_index=self.phase_index, _container_element=self._container_element, start_time=min_start_time, end_time=max_end_time, nodes_by_type=full_duration_nodes_by_type)

        # make sure sub durations are successive
        last_timestamp_tuple = None
        self.sub_duration_nodes: list[DurationNodes] = []
        for (timestamp_tuple, nodes) in sorted(sub_duration_nodes_by_type.items()):
            #if last_timestamp_tuple is not None:
            #    assert last_timestamp_tuple[1] == timestamp_tuple[0], f"Sub duration timestamps must be connected. {last_timestamp_tuple=} {timestamp_tuple=} {min_start_time=} {max_end_time=}"

           # last_timestamp_tuple = timestamp_tuple
            self.sub_duration_nodes.append(DurationNodes.create(start_time=timestamp_tuple[0], end_time=timestamp_tuple[1], all_nodes=nodes, container_element=self._container_element, phase_index=self.phase_index))



@dataclass
class TimelineContentEffect(BaseNode):
    duration: float
    duration_str: str
    phases: list[PhaseNode]
    effect_component_phases: list[EffectComponentPhase]
    _effect_components_children_container: ET.Element
    _phases_children_container: ET.Element

    def map_all_guid_children(self, guid_map: dict[str, str], node_type: str) -> None:
        for phase in self.effect_component_phases:
            for phase_node in phase.phase_nodes:
                if phase_node.type_str == node_type:
                    phase_node.map_all_guid_children(
                    guid_map=guid_map
                )

    def append_new_phase(self, existing_phase_to_append: EffectComponentPhase, actor_map_context: ActorMapContext, new_dialog_node_id: Guid, new_reference_id: Guid | None = None) -> int:
        # we need to copy this phase and adjust the timestamps + phase index + actors
        # plus add new phase node higher up and add a new phase here, and adjust total duration. phew
        # TODO swap positions for reverse kisses


        # for now assume this is a destructive operation and the previous EffectComponentPhase should no longer be used.
        new_phase_index = len(self.phases)

        assert len(self.effect_component_phases) == new_phase_index, f"{len(self.effect_component_phases)} == {new_phase_index}"

        new_start_time = self.effect_component_phases[-1].full_duration_nodes.end_time
        new_phase = existing_phase_to_append
        new_phase_nodes = []
        old_start_time = existing_phase_to_append.full_duration_nodes.start_time
        new_phase_dur = existing_phase_to_append.full_duration_nodes.duration
        assert new_phase_dur > 1, f"this node has a duration of {new_phase_dur} which is suspiciously small {existing_phase_to_append.full_duration_nodes.start_time} {existing_phase_to_append.full_duration_nodes.end_time}"
        print(f"Adding new phase {new_phase_index} {new_phase_dur}s from {new_start_time} to {new_start_time + new_phase_dur}")


        shift_amount = new_start_time - old_start_time
        # TODO emotion mapping
        for phase_node in existing_phase_to_append.phase_nodes:
            # we can use the shift method for adjusting the time
            phase_node.shift_timestamp(shift_amount=shift_amount)

            # update the phase index

            phase_node._add_or_update_attribute_node(
                attr=NewAttribute(id_str="PhaseIndex", type_str="int64", value=str(new_phase_index))
            )
            phase_node.phase_index = new_phase_index

            existing_dialog_node_id = phase_node.get_attribute_value("DialogNodeId")
            if existing_dialog_node_id is not None:
                phase_node.update_value_for_attribute(name="DialogNodeId", new_value=new_dialog_node_id)
            
            existing_reference_id = phase_node.get_attribute_value("ReferenceId")
            if existing_reference_id is not None:
                phase_node.update_value_for_attribute(name="ReferenceId", new_value=new_reference_id or new_dialog_node_id)

            # perform actor mapping
            phase_node.map_all_guid_children(
                guid_map=actor_map_context.create_map(node_type=phase_node.type_str)
            )
            new_phase_nodes.append(phase_node)
            self._effect_components_children_container.append(phase_node._node)
        new_phase_component = EffectComponentPhase(_container_element=self._effect_components_children_container, phase_index=new_phase_index, phase_nodes=new_phase_nodes)
        self.effect_component_phases.append(new_phase_component)
        
        self.duration += new_phase_dur
        self.duration_str = str(self.duration)
        self.update_value_for_attribute(name="Duration", new_value=self.duration_str)
        new_phase_node = NewPhasesNode(duration=str(new_phase_dur), dialog_node_id=new_dialog_node_id)
        new_element = new_phase_node.create_element()
        self._phases_children_container.append(new_element)
        self.phases.append(PhaseNode(new_element))
        return new_phase_index
    
    def __init__(self, element: ET.Element) -> None:
        super().__init__(element)
        self.duration_str = self.get_attribute_value("Duration")
        self.duration = float(self.duration_str)
        phases_container = BaseNode(element=self._get_children_elements(child_type="Phases")[0])
        self._phases_children_container = phases_container._children_element_container
        self.phases = [PhaseNode(x) for x in phases_container._get_children_elements(child_type="Phase")]
        effect_component_container_element = self._get_children_elements(child_type="EffectComponents")[0]
        effect_component_container = BaseNode(element=effect_component_container_element)
        effect_components = [EffectComponentNode(x) for x in effect_component_container._get_children_elements(child_type="EffectComponent")]
        self._effect_components_children_container = effect_component_container._children_element_container

        nodes_by_phase: dict[int, list[EffectComponentNode]] = {}
        for node in effect_components:
            if node.phase_index not in nodes_by_phase:
                nodes_by_phase[node.phase_index] = [node]
            else:
                nodes_by_phase[node.phase_index].append(node)
        self.effect_component_phases = []
        for (phase_index, nodes) in sorted(nodes_by_phase.items()):
            assert len(self.effect_component_phases) == phase_index
            self.effect_component_phases.append(EffectComponentPhase(_container_element=self._effect_components_children_container, phase_index=phase_index, phase_nodes=nodes))

        
    def adjust_duration(self, phase_index: int, adjustment_amount: float) -> None:
        current_duration = self.duration
        new_duration = current_duration + adjustment_amount
        self.update_value_for_attribute(name="Duration", new_value=str(new_duration))
        self.duration = new_duration
        self.duration_str = str(new_duration)

        self.phases[phase_index].update_duration(adjustment_amount=adjustment_amount)

    def remove_shapeshift_by_template_id(self, template_id: str, actor: str | None) -> None:
        for e in self.effect_component_phases:
            e.remove_shapeshift_by_template_id(template_id=template_id, actor=actor)
    
    def force_show_armor_to_camp_clothing(self, actor: str, clothing_type: str) -> None:
        for e in self.effect_component_phases:
            e.force_show_armor_to_camp_clothing(actor=actor, clothing_type=clothing_type)

    def map_emotions(self, actor:str, emotion_map: dict[EmotionData, EmotionData]) -> None:
        for e in self.effect_component_phases:
            e.map_emotions(actor=actor, emotion_map=emotion_map)

@dataclass
class TimelineSpeakerNode(BaseNode):
    index: int
    speaker_guid: Guid
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Object"
        super().__init__(element)
        self.index = int(self.get_attribute_value_nonnil(name="MapKey"))
        self.speaker_guid = self.get_attribute_value_nonnil(name="MapValue")


@dataclass
class TimelinePhaseNode(BaseNode):
    dialog_node_uuid: Guid
    phase_index: int
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Object"
        super().__init__(element)
        self.phase_index = int(self.get_attribute_value_nonnil(name="MapValue"))
        self.dialog_node_uuid = self.get_attribute_value_nonnil(name="MapKey")


class TimelineSpeakers(BaseNode):
    speakers: list[TimelineSpeakerNode]
    speakers_container: BaseNode

    def __init__(self, timeline_speakers_element: ET.Element):
        assert timeline_speakers_element.attrib["id"] == "TimelineSpeakers"
        super().__init__(element=timeline_speakers_element)
        timeline_speakers_optional =  self._get_children_elements(child_type="TimelineSpeaker")
        if len(timeline_speakers_optional) > 0:
            assert len(timeline_speakers_optional) == 1
            self.speakers_container = BaseNode(element=timeline_speakers_optional[0])
        else:
            self.speakers_container = self
        self.speakers = [TimelineSpeakerNode(element=x) for x in self.speakers_container._get_children_elements(child_type="Object")]


class TimelinePhases:
    _element_ref: ET.Element
    _node_ref: BaseNode
    phases: list[TimelinePhaseNode]
    phases_by_uuid: dict[str, TimelinePhaseNode] | None = None
    _objects_children_container: ET.Element
    def __init__(self, timeline_phases_element: ET.Element):
        self._element_ref = timeline_phases_element
        self._node_ref = BaseNode(element=timeline_phases_element)
        self._objects_children_container = self._node_ref._children_element_container
        self.phases = [TimelinePhaseNode(element=x) for x in self._node_ref._get_children_elements(child_type="Object")]
    def get_phase_index_by_dialog_uuid(self, dialog_uuid: str) -> int:
        if self.phases_by_uuid is None:
            self.phases_by_uuid = {}
            for phase in self.phases:
                assert phase.dialog_node_uuid not in self.phases_by_uuid
                self.phases_by_uuid[phase.dialog_node_uuid] = phase
        return self.phases_by_uuid[dialog_uuid].phase_index
    def get_phase_index_by_dialog_uuid_optional(self, dialog_uuid: str) -> int | None:
        if self.phases_by_uuid is None:
            self.phases_by_uuid = {}
            for phase in self.phases:
                assert phase.dialog_node_uuid not in self.phases_by_uuid, phase.dialog_node_uuid
                self.phases_by_uuid[phase.dialog_node_uuid] = phase
        if dialog_uuid not in self.phases_by_uuid:
            return None
        return self.phases_by_uuid[dialog_uuid].phase_index
    
    def append_new_phase(self, phase_index: int, dialog_node_id: str) -> None:
        assert dialog_node_id is not None
        new_node = NewTimelinePhasesNode(
            map_key=dialog_node_id, map_value=phase_index
        )
        element = new_node.create_element()
        self._objects_children_container.append(element)
        phases_node = TimelinePhaseNode(element=element)
        self.phases.append(phases_node)
        if  self.phases_by_uuid is not None:
            self.phases_by_uuid[dialog_node_id] = phases_node


@dataclass
class ActorObjectValueNode(BaseNode):
    speaker: str | None
    actor_type_id: str
    actor_type: str
    is_player: str | None
    default_step_out_delay: str
    audience_slot: str | None
    scene_actor_type: str | None
    scene_actor_index: str | None
    camera: str | None
    attach_to: str | None
    look_at: str | None
    resource_id: str | None

    def __init__(self, element: ET.Element):
        assert element.attrib["id"] == "Value"
        super().__init__(element=element)
        self.speaker = self.get_attribute_value("Speaker")
        self.actor_type_id = self.get_attribute_value_nonnil("ActorTypeId")
        self.actor_type = self.get_attribute_value_nonnil("ActorType")
        self.is_player = self.get_attribute_value("IsPlayer")
        self.default_step_out_delay = self.get_attribute_value_nonnil("DefaultStepOutDelay")
        self.audience_slot = self.get_attribute_value("AudienceSlot")
        self.scene_actor_type = self.get_attribute_value("SceneActorType")
        self.scene_actor_index = self.get_attribute_value("SceneActorIndex")
        self.camera = self.get_attribute_value("Camera")
        self.attach_to = self.get_attribute_value("AttachTo")
        self.look_at = self.get_attribute_value("LookAt")
        self.resource_id = self.get_attribute_value("ResourceId")

    def map_all_guid_attributes(self, guid_map: dict[Guid, Guid]) -> None:
        # iterate all children and map any attribute that has Guid type and matches existing_guid

        # check all attributes
        for attribute_name, attribute_element in self._attribute_elements.items():
            attr_type = attribute_element.attrib.get("type", "")
            if attr_type == "guid":
                value = attribute_element.attrib["value"]
                if value in guid_map:
                    old = attribute_element.attrib["value"] 
                    attribute_element.attrib["value"] = guid_map[value]
                    if VERBOSE:
                        print(f"Mapped {attribute_name} - {old} to {guid_map[value]}")


    def print_info(self, context: TimelinePrintInfoContext) -> None:
        if self.camera is not None:
            camera_mapping = context.camera_id_to_name
            if camera_mapping is not None:
                camera_label = camera_mapping.get(self.camera)
            else:
                camera_label = ""
            print(f"{self.actor_type_id}-{self.actor_type}\t camera={self.camera} - \"{camera_label}\" - attach_to={self.attach_to} look_at={self.look_at} actor_type={self.actor_type}")
        else:
            print(f"{self.actor_type_id}-{self.actor_type}\t speaker={self.speaker} player={self.is_player} scene_actor_index={self.scene_actor_index} scene_actor_type={self.scene_actor_type=} audience_slot={self.audience_slot=}")

@dataclass
class ActorObjectNode(BaseNode):
    actor_data_uuid: Guid
    values: list[ActorObjectValueNode]
    def __init__(self, element: ET.Element):
        super().__init__(element=element)
        self.actor_data_uuid = self.get_attribute_value_nonnil("MapKey")
        assert element.attrib["id"] == "Object", self.actor_data_uuid

        self.values = [ActorObjectValueNode(x) for x in self._get_children_elements("Value")]

    def print_info(self, context: TimelinePrintInfoContext) -> None:
        for v in self.values:
            v.print_info(context=context)

    def map_all_guid_attributes(self, guid_map: dict[Guid, Guid]) -> None:
        for node in self.values:
            node.map_all_guid_attributes(guid_map=guid_map)

@dataclass
class TimelineActorDataNode(BaseNode):
    actor_objects: list[ActorObjectNode]

    _actor_objects_children_container_node: BaseNode = field(init=False)
    _actor_objects_map: dict[str, ActorObjectNode] | None = None
    def __init__(self, element: ET.Element):
        assert element.attrib["id"] == "TimelineActorData"
        super().__init__(element=element)
        intermediate_container =  BaseNode(self._get_children_elements("TimelineActorData")[0])
        self._actor_objects_children_container_node = intermediate_container
        self.actor_objects = [ActorObjectNode(x) for x in intermediate_container._get_children_elements("Object")]
        assert len(self.actor_objects) > 4

    def add_actor_object(self, actor_object: ActorObjectNode, guid_map: dict[Guid, Guid]) -> None:
        if self._actor_objects_map is None:
            self._actor_objects_map = {}
            for actor_object in self.actor_objects:
                self._actor_objects_map[actor_object.actor_data_uuid] = actor_object
 
        if actor_object.actor_data_uuid in self._actor_objects_map:
            if VERBOSE:
                print(f"actor object {actor_object.actor_data_uuid} already exists, not adding")
            return
        actor_object.map_all_guid_attributes(guid_map=guid_map)
        self._actor_objects_children_container_node.add_child_node(node=actor_object._node, child_index=-1)
        self.actor_objects.append(actor_object)
        self._actor_objects_map[actor_object.actor_data_uuid] = actor_object

    def remove_actor_object(self, actor_object: ActorObjectNode) -> None:
        self._actor_objects_children_container_node._delete_child(actor_object._node)
        self.actor_objects.remove(actor_object)
        self._actor_objects_map = None



@dataclass
class PhaseDepdenencies:
    scene_nodes: list["SceneNode"]
    stage_nodes: list["StageNode"]
    camera_nodes: list["CameraObjectNode"]   
    actor_nodes: list[ActorObjectNode]
    scene_actor_nodes: list["ActorNode"]
    switch_stage_ids: list[str]

@dataclass
class PeanutObjectNode(BaseNode):
    map_key: str
    map_value: str
    def __init__(self, element: ET.Element):
        assert element.attrib["id"] == "Object"
        super().__init__(element=element)
        self.map_key = self.get_attribute_value_nonnil("MapKey")
        self.map_value = self.get_attribute_value_nonnil("MapValue")

@dataclass
class TimelinePeanutSlotIdMap(BaseNode):
    objects: list[PeanutObjectNode]
    object_container_node: BaseNode
    def __init__(self, element: ET.Element):
        assert element.attrib["id"] == "PeanutSlotIdMap"
        super().__init__(element=element)
        self.object_container_node = BaseNode(element=self._get_children_elements(child_type="Object")[0])
        self.objects = [PeanutObjectNode(x) for x in self.object_container_node._get_children_elements(child_type="Object")]

@dataclass
class TimelineContent(BaseNode):
    effect: TimelineContentEffect
    speakers: TimelineSpeakers
    phases: TimelinePhases
    actor_data: TimelineActorDataNode
    peanut_slot_id_map: TimelinePeanutSlotIdMap
    def __init__(self, timeline_content_element: ET.Element):
        assert timeline_content_element.attrib["id"] == "TimelineContent"
        super().__init__(element=timeline_content_element)
        self.speakers = TimelineSpeakers(timeline_speakers_element=self._get_children_elements(child_type="TimelineSpeakers")[0])
        self.effect = TimelineContentEffect(element=self._get_children_elements(child_type="Effect")[0])
        timeline_phases_container = BaseNode(element=self._get_children_elements(child_type="TimelinePhases")[0])
        self.phases = TimelinePhases(timeline_phases_element=timeline_phases_container._get_children_elements(child_type="Object")[0])
        self.actor_data = TimelineActorDataNode(element=self._get_children_elements(child_type="TimelineActorData")[0])
        self.peanut_slot_id_map = TimelinePeanutSlotIdMap(element=self._get_children_elements(child_type="PeanutSlotIdMap")[0])
        assert len(self.speakers.speakers) >= 2, self.speakers.speakers

    def append_new_phase(self, existing_phase_to_append: EffectComponentPhase, actor_map_context: ActorMapContext, new_dialog_node_id: Guid, new_reference_id: Guid | None = None, update_node_ids: list[Guid] | None = None) -> int:
        from copy import deepcopy
        existing_phase_to_append = deepcopy(existing_phase_to_append)
        if actor_map_context.has_actor_removal():
            nodes = list( existing_phase_to_append.phase_nodes)
            for node in nodes:
                actor = node.get_actor_uuid()
                if actor is not None and actor_map_context.should_remove(actor_uuid=actor):
                    existing_phase_to_append.remove_phase_node(node)

        if update_node_ids is not None:
            # update ALL node uuids
            assert len(update_node_ids) >= len(existing_phase_to_append.phase_nodes)
            for new_uuid, node in zip(update_node_ids, existing_phase_to_append.phase_nodes):
                node.update_value_for_attribute("ID", new_value=new_uuid)
        
        new_phase_id = self.effect.append_new_phase(
            existing_phase_to_append=existing_phase_to_append,
            actor_map_context=actor_map_context,
            new_dialog_node_id=new_dialog_node_id,
            new_reference_id=new_reference_id,
        )
        self.phases.append_new_phase(phase_index=new_phase_id, dialog_node_id=new_dialog_node_id)
        return new_phase_id

    # keeps padding on both sides of voice, but changes duration on the voice itself and thus the entire phase
    def create_new_phase(self, 
                         copying_from_phase: EffectComponentPhase, 
                         new_dialog_duration: float, 
                         new_dialog_node_id: Guid,  
                         actor_map_context: ActorMapContext = ActorMapContext(), 
                         new_reference_id: Guid | None = None, 
                         update_node_ids: list[Guid] | None = None,
                         should_remove_last_subduration: bool = False) -> int:
        from copy import deepcopy
        copying_from_phase = deepcopy(copying_from_phase) # not sure this will work....
        if should_remove_last_subduration:
            copying_from_phase.remove_last_subduration()
        if update_node_ids is not None:
            # update ALL node uuids
            assert len(update_node_ids) >= len(copying_from_phase.phase_nodes)
            for new_uuid, node in zip(update_node_ids, copying_from_phase.phase_nodes):
                node.update_value_for_attribute("ID", new_value=new_uuid)
        
        found_durations: list[DurationNodes] = []
        found_voice_nodes: list[EffectComponentNode] = []
        if "TLVoice" in copying_from_phase.full_duration_nodes.nodes_by_type:
            voice_nodes = copying_from_phase.full_duration_nodes.nodes_by_type["TLVoice"]
            assert len(voice_nodes) == 1
            found_voice_nodes.append(voice_nodes[0])
            found_durations.append(copying_from_phase.full_duration_nodes)

        for duration in copying_from_phase.sub_duration_nodes:
            for voice_node in duration.nodes_by_type.get("TLVoice", []):
                found_voice_nodes.append(voice_node)
                found_durations.append(duration)
        assert len(found_voice_nodes) == 1, f"There should only be 1 voice node but found {len(found_voice_nodes)}"

        voice_node: EffectComponentNode = found_voice_nodes[0]
        voice_node.update_value_for_attribute("DialogNodeId", new_value=new_dialog_node_id)
        voice_node.update_value_for_attribute("ReferenceId", new_value=new_reference_id or new_dialog_node_id)

        old_duration = found_durations[0].duration

        if abs(old_duration - new_dialog_duration) > 0.1:
            # need to adjust duration since theyre too different
            adjustment_amount = new_dialog_duration - old_duration
            current_end_time = found_durations[0].end_time
            new_end_time = current_end_time + adjustment_amount
            assert found_durations[0].start_time < new_end_time, f"startime {found_durations[0].start_time} < endtime {new_end_time}"
            print(f"Existing voice {old_duration} new voice {new_dialog_duration} current end time {current_end_time} new end time {new_end_time}")

            found_durations[0].update_end_time(new_end_time=str(new_end_time))
            new_phase_end_time = None
            for duration in copying_from_phase.sub_duration_nodes:
                print(f"Shifting future duration {duration.start_time}-{duration.end_time} by {adjustment_amount}")
                if duration.start_time > current_end_time:
                    duration.shift_timestamp(shift_amount=adjustment_amount)
                if new_phase_end_time is None or new_phase_end_time < duration.end_time:
                    new_phase_end_time = duration.end_time
            if found_durations[0] != copying_from_phase.full_duration_nodes:
                # finds new endtime
                copying_from_phase.full_duration_nodes.update_end_time(new_end_time=str(new_phase_end_time))
        new_phase_id = self.effect.append_new_phase(
            existing_phase_to_append=copying_from_phase,
            actor_map_context=actor_map_context,
            new_dialog_node_id=new_dialog_node_id,
            new_reference_id=new_reference_id,
        )
        self.phases.append_new_phase(phase_index=new_phase_id, dialog_node_id=new_reference_id or new_dialog_node_id)
        return new_phase_id

    # return linked actor nodes
    def get_actor_data_nodes_used_in_phase(self, phase_index: int) -> list[ActorObjectNode]:
        phase = self.effect.effect_component_phases[phase_index]
        all_guids_in_phase = phase.get_referenced_guids()
        all_guids = set(all_guids_in_phase)
        ret = []
        for node in self.actor_data.actor_objects:
            if node.actor_data_uuid in all_guids:
                ret.append(node)
        return ret
    
    def get_dependency_nodes_used_in_phase(self, phase_index: int, scene_tree: "TimelineSceneTree", companion_mapping: dict[str,str]) -> PhaseDepdenencies:
        phase = self.effect.effect_component_phases[phase_index]
        all_guids_in_phase = phase.get_referenced_guids()
        all_guids = set(all_guids_in_phase)
        actor_nodes = []
        switch_stage_ids = []
        for node in self.actor_data.actor_objects:
            if node.actor_data_uuid in all_guids:
                if VERBOSE:
                    print(f"Taking node with actor_data_uuid {node.actor_data_uuid}")
                actor_nodes.append(node)
                for value_node in node.values:
                    if value_node.camera is not None:
                        all_guids.add(value_node.camera)
    
        stage_nodes = []
        switch_stage_ids = []
        camera_nodes = []
        for dependent_guid in all_guids:
            stage_node = scene_tree.content.get_stage(stage_id=dependent_guid)
            if stage_node is not None:
                stage_nodes.append(stage_node)
                switch_stage_ids.append(stage_node.identifier)
            camera_node = scene_tree.content.cameras.get_camera_object(camera_uuid=dependent_guid)
            if camera_node is not None:
                camera_nodes.append(camera_node)

        companion_scene_actors = [x for x in scene_tree.content.actors.actors if x.template_id in companion_mapping]
        for actor in companion_scene_actors:
            actor.update_value_for_attribute(name="TemplateId", new_value=companion_mapping[actor.template_id])
            actor.template_id = companion_mapping[actor.template_id] # kidna dirty
        return PhaseDepdenencies(
            scene_nodes=[],
            stage_nodes=stage_nodes,
            camera_nodes=camera_nodes,
            scene_actor_nodes=companion_scene_actors,
            actor_nodes=actor_nodes,
            switch_stage_ids=switch_stage_ids
        )

    def print_actor_info(self, context: TimelinePrintInfoContext) -> None:
        for node in self.actor_data.actor_objects:
            print(f"{node.actor_data_uuid}")
            node.print_info(context=context)

    def get_actor_id_to_descriptive_name(self, camera_id_to_name: dict[str, str]) -> dict[str, str]:
        ret = {}
        for node in self.actor_data.actor_objects:
            actor_data_uuid = node.actor_data_uuid
            assert len(node.values) == 1
            for v in node.values:
                if v.actor_type_id == "scenecam":
                    ret[actor_data_uuid] = camera_id_to_name.get(v.camera, "unknowncamera")
                elif v.actor_type_id != "character":
                    ret[actor_data_uuid] = v.resource_id or v.actor_type_id

        return ret

    def generate_actor_map(self, other_tree: "TimelineTree", reverse_map: bool = False) -> ActorMapContext:
        # returns a mapping of other tree -> this tree
        print(f"this tree speakers {len(self.speakers.speakers)} other tree speakers {len(other_tree.content.speakers.speakers)}")
        this_speakers = sorted([(x.index, x.speaker_guid) for x in self.speakers.speakers])
        other_tree_speakers = sorted([(x.index, x.speaker_guid) for x in other_tree.content.speakers.speakers])
        unmapped_speaker_ids = []
        

        def create_speaker_map(local_reverse: bool) -> dict[str, str]:
            local_speaker_map = {}
            for i, this_speaker in this_speakers:
                if i >= len(other_tree_speakers):
                    break # not enough for mapping
                if local_reverse:
                    if i == 0:
                        map_from = other_tree_speakers[1][1]
                    elif i == 1:
                        map_from = other_tree_speakers[0][1]
                    else:
                        map_from = other_tree_speakers[i][1]
                else:
                    map_from = other_tree_speakers[i][1]
                if map_from in local_speaker_map:
                    continue
                map_to = this_speaker
                local_speaker_map[map_from] = map_to
            return local_speaker_map
        speaker_map = create_speaker_map(local_reverse=reverse_map)
        if reverse_map is True:
            custom_speaker_map_for_transform_node = create_speaker_map(local_reverse=False)
        else:
            custom_speaker_map_for_transform_node = None

        for other_speaker in other_tree_speakers:
            if other_speaker[1] not in speaker_map:
                unmapped_speaker_ids.append(other_speaker[1])

        this_peanuts = sorted([(int(x.map_value), x.map_key) for x in self.peanut_slot_id_map.objects])
        other_tree_peanuts = sorted([(int(x.map_value), x.map_key) for x in other_tree.content.peanut_slot_id_map.objects])
        peanut_map = {}
        unmapped_peanut_ids = []

        for i, this_peanut in this_peanuts:
            map_from = other_tree_peanuts[i][1]
            if map_from in peanut_map:
                continue
            map_to = this_peanut
            peanut_map[map_from] = map_to
        for other_peanut in other_tree_peanuts:
            if other_peanut[1] not in peanut_map:
                unmapped_peanut_ids.append(other_peanut[1])

        return ActorMapContext(
            speaker_map=speaker_map,
            peanut_map=peanut_map,
            removed_speakers=unmapped_speaker_ids,
            removed_peanuts=unmapped_peanut_ids,
            custom_speaker_map_for_transform_node=custom_speaker_map_for_transform_node
        )

@dataclass
class TimelineTree:
    _tree_ref: ET.ElementTree
    content: TimelineContent


    @classmethod
    def create(cls, file_path: str) -> "TimelineTree":
        tree = ET.parse(file_path)
        root = tree.getroot()
        assert root.tag == "save"
        return TimelineTree(_tree_ref=tree, content=TimelineContent(timeline_content_element=root.find("region").find("node")))

    def extend_phase_duration(self, phase_index: int, adjustment_amount: float, new_nodes_for_subduration: list[NewNode], extend_subdurations_of_types: list[str]) -> None:
        assert adjustment_amount > 0
        effect_component_phase = self.content.effect.effect_component_phases[phase_index]

        # extend all full duration nodes
        effect_component_phase.extend_end_timestamp(adjustment_amount=adjustment_amount, nodes_for_new_subduration=new_nodes_for_subduration, extend_subdurations_of_types=extend_subdurations_of_types)

        # update phase duration
        self.content.effect.adjust_duration(phase_index=phase_index, adjustment_amount=adjustment_amount)

        # push timestamps of all nodes after this one forward
        for effect_component_phase in self.content.effect.effect_component_phases[phase_index+1:]:
            effect_component_phase.shift_timestamp(shift_amount=adjustment_amount)

        

    def print_info_for_phase_index(self, phase_index: int, context: TimelinePrintInfoContext):
        dialog_node_uuid =[x for x in self.content.phases.phases if x.phase_index == phase_index][0].dialog_node_uuid
        start_time_in_timeline = sum([x.duration for x in self.content.effect.phases[:phase_index]])
        phase_duration = self.content.effect.phases[phase_index].duration
        print(f"{dialog_node_uuid=} {start_time_in_timeline=} {phase_duration=}")

        self.content.effect.effect_component_phases[phase_index].print_info(context=context)
    
    def write_tree(self, output_file_path: str) -> None:
        ET.indent(self._tree_ref, space="\t", level=0)
        self._tree_ref.write(output_file_path, encoding='utf-8', method='xml', xml_declaration=True)
