from dataclasses import dataclass, field
from base_objects import BaseNode, NewBaseNode, NewAttribute, Guid
import xml.etree.ElementTree as ET


# ================ Dialog classes =======================

@dataclass
class DialogSpeakerNode(BaseNode):
    index: int
    speaker_actor_id: str
    list_id: str

    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "speaker"
        assert element.attrib["key"] == "index"
        super().__init__(element=element)
        self.index = int(self.get_attribute_value_nonnil("index"))
        self.speaker_actor_id = self.get_attribute_value_nonnil("SpeakerMappingId")
        self.list_id = self.get_attribute_value_nonnil("list")


        
@dataclass
class DialogSpeakerListNode(BaseNode):
    speakers: list[DialogSpeakerNode]
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "speakerlist"
        super().__init__(element=element)
        self.speakers = [DialogSpeakerNode(e) for e in self._get_children_elements("speaker")]


@dataclass
class FlagNode(BaseNode):
    flag_uuid: str
    flag_value: str
    paramval:  str | None
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "flag"
        super().__init__(element=element)
        self.flag_uuid = self.get_attribute_value_nonnil("UUID")
        self.flag_value = self.get_attribute_value_nonnil("value")
        self.paramval = self.get_attribute_value("paramval")



@dataclass
class FlagGroupNode(BaseNode):
    type_str: str
    flags: list[FlagNode]
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "flaggroup"
        super().__init__(element=element)
        self.type_str = self.get_attribute_value_nonnil("type")
        self.flags = [FlagNode(x) for x in self._get_children_elements("flag")]

    def has_flag(self, flag_uuid: str) -> bool:
        for flag in self.flags:
            if flag.flag_uuid == flag_uuid:
                return True
        return False

@dataclass
class EditorDataNode(BaseNode):
    key_str: str
    val_str: str
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "data"
        super().__init__(element=element)
        self.val_str = self.get_attribute_value_nonnil("val")
        self.key_str = self.get_attribute_value_nonnil("key")


@dataclass
class TagTextNode(BaseNode):
    tag_text: str
    line_id: str
    custom_sequence_id: str | None
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TagText"
        super().__init__(element=element)
        self.tag_text = self.get_attribute_value_nonnil("TagText")
        self.line_id = self.get_attribute_value_nonnil("LineId")
        self.custom_sequence_id = self.get_attribute_value("CustomSequenceId")

@dataclass
class TagTextsNode(BaseNode):
    tag_texts: list[TagTextNode]
    # todo RuleGroup
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TagTexts"
        super().__init__(element=element)
        self.tag_texts = [TagTextNode(x) for x in self._get_children_elements("TagText")]


@dataclass
class TaggedTextNode(BaseNode):
    has_tag_rule: str
    tag_texts: list[TagTextsNode]
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "TaggedText"
        super().__init__(element=element)
        self.has_tag_rule = self.get_attribute_value("HasTagRule")
        self.tag_texts = [TagTextsNode(x) for x in self._get_children_elements("TagTexts")]

    
@dataclass
class DialogNode(BaseNode):
    constructor: str # TagGreeting TagAnswer TagQuestion TagCinematic Jump Alias
    uuid: str
    speaker: str | None

    group_id: str | None
    group_index: str | None
    show_once: str | None
    is_root: str | None

    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "node"
        assert element.attrib["key"] == "UUID"
        super().__init__(element=element)
        self.constructor = self.get_attribute_value_nonnil("constructor")
        self.uuid = self.get_attribute_value_nonnil("UUID")
        self.speaker = self.get_attribute_value("speaker")
        self.group_id = self.get_attribute_value("GroupID")
        self.group_index = self.get_attribute_value("GroupIndex")
        self.show_once = self.get_attribute_value("ShowOnce")
        self.is_root = self.get_attribute_value("Root")

    def get_set_flags(self) -> list[FlagGroupNode]:
        setflags_container = self._get_children_elements(child_type="setflags")
        if len(setflags_container) == 0:
            return []
        return [FlagGroupNode(x) for x in BaseNode(setflags_container[0])._get_children_elements("flaggroup")]

    def has_set_flag(self, flag_uuid: str) -> bool:
        set_flags = self.get_set_flags()
        for flaggroup in set_flags:
            if flaggroup.has_flag(flag_uuid=flag_uuid):
                return True
        return False

    def has_check_flag(self, flag_uuid: str) -> bool:
        check_flags = self.get_check_flags()
        for flaggroup in check_flags:
            if flaggroup.has_flag(flag_uuid=flag_uuid):
                return True
        return False
    
    def get_check_flags(self) -> list[FlagGroupNode]:
        setflags_container = self._get_children_elements(child_type="checkflags")
        if len(setflags_container) == 0:
            return []
        return [FlagGroupNode(x) for x in BaseNode(setflags_container[0])._get_children_elements("flaggroup")]

    def get_tagged_texts(self) -> list[TaggedTextNode]:
        text_container = self._get_children_elements(child_type="TaggedTexts")
        if len(text_container) == 0:
            return []
        return [TaggedTextNode(x) for x in BaseNode(text_container[0])._get_children_elements("TaggedText")]
    
    def get_editor_data(self) -> list[EditorDataNode]:
        editor_container = self._get_children_elements(child_type="editorData")
        if len(editor_container) == 0:
            return []
        return [EditorDataNode(x) for x in BaseNode(editor_container[0])._get_children_elements("data")]
    
    def get_children_uuids(self) -> list[str]:
        children_container = self._get_children_elements(child_type="children")[0]
        children = [BaseNode(n) for n in BaseNode(element=children_container)._get_children_elements(child_type="child")]
        return [x.get_attribute_value_nonnil("UUID") for x in children]
    
    def insert_children_uuids(self, children_uuids: list[str], index: int = -1) -> None:
        children_container = self._get_children_elements(child_type="children")[0]
        children_node =  BaseNode(element=children_container)
        for uuid in children_uuids:
            new_node = ET.Element("node", attrib={"id": "child"})
            new_attr = ET.Element("attribute", attrib={"id": "UUID", "type":"FixedString", "value": uuid})
            new_node.append(new_attr)
            children_node.add_child_node(new_node, child_index=index)

    # clears all children
    def remove_children_uuids(self) -> None:
        children_container = self._get_children_elements(child_type="children")[0]
        children_node = BaseNode(element=children_container)
        children_elements = children_node._get_children_elements(child_type="child")
        for c in children_elements:
            children_node._delete_child(child_element=c)


@dataclass
class DialogRootNode(BaseNode):
    root_node_id: str
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "RootNodes"
        super().__init__(element=element)
        self.root_node_id = self.get_attribute_value_nonnil("RootNodes")



@dataclass
class NewFlag(NewBaseNode):
    uuid: str
    value: bool
    param_val: int | None

    def create(self) -> ET.Element:
        attributes = [
            NewAttribute(id_str="UUID", type_str="FixedString", value=self.uuid),
            NewAttribute(id_str="value", type_str="bool", value="True" if self.value else "False")
        ]
        if self.param_val is not None:
            attributes.append(NewAttribute(id_str="paramval", type_str="int32", value=str(self.param_val)))
        return super().create_element(node_id="flag", node_key="UUID", attributes=attributes)


@dataclass
class NewTagText(NewBaseNode):
    tag_text: str
    line_id: bool
    custom_sequence_id: Guid | None
    def create(self) -> ET.Element:
        attributes = [
            NewAttribute(id_str="TagText", type_str="TranslatedString", value=self.tag_text, write_value_as_handle=True),
            NewAttribute(id_str="LineId", type_str="guid", value=self.line_id),
            NewAttribute(id_str="stub", type_str="bool", value="True")
        ]
        if self.custom_sequence_id is not None:
            attributes.append(NewAttribute(id_str="CustomSequenceId", type_str="guid", value=self.custom_sequence_id))
        return super().create_element(node_id="TagText", attributes=attributes)

@dataclass
class NewTagTexts(NewBaseNode):
    texts: list[NewTagText]
    def create(self) -> ET.Element:
        return super().create_element(node_id="TagTexts", children=[x.create() for x in self.texts])

@dataclass
class NewEmptyRuleGroup(NewBaseNode):
    def create(self) -> ET.Element:
        return super().create_element(node_id="RuleGroup",
                       attributes=[NewAttribute(id_str="TagCombineOp", type_str="uint8", value="0")],
                        children=[ET.Element("node", attrib={"id": "Rules"})])


@dataclass
class NewTaggedText(NewBaseNode):
    tag_texts: NewTagTexts
    def create(self) -> ET.Element:
        return super().create_element(node_id="TaggedText",
                       attributes=[NewAttribute(id_str="HasTagRule", type_str="bool", value="True")],
                        children=[self.tag_texts.create(), NewEmptyRuleGroup().create()])

@dataclass
class NewEditorData(NewBaseNode):
    editor_text: str
    def create(self) -> ET.Element:
        return super().create_element(node_id="data", node_key="key",
                       attributes=[
                           NewAttribute(id_str="key", type_str="FixedString", value="CinematicNodeContext"),
                           NewAttribute(id_str="val", type_str="LSString", value=self.editor_text)
                        ])


@dataclass
class NewDialogFlagGroup(NewBaseNode):
    type_str: str # Object Global Tag
    flags: list[NewFlag]

    def create(self) -> ET.Element:
        attributes = [
            NewAttribute(id_str="type", type_str="FixedString", value=self.type_str)
        ]
        return super().create_element(node_id="flaggroup", node_key="type", attributes=attributes, children=self.flags)



@dataclass
class NewEmptyGameDataNode(NewBaseNode):
    def create(self) -> ET.Element:
        return super().create_element(node_id="GameData", children=[
            NewBaseNode().create_element(node_id="AiPersonalities", node_key="AiPersonality"),
            NewBaseNode().create_element(node_id="MusicInstrumentSounds"),
            NewBaseNode().create_element(node_id="OriginSound"),
        ])

@dataclass
class NewChildUUID(NewBaseNode):
    uuid: str
    def create(self) -> ET.Element:
        return super().create_element(node_id="child", attributes=[
            NewAttribute(id_str="UUID", type_str="FixedString", value=self.uuid)
        ])
    
@dataclass
class NewNodeWithChildren(NewBaseNode):
    node_id: str
    children: list[ET.Element] = field(default_factory=lambda: [] )
    def create(self) -> ET.Element:
        return super().create_element(node_id=self.node_id, children=self.children)
    

@dataclass
class NewDialogNode(NewBaseNode):
    constructor: str
    uuid: str
    speaker: str | None
    source_node: str | None = None
    transitionmode: str | None = None
    endnode: str | None = None
    children_uuids: list[Guid] = field(default_factory=lambda: [])
    set_flags: list[NewDialogFlagGroup] = field(default_factory=lambda: [])
    check_flags: list[NewDialogFlagGroup] = field(default_factory=lambda: [])
    tagged_texts: list[NewTaggedText] = field(default_factory=lambda: [])
    editor_data: list[NewEditorData] = field(default_factory=lambda: [])

    
    def create(self) -> ET.Element:
        attributes = [
            NewAttribute(id_str="constructor", type_str="FixedString", value=self.constructor),
            NewAttribute(id_str="UUID", type_str="FixedString", value=self.uuid),
        ]
        if self.endnode is not None:
            attributes.append(
                NewAttribute(id_str="endnode", type_str="bool", value=self.endnode)
            ) 
        if self.speaker is not None:
            attributes.append(
                NewAttribute(id_str="speaker", type_str="int32", value=self.speaker)
            )
        if self.source_node is not None:
            attributes.append(
                NewAttribute(id_str="SourceNode", type_str="FixedString", value=self.source_node)
            )
        if self.transitionmode is not None:
            attributes.append(
                NewAttribute(id_str="transitionmode", type_str="uint8", value=self.transitionmode)
            )
        children_container = NewNodeWithChildren(node_id="children")
        for child in self.children_uuids:
            children_container.children.append(NewChildUUID(uuid=child).create())


        empty_tags_container = ET.Element("node", attrib={"id": "Tags"})
        set_flags_container = NewNodeWithChildren(node_id="setflags")
        for flag in self.set_flags:
            set_flags_container.children.append(flag.create())

        check_flags_container = NewNodeWithChildren(node_id="checkflags")
        for flag in self.check_flags:
            check_flags_container.children.append(flag.create())

        if self.constructor != "TagCinematic" and self.constructor != "Alias":
            tagegd_text_container = NewNodeWithChildren(node_id="TaggedTexts")
            for text in self.tagged_texts:
                tagegd_text_container.children.append(text.create())
            assert len(self.editor_data) == 0
            children = [children_container, NewEmptyGameDataNode().create(), empty_tags_container,set_flags_container.create(),  check_flags_container.create(), tagegd_text_container.create()]
        else:
            if self.constructor == "TagCinematic":
                if len(self.editor_data) > 0:
                    editor_data_container = NewNodeWithChildren(node_id="editorData", children=[x.create() for x in self.editor_data])
                    children = [children_container, NewEmptyGameDataNode().create(), empty_tags_container,set_flags_container.create(),  check_flags_container.create(), editor_data_container.create()]
                else: 
                    children = [children_container, NewEmptyGameDataNode().create(), empty_tags_container,set_flags_container.create(),  check_flags_container.create()]
            else:
                assert len(self.editor_data) == 0
                children = [children_container, NewEmptyGameDataNode().create(), empty_tags_container,set_flags_container.create(),  check_flags_container.create()]

        return super().create_element(node_id="node", 
                              node_key="UUID", 
                              attributes=attributes, 
                              children=children)



@dataclass
class DialogListNodes(BaseNode):
    dialog_nodes: list[DialogNode]
    root_nodes: list[DialogRootNode]

    dialog_nodes_by_uuid: dict[str, DialogNode] | None = None
    dialog_uuid_to_parents: dict[str, list[DialogNode]] | None = None
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "nodes"
        super().__init__(element=element)
        self.dialog_nodes = [DialogNode(n) for n in self._get_children_elements(child_type="node")]
        self.root_nodes = [DialogRootNode(n) for n in self._get_children_elements(child_type="RootNodes")]

    def insert_child_node(self, node_uuid: str, child_uuids: list[str], index: int) -> None:
        for dialog_node in self.dialog_nodes:
            if dialog_node.uuid == node_uuid:
                dialog_node.insert_children_uuids(children_uuids=child_uuids, index=index)
                return

        
        assert False, f"did not find node with uuid {node_uuid}"

    def get_node_by_uuid(self, node_uuid: str) -> ET.Element:
        if self.dialog_nodes_by_uuid is None:
            self.dialog_nodes_by_uuid = {}
            for node in self.dialog_nodes:
                assert node.uuid not in self.dialog_nodes_by_uuid
                self.dialog_nodes_by_uuid[node.uuid] = node
        return self.dialog_nodes_by_uuid[node_uuid]
    
    def get_parents_by_child_uuid(self, child_uuid: str) -> list[DialogNode]:
        if self.dialog_uuid_to_parents is None:
            self.dialog_uuid_to_parents = {}
            for node in self.dialog_nodes:
                children = node.get_children_uuids()
                for child in children:

                    if child not in self.dialog_uuid_to_parents:
                        self.dialog_uuid_to_parents[child] = [node]
                    else:
                        self.dialog_uuid_to_parents[child].append(node)
        return self.dialog_uuid_to_parents[child_uuid]

    def add_dialog_node(self, new_node: NewDialogNode) -> None:
        element = new_node.create()
        self._children_element_container.insert(0, element)
        self.dialog_nodes.append(DialogNode(element=element))


@dataclass
class DialogContent(BaseNode):
    speaker_list: DialogSpeakerListNode
    dialog_nodes: DialogListNodes
    def __init__(self, element: ET.Element) -> None:
        assert element.attrib["id"] == "dialog"
        super().__init__(element=element)
        self.speaker_list = DialogSpeakerListNode(element=self._get_children_elements(child_type="speakerlist")[0])
        self.dialog_nodes = DialogListNodes(element=self._get_children_elements(child_type="nodes")[0])

@dataclass
class DialogTree:
    _tree_ref: ET.ElementTree
    content: DialogContent

    @classmethod
    def create(cls, file_path: str) -> "DialogTree":
        tree = ET.parse(file_path)
        root = tree.getroot()
        assert root.tag == "save"
        return DialogTree(_tree_ref=tree, content=DialogContent(element=root.find("region").find("node")))

    def write_tree(self, output_file_path: str) -> None:
        ET.indent(self._tree_ref, space="\t", level=0)
        self._tree_ref.write(output_file_path, encoding='utf-8', method='xml', xml_declaration=True)