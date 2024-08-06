from dataclasses import dataclass, field
from dialog_tree_objects import NewDialogNode, NewDialogFlagGroup, NewTaggedText, NewFlag, NewTagTexts,NewTagText, NewEditorData
from kiss_utils import kiss_type_to_flag, body_type_to_tag


@dataclass
class DialogTextEntry:
    text_uuid: str
    line_id: str

@dataclass
class TagEntry:
    tag_uuid: str
    tag_value: bool
    tag_paramval: int

@dataclass
class FlagEntry:
    flag_uuid: str
    flag_value: bool


@dataclass
class KissEdits:
    # tav dialog node in existing relationship dialog to enter modded kiss group
    modded_kisses_entry_dialog_node_uuid: str = "d4066cad-7306-4e24-8687-45af0d2169c4"
    # companion dialog node as response to tav node above, leads to group of modded kisses
    companion_response_node_uuid: str  = "e4d8d177-a20b-4c2a-9520-3bdd6d50b355"
    # node that kisses should return to after end kiss companion response. This node will bring dialog back to the modded kisses group above
    modded_kiss_response_destination_node_uuid: str = "8fc60200-8bc6-402a-8591-a1ef97953c85"


    global_flags_for_modded_kisses: list[FlagEntry] = field(default_factory=lambda: [
        FlagEntry("c446ce94-efd8-45d5-b407-284177b6b57e", True), # vampire lord
        FlagEntry("347b8d34-c287-4d15-83c5-7ae6786003c7", True), # after black mass
    ])
    companion_REALLY_tag: str = "23a46e79-e73c-4043-940f-cb0aace9ab2e" # ast

    # existing node in tree that lets player leave dialog. we reuse this.
    existing_companion_leave_node_uuid: str = "47beea43-1e75-49aa-b672-7e3b05e648e9"

    created_modded_kiss_options: list[str] = field(default_factory=lambda: [])
    did_create_kiss_response_destination: bool = False

    # creates a parent dialog option in the companion's existing relationship dialog
    # modded kiss groups can then be added to this dialog group
    def create_kiss_options_shared(self,
                                tav_option_text_uuid: str = "h8f247539gd84cg462cgaf34ga8a59fe81850", # I wouldn't say no to a kiss
                                line_id: str = "e7db5769-af66-4acf-b16f-baff8c170c9a", # not actually used
    ) -> NewDialogNode:
        return NewDialogNode(
            constructor="TagQuestion",
            uuid=self.modded_kisses_entry_dialog_node_uuid,
            speaker="1",
            children_uuids=[
                self.companion_response_node_uuid
            ],
            check_flags=[
                NewDialogFlagGroup(
                    type_str="Global",
                    flags=[
                        NewFlag(
                            uuid=x.flag_uuid,
                            value=x.flag_value, 
                            param_val=None
                        ) for x in self.global_flags_for_modded_kisses
                    ]
                ),
                NewDialogFlagGroup(
                    type_str="Tag",
                    flags=[
                        NewFlag(
                            uuid=self.companion_REALLY_tag,
                            value=True, 
                            param_val=0
                        ),
                        NewFlag(
                            uuid="1a2f70d6-8ead-4eb5-a824-79ee1971764a", # disable karlach tav
                            value=False, 
                            param_val=1
                        )
                    ]
                )
            ],
            tagged_texts=[
                NewTaggedText(
                    tag_texts=NewTagTexts(
                        texts=[
                            NewTagText(
                                tag_text=tav_option_text_uuid,
                                line_id=line_id,
                                custom_sequence_id=None,
                            )
                        ]
                    )
                )
            ]
        )

    # run this at the end
    def create_modded_kiss_options_destinations(self, 
        existing_response_node: str | None,
        companion_response_text_and_id: list[DialogTextEntry] = [],
        should_alias: bool = True,
    ) -> list[NewDialogNode]:

        assert not self.did_create_kiss_response_destination
        self.did_create_kiss_response_destination = True
        
        nodes = [
            NewDialogNode(
            constructor="TagAnswer",
            uuid=self.companion_response_node_uuid,
            speaker="0",
            transitionmode=None if len(companion_response_text_and_id) > 0 else "2",
            children_uuids=self.created_modded_kiss_options + [
                self.existing_companion_leave_node_uuid
            ],
            tagged_texts=[
                NewTaggedText(
                    tag_texts=NewTagTexts(
                        texts=[
                            NewTagText(
                                tag_text=x.text_uuid,
                                line_id=x.line_id,
                                custom_sequence_id=None if i == 0 else x.line_id,
                            ) for i, x in enumerate(companion_response_text_and_id)
                        ]
                    )
                ) 
            ] if len(companion_response_text_and_id) > 0 else []
        )]
        if should_alias and existing_response_node is not None:
            nodes.append(NewDialogNode(
                constructor="Alias",
                uuid=self.modded_kiss_response_destination_node_uuid, # mod kisses should come back to this node
                speaker="-1",
                source_node=existing_response_node, # existing kiss end response but maybe make a new one for custom dialog
                children_uuids=self.created_modded_kiss_options + [
                    self.existing_companion_leave_node_uuid
                ],
            ))

        return nodes


    def create_dialog_options_for_kisses(
        self,
        option_node_uuid: str,
        transition_node_uuid: str,
        kiss_node_uuids: list[str],
        tav_dialog_option: DialogTextEntry,
        companion_response_data: list[DialogTextEntry], # list of text uuid and line id
        tags_required_for_option: list[TagEntry] = [],
    ) -> list[NewDialogNode]:
        assert not self.did_create_kiss_response_destination
        self.created_modded_kiss_options.append(option_node_uuid)
        if len(companion_response_data) == 0:
            companion_response_node = NewDialogNode(
                constructor="TagAnswer",
                uuid=transition_node_uuid,
                speaker="0",
                transitionmode="2",
                children_uuids=kiss_node_uuids # leads to kisses in this batch
            )
        else:
            companion_response_node = NewDialogNode(
                constructor="TagAnswer",
                uuid=transition_node_uuid,
                speaker="0",
                children_uuids=kiss_node_uuids, # leads to kisses in this batch
                tagged_texts=[
                    NewTaggedText(
                    tag_texts=NewTagTexts(
                        texts=[
                            NewTagText(
                                tag_text=x.text_uuid,
                                line_id=x.line_id,
                                custom_sequence_id=None if i == 0 else x.line_id,
                            ) for i, x in enumerate(companion_response_data)
                        ]
                    )
                )
                ]
            )
        check_flags = []
        if len(tags_required_for_option) > 0:
            check_flags.append(NewDialogFlagGroup(
                type_str="Tag",
                flags=[
                        NewFlag(
                            uuid=x.tag_uuid,
                            value=x.tag_value, 
                            param_val=x.tag_paramval
                        ) for x in tags_required_for_option
                    ]
            ))
        return[ NewDialogNode( # dialog option for tav to choose this group of kisses
            constructor="TagQuestion",
            speaker="1",
            uuid=option_node_uuid,
            children_uuids=[transition_node_uuid],
            set_flags=[           
                NewDialogFlagGroup(
                    type_str="Object",
                    flags=[
                        NewFlag(
                            uuid="2a98bc41-f6b7-4277-a282-1a91c4ef8a9b", # start kiss
                            value=True, 
                            param_val=0
                        )
                    ]
                )],
            check_flags=check_flags,
            tagged_texts=[
                NewTaggedText(
                    tag_texts=NewTagTexts(
                        texts=[
                            NewTagText( # Tav option node
                                tag_text=tav_dialog_option.text_uuid,
                                line_id=tav_dialog_option.line_id,
                                custom_sequence_id=None,
                            ),
                        ]
                    )
                )
            ]
        ), companion_response_node]

    # add options that are not kisses. for example hugs or just chatting
    def add_existing_dialog_option(
        self,
        tav_node_uuid: str,
    ) -> None:
        assert not self.did_create_kiss_response_destination
        self.created_modded_kiss_options.append(tav_node_uuid)
       
        
    def create_kiss_cinematic_node(self, node_uuid: str,
                                kiss_type_letter: str,
                                kiss_body_tags: list[str],
                                editor_text: str) -> NewDialogNode:
        assert not self.did_create_kiss_response_destination

        check_flags = [
                NewDialogFlagGroup(
                    type_str="Object",
                    flags=[
                        NewFlag(
                            uuid=kiss_type_to_flag[kiss_type_letter], 
                            value=True, 
                            param_val=0
                        )
                    ]
            )]
        for body_tag in kiss_body_tags:
            check_flags.append(
                NewDialogFlagGroup(
                    type_str="Tag",
                    flags=[
                        NewFlag(
                            uuid=body_type_to_tag[body_tag], 
                            value=True, 
                            param_val=1
                        )
                    ]
            )
            )
        return NewDialogNode(
            constructor="TagCinematic",
            uuid=node_uuid,
            speaker="-1",
            children_uuids=[self.modded_kiss_response_destination_node_uuid],
            set_flags=[           
                NewDialogFlagGroup(
                    type_str="Object",
                    flags=[
                        NewFlag(
                            uuid="f13348d0-34bf-4328-80a5-29dd8a7b0aef", # end kiss
                            value=True, 
                            param_val=0
                        )
                    ]
            )],
            check_flags=check_flags,
            editor_data=[NewEditorData(editor_text=editor_text)]
        )