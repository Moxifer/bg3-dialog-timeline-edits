from dataclasses import dataclass
from base_objects import NewNode, NewAttribute, BaseNode
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from dialog_tree_objects import DialogSpeakerListNode, DialogNode, DialogTree
from timeline_parser import TimelineTree

from text_utils import TextEntry, TextKey

english_string_files = [
    r"Y:\bg3\multitool\UnpackedData\English\Localization\English\english.loca.xml",
]
@dataclass
class PrintInfoContext:
    # hash to text mapping
    english_loca_file: dict[str, str] | None
    # list character id to character name
    characters: dict[str, str] | None
    # speakers from dialog tree
    # speaker id to list id
    speakers: dict[str, str] | None

def get_effect_name_mapping() -> dict[str,str]:
    effects_files = [
        r"Y:\bg3\multitool\UnpackedData\Shared\Public\SharedDev\Content\Assets\Effects\Effects\[PAK]_Cinematic\_merged.lsf.lsx",
        r"Y:\bg3\multitool\UnpackedData\Shared\Public\SharedDev\Content\Assets\Effects\Effects\[PAK]_Status\_merged.lsf.lsx",
        r"Y:\bg3\multitool\UnpackedData\Shared\Public\Shared\Content\Assets\Effects\Effects\[PAK]_Combat\_merged.lsf.lsx",
        r"Y:\bg3\multitool\UnpackedData\Shared\Public\Shared\Content\Assets\Effects\Effects\[PAK]_Cinematics\_merged.lsf.lsx",
    ]
    ret = {}
    for effects_file in effects_files:
        tree = ET.parse(effects_file)
        root = tree.getroot()
        assert root.tag == "save"
        templates = BaseNode(element=root.find("region").find("node"))
        objects = templates._get_children_elements("Resource")
        object_nodes = [BaseNode(x) for x in objects]
        for node in object_nodes:
            name = node.get_attribute_value_nonnil("Name")
            uuid = node.get_attribute_value_nonnil("ID")
            ret[uuid] = name
    return ret


def get_characters_mapping(verbose: bool = False) -> dict[str, str]:
    characters_files = [
        r"Y:\bg3\multitool\UnpackedMods\Gustav\Mods\Gustav\Globals\WLD_Main_A\Characters\_merged.lsf.lsx", 
        r"Y:\bg3\multitool\UnpackedData\Gustav\Mods\GustavDev\Globals\BGO_Main_A\Characters\_merged.lsf.lsx",
        r"Y:\bg3\multitool\UnpackedData\Gustav\Mods\GustavDev\Globals\CTY_Main_A\Characters\_merged.lsf.lsx",
        r"Y:\bg3\multitool\UnpackedData\Gustav\Mods\GustavDev\Levels\CTY_Main_A\Characters\_merged.lsf.lsx"]
    # returns a mapping of character uuids to label
    ret = {}
    for characters_file in characters_files:
        tree = ET.parse(characters_file)
        root = tree.getroot()
        assert root.tag == "save"
        
        templates = BaseNode(element=root.find("region").find("node"))
        objects = templates._get_children_elements("GameObjects")
        object_nodes = [BaseNode(x) for x in objects]
        for node in object_nodes:
            if node.get_attribute_value_nonnil("Type") == "character":
                name = node.get_attribute_value_nonnil("Name")
                uuid = node.get_attribute_value_nonnil("MapKey")
                ret[uuid] = name
    return ret

def get_speaker_group_mapping(verbose: bool = False) -> dict[str,str]:
    speakers_file = r"Y:\bg3\multitool\UnpackedData\Shared\Public\Shared\Voice\SpeakerGroups.lsf.lsx"
    tree = ET.parse(speakers_file)
    root = tree.getroot()
    assert root.tag == "save"
    
    templates = BaseNode(element=root.find("region").find("node"))
    objects = templates._get_children_elements("SpeakerGroup")
    object_nodes = [BaseNode(x) for x in objects]
    ret = {}
    for node in object_nodes:
        name = node.get_attribute_value_nonnil("Name")
        description = node.get_attribute_value_nonnil("Description")

        uuid = node.get_attribute_value_nonnil("UUID")
        if verbose:
            ret[uuid] = f"{name} - {description}"
        else:
            ret[uuid] = name
    return ret

manual_mapping = {
    "82b2b28f-c1cd-4baa-9341-71b465afd853": "S_LOW_CazadorsPalace_RitualRoom_CoffinLid"
}

def create_speaker_labels(node: DialogSpeakerListNode, verbose: bool = False) -> dict[str, str]:
    character_label_map = get_characters_mapping(verbose=verbose)
    speaker_group_map = get_speaker_group_mapping(verbose=verbose)

    speaker_labels = {}
    for speaker in node.speakers:
        label = character_label_map.get(speaker.list_id, speaker_group_map.get(speaker.list_id,manual_mapping.get(speaker.list_id,"unknown")))
        speaker_labels[speaker.list_id] = label
        speaker_labels[speaker.speaker_actor_id] = label
    return speaker_labels

def create_strings_map() -> dict[str, str]:
    strings_map = {}
    for file in english_string_files:
        english_tree =  ET.parse(file)
        root = english_tree.getroot()
        assert root.tag == "contentList"
        for child in root:
            text_hash = child.attrib["contentuid"]
            text_content = child.text
            strings_map[text_hash] = text_content
    return strings_map


def get_dialog_node_id_to_text_entry(dialog_tree: DialogTree, strings_map: dict[str, str]) -> dict[TextKey, TextEntry]:
    ret = {}
    for dialog_node in dialog_tree.content.dialog_nodes.dialog_nodes:
        is_first_text = True
        for tagged_text_node in dialog_node.get_tagged_texts():
            for tag_text in tagged_text_node.tag_texts:
                for node in tag_text.tag_texts:
                    text_hash = node.tag_text
                    line_id = node.line_id
                    text_content = strings_map.get(text_hash, f"{text_hash}_missing")
                    key = TextKey(
                        dialog_node_id=dialog_node.uuid,
                        line_id=line_id if not is_first_text else dialog_node.uuid
                    )
                    entry = TextEntry(
                        text = text_content,
                        text_uuid=text_hash,
                        line_id=line_id
                    )
                    ret[key] = entry
                    is_first_text = False
    return ret
# tuples of string, uuid, lineid
def get_strings_for_dialog(dialog_node: DialogNode, strings_map: dict[str, str]) -> list[TextEntry]:
    ret = []
    for taggedtexts in dialog_node.get_tagged_texts():
        texts = taggedtexts.tag_texts
        for text in texts:
            tag_text_nodes = text.tag_texts
            for node in tag_text_nodes:
                text_hash = node.tag_text
                line_id = node.line_id
                text_content = strings_map.get(text_hash, f"{text_hash}_missing")
                ret.append(TextEntry(text_content, text_hash, line_id))
    return ret

def walk_dialog_nodes(dialog_node: DialogNode, tree: DialogTree, timeline: TimelineTree, strings_map: dict[str, str], max_depth: int, current_depth: int) -> None:
    if max_depth == current_depth:
        return
    dialog_results_for_node = get_strings_for_dialog(dialog_node=dialog_node, strings_map=strings_map)
    whitespace = "".join([" "]*current_depth*2)
    for text_entry in dialog_results_for_node:
        text = text_entry.text
        text_uuid = text_entry.text_uuid
        line_id = text_entry.line_id

        custom_sequence_id = None
        phase_index = timeline.content.phases.get_phase_index_by_dialog_uuid_optional(dialog_uuid=line_id)
        if phase_index is not None:
            custom_sequence_id = line_id
        else:
            phase_index = timeline.content.phases.get_phase_index_by_dialog_uuid_optional(dialog_uuid=dialog_node.uuid)

        print(f"{whitespace} {text}      [{text_uuid}, {phase_index}, {dialog_node.constructor}, {dialog_node.uuid}, {custom_sequence_id}]") # todo print speaker

    children = dialog_node.get_children_uuids()
    for child in children:
        walk_dialog_nodes(dialog_node=tree.content.dialog_nodes.get_node_by_uuid(child),
                          tree=tree,
                          timeline=timeline,
                          strings_map=strings_map,
                          max_depth=max_depth,
                          current_depth=current_depth+1)

soundbanks_data_files = [
    r"Y:\bg3\multitool\UnpackedData\VoiceMeta\Mods\Gustav\Localization\English\Soundbanks\3ed74f063c6042dc83f6f034cb47c679.lsf.lsx",
    r"Y:\bg3\multitool\UnpackedData\VoiceMeta\Mods\Gustav\Localization\English\Soundbanks\c7c13742bacd460a8f65f864fe41f255.lsf.lsx",
    r"Y:\bg3\multitool\UnpackedData\VoiceMeta\Mods\Gustav\Localization\English\Soundbanks\ad9af97d75da406aae137071c563f604.lsf.lsx",
]
# string uuid to tuple of duration, sourcefile, chracterid
SoundBanksDuration = dict[str,tuple[float, str, str]]
def create_sound_banks_duration_mapping() -> SoundBanksDuration:
    ret = {}
    for file in soundbanks_data_files:
        tree = ET.parse(file)
        root = tree.getroot()
        assert root.tag == "save"
        
        templates = BaseNode(element=root.find("region").find("node"))
        metadata = BaseNode(templates._get_children_elements("VoiceSpeakerMetaData")[0])
        character_id = metadata.get_attribute_value_nonnil("MapKey")
        map_value_node = BaseNode(metadata._get_children_elements("MapValue")[0])
        voice_data = map_value_node._get_children_elements("VoiceTextMetaData")
        for x in voice_data:
            node = BaseNode(x)
            text_uuid = node.get_attribute_value("MapKey")
            metadata = BaseNode(node._get_children_elements("MapValue")[0])
            source_file = metadata.get_attribute_value("Source")
            duration = float(metadata.get_attribute_value("Length"))
            ret[text_uuid] = (duration, source_file, character_id)
    return ret




def _walk_dialog_nodes_along_path(current_node: DialogNode, dialog_tree: DialogTree, timeline: TimelineTree, durations: SoundBanksDuration, strings_map: dict[str, str], speakers_labels: dict[int, str], choice_indices: list[int], max_depth: int, current_depth: int) -> None:
    if max_depth == current_depth:
        print("End")
        return
    whitespace = "".join([" "]*current_depth*2)
    speaker_index = current_node.speaker
    if current_node.constructor == "Jump":
        _walk_dialog_nodes_along_path(current_node=dialog_tree.content.dialog_nodes.get_node_by_uuid(current_node.get_attribute_value("jumptarget")),
                            dialog_tree=dialog_tree,
                            timeline=timeline,
                            durations=durations,
                            strings_map=strings_map,
                            speakers_labels=speakers_labels, 
                            choice_indices=choice_indices,
                            max_depth=max_depth,
                            current_depth=current_depth)
        return
    elif current_node.constructor == "Alias":
        _walk_dialog_nodes_along_path(current_node=dialog_tree.content.dialog_nodes.get_node_by_uuid(current_node.get_attribute_value("SourceNode")),
                    dialog_tree=dialog_tree,
                    timeline=timeline,
                    durations=durations,
                    strings_map=strings_map,
                    speakers_labels=speakers_labels, 
                    choice_indices=choice_indices,
                    max_depth=max_depth,
                    current_depth=current_depth)
        return
    elif current_node.constructor == "TagCinematic":
        phase_index = timeline.content.phases.get_phase_index_by_dialog_uuid_optional(dialog_uuid=current_node.uuid)
        editor_data = current_node.get_editor_data()
        editor_str = ", ".join([x.val_str for x in editor_data])
        print(f"{whitespace}  [{phase_index}, {current_node.constructor}, {current_node.uuid}, {editor_str}]") 
    else:
        dialog_results_for_node = get_strings_for_dialog(dialog_node=current_node, strings_map=strings_map)

        if speaker_index == "-666":
            speaker_label = "narrator"
        elif speaker_index == "-1" or speaker_index is None:
            speaker_label = "nospeaker"
        else:
            speaker_label =  speakers_labels[int(current_node.speaker)]
        for text_entry in dialog_results_for_node:
            text = text_entry.text
            text_uuid = text_entry.text_uuid
            line_id = text_entry.line_id
            custom_sequence_id = None
            phase_index = timeline.content.phases.get_phase_index_by_dialog_uuid_optional(dialog_uuid=line_id)
            if phase_index is not None:
                custom_sequence_id = line_id
            else:
                phase_index = timeline.content.phases.get_phase_index_by_dialog_uuid_optional(dialog_uuid=current_node.uuid)

            duration_tuple = durations.get(text_uuid)
            duration_str = duration_tuple[0] if duration_tuple is not None else None
            print(f"{whitespace} {speaker_label}: {text}      [{duration_str}, {text_uuid}, {phase_index}, {current_node.constructor}, {current_node.uuid}, {custom_sequence_id}]") 

    children = current_node.get_children_uuids()
    if len(children) > 1 and len(choice_indices) > 0:
        choice = choice_indices[0]
        choice_indices = choice_indices[1:]
        if choice >= 0:
            print(f"CHOICE {choice}/{len(children)}")
            assert len(children) > choice
            children =  children[choice:choice+1]
    for child in children:
        _walk_dialog_nodes_along_path(current_node=dialog_tree.content.dialog_nodes.get_node_by_uuid(child),
                                    dialog_tree=dialog_tree,
                                    timeline=timeline,
                                    durations=durations,
                                    strings_map=strings_map,
                                    speakers_labels=speakers_labels, 
                                    choice_indices=choice_indices,
                                    max_depth=max_depth,
                                    current_depth=current_depth+1)



def walk_dialog_nodes_along_path(dialog_tree: DialogTree, timeline: TimelineTree, strings_map: dict[str, str], speakers_map: dict[str, str], choice_indices: list[int], root_node_index: int, max_depth: int) -> None:
    speakers = dialog_tree.content.speaker_list.speakers
    speaker_labels: dict[int, str] = {}
    for speaker_node in speakers:
        list_id = speaker_node.list_id
        speaker_index = speaker_node.index
        label = speakers_map[list_id]
        speaker_labels[speaker_index] = label
    root_nodes = dialog_tree.content.dialog_nodes.root_nodes
    root_node = root_nodes[root_node_index]
    first_node = dialog_tree.content.dialog_nodes.get_node_by_uuid(root_node.root_node_id)
    durations = create_sound_banks_duration_mapping()
    _walk_dialog_nodes_along_path(current_node=first_node,
                                  dialog_tree=dialog_tree,
                                  timeline=timeline,
                                  durations=durations,
                                  strings_map=strings_map,
                                  speakers_labels=speaker_labels, 
                                  choice_indices=choice_indices,
                                  max_depth=max_depth,
                                  current_depth=0)


def walk_all_root(dialog_tree: DialogTree, timeline_tree: TimelineTree, strings_mapping: dict[str, str], max_depth: int) -> None:
        # start with root nodes and walk down
    root_nodes = dialog_tree.content.dialog_nodes.root_nodes
    for root in root_nodes:
        print("\n\nRootNode")
        node_id = root.root_node_id
        root_node = dialog_tree.content.dialog_nodes.get_node_by_uuid(node_id)
        walk_dialog_nodes(dialog_node=root_node,
                          tree=dialog_tree,
                          timeline=timeline_tree,
                          strings_map=strings_mapping,
                          max_depth=max_depth,
                          current_depth=0)

