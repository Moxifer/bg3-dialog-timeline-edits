from timeline_parser import TimelineTree, TimelinePrintInfoContext, EmotionData
from dataclasses import dataclass
from dialog_tree_objects import DialogTree, DialogNode, NewDialogNode, NewDialogFlagGroup, NewTaggedText, NewFlag, NewTagTexts,NewTagText
from print_info_utils import create_speaker_labels, create_strings_map, get_dialog_node_id_to_text_entry, create_sound_banks_duration_mapping
from companion_utils import companion_REALLY_tags, companion_uuids
from typing import Callable
from kiss_edits import KissEdits, DialogTextEntry
from kiss_utils import KissEntry, body_type_ordering_in_dialog, BODYTYPE, KISSTYPE, body_type_to_tag
from timeline_scene_parser import TimelineSceneTree

VERBOSE = False

# top level utils for all scene edits
@dataclass
class DialogAndTimelineBaseContext:
    timeline_tree: TimelineTree
    scene_tree: TimelineSceneTree
    dialog_tree: DialogTree

    
    def __init__(self,timeline_path: str,
                 scene_path: str,
                dialog_path: str
            ) -> None:
        self.timeline_tree = TimelineTree.create(file_path=timeline_path)
        self.scene_tree = TimelineSceneTree.create(file_path=scene_path)
        self.dialog_tree = DialogTree.create(file_path=dialog_path)
        
@dataclass
class DialogAndTimelineContext(DialogAndTimelineBaseContext):
    pop_one_uuid: Callable[[None], str]
    pop_n_uuids: Callable[[int], list[str]]
    
    def __init__(self,timeline_path: str,
                 scene_path: str,
                dialog_path: str,
                pop_one_uuid: Callable[[None], str],
                pop_n_uuids: Callable[[int], list[str]]
            ) -> None:
        super().__init__(timeline_path, scene_path, dialog_path)
        self.pop_one_uuid = pop_one_uuid
        self.pop_n_uuids = pop_n_uuids


durations = create_sound_banks_duration_mapping()
def add_timeline_nodes_for_companion_response(
        context: DialogAndTimelineContext,
        companion_response_dialog_uuid: str,
        dialog: list[DialogTextEntry],
        phase_index_to_copy: int) -> None:
    phase_to_copy = context.timeline_tree.content.effect.effect_component_phases[phase_index_to_copy]
    n_nodes = len(phase_to_copy.phase_nodes)
    if VERBOSE:
        print(f"Reusing phase {phase_index_to_copy} for copying {phase_to_copy.full_duration_nodes.start_time} {phase_to_copy.full_duration_nodes.end_time}")

    for i, dialog_entry in enumerate(dialog):
        reference_id = None if i == 0 else dialog_entry.line_id
        text_uuid = dialog_entry.text_uuid
        duration_for_text = durations[text_uuid][0]

        if VERBOSE:
            print(f"!Updating {n_nodes} uuids in nodes for astarion")
            print(f"Duration for voice {duration_for_text}")

        context.timeline_tree.content.create_new_phase(
            copying_from_phase=phase_to_copy,
            new_dialog_duration=duration_for_text,
            new_dialog_node_id=companion_response_dialog_uuid,
            new_reference_id=reference_id,
            update_node_ids=context.pop_n_uuids(n=n_nodes)
        )


@dataclass
class CinematicContext:
    timeline_tree: TimelineTree
    scene_tree: TimelineSceneTree
    phase_to_bodytypes: dict[int, tuple[BODYTYPE, ...]]
    companion_key: str

    def add_hug_to_dialog(self,
                          context: DialogAndTimelineContext,
                          post_hug_dialog_node_uuid: str,
                          companion_key: str,
                          tav_hug_option_uuid: str, 
                          tav_hug_option_string_handle: str, 
                          companion_response_string_handle: str | None , # str companion says before hug
                          phase_index_to_copy: int | None,
                          emotions_map: dict[str, dict[EmotionData, EmotionData]] = {},
                          required_flags: list[str] = []) -> None:
        companion_response_uuid = context.pop_one_uuid()
        hug_cinematic_node_uuids = []
        companion_mapping = {}
        if companion_key != self.companion_key:
            companion_mapping = {companion_uuids[self.companion_key]: companion_uuids[companion_key]}
        for phase_index, body_types in self.phase_to_bodytypes.items():
            hug_cinematic_node_uuid = context.pop_one_uuid()
            hug_cinematic_node_uuids.append(hug_cinematic_node_uuid)
            copy_phase(from_timeline=self.timeline_tree, 
                from_phase_index=phase_index, 
                from_timeline_scene=self.scene_tree, 
                to_timeline=context.timeline_tree, 
                to_timeline_scene=context.scene_tree, 
                dialog_node_uuid_for_new_phase=hug_cinematic_node_uuid,
                pop_n_uuids=context.pop_n_uuids,
                companion_mapping=companion_mapping,
                should_replace_uuids=False,
                should_reverse_actor_map=False,
                pull_in_camera=True,
            )
            for actor, actor_emotions_map in emotions_map.items():
                context.timeline_tree.content.effect.effect_component_phases[-1].map_emotions(actor=actor,
                                        emotion_map=actor_emotions_map)
            check_flags = []
            if len(body_types) > 0:
                check_flags.append(NewDialogFlagGroup(
                    type_str="Tag",
                    flags=[
                            NewFlag(
                                uuid=body_type_to_tag[x],
                                value=True, 
                                param_val=1,
                            ) for x in list(body_types)
                        ]
                ))
            hug_cinematic = NewDialogNode(
                constructor="TagCinematic",
                uuid=hug_cinematic_node_uuid,
                speaker="-1",
                check_flags=check_flags,
                children_uuids=[post_hug_dialog_node_uuid], # post hug dialog
            )

            context.dialog_tree.content.dialog_nodes.add_dialog_node(hug_cinematic)
        
        # pre hug response from companion
        pre_hug_response_node = NewDialogNode(
            constructor="TagAnswer",
            uuid=companion_response_uuid,
            speaker="0",
            transitionmode="2" if companion_response_string_handle is None else None,
            children_uuids=hug_cinematic_node_uuids,
            tagged_texts=[
                NewTaggedText(tag_texts=NewTagTexts(texts=[
                    NewTagText(
                        tag_text=companion_response_string_handle, 
                        line_id=context.pop_one_uuid(),
                        custom_sequence_id=None,
                    )
                ]))
            ] if companion_response_string_handle is not None else []
        )
        context.dialog_tree.content.dialog_nodes.add_dialog_node(pre_hug_response_node)
        if companion_response_string_handle is not None:
            assert phase_index_to_copy is not None
            add_timeline_nodes_for_companion_response(
                context=context,
                companion_response_dialog_uuid=companion_response_uuid,
                dialog=[DialogTextEntry(companion_response_string_handle, context.pop_one_uuid())],
                phase_index_to_copy=phase_index_to_copy,
            )
        # pre hug request from tav
        check_flags = []
        if len(required_flags) > 0:
            check_flags.append(NewDialogFlagGroup(
                        type_str="Global",
                        flags=[
                            NewFlag(
                                uuid=x,
                                value=True, 
                                param_val=None
                            ) for x in required_flags
                        ]
                    ))
        check_flags.append(
            NewDialogFlagGroup(
                type_str="Tag",
                flags=[
                    NewFlag(
                        uuid=companion_REALLY_tags["karl"], # disable karlach tav
                        value=False, 
                        param_val=1
                    )
                ]
            ))

        tav_hug_option = NewDialogNode(
            constructor="TagQuestion",
            uuid=tav_hug_option_uuid,
            speaker="1",
            children_uuids=[companion_response_uuid],
            check_flags=check_flags,
            tagged_texts=[
                NewTaggedText(tag_texts=NewTagTexts(texts=[
                    NewTagText(
                        tag_text=tav_hug_option_string_handle,
                        line_id=context.pop_one_uuid(),
                        custom_sequence_id=None,
                    )
                ]))
            ]
        )
        context.dialog_tree.content.dialog_nodes.add_dialog_node(tav_hug_option)
        
#kiss:
# 330 7899b25f-0afa-ceb9-2c68-61d5eb9248e6 FULL_CEREMORPH
# 148 ff7baa25-621d-4e4c-d8e3-4d28e8588d31 DWARF
# 204 26158016-a869-0fe0-4038-4ede640f56a4 SHORT
# 313 63d5576b-c054-7a67-b97b-520eaa30f93a DRAGONBORN
# 50 b9820d13-94b3-8af6-7664-9023b42b37d7 BODYTYPE_STRONG
# 246 38ac4e58-c027-8405-284b-622e3cc7ae74

#kiss:  Six months without a kiss from you... it's been agony. May I?
# 358 7899b25f-0afa-ceb9-2c68-61d5eb9248e6 FULL_CEREMORPH
# 163 ff7baa25-621d-4e4c-d8e3-4d28e8588d31 DWARF
# 91 26158016-a869-0fe0-4038-4ede640f56a4 SHORT
# 351 63d5576b-c054-7a67-b97b-520eaa30f93a DRAGONBORN
# 20 b9820d13-94b3-8af6-7664-9023b42b37d7 BODYTYPE_STRONG
# 110 38ac4e58-c027-8405-284b-622e3cc7ae74

#hug:
# 107 c32ee23c-dbcf-01ee-551b-85a082e0fc93 FULL_CEREMORPH
# 201 81b7fe7a-7ed1-3cfc-930b-499f778e1d1c DWARF
# 380 59370eb6-9a51-a870-452c-dfae7526943d SHORT
# 276 13b3f559-d8ae-cfa5-2934-60bd0cdefc2c DRAGONBORN
# 168 8601b3e7-270a-de8f-4244-af9fb1b6833d BODTTYPE_STRING
# 281  11ab7c50-d0d7-f606-b259-69a4801a7ea1

#  shart_context = DialogAndTimelineBaseContext(
#      timeline_path=r"Y:\bg3\multitool\UnpackedMods\Gustav\Public\GustavDev\Timeline\Generated\EPI_Epilogue_Shadowheart.lsf.lsx",
#      scene_path=r"Y:\bg3\multitool\UnpackedMods\Gustav\Public\GustavDev\Timeline\Generated\EPI_Epilogue_Shadowheart_Scene.lsf.lsx",
#     dialog_path=r"Y:\bg3\multitool\UnpackedMods\Gustav\Mods\GustavDev\Story\DialogsBinary\Act3\EndGame\Epilogue\EPI_Epilogue_Shadowheart.lsf.lsx",
# )
#   print_context = create_print_info_context(context=shart_context)
@dataclass
class ShadowheartHugCinematicContext(CinematicContext):
    def __init__(self) -> None:
        timeline_path = r"Y:\bg3\multitool\UnpackedMods\Gustav\Public\GustavDev\Timeline\Generated\EPI_Epilogue_Shadowheart.lsf.lsx"
        scene_path = r"Y:\bg3\multitool\UnpackedMods\Gustav\Public\GustavDev\Timeline\Generated\EPI_Epilogue_Shadowheart_Scene.lsf.lsx"
        timeline_tree = TimelineTree.create(file_path=timeline_path)
        scene_tree = TimelineSceneTree.create(file_path=scene_path)

        phase_to_bodytypes = {
            201: ("dwarf",),
            380: ("short",),
            276: ("dragonborn",),
            168: ("strong",),
            281: (),
        }
        super().__init__(
            timeline_tree=timeline_tree,
            scene_tree=scene_tree,
            phase_to_bodytypes=phase_to_bodytypes,
            companion_key="shart",
        )


@dataclass
class GaleHugCinematicContext(CinematicContext):
    def __init__(self) -> None:
        timeline_path = r"Y:\bg3\multitool\UnpackedMods\Gustav\Public\GustavDev\Timeline\Generated\EPI_Epilogue_Gale.lsf.lsx"
        scene_path = r"Y:\bg3\multitool\UnpackedMods\Gustav\Public\GustavDev\Timeline\Generated\EPI_Epilogue_Gale_Scene.lsf.lsx"
        timeline_tree = TimelineTree.create(file_path=timeline_path)
        scene_tree = TimelineSceneTree.create(file_path=scene_path)

        phase_to_bodytypes = {
            103: ("strong",),
            67: ("short",),
            91: (),
        }
        super().__init__(
            timeline_tree=timeline_tree,
            scene_tree=scene_tree,
            phase_to_bodytypes=phase_to_bodytypes,
            companion_key="gale",
        )
strings_mapping = create_strings_map()

def create_print_info_context(context: DialogAndTimelineBaseContext) -> TimelinePrintInfoContext:
    camera_mapping = context.scene_tree.content.get_camera_id_to_name_mapping()
    speaker_labels = create_speaker_labels(context.dialog_tree.content.speaker_list)
    dialog_text_map = get_dialog_node_id_to_text_entry(dialog_tree=context.dialog_tree, strings_map=strings_mapping)
    camera_actor_labels = context.timeline_tree.content.get_actor_id_to_descriptive_name(camera_id_to_name=camera_mapping)
    return TimelinePrintInfoContext(
        dialog_text_map=dialog_text_map,
        allowed_node_type_strs=None,
        allowed_actor_uuids=None,
        uuid_labels=speaker_labels | camera_actor_labels,
        camera_id_to_name=camera_mapping,
    )
      

def copy_phase(from_timeline: TimelineTree, 
               from_phase_index: int, 
               from_timeline_scene: TimelineSceneTree, 
               to_timeline: TimelineTree, 
               to_timeline_scene: TimelineSceneTree, 
               dialog_node_uuid_for_new_phase: str,
               pop_n_uuids: Callable[[int], list[str]],
               emotions_map: dict[str, dict[EmotionData, EmotionData]] = {},
               companion_mapping: dict[str, str] = {},
               should_replace_uuids: bool = False,
               should_reverse_actor_map: bool = False,
               pull_in_camera: bool = False) -> None:
    # generate mapping for speaker and peanut uuids
    actor_map_context = to_timeline.content.generate_actor_map(
        other_tree=from_timeline,
        reverse_map=should_reverse_actor_map,
    )
    # phase nodes we are copying from
    phase_node = from_timeline.content.effect.effect_component_phases[from_phase_index]

    # all the nodes we need to copy
    dependencies = from_timeline.content.get_dependency_nodes_used_in_phase(phase_index=from_phase_index, scene_tree=from_timeline_scene, companion_mapping=companion_mapping)
    if should_replace_uuids:
        # if we are copying nodes from the same tree, we need to change the uuids so there's no dups
        # it actually works fine without this but this keeps things clean
        to_timeline.content.append_new_phase(
            existing_phase_to_append=phase_node,
            actor_map_context=actor_map_context,
            new_dialog_node_id=dialog_node_uuid_for_new_phase,
            update_node_ids=pop_n_uuids(n=len(phase_node.phase_nodes))
        )
    else:
        to_timeline.content.append_new_phase(
            existing_phase_to_append=phase_node,
            actor_map_context=actor_map_context,
            new_dialog_node_id=dialog_node_uuid_for_new_phase
        )

    # map emotions
    for actor, actor_emotion_map in emotions_map.items():
        to_timeline.content.effect.effect_component_phases[-1].map_emotions(actor=actor,
                                emotion_map=actor_emotion_map)
        
    # copy scenecams
    for actor_node in dependencies.actor_nodes:
        if actor_node.values[0].actor_type_id == "scenecam":
            if VERBOSE:
                print(f"Adding actornode {actor_node.actor_data_uuid} {actor_node.values[0].actor_type_id} {actor_node.values[0].camera}")
            to_timeline.content.actor_data.add_actor_object(actor_object=actor_node, guid_map=actor_map_context.create_map(node_type=None))
    
    # copy stages
    for stage in dependencies.stage_nodes:
        if VERBOSE:
            print(f"Adding stage {stage.name} {stage.identifier}")
        if not should_replace_uuids:
            assert stage.variation_conditions_id is None, f"TODO handle stages with variations"
        to_timeline_scene.content.add_stage(stage=stage)
    # copy cameras
    for camera in dependencies.camera_nodes:
        if VERBOSE:
            print(f"Adding camera {camera.map_key} {camera.camera.name}")
        to_timeline_scene.content.cameras.add_camera_object(camera, stage_ids=dependencies.switch_stage_ids, pull_in_camera=pull_in_camera)
    
    # copy scene actors
    for actor in dependencies.scene_actor_nodes:
        if VERBOSE:
            print(f"Adding scene actor {actor.template_id}")
        to_timeline_scene.content.actors.add_actors_node(node=actor)




def add_kisses(
        context: DialogAndTimelineContext,
        kiss_edits:KissEdits, 
        kiss_entries: list[KissEntry],
        companion_name_key: str,
        reverse: bool = False,
        debug_label: str | None = None,
        emotions_map: dict[str, dict[EmotionData, EmotionData]] = {},
        body_type_filter: list[tuple[BODYTYPE]] | None = None) -> tuple[list[str], list[DialogNode]]:
    kiss_cinematic_nodes = []
    kiss_type_to_kiss_uuids: dict[tuple[KISSTYPE, tuple[BODYTYPE,...]], str] = {}
    for kiss_type, kiss_entries in zip(["A", "B", "C", "D"], kiss_entries):
        for kiss_entry in kiss_entries:
            if body_type_filter is not None:
                if kiss_entry.kiss_body_types not in body_type_filter:
                    continue
            uuid_for_this_kiss = context.pop_one_uuid()
            kiss_type_to_kiss_uuids[(kiss_type, kiss_entry.kiss_body_types)] = uuid_for_this_kiss
            cinematic_node = kiss_edits.create_kiss_cinematic_node(
                node_uuid=uuid_for_this_kiss,
                kiss_type_letter=kiss_type,
                kiss_body_tags=kiss_entry.kiss_body_types,
                editor_text=f"{debug_label or companion_name_key} Smooches {kiss_type}: {kiss_entry.companion} from [{kiss_entry.kiss_type},{kiss_entry.kiss_timeline_phase_index}] for bodytypes: [{",".join(kiss_entry.kiss_body_types)}]"
            )
            kiss_cinematic_nodes.append(cinematic_node)

            companion_mapping = {}

            if kiss_entry.companion != companion_name_key:
                from_key = companion_uuids[kiss_entry.companion]
                to_key = companion_uuids[companion_name_key]
                if to_key != from_key:
                    companion_mapping = {from_key: to_key}

            print(f"\n\nAdding kiss entry {kiss_entry.companion} {kiss_type} {uuid_for_this_kiss} {kiss_entry.kiss_body_types} {kiss_entry.kiss_timeline_phase_index}")
            copy_phase(from_timeline=kiss_entry.timeline, 
                from_phase_index=kiss_entry.kiss_timeline_phase_index, 
                from_timeline_scene=kiss_entry.scene, 
                to_timeline=context.timeline_tree, 
                to_timeline_scene=context.scene_tree, 
                dialog_node_uuid_for_new_phase=uuid_for_this_kiss,
                pop_n_uuids=context.pop_n_uuids,
                companion_mapping=companion_mapping,
                should_replace_uuids= kiss_entry.companion == companion_name_key,
                should_reverse_actor_map=reverse,
                emotions_map=emotions_map)
            
    # we want to add kisses in a specific order to match how the game does it, ordered by body tags, with no body tags at the very end
    body_type_ordering_in_dialog_map = { body_type: i for i, body_type in enumerate(body_type_ordering_in_dialog)}
    kiss_uuids: list[tuple[tuple[KISSTYPE, tuple[BODYTYPE]],str]] = list(kiss_type_to_kiss_uuids.items())
    body_type_lists_sorted = sorted(kiss_uuids, key=lambda x: (tuple([body_type_ordering_in_dialog_map[x] for x in list(x[0][1])]), x[0][0]))
    if body_type_lists_sorted[-1][0][1] != ():
        while body_type_lists_sorted[0][0][1] == (): # put back
            el =  body_type_lists_sorted.pop(0)
            body_type_lists_sorted.append(el)
    
    print(f"Added {body_type_lists_sorted}")
    return ([x[1] for x in body_type_lists_sorted] , kiss_cinematic_nodes)

