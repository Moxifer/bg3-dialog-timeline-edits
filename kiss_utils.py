
from dataclasses import dataclass
from dialog_tree_objects import DialogTree
from timeline_parser import TimelineTree
from kiss_data import KissData
from typing import Literal, TypeAlias
from timeline_scene_parser import TimelineSceneTree

KISSTYPE: TypeAlias = Literal["A", "B", "C", "D"]
kiss_type_to_flag: dict[KISSTYPE, str] = {
    "A": "6061dd44-55fe-41b0-a79c-fc696073de0a",
    "B": "8da83898-1476-43e7-ab38-314c61b1ff74",
    "C": "98e473ed-0144-482c-853a-e4fc739646f5",
    "D": "0bdf3afd-1997-4c9e-82f3-b1365a47034c"
}

BODYTYPE: TypeAlias = Literal["dragonborn", "strong", "dwarf", "short", "female"]
body_type_to_tag: dict[BODYTYPE, str] = {
    "fullcereomorph": "3797bfc4-8004-4a19-9578-61ce0714cc0b",
    "dragonborn": "02e5e9ed-b6b2-4524-99cd-cb2bc84c754a",
    "strong": "d3116e58-c55a-4853-a700-bee996207397",
    "dwarf": "486a2562-31ae-437b-bf63-30393e18cbdd",
    "short": "50e7beca-4e90-43cd-b7c5-c235e236077f",
    "female": "3806477c-65a7-4100-9f92-be4c12c4fa4f",
}
body_type_ordering_in_dialog = [
    "dwarf",
    "short",
    "dragonborn",
    "strong",
    "female",
]


kisskeys: dict[str, KISSTYPE] = {v: k for k, v in kiss_type_to_flag.items()}

bodytypes: dict[str, BODYTYPE] = {v: k for k, v in body_type_to_tag.items()}

extra_kiss_types = {
    "vampirelord": "c446ce94-efd8-45d5-b407-284177b6b57e" ,
    "enemyofshar": "055bbe0f-05f5-444b-a7e2-0f66edd2178c",
}

kissstart = "2a98bc41-f6b7-4277-a282-1a91c4ef8a9b"
kissend = "f13348d0-34bf-4328-80a5-29dd8a7b0aef"

@dataclass
class KissEntry:
    kiss_type: KISSTYPE
    kiss_body_types: tuple[BODYTYPE, ...]
    kiss_cinematic_uuid: str # tagcinematic node uuid in dialog tree
    kiss_timeline_phase_index: int # phase index in timeline
    kiss_extra_flags: list[str] # keys of extra_kiss_types
    companion: str # character_name in KissData

    dialog_tree: DialogTree
    timeline: TimelineTree
    scene: TimelineSceneTree

    def description_label(self) -> str:
        if len(self.kiss_body_types) == 0:
            body_str = "regular"
        else:
            body_str = ",".join(self.kiss_body_types)
        return f"{body_str} ({self.kiss_timeline_phase_index})"
    
    def type_label(self) -> str:
        if len(self.kiss_extra_flags) > 0:
            extra_flags = ",".join(self.kiss_extra_flags)
            return f"{self.kiss_type}_{extra_flags}"
        return self.kiss_type

def identify_kiss_nodes(dialog_tree: DialogTree, timeline_tree: TimelineTree, timeline_scene_tree: TimelineSceneTree, companion: str) -> list[KissEntry]:
    kisses = []
    for node in dialog_tree.content.dialog_nodes.dialog_nodes:
        if node.constructor != "TagCinematic":
            continue
        check_flags = node.get_check_flags()
        # kiss cinematic nodes always have a kiss flag
        if len(check_flags) == 0:
            continue
        found_kiss_flag = None
        seen_body_types = []
        kiss_extra_flags = []
        for flag_group in check_flags:
            # only care about Object type 
            if flag_group.has_flag(extra_kiss_types["enemyofshar"]):
                kiss_extra_flags.append("enemyofshar")
            if flag_group.type_str == "Object":
                for flag in flag_group.flags:
                    if flag.flag_uuid in kisskeys:
                        # found a kiss!
                        found_kiss_flag = flag
                        break
            elif flag_group.type_str == "Tag":
                 for flag in flag_group.flags:
                    if flag.flag_value == "True":
                        if flag.flag_uuid in bodytypes:
                            seen_body_types.append(bodytypes[flag.flag_uuid])
                    else:
                        print(f"WARNING Found tag {flag.flag_uuid} that's not True")
                
        if found_kiss_flag is not None:
            assert node.has_set_flag(flag_uuid=kissend), "Kiss node must set end kiss flag"
            kiss_uuid = node.uuid
            kiss_type = kisskeys[found_kiss_flag.flag_uuid]

            parents = dialog_tree.content.dialog_nodes.get_parents_by_child_uuid(kiss_uuid)
            assert len(parents) > 0
            for parent in parents:
                if parent.has_check_flag(extra_kiss_types["vampirelord"]):
                    kiss_extra_flags.append("vampirelord")
                    break
            phase_index = timeline_tree.content.phases.get_phase_index_by_dialog_uuid(dialog_uuid=kiss_uuid)
            entry = KissEntry(
                kiss_type=kiss_type,
                kiss_body_types=tuple(seen_body_types),
                kiss_cinematic_uuid=kiss_uuid,
                kiss_timeline_phase_index=phase_index,
                kiss_extra_flags=kiss_extra_flags,
                companion=companion,
                dialog_tree=dialog_tree,
                timeline=timeline_tree,
                scene=timeline_scene_tree
            )
            kisses.append(entry)
    return kisses



def get_kiss_entries(kiss_datas: list[KissData], print_info: bool = True) -> dict[str, dict[str, list[KissEntry]]]:
    ret = {}
    for kiss_data in kiss_datas:
        character_name = kiss_data.character_name
        dialog_file = kiss_data.dialog_path
        timeline_file = kiss_data.timeline_path
        timeline_scene_file = kiss_data.scene_path

        timeline_tree = TimelineTree.create(file_path=timeline_file)
        scene_tree = TimelineSceneTree.create(file_path=timeline_scene_file)
        dialog_tree = DialogTree.create(file_path=dialog_file)

        kisses = identify_kiss_nodes(
            dialog_tree=dialog_tree, timeline_tree=timeline_tree, timeline_scene_tree=scene_tree, companion=character_name)
        
        # by type
        kisses_by_type = {}
        kiss_entries_by_type ={}
        for kiss in kisses:
            type_label = kiss.type_label()
            if type_label not in kisses_by_type:
                kisses_by_type[type_label] = [kiss.description_label()]
                kiss_entries_by_type[type_label] = [kiss]
            else:
                kisses_by_type[type_label].append(kiss.description_label())
                kiss_entries_by_type[type_label].append(kiss)
        for k, v in kisses_by_type.items():
            kisses_by_type[k] = sorted(v)
        
        if print_info:
            sorted_kisses = sorted(kisses_by_type.items())
            print("\n".join([f"{t}: {ks}" for t, ks in sorted_kisses]))
        ret[character_name] = kiss_entries_by_type
    return ret


if __name__ == '__main__':
    get_kiss_entries()