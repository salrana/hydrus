import ClientConstants as CC
import ClientGUICommon
import ClientGUIDialogs
import ClientGUIListCtrl
import ClientGUIScrolledPanelsReview
import ClientGUITopLevelWindows
import ClientThreading
import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import HydrusGlobals as HG
import HydrusNATPunch
import HydrusNetwork
import HydrusPaths
import os
import time
import wx

class ReviewServicePanel( wx.Panel ):
    
    def __init__( self, parent, service ):
        
        wx.Panel.__init__( self, parent )
        
        self._service = service
        
        service_type = self._service.GetServiceType()
        
        subpanels = []
        
        subpanels.append( self._ServicePanel( self, service ) )
        
        if service_type in HC.REMOTE_SERVICES:
            
            subpanels.append( self._ServiceRemotePanel( self, service ) )
            
        
        if service_type in HC.RESTRICTED_SERVICES:
            
            subpanels.append( self._ServiceRestrictedPanel( self, service ) )
            
        
        if service_type in HC.FILE_SERVICES:
            
            subpanels.append( self._ServiceFilePanel( self, service ) )
            
        
        if self._service.GetServiceKey() == CC.COMBINED_LOCAL_FILE_SERVICE_KEY:
            
            subpanels.append( self._ServiceCombinedLocalFilesPanel( self, service ) )
            
        
        if self._service.GetServiceKey() == CC.TRASH_SERVICE_KEY:
            
            subpanels.append( self._ServiceTrashPanel( self, service ) )
            
        
        if service_type in HC.TAG_SERVICES:
            
            subpanels.append( self._ServiceTagPanel( self, service ) )
            
        
        if service_type in HC.RATINGS_SERVICES:
            
            subpanels.append( self._ServiceRatingPanel( self, service ) )
            
        
        if service_type in HC.REPOSITORIES:
            
            subpanels.append( self._ServiceRepositoryPanel( self, service ) )
            
        
        if service_type == HC.IPFS:
            
            subpanels.append( self._ServiceIPFSPanel( self, service ) )
            
        
        if service_type == HC.LOCAL_BOORU:
            
            subpanels.append( self._ServiceLocalBooruPanel( self, service ) )
            
        
        #
        
        vbox = wx.BoxSizer( wx.VERTICAL )
        
        for panel in subpanels:
            
            vbox.Add( panel, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        self.SetSizer( vbox )
        
    
    def _DisplayService( self ):
        
        service_type = self._service.GetServiceType()
        
        self._DisplayAccountInfo()
        
        if service_type in HC.REPOSITORIES + HC.LOCAL_SERVICES:
            
            service_info = self._controller.Read( 'service_info', self._service_key )
            
            if service_type in ( HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ):
                
                num_ratings = service_info[ HC.SERVICE_INFO_NUM_FILES ]
                
                self._ratings_text.SetLabelText( HydrusData.ToHumanInt( num_ratings ) + ' files rated' )
                
            elif service_type == HC.LOCAL_BOORU:
                
                num_shares = service_info[ HC.SERVICE_INFO_NUM_SHARES ]
                
                self._num_shares.SetLabelText( HydrusData.ToHumanInt( num_shares ) + ' shares currently active' )
                
            
        
    
    def EventImmediateSync( self, event ):
        
        def do_it():
            
            job_key = ClientThreading.JobKey( pausable = True, cancellable = True )
            
            job_key.SetVariable( 'popup_title', self._service.GetName() + ': immediate sync' )
            job_key.SetVariable( 'popup_text_1', 'downloading' )
            
            self._controller.pub( 'message', job_key )
            
            content_update_package = self._service.Request( HC.GET, 'immediate_content_update_package' )
            
            c_u_p_num_rows = content_update_package.GetNumRows()
            c_u_p_total_weight_processed = 0
            
            update_speed_string = ''
            
            content_update_index_string = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
            
            job_key.SetVariable( 'popup_text_1', content_update_index_string + 'committing' + update_speed_string )
            
            job_key.SetVariable( 'popup_gauge_1', ( c_u_p_total_weight_processed, c_u_p_num_rows ) )
            
            for ( content_updates, weight ) in content_update_package.IterateContentUpdateChunks():
                
                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                
                if should_quit:
                    
                    job_key.Delete()
                    
                    return
                    
                
                content_update_index_string = 'content row ' + HydrusData.ConvertValueRangeToPrettyString( c_u_p_total_weight_processed, c_u_p_num_rows ) + ': '
                
                job_key.SetVariable( 'popup_text_1', content_update_index_string + 'committing' + update_speed_string )
                
                job_key.SetVariable( 'popup_gauge_1', ( c_u_p_total_weight_processed, c_u_p_num_rows ) )
                
                precise_timestamp = HydrusData.GetNowPrecise()
                
                self._controller.WriteSynchronous( 'content_updates', { self._service_key : content_updates } )
                
                it_took = HydrusData.GetNowPrecise() - precise_timestamp
                
                rows_s = weight / it_took
                
                update_speed_string = ' at ' + HydrusData.ToHumanInt( rows_s ) + ' rows/s'
                
                c_u_p_total_weight_processed += weight
                
            
            job_key.DeleteVariable( 'popup_gauge_1' )
            
            self._service.SyncThumbnails( job_key )
            
            job_key.SetVariable( 'popup_text_1', 'done! ' + HydrusData.ToHumanInt( c_u_p_num_rows ) + ' rows added.' )
            
            job_key.Finish()
            
        
        self._controller.CallToThread( do_it )
        
    
    def GetServiceKey( self ):
        
        return self._service.GetServiceKey()
        
    
    class _ServicePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'name and type' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._name_and_type = ClientGUICommon.BetterStaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._name_and_type, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            name = self._service.GetName()
            service_type = self._service.GetServiceType()
            
            label = name + ' - ' + HC.service_string_lookup[ service_type ]
            
            self._name_and_type.SetLabelText( label )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceCombinedLocalFilesPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'combined local files' )
            
            self._service = service
            
            self._clear_deleted_files_record = ClientGUICommon.BetterButton( self, 'clear deleted files record', self._ClearDeletedFilesRecord )
            
            #
            
            self.Add( self._clear_deleted_files_record, CC.FLAGS_LONE_BUTTON )
            
        
        def _ClearDeletedFilesRecord( self ):
            
            message = 'This will instruct your database to forget its entire record of locally deleted files, meaning that if it ever encounters any of those files again, it will assume they are new and reimport them. This operation cannot be undone.'
            
            with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg_add:
                
                result = dlg_add.ShowModal()
                
                if result == wx.ID_YES:
                    
                    hashes = None
                    
                    content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADVANCED, ( 'delete_deleted', hashes ) )
                    
                    service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ content_update ] }
                    
                    HG.client_controller.Write( 'content_updates', service_keys_to_content_updates )
                    
                    HG.client_controller.pub( 'service_updated', self._service )
                    
                
            
        
    
    class _ServiceFilePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'files' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._file_info_st = ClientGUICommon.BetterStaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._file_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( text ):
                
                if not self:
                    
                    return
                    
                
                self._file_info_st.SetLabelText( text )
                
            
            service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
            
            num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            total_size = service_info[ HC.SERVICE_INFO_TOTAL_SIZE ]
            
            text = HydrusData.ToHumanInt( num_files ) + ' files, totalling ' + HydrusData.ConvertIntToBytes( total_size )
            
            if service.GetServiceType() in ( HC.COMBINED_LOCAL_FILE, HC.FILE_REPOSITORY ):
                
                num_deleted_files = service_info[ HC.SERVICE_INFO_NUM_DELETED_FILES ]
                
                text += ' - ' + HydrusData.ToHumanInt( num_deleted_files ) + ' deleted files'
                
            
            wx.CallAfter( wx_code, text )
            
        
    
    class _ServiceRemotePanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'this client\'s network use' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._address = ClientGUICommon.BetterStaticText( self )
            self._functional = ClientGUICommon.BetterStaticText( self )
            self._bandwidth_summary = ClientGUICommon.BetterStaticText( self )
            self._bandwidth_panel = wx.Panel( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._address, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._functional, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            credentials = self._service.GetCredentials()
            
            ( host, port ) = credentials.GetAddress()
            
            self._address.SetLabelText( host + ':' + str( port ) )
            
            status = self._service.GetStatusString()
            
            self._functional.SetLabelText( status )
            
            bandwidth_summary = self._service.GetBandwidthCurrentMonthSummary()
            
            self._bandwidth_summary.SetLabelText( bandwidth_summary )
            
            self._bandwidth_panel.DestroyChildren()
            
            b_gauges = []
            
            bandwidth_rows = self._service.GetBandwidthStringsAndGaugeTuples()
            
            b_vbox = wx.BoxSizer( wx.VERTICAL )
            
            for ( status, ( value, range ) ) in bandwidth_rows:
                
                gauge = ClientGUICommon.TextAndGauge( self._bandwidth_panel )
                
                gauge.SetValue( status, value, range )
                
                b_vbox.Add( gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            self._bandwidth_panel.SetSizer( b_vbox )
            
            self.Layout()
            
            ClientGUITopLevelWindows.PostSizeChangedEvent( self )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceRestrictedPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'hydrus service account' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._title_and_expires_st = ClientGUICommon.BetterStaticText( self )
            self._status_st = ClientGUICommon.BetterStaticText( self )
            self._next_sync_st = ClientGUICommon.BetterStaticText( self )
            self._bandwidth_summary = ClientGUICommon.BetterStaticText( self )
            self._bandwidth_panel = wx.Panel( self )
            
            self._refresh_account_button = ClientGUICommon.BetterButton( self, 'refresh account', self._RefreshAccount )
            self._copy_account_key_button = ClientGUICommon.BetterButton( self, 'copy account key', self._CopyAccountKey )
            self._permissions_button = ClientGUICommon.MenuButton( self, 'see special permissions', [] )
            
            #
            
            self._Refresh()
            
            #
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._refresh_account_button, CC.FLAGS_LONE_BUTTON )
            hbox.Add( self._copy_account_key_button, CC.FLAGS_LONE_BUTTON )
            hbox.Add( self._permissions_button, CC.FLAGS_LONE_BUTTON )
            
            self.Add( self._title_and_expires_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._status_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._next_sync_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_summary, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._bandwidth_panel, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
            self.Add( hbox, CC.FLAGS_BUTTON_SIZER )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _CopyAccountKey( self ):
            
            account = self._service.GetAccount()
            
            account_key = account.GetAccountKey()
            
            account_key_hex = account_key.encode( 'hex' )
            
            HG.client_controller.pub( 'clipboard', 'text', account_key_hex )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            account = self._service.GetAccount()
            
            account_type = account.GetAccountType()
            
            title = account_type.GetTitle()
            
            expires_status = account.GetExpiresString()
            
            self._title_and_expires_st.SetLabelText( title + ' that ' + expires_status )
            
            account_status = account.GetStatusString()
            
            self._status_st.SetLabelText( account_status )
            
            next_sync_status = self._service.GetNextAccountSyncStatus()
            
            self._next_sync_st.SetLabelText( next_sync_status )
            
            #
            
            bandwidth_summary = account.GetBandwidthCurrentMonthSummary()
            
            self._bandwidth_summary.SetLabelText( bandwidth_summary )
            
            self._bandwidth_panel.DestroyChildren()
            
            b_gauges = []
            
            bandwidth_rows = account.GetBandwidthStringsAndGaugeTuples()
            
            b_vbox = wx.BoxSizer( wx.VERTICAL )
            
            for ( status, ( value, range ) ) in bandwidth_rows:
                
                gauge = ClientGUICommon.TextAndGauge( self._bandwidth_panel )
                
                gauge.SetValue( status, value, range )
                
                b_vbox.Add( gauge, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
                
            
            self._bandwidth_panel.SetSizer( b_vbox )
            
            #
            
            self._refresh_account_button.SetLabelText( 'refresh account' )
            self._refresh_account_button.Enable()
            
            account_key = account.GetAccountKey()
            
            if account_key is None or account_key == '':
                
                self._copy_account_key_button.Disable()
                
            else:
                
                self._copy_account_key_button.Enable()
                
            
            menu_items = []
            
            p_s = account_type.GetPermissionStrings()
            
            if len( p_s ) == 0:
                
                menu_items.append( ( 'label', 'no special permissions', 'no special permissions', None ) )
                
            else:
                
                for s in p_s:
                    
                    menu_items.append( ( 'label', s, s, None ) )
                    
                
            
            self._permissions_button.SetMenuItems( menu_items )
            
            self.Layout()
            
            ClientGUITopLevelWindows.PostSizeChangedEvent( self )
            
        
        def _RefreshAccount( self ):
            
            def do_it():
                
                try:
                    
                    self._service.SyncAccount( force = True )
                    
                except Exception as e:
                    
                    HydrusData.ShowException( e )
                    
                    wx.CallAfter( wx.MessageBox, HydrusData.ToUnicode( e ) )
                    
                
                wx.CallAfter( self._Refresh )
                
            
            self._refresh_account_button.Disable()
            self._refresh_account_button.SetLabelText( u'fetching\u2026' )
            
            HG.client_controller.CallToThread( do_it )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
    
    class _ServiceRepositoryPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'repository sync' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._content_panel = wx.Panel( self )
            
            self._metadata_st = ClientGUICommon.BetterStaticText( self )
            
            self._download_progress = ClientGUICommon.TextAndGauge( self )
            self._processing_progress = ClientGUICommon.TextAndGauge( self )
            
            self._sync_now_button = ClientGUICommon.BetterButton( self, 'process now', self._SyncNow )
            self._pause_play_button = ClientGUICommon.BetterButton( self, 'pause', self._PausePlay )
            self._export_updates_button = ClientGUICommon.BetterButton( self, 'export updates', self._ExportUpdates )
            self._reset_button = ClientGUICommon.BetterButton( self, 'reset processing cache', self._Reset )
            
            #
            
            self._Refresh()
            
            #
            
            new_options = HG.client_controller.new_options
            
            if not new_options.GetBoolean( 'advanced_mode' ):
                
                self._sync_now_button.Hide()
                self._export_updates_button.Hide()
                self._reset_button.Hide()
                
            
            hbox = wx.BoxSizer( wx.HORIZONTAL )
            
            hbox.Add( self._sync_now_button, CC.FLAGS_LONE_BUTTON )
            hbox.Add( self._pause_play_button, CC.FLAGS_LONE_BUTTON )
            hbox.Add( self._export_updates_button, CC.FLAGS_LONE_BUTTON )
            hbox.Add( self._reset_button, CC.FLAGS_LONE_BUTTON )
            
            self.Add( self._metadata_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._download_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._processing_progress, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( hbox, CC.FLAGS_BUTTON_SIZER )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _ExportUpdates( self ):
            
            def wx_done():
                
                if not self:
                    
                    return
                    
                
                self._export_updates_button.SetLabelText( 'export updates' )
                self._export_updates_button.Enable()
                
            
            def do_it( dest_dir, service ):
                
                try:
                    
                    update_hashes = service.GetUpdateHashes()
                    
                    num_to_do = len( update_hashes )
                    
                    if num_to_do == 0:
                        
                        wx.CallAfter( wx.MessageBox, 'No updates to export!' )
                        
                    else:
                        
                        job_key = ClientThreading.JobKey( cancellable = True )
                        
                        try:
                            
                            job_key.SetVariable( 'popup_title', 'exporting updates for ' + service.GetName() )
                            HG.client_controller.pub( 'message', job_key )
                            
                            client_files_manager = HG.client_controller.client_files_manager
                            
                            for ( i, update_hash ) in enumerate( update_hashes ):
                                
                                ( i_paused, should_quit ) = job_key.WaitIfNeeded()
                                
                                if should_quit:
                                    
                                    job_key.SetVariable( 'popup_text_1', 'Cancelled!' )
                                    
                                    return
                                    
                                
                                try:
                                    
                                    update_path = client_files_manager.GetFilePath( update_hash, HC.APPLICATION_HYDRUS_UPDATE_CONTENT )
                                    
                                    dest_path = os.path.join( dest_dir, update_hash.encode( 'hex' ) )
                                    
                                    HydrusPaths.MirrorFile( update_path, dest_path )
                                    
                                except HydrusExceptions.FileMissingException:
                                    
                                    continue
                                    
                                finally:
                                    
                                    job_key.SetVariable( 'popup_text_1', HydrusData.ConvertValueRangeToPrettyString( i + 1, num_to_do ) )
                                    job_key.SetVariable( 'popup_gauge_1', ( i, num_to_do ) )
                                    
                                
                            
                            job_key.SetVariable( 'popup_text_1', 'Done!' )
                            
                        finally:
                            
                            job_key.DeleteVariable( 'popup_gauge_1' )
                            
                            job_key.Finish()
                            
                        
                    
                finally:
                    
                    wx.CallAfter( wx_done )
                    
                
            
            with wx.DirDialog( self, 'Select export location.' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_OK:
                    
                    path = HydrusData.ToUnicode( dlg.GetPath() )
                    
                    self._export_updates_button.SetLabelText( u'exporting\u2026' )
                    self._export_updates_button.Disable()
                    
                    HG.client_controller.CallToThread( do_it, path, self._service )
                    
                
            
        
        def _PausePlay( self ):
            
            self._service.PausePlay()
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            service_paused = self._service.IsPaused()
            
            self._sync_now_button.Disable()
            
            if service_paused:
                
                self._pause_play_button.SetLabelText( 'unpause' )
                
            else:
                
                self._pause_play_button.SetLabelText( 'pause' )
                
            
            self._metadata_st.SetLabelText( self._service.GetNextUpdateDueString() )
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def _Reset( self ):
            
            name = self._service.GetName()
            
            message = 'This will remove all the processed information for ' + name + ' from the database, setting the \'processed\' gauge back to 0.' + os.linesep * 2 + 'Once the service is reset, you will have to reprocess everything that has been downloaded over again. The client will naturally do this in its idle time as before, just starting over from the beginning.' + os.linesep * 2 + 'If you do not understand what this does, click no!'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    message = 'Seriously, are you absolutely sure?'
                    
                    with ClientGUIDialogs.DialogYesNo( self, message ) as dlg2:
                        
                        if dlg2.ShowModal() == wx.ID_YES:
                            
                            self._service.Reset()
                            
                        
                    
                
            
        
        def _SyncNow( self ):
            
            message = 'This will tell the database to process any outstanding update files.'
            message += os.linesep * 2
            message += 'This is a big task that usually runs during idle time. It locks the entire database and takes over the ui, stopping you from interacting with it. It is cancellable but may still take some time to return ui control to you.'
            message += os.linesep * 2
            message += 'If you are a new user, click \'no\'!'
            
            with ClientGUIDialogs.DialogYesNo( self, message ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    def do_it():
                        
                        self._service.Sync( False )
                        
                        self._my_updater.Update()
                        
                    
                    self._sync_now_button.Disable()
                    
                    HG.client_controller.CallToThread( do_it )
                    
                
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( download_text, download_value, processing_text, processing_value, range ):
                
                if not self:
                    
                    return
                    
                
                self._download_progress.SetValue( download_text, download_value, range )
                self._processing_progress.SetValue( processing_text, processing_value, range )
                
                if processing_value == download_value:
                    
                    self._sync_now_button.Disable()
                    
                
                if download_value == 0:
                    
                    self._export_updates_button.Disable()
                    
                else:
                    
                    self._export_updates_button.Enable()
                    
                
                if processing_value == 0:
                    
                    self._reset_button.Disable()
                    
                else:
                    
                    self._reset_button.Enable()
                    
                
                processing_work_to_do = processing_value < download_value
                
                service_paused = self._service.IsPaused()
                
                all_repo_sync_paused = HG.client_controller.options[ 'pause_repo_sync' ]
                
                if service_paused or all_repo_sync_paused or not processing_work_to_do:
                    
                    self._sync_now_button.Disable()
                    
                else:
                    
                    self._sync_now_button.Enable()
                    
                
            
            ( download_value, processing_value, range ) = HG.client_controller.Read( 'repository_progress', service.GetServiceKey() )
            
            download_text = 'downloaded ' + HydrusData.ConvertValueRangeToPrettyString( download_value, range )
            
            processing_text = 'processed ' + HydrusData.ConvertValueRangeToPrettyString( processing_value, range )
            
            wx.CallAfter( wx_code, download_text, download_value, processing_text, processing_value, range )
            
        
    
    class _ServiceIPFSPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'ipfs' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._check_running_button = ClientGUICommon.BetterButton( self, 'check daemon', self._CheckRunning )
            
            self._ipfs_shares = ClientGUIListCtrl.SaneListCtrl( self, 200, [ ( 'multihash', 120 ), ( 'num files', 80 ), ( 'total size', 80 ), ( 'note', -1 ) ], delete_key_callback = self._Unpin, activation_callback = self._SetNotes )
            
            self._copy_multihash_button = ClientGUICommon.BetterButton( self, 'copy multihashes', self._CopyMultihashes )
            self._show_selected_button = ClientGUICommon.BetterButton( self, 'show selected in main gui', self._ShowSelectedInNewPages )
            self._set_notes_button = ClientGUICommon.BetterButton( self, 'set notes', self._SetNotes )
            self._unpin_button = ClientGUICommon.BetterButton( self, 'unpin selected', self._Unpin )
            
            #
            
            self._Refresh()
            
            #
            
            button_box = wx.BoxSizer( wx.HORIZONTAL )
            
            button_box.Add( self._copy_multihash_button, CC.FLAGS_VCENTER )
            button_box.Add( self._show_selected_button, CC.FLAGS_VCENTER )
            button_box.Add( self._set_notes_button, CC.FLAGS_VCENTER )
            button_box.Add( self._unpin_button, CC.FLAGS_VCENTER )
            
            self.Add( self._check_running_button, CC.FLAGS_LONE_BUTTON )
            self.Add( self._ipfs_shares, CC.FLAGS_EXPAND_BOTH_WAYS )
            self.Add( button_box, CC.FLAGS_BUTTON_SIZER )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _CheckRunning( self ):
            
            def wx_clean_up():
                
                if self:
                    
                    self._check_running_button.Enable()
                    
                
            
            def do_it():
                
                try:
                    
                    version = self._service.GetDaemonVersion()
                    
                    message = 'Everything looks ok! Daemon reports version: ' + version
                    
                    wx.CallAfter( wx.MessageBox, message )
                    
                except:
                    
                    message = 'There was a problem! Check your popup messages for the error.'
                    
                    wx.CallAfter( wx.MessageBox, message )
                    
                finally:
                    
                    wx.CallAfter( wx_clean_up )
                    
                
            
            self._check_running_button.Disable()
            
            HG.client_controller.CallToThread( do_it )
            
        
        def _CopyMultihashes( self ):
            
            multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetSelectedClientData() ]
            
            if len( multihashes ) == 0:
                
                multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetClientData() ]
                
            
            if len( multihashes ) > 0:
                
                multihash_prefix = self._service.GetMultihashPrefix()
                
                text = os.linesep.join( ( multihash_prefix + multihash for multihash in multihashes ) )
                
                HG.client_controller.pub( 'clipboard', 'text', text )
                
            
        
        def _GetDisplayTuple( self, sort_tuple ):
            
            ( multihash, num_files, total_size, note ) = sort_tuple
            
            pretty_multihash = multihash
            pretty_num_files = HydrusData.ToHumanInt( num_files )
            pretty_total_size = HydrusData.ConvertIntToBytes( total_size )
            pretty_note = note
            
            return ( pretty_multihash, pretty_num_files, pretty_total_size, pretty_note )
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def _SetNotes( self ):
            
            for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetSelectedClientData():
                
                with ClientGUIDialogs.DialogTextEntry( self, 'Set a note for ' + multihash + '.' ) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        hashes = HG.client_controller.Read( 'service_directory', self._service.GetServiceKey(), multihash )
                        
                        note = dlg.GetValue()
                        
                        content_update_row = ( hashes, multihash, note )
                        
                        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_DIRECTORIES, HC.CONTENT_UPDATE_ADD, content_update_row ) ]
                        
                        HG.client_controller.Write( 'content_updates', { self._service.GetServiceKey() : content_updates } )
                        
                    else:
                        
                        break
                        
                    
                
            
            self._my_updater.Update()
            
        
        def _ShowSelectedInNewPages( self ):
            
            def do_it( shares ):
                
                try:
                    
                    for ( multihash, num_files, total_size, note ) in shares:
                        
                        hashes = HG.client_controller.Read( 'service_directory', self._service.GetServiceKey(), multihash )
                        
                        HG.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes, page_name = 'ipfs directory' )
                        
                    
                finally:
                    
                    wx.CallAfter( self._ipfs_shares.Enable )
                    
                
            
            shares = self._ipfs_shares.GetSelectedClientData()
            
            self._ipfs_shares.Disable()
            
            HG.client_controller.CallToThread( do_it, shares )
            
        
        def _Unpin( self ):
            
            def do_it( multihashes ):
                
                try:
                    
                    for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetSelectedClientData():
                        
                        self._service.UnpinDirectory( multihash )
                        
                    
                    self._ipfs_shares.RemoveAllSelected()
                    
                finally:
                    
                    wx.CallAfter( self._ipfs_shares.Enable )
                    
                
            
            with ClientGUIDialogs.DialogYesNo( self, 'Unpin (remove) all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    multihashes = [ multihash for ( multihash, num_files, total_size, note ) in self._ipfs_shares.GetSelectedClientData() ]
                    
                    self._ipfs_shares.Disable()
                    
                    HG.client_controller.CallToThread( do_it, multihashes )
                    
                
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( ipfs_shares ):
                
                if not self:
                    
                    return
                    
                
                self._ipfs_shares.DeleteAllItems()
                
                for ( multihash, num_files, total_size, note ) in ipfs_shares:
                    
                    sort_tuple = ( multihash, num_files, total_size, note )
                    
                    display_tuple = self._GetDisplayTuple( sort_tuple )
                    
                    self._ipfs_shares.Append( display_tuple, sort_tuple )
                    
                
            
            ipfs_shares = HG.client_controller.Read( 'service_directories', service.GetServiceKey() )
            
            wx.CallAfter( wx_code, ipfs_shares )
            
        
    
    class _ServiceLocalBooruPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'local booru' )
            
            self._service = service
            
            self._share_key_info = {}
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._service_status = ClientGUICommon.BetterStaticText( self )
            
            booru_search_panel = ClientGUIListCtrl.BetterListCtrlPanel( self )
            
            columns = [ ( 'name', -1 ), ( 'info', 36 ), ( 'expires', 12 ), ( 'files', 12 ) ]
            
            self._booru_shares = ClientGUIListCtrl.BetterListCtrl( booru_search_panel, 'local_booru_shares', 10, 36, columns, self._ConvertDataToListCtrlTuple, delete_key_callback = self._Delete, activation_callback = self._Edit )
            
            booru_search_panel.SetListCtrl( self._booru_shares )
            
            booru_search_panel.AddButton( 'edit', self._Edit, enabled_only_on_selection = True )
            booru_search_panel.AddButton( 'delete', self._Delete, enabled_only_on_selection = True )
            booru_search_panel.AddSeparator()
            booru_search_panel.AddButton( 'open in new page', self._OpenSearch, enabled_only_on_selection = True )
            booru_search_panel.AddButton( 'copy internal share url', self._CopyInternalShareURL, enabled_check_func = self._CanCopyURL )
            booru_search_panel.AddButton( 'copy external share url', self._CopyExternalShareURL, enabled_check_func = self._CanCopyURL )
            
            self._booru_shares.Sort()
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._service_status, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( booru_search_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _CanCopyURL( self ):
            
            has_selected = self._booru_shares.HasSelected()
            service_is_running = self._service.GetPort() is not None
            
            return has_selected and service_is_running
            
        
        def _ConvertDataToListCtrlTuple( self, share_key ):
            
            info = self._share_key_info[ share_key ]
            
            name = info[ 'name' ]
            text = info[ 'text' ]
            timeout = info[ 'timeout' ]
            hashes = info[ 'hashes' ]
            
            num_hashes = len( hashes )
            
            pretty_name = name
            pretty_text = text
            pretty_timeout = HydrusData.ConvertTimestampToPrettyExpires( timeout )
            pretty_hashes = HydrusData.ToHumanInt( num_hashes )
            
            display_tuple = ( pretty_name, pretty_text, pretty_timeout, pretty_hashes )
            sort_tuple = ( name, text, timeout, num_hashes )
            
            return ( display_tuple, sort_tuple )
            
        
        def _CopyExternalShareURL( self ):
            
            try:
                
                external_ip = HydrusNATPunch.GetExternalIP()
                
            except Exception as e:
                
                wx.MessageBox( HydrusData.ToUnicode( e ) )
                
                return
                
            
            internal_port = self._service.GetPort()
            
            if internal_port is None:
                
                wx.MessageBox( 'The local booru is not currently running!' )
                
            
            external_port = self._service.GetUPnPPort()
            
            if external_port is None:
                
                external_port = internal_port
                
            
            urls = []
            
            for share_key in self._booru_shares.GetData( only_selected = True ):
                
                url = 'http://' + external_ip + ':' + HydrusData.ToUnicode( external_port ) + '/gallery?share_key=' + share_key.encode( 'hex' )
                
                urls.append( url )
                
            
            text = os.linesep.join( urls )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
        def _CopyInternalShareURL( self ):
            
            internal_ip = '127.0.0.1'
            
            internal_port = self._service.GetPort()
            
            if internal_port is None:
                
                wx.MessageBox( 'The local booru is not currently running!' )
                
            
            urls = []
            
            for share_key in self._booru_shares.GetData( only_selected = True ):
                
                url = 'http://' + internal_ip + ':' + str( internal_port ) + '/gallery?share_key=' + share_key.encode( 'hex' )
                
                urls.append( url )
                
            
            text = os.linesep.join( urls )
            
            HG.client_controller.pub( 'clipboard', 'text', text )
            
        
        def _Delete( self ):
            
            with ClientGUIDialogs.DialogYesNo( self, 'Remove all selected?' ) as dlg:
                
                if dlg.ShowModal() == wx.ID_YES:
                    
                    for share_key in self._booru_shares.GetData( only_selected = True ):
                        
                        HG.client_controller.Write( 'delete_local_booru_share', share_key )
                        
                    
                    self._booru_shares.DeleteSelected()
                    
                
            
        
        def _Edit( self ):
            
            for share_key in self._booru_shares.GetData( only_selected = True ):
                
                info = self._share_key_info[ share_key ]
                
                name = info[ 'name' ]
                text = info[ 'text' ]
                timeout = info[ 'timeout' ]
                hashes = info[ 'hashes' ]
                
                with ClientGUIDialogs.DialogInputLocalBooruShare( self, share_key, name, text, timeout, hashes, new_share = False) as dlg:
                    
                    if dlg.ShowModal() == wx.ID_OK:
                        
                        ( share_key, name, text, timeout, hashes ) = dlg.GetInfo()
                        
                        info = {}
                        
                        info[ 'name' ] = name
                        info[ 'text' ] = text
                        info[ 'timeout' ] = timeout
                        info[ 'hashes' ] = hashes
                        
                        HG.client_controller.Write( 'local_booru_share', share_key, info )
                        
                    else:
                        
                        break
                        
                    
                
            
            self._Refresh()
            
        
        def _OpenSearch( self ):
            
            for share_key in self._booru_shares.GetData( only_selected = True ):
                
                info = self._share_key_info[ share_key ]
                
                name = info[ 'name' ]
                hashes = info[ 'hashes' ]
                
                HG.client_controller.pub( 'new_page_query', CC.LOCAL_FILE_SERVICE_KEY, initial_hashes = hashes, page_name = 'booru share: ' + name )
                
            
        
        def _Refresh( self ):
            
            if not self:
                
                return
                
            
            port = self._service.GetPort()
            
            if port is None:
                
                status = 'The local booru is not running.'
                
            else:
                
                status = 'The local booru should be running on port ' + str( port ) + '.'
                
            
            self._service_status.SetLabelText( status )
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( booru_shares ):
                
                if not self:
                    
                    return
                    
                
                self._share_key_info.update( booru_shares )
                
                self._booru_shares.SetData( booru_shares.keys() )
                
                self._booru_shares.Sort()
                
            
            booru_shares = HG.client_controller.Read( 'local_booru_shares' )
            
            wx.CallAfter( wx_code, booru_shares )
            
        
    
    class _ServiceRatingPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'ratings' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._rating_info_st = ClientGUICommon.BetterStaticText( self )
            
            #
            
            self._Refresh()
            
            #
            
            self.Add( self._rating_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _Refresh( self ):
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( text ):
                
                if not self:
                    
                    return
                    
                
                self._rating_info_st.SetLabelText( text )
                
            
            service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
            
            num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            
            text = HydrusData.ToHumanInt( num_files ) + ' files are rated'
            
            wx.CallAfter( wx_code, text )
            
        
    
    class _ServiceTagPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'tags' )
            
            self._service = service
            
            self._my_updater = ClientGUICommon.ThreadToGUIUpdater( self, self._Refresh )
            
            self._tag_info_st = ClientGUICommon.BetterStaticText( self )
            
            self._advanced_content_update = ClientGUICommon.BetterButton( self, 'advanced service-wide update', self._AdvancedContentUpdate )
            
            #
            
            new_options = HG.client_controller.new_options
            
            advanced_mode = new_options.GetBoolean( 'advanced_mode' )
            
            if not advanced_mode:
                
                self._advanced_content_update.Hide()
                
            
            self._Refresh()
            
            #
            
            self.Add( self._tag_info_st, CC.FLAGS_EXPAND_PERPENDICULAR )
            self.Add( self._advanced_content_update, CC.FLAGS_LONE_BUTTON )
            
            HG.client_controller.sub( self, 'ServiceUpdated', 'service_updated' )
            
        
        def _AdvancedContentUpdate( self ):
            
            with ClientGUITopLevelWindows.DialogNullipotent( self, 'advanced content update' ) as dlg:
                
                panel = ClientGUIScrolledPanelsReview.AdvancedContentUpdatePanel( dlg, self._service.GetServiceKey() )
                
                dlg.SetPanel( panel )
                
                dlg.ShowModal()
                
            
        
        def _Refresh( self ):
            
            HG.client_controller.CallToThread( self.THREADFetchInfo, self._service )
            
        
        def ServiceUpdated( self, service ):
            
            if service.GetServiceKey() == self._service.GetServiceKey():
                
                self._service = service
                
                self._my_updater.Update()
                
            
        
        def THREADFetchInfo( self, service ):
            
            def wx_code( text ):
                
                if not self:
                    
                    return
                    
                
                self._tag_info_st.SetLabelText( text )
                
            
            service_info = HG.client_controller.Read( 'service_info', service.GetServiceKey() )
            
            num_files = service_info[ HC.SERVICE_INFO_NUM_FILES ]
            num_tags = service_info[ HC.SERVICE_INFO_NUM_TAGS ]
            num_mappings = service_info[ HC.SERVICE_INFO_NUM_MAPPINGS ]
            
            text = HydrusData.ToHumanInt( num_mappings ) + ' total mappings involving ' + HydrusData.ToHumanInt( num_tags ) + ' different tags on ' + HydrusData.ToHumanInt( num_files ) + ' different files'
            
            if service.GetServiceType() == HC.TAG_REPOSITORY:
                
                num_deleted_mappings = service_info[ HC.SERVICE_INFO_NUM_DELETED_MAPPINGS ]
                
                text += ' - ' + HydrusData.ToHumanInt( num_deleted_mappings ) + ' deleted mappings'
                
            
            wx.CallAfter( wx_code, text )
            
        
    
    class _ServiceTrashPanel( ClientGUICommon.StaticBox ):
        
        def __init__( self, parent, service ):
            
            ClientGUICommon.StaticBox.__init__( self, parent, 'trash' )
            
            self._service = service
            
            self._clear_trash = ClientGUICommon.BetterButton( self, 'clear trash', self._ClearTrash )
            
            #
            
            self.Add( self._clear_trash, CC.FLAGS_LONE_BUTTON )
            
        
        def _ClearTrash( self ):
            
            message = 'This will completely clear your trash of all its files, deleting them permanently from the client. This operation cannot be undone.'
            message += os.linesep * 2
            message += 'If you have many files in your trash, it will take some time to complete and for all the files to eventually be deleted.'
            
            with ClientGUIDialogs.DialogYesNo( self, message, yes_label = 'do it', no_label = 'forget it' ) as dlg_add:
                
                result = dlg_add.ShowModal()
                
                if result == wx.ID_YES:
                    
                    def do_it():
                        
                        hashes = HG.client_controller.Read( 'trash_hashes' )
                        
                        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes )
                        
                        service_keys_to_content_updates = { CC.TRASH_SERVICE_KEY : [ content_update ] }
                        
                        HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                        
                        HG.client_controller.pub( 'service_updated', self._service )
                        
                    
                    HG.client_controller.CallToThread( do_it )
                    
                
            
        
    
