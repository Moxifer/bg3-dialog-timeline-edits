from kiss_utils import get_kiss_entries
from aeries_gale_dekarios_uuids import pop_one_uuid, pop_n_uuids
from kiss_data import ast_kiss_data, wyll_kiss_data, gale_last_kiss_data
from dialog_tree_objects import NewDialogNode, NewTaggedText, NewTagTexts,NewTagText
from kiss_edits import KissEdits, DialogTextEntry
from dialog_and_timeline_utils import GaleHugCinematicContext, DialogAndTimelineContext, add_kisses, ShadowheartHugCinematicContext, add_timeline_nodes_for_companion_response
from companion_utils import companion_REALLY_tags

aeries_gale_context = DialogAndTimelineContext(
    timeline_path = r"Y:\bg3\multitool\UnpackedMods\Gustav\Public\GustavDev\Timeline\Generated\Gale_InParty2_Nested_RomanticFeelings.lsf.lsx",
    scene_path = r"Y:\bg3\multitool\UnpackedMods\Gustav\Public\GustavDev\Timeline\Generated\Gale_InParty2_Nested_RomanticFeelings_Scene.lsf.lsx",
    dialog_path = r"Y:\bg3\multitool\UnpackedMods\Gustav\Mods\GustavDev\Story\DialogsBinary\Companions\Gale_InParty2_Nested_RomanticFeelings.lsf.lsx",
    pop_one_uuid=pop_one_uuid,
    pop_n_uuids=pop_n_uuids,
)
new_post_kiss_response_node = aeries_gale_context.pop_one_uuid()

new_leave_node = aeries_gale_context.pop_one_uuid()
modded_kisses_entry_dialog_node_uuid= aeries_gale_context.pop_one_uuid()
aeries_kiss_edits = KissEdits(
    modded_kisses_entry_dialog_node_uuid=modded_kisses_entry_dialog_node_uuid,
    companion_response_node_uuid=pop_one_uuid(),
    modded_kiss_response_destination_node_uuid=new_post_kiss_response_node,
    global_flags_for_modded_kisses=[],
    companion_REALLY_tag=companion_REALLY_tags["gale"],
    existing_companion_leave_node_uuid=new_leave_node,
)

def run():
    all_kisses = get_kiss_entries(
        kiss_datas=[ast_kiss_data, wyll_kiss_data, gale_last_kiss_data],
        print_info=True,
    )

    alt_kiss_entries = [all_kisses["wyll"]["A"], all_kisses["wyll"]["C"], all_kisses["ast"]["B"], all_kisses["ast"]["C"]]
    alt_kiss_tav_string_handle = "h685c132cgab52g4eabg8a95gbaffd6938169" # Tav: I wouldn't say no to a kiss
    alt_kiss_companion_responses = [
       # DialogTextEntry(text_uuid="h019f17e2gd852g455agb6f2g9490cabdd27a", line_id=aeries_gale_context.pop_one_uuid()), # Fee, Don't tempt me. (remove)
        # DialogTextEntry(text_uuid="h453b3f70gbde5g4874gb3c0g04bc48c61e77", line_id=aeries_gale_context.pop_one_uuid()), # I've never wanted to kiss you more than I do now. (he's kneeling here, remove)
        DialogTextEntry(text_uuid="h5f37c801g99c0g46cfg9b10g9013ef01770d", line_id=aeries_gale_context.pop_one_uuid()), # Splendid. A bit of boldness will serve us well.
        DialogTextEntry(text_uuid="h72d6a584g47beg4736gb392g9329f0ef59ac", line_id=aeries_gale_context.pop_one_uuid()), # I like the sound of that
     #   DialogTextEntry(text_uuid="h453b3f70gbde5g4874gb3c0g04bc48c61e77", line_id=aeries_gale_context.pop_one_uuid()), # 	I've never wanted to kiss you more than I do now. (he'skneeling, remove)
      #  DialogTextEntry(text_uuid="hf4218f05g7b72g410bg8a62g9f438098b69e", line_id=aeries_gale_context.pop_one_uuid()), # Careful - I may just take you up on that.
    ]
    last_kiss_entries = [all_kisses["gale_last"]["A"], all_kisses["gale_last"]["B"], all_kisses["gale_last"]["C"], all_kisses["gale_last"]["D"]]
    last_kiss_tav_string_handle = "ha4909ff5g2266g4fb5g90a0g9930b216c600" # Tav:  Do we have time for one last kiss?
    last_kiss_companion_responses = [
        DialogTextEntry(text_uuid="h4bec54c2g4c84g4c77gbbbfg56e5f72f4b63", line_id=aeries_gale_context.pop_one_uuid()), #There's <i>nothing</i> we can't handle - I promise you that.
        DialogTextEntry(text_uuid="hfcb427aag9044g4916gb86dg3d46ef07c886", line_id=aeries_gale_context.pop_one_uuid()), # It's now or never

    ]
    kiss_nodes = []
    companion_dialog_uuid_and_handle=[]
    for kiss_entries, kiss_tav_string_handle, companion_responses in [(alt_kiss_entries, alt_kiss_tav_string_handle, alt_kiss_companion_responses), (last_kiss_entries, last_kiss_tav_string_handle, last_kiss_companion_responses)]:
        
        this_kiss_guids, this_kiss_dialog_nodes = add_kisses(context=aeries_gale_context, kiss_edits=aeries_kiss_edits, kiss_entries=kiss_entries, companion_name_key="gale")
        kiss_nodes.extend(this_kiss_dialog_nodes)
        kiss_companion_response_node_uuid = aeries_gale_context.pop_one_uuid()
        option_nodes = aeries_kiss_edits.create_dialog_options_for_kisses(
            option_node_uuid=aeries_gale_context.pop_one_uuid(),
            transition_node_uuid=kiss_companion_response_node_uuid,
            kiss_node_uuids=this_kiss_guids,
            tav_dialog_option=DialogTextEntry(text_uuid=kiss_tav_string_handle, line_id=aeries_gale_context.pop_one_uuid()),
            companion_response_data=companion_responses
        )
        companion_dialog_uuid_and_handle.append((kiss_companion_response_node_uuid, companion_responses))

        kiss_nodes.extend(option_nodes)

    shared_options = aeries_kiss_edits.create_kiss_options_shared(
        tav_option_text_uuid="he2213255g0588g4886ga55cg6e033b77d28a", # A private word would be nice
        line_id=aeries_gale_context.pop_one_uuid()
    )
    
    tav_hug_option_uuid = aeries_gale_context.pop_one_uuid()
    tav_hug_option_uuid2 = aeries_gale_context.pop_one_uuid()

    aeries_kiss_edits.add_existing_dialog_option(
        tav_node_uuid=tav_hug_option_uuid
    )
    aeries_kiss_edits.add_existing_dialog_option(
        tav_node_uuid=tav_hug_option_uuid2
    )
    new_post_kiss_responses = [
        DialogTextEntry(text_uuid="h8d273ab8g513eg43c3gb437g127c9604a897", line_id=aeries_gale_context.pop_one_uuid()), # You're quite spectacular, you know.
        DialogTextEntry(text_uuid="h5e3fa0c4g90f2g48edg93ebg05d0064598fb", line_id=aeries_gale_context.pop_one_uuid()), # The chance to see life through your eyes, as well as my own - it's been everything I hoped it would be.
        DialogTextEntry(text_uuid="h1e42914cg9447g46e6gb977g4cf4fe1568fb", line_id=aeries_gale_context.pop_one_uuid()), # You like so many things about me I'd have sooner discarded... Your generosity is quite wonderful.
        DialogTextEntry(text_uuid="h354b58a5g3023g49f0gb9b8gbc1ee4660ce9", line_id=aeries_gale_context.pop_one_uuid()), # I can't imagine anywhere that could turn my heart from you, cursed or otherwise. You'd always be as beautiful, and as impressive.
       # DialogTextEntry(text_uuid="h33fcbff8g004cg4e2ag84a2g1f1e181edc39", line_id=aeries_gale_context.pop_one_uuid()), # I am beyond lucky to have you. Sometimes even the power of the Weave seems mundane, compared to how you make me feel. (too strong, remove)
      #  DialogTextEntry(text_uuid="hb1f0a717g994dg4f24gb8cegb8edef3c52cb", line_id=aeries_gale_context.pop_one_uuid()), # Over far too soon. I was rather enjoying that.
      #  DialogTextEntry(text_uuid="h9c941405g45d8g4eceg8643ge7298b425ce5", line_id=aeries_gale_context.pop_one_uuid()), # That hit the spot
    ]
    aeries_gale_context.dialog_tree.content.dialog_nodes.add_dialog_node(
        NewDialogNode(
            constructor="TagAnswer",
            uuid=new_post_kiss_response_node, # try no children? maybe it'll work? :D 
            speaker="0",
            tagged_texts=[
                NewTaggedText(tag_texts=NewTagTexts(texts=[
                    NewTagText(
                        tag_text=x.text_uuid, # You're quite spectacular, you know.
                        line_id=x.line_id,
                        custom_sequence_id=None if i == 0 else x.line_id,
                    ) for i, x in enumerate(new_post_kiss_responses)
                ]))
            ]
        )
    )
    
    # responses to A private word would be nice
    modded_options_companion_responses = [
        DialogTextEntry(text_uuid="h5f32e3c5g753cg46d4g83a0g3946a8f00cea", line_id=aeries_gale_context.pop_one_uuid()), # Well if you insist
        DialogTextEntry(text_uuid="hc82a17fcg1fc0g44dfgaac5gb36519788952", line_id=aeries_gale_context.pop_one_uuid()), # I thought you might say that
        DialogTextEntry(text_uuid="h8c90dd2agdbbeg40b2gbfecgbd15474cb305", line_id=aeries_gale_context.pop_one_uuid()), # as you wish
       # DialogTextEntry(text_uuid="hc0b58f62g088dg43e5g8b4cg06249d525ebc", line_id=aeries_gale_context.pop_one_uuid()) , # always
       # DialogTextEntry(text_uuid="hf8546ea2g27bag40cfg8127gaf1d9664864a", line_id=aeries_gale_context.pop_one_uuid()), # Oh yes
    ]
    destinations = aeries_kiss_edits.create_modded_kiss_options_destinations(
        existing_response_node=new_post_kiss_response_node,
        companion_response_text_and_id=modded_options_companion_responses,
        should_alias=False
    )

    for node in kiss_nodes + [shared_options] + destinations :
        aeries_gale_context.dialog_tree.content.dialog_nodes.add_dialog_node(new_node=node)
        
    phase_to_copy = aeries_gale_context.timeline_tree.content.effect.effect_component_phases[0]
    n_nodes = len(phase_to_copy.phase_nodes)
    phase_index_to_copy = aeries_gale_context.timeline_tree.content.create_new_phase(
        copying_from_phase=phase_to_copy,
        new_dialog_duration=2,
        new_dialog_node_id="fc11260c-c5af-45d5-914b-3d54c1d42da0", # not used
        new_reference_id=None,
        update_node_ids=aeries_gale_context.pop_n_uuids(n=n_nodes),
        should_remove_last_subduration=True,
    )
    print(f"Using newly created phase {phase_index_to_copy=}")

    add_timeline_nodes_for_companion_response(
        context=aeries_gale_context,
        companion_response_dialog_uuid=aeries_kiss_edits.companion_response_node_uuid,
        dialog=modded_options_companion_responses,
        phase_index_to_copy=phase_index_to_copy,
    )
    add_timeline_nodes_for_companion_response(
        context=aeries_gale_context,
        companion_response_dialog_uuid=new_post_kiss_response_node,
        dialog=new_post_kiss_responses,
        phase_index_to_copy=phase_index_to_copy,
    )
    
    for dialog_uuid, dialog_entries in companion_dialog_uuid_and_handle:
        add_timeline_nodes_for_companion_response(
            context=aeries_gale_context,
            companion_response_dialog_uuid=dialog_uuid,
            dialog=dialog_entries,
            phase_index_to_copy=phase_index_to_copy,
        )
        
        
    aeries_gale_context.dialog_tree.content.dialog_nodes.insert_child_node(
        node_uuid="827b309c-b1e0-47d3-89f4-12f4bca14009", 
        child_uuids=[modded_kisses_entry_dialog_node_uuid], index=-3)

    gale_hugs = GaleHugCinematicContext()
    gale_hugs.add_hug_to_dialog(
        context=aeries_gale_context,
        post_hug_dialog_node_uuid=new_post_kiss_response_node, # new post kiss dialog
        companion_key="gale",
        tav_hug_option_uuid=tav_hug_option_uuid,
        tav_hug_option_string_handle="h2a17d3a8g24acg420fgbba7g173d4b120bd1", # May I have a hug?
        companion_response_string_handle="h690d1195g1431g4965gbfc2gdccdc2d338be", # how can I not?
        phase_index_to_copy=phase_index_to_copy
    )

    aeries_gale_context.dialog_tree.content.dialog_nodes.add_dialog_node(
        NewDialogNode(
            constructor="TagQuestion",
            uuid=new_leave_node,
            speaker="1",
            endnode="True",
            tagged_texts=[
                NewTaggedText(tag_texts=NewTagTexts(texts=[
                    NewTagText(
                        tag_text="h006f51bagc132g4c9eg8f7egcc8cc7244615", # leave
                        line_id=pop_one_uuid(),
                        custom_sequence_id=None,
                    )
                ]))
            ]
        )
    )
    
    shadowheart_hugs = ShadowheartHugCinematicContext()
    shadowheart_hugs.add_hug_to_dialog(
        context=aeries_gale_context,
        post_hug_dialog_node_uuid=new_post_kiss_response_node, # new post kiss dialog
        companion_key="gale",
        tav_hug_option_uuid=tav_hug_option_uuid2,
        tav_hug_option_string_handle="h445ea9e6g9c54g4e38g9974g0489e43cd78a", # You sound like you need a hug
        companion_response_string_handle="h75a3a48dg5c02g4547g9ef0g96373fa4c3e3", # I have to admit you're right about that.
        phase_index_to_copy=phase_index_to_copy
    )

    aeries_gale_context.timeline_tree.write_tree(output_file_path=r"Y:\bg3\mycode\galeromantic_timeline.lsx")
    aeries_gale_context.scene_tree.write_tree(output_file_path=r"Y:\bg3\mycode\galeromantic_timeline_scene.lsx")
    aeries_gale_context.dialog_tree.write_tree(output_file_path=r"Y:\bg3\mycode\galeromantic_dialog.lsx")


if __name__ == '__main__':
    run()