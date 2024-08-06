import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import TypeAlias, Literal

from base_objects import NewTimelinePhasesNode, NewPhasesNode, NewAttribute, BaseNode, create_comment, NewNode, NewBaseNode, Guid, EffectComponentChildType, EffectComponentType,emotions_labels,known_effect_component_child_type, known_effect_component_types
from dialog_tree_objects import DialogContent
from text_utils import TextEntry, TextKey
VERBOSE = False


# ================ Timeilne Scene classes =======================
@dataclass
class LightNode(BaseNode):
    light_name: str
    light_uuid: str
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Light"
        super().__init__(element=element)
        self.light_name = self.get_attribute_value_nonnil(name="Name")
        self.light_uuid = self.get_attribute_value_nonnil(name="Id")

@dataclass
class TimelineSceneLightingSetups(BaseNode):
    lights: list[LightNode]
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "LightingSetups"
        super().__init__(element=element)
        lighting_setup_elements = self._get_children_elements(child_type="LightingSetup")
        assert len(lighting_setup_elements) == 1
        lighting_setup_node = BaseNode(element=lighting_setup_elements[0])
        lighting_setup_name = lighting_setup_node.get_attribute_value_nonnil("Name")
        assert lighting_setup_name == "Default"
        lights_elements = lighting_setup_node._get_children_elements("Lights")
        assert len(lights_elements) == 1
        lights_node = BaseNode(element=lights_elements[0])
        light_elements = lights_node._get_children_elements("Light")
        self.lights = [LightNode(x) for x in light_elements]

@dataclass
class LightObjectLightsNode(BaseNode):
    attach_to: int
    light_uuid: Guid
    light_name: str
    template_id: str
    light_type: int
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Lights"
        super().__init__(element=element)
        self.attach_to = int(self.get_attribute_value_nonnil(name="AttachTo"))
        self.light_uuid = self.get_attribute_value_nonnil(name="Id")
        self.light_name = self.get_attribute_value_nonnil(name="Name")
        self.template_id = self.get_attribute_value_nonnil(name="TemplateId")
        self.light_type = int(self.get_attribute_value_nonnil(name="Type"))


@dataclass
class LightObjectNode(BaseNode):
    lights: list[LightObjectLightsNode]
    map_key: Guid
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Object"
        super().__init__(element=element)
        self.map_key = self.get_attribute_value_nonnil("MapKey")
        self.lights = [LightObjectLightsNode(x) for x in self._get_children_elements("Lights")] 

@dataclass
class TimelineSceneLightsNode(BaseNode):
    lights: list[LightObjectNode]
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Lights"
        super().__init__(element=element)
        self.lights = [LightObjectNode(x) for x in self._get_children_elements("Object")] 

@dataclass
class ActorTransformObjectNode(BaseNode):
    map_key: str
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Object"
        super().__init__(element=element)
        self.map_key = self.get_attribute_value_nonnil("MapKey")


@dataclass
class ActorTransformsNode(BaseNode):
    transform_objects: list[ActorTransformObjectNode]

    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Transforms"
        super().__init__(element=element)
        self.transform_objects = [ActorTransformObjectNode(x) for x in self._get_children_elements("Object")] 

    def add_transform(self, transform_object: ActorTransformObjectNode) -> None:
        for transform in self.transform_objects:
            if transform.map_key == transform_object.map_key:
                if VERBOSE:
                    print(f"Not adding duplicate actor transform {transform.map_key }")
                return
        self.add_child_node(node=transform_object._node, child_index=-1, debug_comment="Adding transform object for scene actor")
        self.transform_objects.append(transform_object)

@dataclass
class ActorNode(BaseNode):
    actor_type: str
    template_id: str | None
    important_for_staging: str | None
    transforms: ActorTransformsNode | None
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TLActor"
        super().__init__(element=element)
        self.important_for_staging = self.get_attribute_value("ImportantForStaging")
        self.template_id = self.get_attribute_value("TemplateId")
        self.actor_type = self.get_attribute_value_nonnil("ActorType")
        transforms_elements = self._get_children_elements("Transforms")
        assert len(transforms_elements) <= 1, f"{transforms_elements} {self.template_id} {self.actor_type}"
        if len(transforms_elements) == 1:
            self.transforms = ActorTransformsNode(element=transforms_elements[0])
        else:
            self.transforms = None

    def add_transform(self, transform_node: ActorTransformsNode) -> None:
        assert self.transforms is not None
        self.transforms.add_transform(transform_object=transform_node)


@dataclass
class TimelineSceneActorsNode(BaseNode):
    actors: list[ActorNode]
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TLActors"
        super().__init__(element=element)
        self.actors = [ActorNode(x) for x in self._get_children_elements("TLActor")] 
        assert len(self.actors) > 4

    def add_actors_node(self, node: ActorNode) -> None:
        if node.template_id is None:
            if VERBOSE:
                print(f"Not adding actor with empty template id")
            return
        for actor in self.actors:
            if actor.template_id == node.template_id:
                if node.transforms is None:
                    return
                print(f"Actor for template {actor.template_id} already exists, combining children instead")
                for transform_object in node.transforms.transform_objects:
                    actor.transforms.add_transform(transform_object=transform_object)
                return
            
        self.add_child_node(node=node._node, child_index=-1, debug_comment="Adding scene actor node")
        self.actors.append(node)

@dataclass
class CamerasChildObjectNode(BaseNode):
    map_key: str
    def __init__(self, element: ET.Element) -> None:
        super().__init__(element=element)
        self.map_key = self.get_attribute_value("MapKey")

@dataclass
class CamerasChildNode(BaseNode):
    node_id: str
    objects: list[CamerasChildObjectNode]

    def __init__(self, element: ET.Element) -> None:
        super().__init__(element=element)
        self.node_id = element.attrib["id"]
        self.objects = [CamerasChildObjectNode(x) for x in self._get_children_elements()]

    def add_object_node(self, object_node: CamerasChildObjectNode, cam_name: str) -> None:
        for existing_object_node in self.objects:
            if existing_object_node.map_key == object_node.map_key:
                if VERBOSE:
                    print(f"Not adding object node {existing_object_node.map_key} because it already exists")
                return
        self.add_child_node(node=object_node._node, child_index=-1, debug_comment=cam_name)
        self.objects.append(object_node)

@dataclass
class NewCamerasChildNode(NewBaseNode):
    node_id: str
    def create(self) -> ET.Element:
        return super().create_element(
            node_id=self.node_id
        )

@dataclass
class CamerasNode(BaseNode):
    attach_to: str | None
    camera_type:str | None
    identifier: Guid
    look_at: str | None
    name: str

    children: list[CamerasChildNode]
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TLCameras"
        super().__init__(element=element)
        self.attach_to = self.get_attribute_value("AttachTo")
        self.camera_type = self.get_attribute_value("CameraType")
        self.identifier = self.get_attribute_value_nonnil("Identifier")
        self.look_at = self.get_attribute_value("LookAt")
        self.name = self.get_attribute_value_nonnil("Name")
        self.children = [CamerasChildNode(x) for x in self._get_children_elements()]

        seen_children_type = set()
        for child in self.children:
            assert child.node_id not in seen_children_type
            seen_children_type.add(child.node_id)
    
    def get_child(self, node_id: str) -> CamerasChildNode | None:
        for child in self.children:
            if child.node_id == node_id:
                return child
        return None
    
    def add_child(self, node_id: str) -> CamerasChildNode:
        assert self.get_child(node_id=node_id) is None
        new_node = NewCamerasChildNode(node_id=node_id)
        new_element = new_node.create()
        self.add_child_node(new_element, child_index=-1)
        child_node = CamerasChildNode(element=new_element)
        self.children.append(child_node)
        return child_node

@dataclass
class CameraObjectNode(BaseNode):
    map_key: str
    camera: CamerasNode
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "Object"
        super().__init__(element=element)
        self.map_key = self.get_attribute_value_nonnil("MapKey")
        camera_elements = self._get_children_elements("TLCameras")
        assert len(camera_elements) == 1, self.map_key
        self.camera = CamerasNode(camera_elements[0])
        assert self.camera.identifier == self.map_key

@dataclass
class TimelineSceneCamerasNode(BaseNode):
    cameras: list[CameraObjectNode]
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TLCameras"
        super().__init__(element=element)
        self.cameras = [CameraObjectNode(x) for x in self._get_children_elements("Object")]

    def add_camera_object(self, camera_node: CameraObjectNode, stage_ids: list[str], pull_in_camera: bool = False) -> None:
        # make sure it doesn't already exist
        camera_uuid = camera_node.map_key
        for existing_camera in self.cameras:
            if existing_camera.map_key == camera_uuid:
                if VERBOSE:
                    print(f"Not adding camera {camera_uuid} because it already exists, combining children instead for {stage_ids}")
                for child in camera_node.camera.children:
                    # get all object nodes for our stages
                    object_nodes_to_add = []
                    for object_node in child.objects:
                        #if object_node.map_key in stage_ids:
                        object_nodes_to_add.append(object_node)
                        if VERBOSE:
                            print(f"Adding child for {object_node.map_key}")
                    if len(object_nodes_to_add) == 0:
                        continue

                    node_id = child.node_id
                    existing_child = existing_camera.camera.get_child(node_id=node_id)
                    if existing_child is None:
                        # create child
                        existing_child = existing_camera.camera.add_child(node_id=node_id)
                    for object_node in object_nodes_to_add:
                        existing_child.add_object_node(object_node, cam_name=existing_camera.camera.name)
                    
                        if pull_in_camera and node_id == "Transform":
                            map_value_nodes = object_node._get_children_elements(child_type="MapValue")
                            for n in map_value_nodes:
                                map_value_node = BaseNode(n)
                                position_value = map_value_node.get_attribute_value_nonnil("Position")

                                values = position_value.split(" ")
                                x = float(values[0])
                                z = float(values[2])
                                if x < 0:
                                    x = max(-2.3, x)
                                else:
                                    x = min(2.3, x)
                                if z < 0:
                                    z = max(-2.3, z)
                                else:
                                    z = min(2,3, z)
                                values[0] = str(x)
                                values[2] = str(z)
                                if VERBOSE:
                                    print(f"Updating camera position from {position_value} to {values}")
                                map_value_node.update_value_for_attribute(name="Position", new_value=" ".join(values))


                return
        self.add_child_node(node=camera_node._node, child_index=-1)
        self.cameras.append(camera_node)
        if pull_in_camera:
            for child in camera_node.camera.children:
                node_id = child.node_id
                if node_id != "Transform":
                    continue
                for object_node in child.objects:                
                    map_value_nodes = object_node._get_children_elements(child_type="MapValue")
                    for n in map_value_nodes:
                        map_value_node = BaseNode(n)
                        position_value = map_value_node.get_attribute_value_nonnil("Position")

                        values = position_value.split(" ")
                        x = float(values[0])
                        z = float(values[2])
                        if x < 0:
                            x = max(-2, x)
                        else:
                            x = min(2, x)
                        if z < 0:
                            z = max(-2, z)
                        else:
                            z = min(2, z)
                        values[0] = str(x)
                        values[2] = str(z)
                        if VERBOSE:
                            print(f"Updating camera position from {position_value} to {values}")

                        map_value_node.update_value_for_attribute(name="Position", new_value=" ".join(values))

    def get_camera_object(self, camera_uuid: Guid) -> CameraObjectNode | None:
        for existing_camera in self.cameras:
            if existing_camera.map_key == camera_uuid:
                return existing_camera
        return None


@dataclass
class SceneNode(BaseNode):
    object_str: str
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TLScene"
        super().__init__(element=element)
        self.object_str = self.get_attribute_value_nonnil("Object")

@dataclass
class StageNode(BaseNode):
    name: str | None
    variation_conditions_id: str | None
    variation_target_id: str | None
    identifier: Guid
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TLStage"
        super().__init__(element=element)
        self.variation_conditions_id = self.get_attribute_value("VariationConditionsId")
        self.variation_target_id = self.get_attribute_value("VariationTargetId")
        self.name = self.get_attribute_value("Name")
        self.identifier = self.get_attribute_value_nonnil("Identifier")


@dataclass
class TimelineSceneContent(BaseNode):
    # todo conditions
    lighting_setups: TimelineSceneLightingSetups
    lights: TimelineSceneLightsNode
    actors: TimelineSceneActorsNode
    cameras: TimelineSceneCamerasNode
    inherited_scenes: list[SceneNode]
    stages: list[StageNode]

    _stages_children_container: ET.Element = field(init=False)
    _inherited_scenes_children_container: ET.Element = field(init=False)

    def get_camera_id_to_name_mapping(self) -> dict[str, str]:
        ret = {}
        for camera_node in self.cameras.cameras:
            camera_id = camera_node.map_key
            camera_object = camera_node.camera
            camera_name = camera_object.name
            assert camera_object.identifier == camera_id
            ret[camera_id] = camera_name
        return ret
    
    def add_stage(self, stage: StageNode) -> None:
        for existing_stage in self.stages:
            if existing_stage.identifier == stage.identifier:
                if VERBOSE:
                    print(f"Not adding stage {stage.identifier} because it already exists")
                return
        self._stages_children_container.append(stage._node)
        self.stages.append(stage)

    def get_stage(self, stage_id: Guid) -> StageNode | None:
        for stage in self.stages:
            if stage.identifier == stage_id:
                return stage
        return None

    def add_scene(self, scene: SceneNode) -> None:
        self._inherited_scenes_children_container.append(scene._node)
        self.inherited_scenes.append
    
    def get_scene(self, scene_value: str) -> SceneNode | None:
        for scene in self.inherited_scenes:
            if scene.value == scene_value:
                return scene
        return None

    def __init__(self, timeline_scenecontent_element: ET.Element):
        super().__init__(element=timeline_scenecontent_element)
        stages_element = self._get_children_elements("TLStages")[0]
        stage_node = BaseNode(stages_element)
        self._stages_children_container = stage_node._children_element_container
        self.stages = [StageNode(x) for x in stage_node._get_children_elements("TLStage")]
        scenes_element = self._get_children_elements("TLInheritedScenes")[0]

        scenes_node =BaseNode(scenes_element)
        self._inherited_scenes_children_container=scenes_node._children_element_container
        self.inherited_scenes = [SceneNode(x) for x in scenes_node._get_children_elements("TLScene")]

        self.cameras = TimelineSceneCamerasNode(element=self._get_children_elements("TLCameras")[0])
        self.actors = TimelineSceneActorsNode(element=self._get_children_elements("TLActors")[0])
        lights_element = self._get_children_elements("Lights")
        if len(lights_element) > 0:
            assert len(lights_element) == 1
            self.lights = TimelineSceneLightsNode(element=lights_element[0])
        else:
            self.lights = []
        self.lighting_setups = TimelineSceneLightingSetups(element=self._get_children_elements("LightingSetups")[0])

@dataclass
class TimelineSceneTree:
    _tree_ref: ET.ElementTree
    content: TimelineSceneContent

    @classmethod
    def create(cls, file_path: str) -> "TimelineSceneTree":
        tree = ET.parse(file_path)
        root = tree.getroot()
        assert root.tag == "save"
        return TimelineSceneTree(_tree_ref=tree, content=TimelineSceneContent(timeline_scenecontent_element=root.find("region").find("node")))

    def write_tree(self, output_file_path: str) -> None:
        ET.indent(self._tree_ref, space="\t", level=0)
        self._tree_ref.write(output_file_path, encoding='utf-8', method='xml', xml_declaration=True)






