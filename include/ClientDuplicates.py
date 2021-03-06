import ClientConstants as CC
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusSerialisable

class DuplicateActionOptions( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS
    SERIALISABLE_NAME = 'Duplicate Action Options'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, tag_service_actions = None, rating_service_actions = None, delete_second_file = False, sync_archive = False, delete_both_files = False, sync_urls_action = None ):
        
        if tag_service_actions is None:
            
            tag_service_actions = []
            
        
        if rating_service_actions is None:
            
            rating_service_actions = []
            
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._tag_service_actions = tag_service_actions
        self._rating_service_actions = rating_service_actions
        self._delete_second_file = delete_second_file
        self._sync_archive = sync_archive
        self._delete_both_files = delete_both_files
        self._sync_urls_action = sync_urls_action
        
    
    def _GetSerialisableInfo( self ):
        
        if HG.client_controller.IsBooted():
            
            services_manager = HG.client_controller.services_manager
            
            self._tag_service_actions = [ ( service_key, action, tag_filter ) for ( service_key, action, tag_filter ) in self._tag_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in ( HC.LOCAL_TAG, HC.TAG_REPOSITORY ) ]
            self._rating_service_actions = [ ( service_key, action ) for ( service_key, action ) in self._rating_service_actions if services_manager.ServiceExists( service_key ) and services_manager.GetServiceType( service_key ) in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ]
            
        
        serialisable_tag_service_actions = [ ( service_key.encode( 'hex' ), action, tag_filter.GetSerialisableTuple() ) for ( service_key, action, tag_filter ) in self._tag_service_actions ]
        serialisable_rating_service_actions = [ ( service_key.encode( 'hex' ), action ) for ( service_key, action ) in self._rating_service_actions ]
        
        return ( serialisable_tag_service_actions, serialisable_rating_service_actions, self._delete_second_file, self._sync_archive, self._delete_both_files, self._sync_urls_action )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_tag_service_actions, serialisable_rating_service_actions, self._delete_second_file, self._sync_archive, self._delete_both_files, self._sync_urls_action ) = serialisable_info
        
        self._tag_service_actions = [ ( serialisable_service_key.decode( 'hex' ), action, HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_filter ) ) for ( serialisable_service_key, action, serialisable_tag_filter ) in serialisable_tag_service_actions ]
        self._rating_service_actions = [ ( serialisable_service_key.decode( 'hex' ), action ) for ( serialisable_service_key, action ) in serialisable_rating_service_actions ]
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_service_actions, delete_second_file ) = old_serialisable_info
            
            tag_service_actions = []
            rating_service_actions = []
            
            # As the client isn't booted when this is loaded in options, there isn't a good way to figure out tag from rating
            # So, let's just dupe and purge later on, in serialisation
            for ( service_key_encoded, action ) in serialisable_service_actions:
                
                service_key = service_key_encoded.decode( 'hex' )
                
                import ClientTags
                
                tag_filter = ClientTags.TagFilter()
                
                tag_service_actions.append( ( service_key, action, tag_filter ) )
                
                rating_service_actions.append( ( service_key, action ) )
                
            
            serialisable_tag_service_actions = [ ( service_key.encode( 'hex' ), action, tag_filter.GetSerialisableTuple() ) for ( service_key, action, tag_filter ) in tag_service_actions ]
            serialisable_rating_service_actions = [ ( service_key.encode( 'hex' ), action ) for ( service_key, action ) in rating_service_actions ]
            
            sync_archive = delete_second_file
            delete_both_files = False
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files ) = old_serialisable_info
            
            sync_urls_action = None
            
            new_serialisable_info = ( serialisable_tag_service_actions, serialisable_rating_service_actions, delete_second_file, sync_archive, delete_both_files, sync_urls_action )
            
            return ( 3, new_serialisable_info )
            
        
    
    def GetDeletedHashes( self, first_media, second_media ):
        
        first_hashes = first_media.GetHashes()
        second_hashes = second_media.GetHashes()
        
        if self._delete_second_file:
            
            return second_hashes
            
        elif self._delete_both_files:
            
            return first_hashes.union( second_hashes )
            
        else:
            
            return set()
            
        
    
    def SetTuple( self, tag_service_actions, rating_service_actions, delete_second_file, sync_archive, delete_both_files, sync_urls_action ):
        
        self._tag_service_actions = tag_service_actions
        self._rating_service_actions = rating_service_actions
        self._delete_second_file = delete_second_file
        self._sync_archive = sync_archive
        self._delete_both_files = delete_both_files
        self._sync_urls_action = sync_urls_action
        
    
    def ToTuple( self ):
        
        return ( self._tag_service_actions, self._rating_service_actions, self._delete_second_file, self._sync_archive, self._delete_both_files, self._sync_urls_action )
        
    
    def ProcessPairIntoContentUpdates( self, first_media, second_media ):
        
        list_of_service_keys_to_content_updates = []
        
        first_hashes = first_media.GetHashes()
        second_hashes = second_media.GetHashes()
        
        #
        
        service_keys_to_content_updates = {}
        
        services_manager = HG.client_controller.services_manager
        
        for ( service_key, action, tag_filter ) in self._tag_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            service_type = service.GetServiceType()
            
            if service_type == HC.LOCAL_TAG:
                
                add_content_action = HC.CONTENT_UPDATE_ADD
                
            elif service_type == HC.TAG_REPOSITORY:
                
                add_content_action = HC.CONTENT_UPDATE_PEND
                
            
            first_current_tags = first_media.GetTagsManager().GetCurrent( service_key )
            second_current_tags = second_media.GetTagsManager().GetCurrent( service_key )
            
            first_current_tags = tag_filter.Filter( first_current_tags )
            second_current_tags = tag_filter.Filter( second_current_tags )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_current_tags.difference( first_current_tags )
                second_needs = first_current_tags.difference( second_current_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, second_hashes ) ) for tag in second_needs ) )
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_current_tags.difference( first_current_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                
            elif service_type == HC.LOCAL_TAG and action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                first_needs = second_current_tags.difference( first_current_tags )
                
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, add_content_action, ( tag, first_hashes ) ) for tag in first_needs ) )
                content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, second_hashes ) ) for tag in second_current_tags ) )
                
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        for ( service_key, action ) in self._rating_service_actions:
            
            content_updates = []
            
            try:
                
                service = services_manager.GetService( service_key )
                
            except HydrusExceptions.DataMissing:
                
                continue
                
            
            first_current_value = first_media.GetRatingsManager().GetRating( service_key )
            second_current_value = second_media.GetRatingsManager().GetRating( service_key )
            
            if action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                if first_current_value == second_current_value:
                    
                    continue
                    
                
                if first_current_value is None and second_current_value is not None:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                    
                elif first_current_value is not None and second_current_value is None:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( first_current_value, second_hashes ) ) )
                    
                
            elif action == HC.CONTENT_MERGE_ACTION_COPY:
                
                if first_current_value == second_current_value:
                    
                    continue
                    
                
                if first_current_value is None and second_current_value is not None:
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                    
                
            elif action == HC.CONTENT_MERGE_ACTION_MOVE:
                
                if second_current_value is not None:
                    
                    if first_current_value is None:
                        
                        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( second_current_value, first_hashes ) ) )
                        
                    
                    content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, second_hashes ) ) )
                    
                
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates[ service_key ] = content_updates
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            list_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
            
        
        #
        
        service_keys_to_content_updates = {}
        
        if self._sync_archive:
            
            if first_media.HasInbox() and second_media.HasArchive():
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, first_hashes )
                
                service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ content_update ]
                
            elif first_media.HasArchive() and second_media.HasInbox():
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, second_hashes )
                
                service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ content_update ]
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            list_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
            
        
        #
        
        if self._sync_urls_action is not None:
            
            first_urls = set( first_media.GetLocationsManager().GetURLs() )
            second_urls = set( second_media.GetLocationsManager().GetURLs() )
            
            content_updates = []
            
            if self._sync_urls_action == HC.CONTENT_MERGE_ACTION_TWO_WAY_MERGE:
                
                first_needs = second_urls.difference( first_urls )
                second_needs = first_urls.difference( second_urls )
                
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, first_hashes ) ) )
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( second_needs, second_hashes ) ) )
                
            elif self._sync_urls_action == HC.CONTENT_MERGE_ACTION_COPY:
                
                first_needs = second_urls.difference( first_urls )
                
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( first_needs, first_hashes ) ) )
                
            
            if len( content_updates ) > 0:
                
                service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : content_updates }
                
                list_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
                
            
        
        #
        
        service_keys_to_content_updates = {}
        
        deletee_media = []
        
        if self._delete_second_file or self._delete_both_files:
            
            if self._delete_both_files:
                
                deletee_media.append( first_media )
                
            
            deletee_media.append( second_media )
            
        
        for media in deletee_media:
            
            current_locations = media.GetLocationsManager().GetCurrent()
            
            if CC.LOCAL_FILE_SERVICE_KEY in current_locations:
                
                deletee_service_key = CC.LOCAL_FILE_SERVICE_KEY
                
            elif CC.TRASH_SERVICE_KEY in current_locations:
                
                deletee_service_key = CC.TRASH_SERVICE_KEY
                
            else:
                
                deletee_service_key = None
                
            
            if deletee_service_key is not None:
                
                if deletee_service_key not in service_keys_to_content_updates:
                    
                    service_keys_to_content_updates[ deletee_service_key ] = []
                    
                
                content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, media.GetHashes() )
                
                service_keys_to_content_updates[ deletee_service_key ].append( content_update )
                
            
        
        if len( service_keys_to_content_updates ) > 0:
            
            list_of_service_keys_to_content_updates.append( service_keys_to_content_updates )
            
        
        #
        
        return list_of_service_keys_to_content_updates
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DUPLICATE_ACTION_OPTIONS ] = DuplicateActionOptions
