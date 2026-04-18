// Main TypeScript entry point
var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
var __spreadArray = (this && this.__spreadArray) || function (to, from, pack) {
    if (pack || arguments.length === 2) for (var i = 0, l = from.length, ar; i < l; i++) {
        if (ar || !(i in from)) {
            if (!ar) ar = Array.prototype.slice.call(from, 0, i);
            ar[i] = from[i];
        }
    }
    return to.concat(ar || Array.prototype.slice.call(from));
};
var App = /** @class */ (function () {
    function App() {
        var _this = this;
        var _a, _b;
        this.settingsSaveTimer = null;
        this.settingsSaveDelayMs = 500;
        this.statusUpdateInterval = null;
        this.jobStatusInterval = null;
        this.jobStatusPolling = false;
        this.activeJobMap = new Map();
        this.jobsUpdateInterval = null;
        this.currentJobsPage = 1;
        this.jobsPageSize = 20;
        this.jobsListCache = [];
        this.jobsTotalCountCache = 0;
        this.isDownloadingAll = false;
        this.downloadAllCancelRequested = false;
        this.currentDownloadController = null;
        this.downloadAllScope = 'loose';
        this.currentAudio = null;
        this.currentPlayingTrackId = null;
        this.currentPlayButton = null;
        this.currentAudioCleanup = null;
        this.lastRetryFunction = null;
        this.isPlexConfigured = false;
        this.isHandlingPopState = false;
        this.currentPage = 'explore';
        this.pendingRequestController = null;
        this.libraryArtistsPageSize = 50;
        this.libraryArtistsOffset = 0;
        this.libraryArtistsTotal = 0;
        this.libraryCurrentArtist = null;
        this.libraryCurrentAlbum = null;
        this.libraryLoadedOnce = false;
        this.matchReviewPollingInterval = null;
        this.lastMatchActivityJobId = null;
        this.lastMatchActivityStatus = null;
        this.activeMatchActivityJobId = null;
        this.matchCandidateCache = new Map();
        this.matchCandidateSearchTerms = new Map();
        this.matchCandidateRequestsInFlight = new Set();
        this.currentExploreRoute = { view: 'home' };
        this.exploreBreadcrumbRoutes = [];
        this.exploreSearchRoute = null;
        this.exploreArtistName = null;
        this.exploreAlbumTitle = null;
        this.explorePlaylistTitle = null;
        this.exploreLastfmPlaylistName = null;
        this.exploreYoutubePlaylistName = null;
        this.listenbrainzCurrentUsername = null;
        this.listenbrainzCurrentPlaylist = null;
        // New page navigation elements
        var navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(function (item) {
            item.addEventListener('click', function (e) {
                e.preventDefault();
                var page = item.getAttribute('data-page');
                if (page) {
                    _this.switchPage(page);
                }
            });
        });
        this.searchInput = document.getElementById('searchInput');
        this.searchTypeSelect = document.getElementById('searchType');
        this.searchButton = document.getElementById('searchButton');
        this.exploreBreadcrumbContainer = document.getElementById('exploreBreadcrumb');
        this.libraryBreadcrumbContainer = document.getElementById('libraryBreadcrumb');
        this.resultsContainer = document.getElementById('results');
        this.libraryResultsContainer = document.getElementById('libraryResults');
        // Old flyout elements (may not exist in new layout)
        this.statusButton = document.getElementById('statusButton');
        this.statusFlyout = document.getElementById('statusFlyout');
        this.flyoutOverlay = document.getElementById('flyoutOverlay');
        this.closeFlyoutButton = document.getElementById('closeFlyout');
        this.flyoutContent = document.getElementById('flyoutContent');
        this.jobsButton = document.getElementById('jobsButton');
        this.jobsFlyout = document.getElementById('jobsFlyout');
        this.jobsOverlay = document.getElementById('jobsOverlay');
        this.closeJobsButton = document.getElementById('closeJobs');
        this.jobsFilterSelect = document.getElementById('jobsFilter');
        this.cancelPendingJobsButton = document.getElementById('cancelPendingJobs');
        this.retryAllJobsButton = document.getElementById('retryAllJobs');
        this.jobsContent = document.getElementById('jobsContent');
        this.jobsPagination = document.getElementById('jobsPagination');
        this.matchReviewRunScanButton = document.getElementById('startHifiMatchScan');
        this.matchReviewRefreshButton = document.getElementById('refreshHifiMatchReview');
        this.matchReviewEntityFilter = document.getElementById('matchReviewEntityFilter');
        this.matchReviewMaxConfidenceInput = document.getElementById('matchReviewMaxConfidence');
        this.matchReviewStatusEl = document.getElementById('matchReviewStatus');
        this.matchReviewActivity = document.getElementById('matchReviewActivity');
        this.matchReviewSummary = document.getElementById('matchReviewSummary');
        this.matchReviewContent = document.getElementById('matchReviewContent');
        this.settingsButton = document.getElementById('settingsButton');
        this.settingsFlyout = document.getElementById('settingsFlyout');
        this.settingsOverlay = document.getElementById('settingsOverlay');
        this.closeSettingsButton = document.getElementById('closeSettings');
        this.qualityLosslessInput = document.getElementById('qualityLossless');
        this.qualityHighInput = document.getElementById('qualityHigh');
        this.qualityLowInput = document.getElementById('qualityLow');
        this.fileNamingAlbumInput = document.getElementById('fileNamingAlbum');
        this.jobsRefreshIntervalSecondsInput = document.getElementById('jobsRefreshIntervalSeconds');
        this.listenbrainzTokenInput = document.getElementById('listenbrainzToken');
        this.saveLbConfigButton = document.getElementById('saveLbConfig');
        this.lbConfigStatusEl = document.getElementById('lbConfigStatus');
        this.plexLoginButton = document.getElementById('plexLoginButton');
        this.plexPinContainer = document.getElementById('plexPinContainer');
        this.plexPinDisplay = document.getElementById('plexPinDisplay');
        this.plexPinCopyButton = document.getElementById('plexPinCopy');
        this.plexPinStatus = document.getElementById('plexPinStatus');
        this.plexLibraryConfigContainer = document.getElementById('plexLibraryConfig');
        this.plexLibraryNameSelect = document.getElementById('plexLibraryName');
        this.plexPlaylistContainer = document.getElementById('plexPlaylistContainer');
        this.plexPlaylistContainerHomeParent = (_a = this.plexPlaylistContainer) === null || _a === void 0 ? void 0 : _a.parentElement;
        this.plexPlaylistContainerHomeNextSibling = ((_b = this.plexPlaylistContainer) === null || _b === void 0 ? void 0 : _b.nextSibling) || null;
        this.plexPlaylistNameInput = document.getElementById('plexPlaylistName');
        this.plexPlaylistOptions = document.getElementById('plexPlaylistOptions');
        this.plexPlaylistBackButton = document.getElementById('plexPlaylistBack');
        this.savePlexConfigButton = document.getElementById('savePlexConfig');
        this.plexSyncIntervalHoursInput = document.getElementById('plexSyncIntervalHours');
        this.startPlexSyncButton = document.getElementById('startPlexSync');
        this.plexSyncStatusEl = document.getElementById('plexSyncStatus');
        this.plexConfigStatusEl = document.getElementById('plexConfigStatus');
        this.plexConnectedStatusEl = document.getElementById('plexConnectedStatus');
        this.plexClearCredentialsButton = document.getElementById('plexClearCredentialsButton');
        this.plexUserDropdownContainer = document.getElementById('plexUserDropdownContainer');
        this.plexUserSelect = document.getElementById('plexUserSelect');
        this.ignoreMatchesCheckbox = document.getElementById('ignoreMatchesCheckbox');
        // User dropdown for top bar
        this.userButton = document.getElementById('userButton');
        this.userDropdownModal = document.getElementById('userDropdownModal');
        this.userDropdownOverlay = document.getElementById('userDropdownOverlay');
        this.userDropdownList = document.getElementById('userDropdownList');
        this.userButtonText = document.getElementById('userButtonText');
        this.initializeEventListeners();
        this.downloadSettings = this.defaultDownloadSettings();
        this.applySettingsToForm(this.downloadSettings);
        // Initialize page navigation (start with Explore page)
        this.switchPage('explore', false);
        this.initializeHistoryNavigation();
        void this.fetchDownloadSettingsFromServer();
        void this.loadListenbrainzConfig();
        void this.loadPlexConfig();
        void this.updatePlexClearCredentialsButton();
        // Initialize user button and sidebar playlists
        void this.initializeUserButton();
        this.updateEndpointStatus(); // Initial load
        // Update status every 30 seconds
        this.statusUpdateInterval = window.setInterval(function () {
            _this.updateEndpointStatus();
        }, 30000);
    }
    App.prototype.getSearchTypeName = function (searchType) {
        var normalized = (searchType || 's').toLowerCase();
        var labels = {
            s: 'Tracks',
            a: 'Artists',
            al: 'Albums',
            p: 'Playlists',
            trackid: 'Track ID',
            lastfm: 'Last.fm',
            youtube_music: 'YouTube Music',
            listenbrainz: 'ListenBrainz'
        };
        return labels[normalized] || 'Results';
    };
    App.prototype.renderExploreTopBarBreadcrumb = function (route) {
        var _a, _b, _c, _d, _e;
        if (route === void 0) { route = this.currentExploreRoute; }
        if (!this.exploreBreadcrumbContainer) {
            return;
        }
        var crumbs = [];
        var username = route.username || this.listenbrainzCurrentUsername || '';
        var playlistTitle = ((_a = this.listenbrainzCurrentPlaylist) === null || _a === void 0 ? void 0 : _a.title) || this.explorePlaylistTitle || '';
        if (route.view === 'home') {
            crumbs.push({ label: 'Explore' });
        }
        else if (route.view === 'search') {
            var query = route.query || ((_c = (_b = this.searchInput) === null || _b === void 0 ? void 0 : _b.value) === null || _c === void 0 ? void 0 : _c.trim()) || '';
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: query ? "".concat(this.getSearchTypeName(route.searchType), " - \"").concat(query, "\"") : this.getSearchTypeName(route.searchType) });
        }
        else if (route.view === 'artist') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            if (((_d = this.exploreSearchRoute) === null || _d === void 0 ? void 0 : _d.view) === 'search') {
                var query = this.exploreSearchRoute.query || '';
                var label = query ? "".concat(this.getSearchTypeName(this.exploreSearchRoute.searchType), " - \"").concat(query, "\"") : this.getSearchTypeName(this.exploreSearchRoute.searchType);
                crumbs.push({ label: label, route: __assign({}, this.exploreSearchRoute) });
            }
            crumbs.push({ label: this.exploreArtistName || 'Artist' });
        }
        else if (route.view === 'album') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            if (((_e = this.exploreSearchRoute) === null || _e === void 0 ? void 0 : _e.view) === 'search') {
                var query = this.exploreSearchRoute.query || '';
                var label = query ? "".concat(this.getSearchTypeName(this.exploreSearchRoute.searchType), " - \"").concat(query, "\"") : this.getSearchTypeName(this.exploreSearchRoute.searchType);
                crumbs.push({ label: label, route: __assign({}, this.exploreSearchRoute) });
            }
            crumbs.push({ label: this.exploreAlbumTitle || 'Album' });
        }
        else if (route.view === 'playlist') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: this.explorePlaylistTitle || 'Playlist' });
        }
        else if (route.view === 'listenbrainz_playlists') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'ListenBrainz' });
            if (username) {
                crumbs.push({ label: username });
            }
        }
        else if (route.view === 'listenbrainz_playlist_tracks') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            if (username) {
                crumbs.push({ label: 'ListenBrainz', route: { view: 'listenbrainz_playlists', username: username } });
                crumbs.push({ label: username, route: { view: 'listenbrainz_playlists', username: username } });
            }
            else {
                crumbs.push({ label: 'ListenBrainz' });
            }
            crumbs.push({ label: playlistTitle || 'Playlist' });
        }
        else if (route.view === 'lastfm_playlist') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Last.fm' });
            crumbs.push({ label: this.exploreLastfmPlaylistName || 'Playlist' });
        }
        else if (route.view === 'youtube_music_playlist') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'YouTube Music' });
            crumbs.push({ label: this.exploreYoutubePlaylistName || 'Playlist' });
        }
        else if (route.view === 'similar_tracks') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Similar Tracks' });
        }
        else if (route.view === 'similar_albums') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Similar Albums' });
        }
        else if (route.view === 'similar_artists') {
            crumbs.push({ label: 'Explore', route: { view: 'home' } });
            crumbs.push({ label: 'Similar Artists' });
        }
        else {
            crumbs.push({ label: 'Explore' });
        }
        this.exploreBreadcrumbRoutes = [];
        var parts = [];
        for (var index = 0; index < crumbs.length; index += 1) {
            var crumb = crumbs[index];
            var isLast = index === crumbs.length - 1;
            var safeLabel = this.escapeHtml(crumb.label);
            if (isLast || !crumb.route) {
                parts.push("<span class=\"library-crumb-current\">".concat(safeLabel, "</span>"));
            }
            else {
                var routeIndex = this.exploreBreadcrumbRoutes.push(__assign({}, crumb.route)) - 1;
                parts.push("<button class=\"library-crumb-btn\" data-explore-route-index=\"".concat(routeIndex, "\">").concat(safeLabel, "</button>"));
            }
            if (!isLast) {
                parts.push('<span class="library-crumb-separator">&gt;</span>');
            }
        }
        this.exploreBreadcrumbContainer.innerHTML = parts.join('');
        this.exploreBreadcrumbContainer.style.display = parts.length > 0 ? 'flex' : 'none';
    };
    App.prototype.renderTopBarTitle = function (title) {
        var topBarLeft = document.querySelector('.top-bar-left');
        if (!topBarLeft) {
            return;
        }
        topBarLeft.innerHTML = "<h2>".concat(this.escapeHtml(title), "</h2>");
    };
    App.prototype.initializeEventListeners = function () {
        var _this = this;
        if (this.searchButton) {
            this.searchButton.addEventListener('click', function () { return _this.handleSearch(); });
        }
        if (this.searchInput) {
            this.searchInput.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') {
                    _this.handleSearch();
                }
            });
        }
        if (this.exploreBreadcrumbContainer) {
            this.exploreBreadcrumbContainer.addEventListener('click', function (e) {
                var target = e.target;
                var button = target.closest('[data-explore-route-index]');
                if (button) {
                    e.preventDefault();
                    e.stopPropagation();
                    var routeIndex = Number(button.getAttribute('data-explore-route-index') || '-1');
                    if (Number.isInteger(routeIndex) && routeIndex >= 0 && routeIndex < _this.exploreBreadcrumbRoutes.length) {
                        void _this.navigateToRoute(__assign({}, _this.exploreBreadcrumbRoutes[routeIndex]), true);
                    }
                }
            });
        }
        if (this.libraryBreadcrumbContainer) {
            this.libraryBreadcrumbContainer.addEventListener('click', function (e) {
                var target = e.target;
                var breadcrumbButton = target.closest('[data-library-crumb]');
                if (!breadcrumbButton) {
                    return;
                }
                e.preventDefault();
                var crumb = breadcrumbButton.getAttribute('data-library-crumb');
                if (crumb === 'library') {
                    void _this.loadLibraryArtists(0);
                    return;
                }
                if (crumb === 'artist' && _this.libraryCurrentArtist) {
                    void _this.loadLibraryArtistAlbums(_this.libraryCurrentArtist.id, _this.libraryCurrentArtist.name);
                }
            });
        }
        // User dropdown listeners
        if (this.userButton) {
            console.log('[DEBUG] Attaching user button listener');
            this.userButton.addEventListener('click', function () {
                console.log('[DEBUG] User button clicked');
                _this.openUserDropdown();
            });
        }
        else {
            console.error('[DEBUG] userButton element not found');
        }
        if (this.userDropdownOverlay) {
            this.userDropdownOverlay.addEventListener('click', function () { return _this.closeUserDropdown(); });
        }
        var userDropdownClose = document.getElementById('userDropdownClose');
        if (userDropdownClose) {
            userDropdownClose.addEventListener('click', function () { return _this.closeUserDropdown(); });
        }
        // Old flyout listeners (safe if elements don't exist)
        if (this.statusButton) {
            this.statusButton.addEventListener('click', function () { return _this.openFlyout(); });
        }
        if (this.closeFlyoutButton) {
            this.closeFlyoutButton.addEventListener('click', function () { return _this.closeFlyout(); });
        }
        if (this.flyoutOverlay) {
            this.flyoutOverlay.addEventListener('click', function () { return _this.closeFlyout(); });
        }
        if (this.jobsButton) {
            this.jobsButton.addEventListener('click', function () { return _this.openJobsFlyout(); });
        }
        if (this.closeJobsButton) {
            this.closeJobsButton.addEventListener('click', function () { return _this.closeJobsFlyout(); });
        }
        if (this.jobsOverlay) {
            this.jobsOverlay.addEventListener('click', function () { return _this.closeJobsFlyout(); });
        }
        if (this.jobsFilterSelect) {
            this.jobsFilterSelect.addEventListener('change', function () {
                _this.currentJobsPage = 1;
                _this.updateJobsActionButtons(0, _this.jobsFilterSelect.value, 0);
                void _this.loadJobs();
            });
        }
        if (this.cancelPendingJobsButton) {
            this.cancelPendingJobsButton.addEventListener('click', function () {
                void _this.cancelAllPendingJobs();
            });
        }
        if (this.retryAllJobsButton) {
            this.retryAllJobsButton.addEventListener('click', function () {
                void _this.retryAllFilteredJobs();
            });
        }
        if (this.jobsContent) {
            this.jobsContent.addEventListener('click', function (e) {
                void _this.handleJobsContentClick(e);
            });
        }
        if (this.matchReviewRunScanButton) {
            this.matchReviewRunScanButton.addEventListener('click', function () {
                if (_this.activeMatchActivityJobId) {
                    void _this.cancelHifiMatchScan(_this.activeMatchActivityJobId);
                    return;
                }
                void _this.startHifiMatchScan();
            });
        }
        if (this.matchReviewRefreshButton) {
            this.matchReviewRefreshButton.addEventListener('click', function () {
                _this.matchCandidateCache.clear();
                void _this.loadMatchReview();
            });
        }
        if (this.matchReviewEntityFilter) {
            this.matchReviewEntityFilter.addEventListener('change', function () {
                _this.matchCandidateCache.clear();
                void _this.loadMatchReview();
            });
        }
        if (this.matchReviewMaxConfidenceInput) {
            this.matchReviewMaxConfidenceInput.addEventListener('change', function () {
                _this.matchCandidateCache.clear();
                void _this.loadMatchReview();
            });
        }
        if (this.matchReviewContent) {
            this.matchReviewContent.addEventListener('click', function (e) {
                void _this.handleMatchReviewClick(e);
            });
            this.matchReviewContent.addEventListener('keydown', function (e) {
                void _this.handleMatchReviewKeydown(e);
            });
        }
        if (this.settingsButton) {
            this.settingsButton.addEventListener('click', function () { return _this.openSettingsFlyout(); });
        }
        if (this.closeSettingsButton) {
            this.closeSettingsButton.addEventListener('click', function () { return _this.closeSettingsFlyout(); });
        }
        if (this.settingsOverlay) {
            this.settingsOverlay.addEventListener('click', function () { return _this.closeSettingsFlyout(); });
        }
        if (this.qualityLosslessInput) {
            this.qualityLosslessInput.addEventListener('change', function () { return _this.updateSettingsFromForm(); });
        }
        if (this.qualityHighInput) {
            this.qualityHighInput.addEventListener('change', function () { return _this.updateSettingsFromForm(); });
        }
        if (this.qualityLowInput) {
            this.qualityLowInput.addEventListener('change', function () { return _this.updateSettingsFromForm(); });
        }
        if (this.fileNamingAlbumInput) {
            this.fileNamingAlbumInput.addEventListener('input', function () { return _this.updateSettingsFromForm(); });
        }
        if (this.jobsRefreshIntervalSecondsInput) {
            this.jobsRefreshIntervalSecondsInput.addEventListener('change', function () { return _this.updateSettingsFromForm(); });
        }
        if (this.ignoreMatchesCheckbox) {
            this.ignoreMatchesCheckbox.addEventListener('change', function () { return _this.updateSettingsFromForm(); });
        }
        if (this.saveLbConfigButton) {
            this.saveLbConfigButton.addEventListener('click', function () { return _this.saveListenbrainzConfig(); });
        }
        if (this.savePlexConfigButton) {
            this.savePlexConfigButton.addEventListener('click', function () {
                void _this.savePlexConfig();
            });
        }
        // Remove save/test config listeners, add PIN login logic
        if (this.plexLoginButton) {
            this.plexLoginButton.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0: return [4 /*yield*/, this.startPlexPinLogin()];
                        case 1:
                            _a.sent();
                            void this.updatePlexClearCredentialsButton();
                            void this.loadPlexLibraries();
                            return [2 /*return*/];
                    }
                });
            }); });
        }
        if (this.plexClearCredentialsButton) {
            this.plexClearCredentialsButton.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                var resp, e_1;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            _a.trys.push([0, 3, 4, 6]);
                            return [4 /*yield*/, fetch('/api/plex/clear_credentials', { method: 'POST' })];
                        case 1:
                            resp = _a.sent();
                            if (!resp.ok) {
                                throw new Error('Failed to clear Plex credentials');
                            }
                            // Ensure the cached health status is updated (server sets ok=false when credentials are cleared)
                            return [4 /*yield*/, fetch('/api/plex/health', { cache: 'no-store' })];
                        case 2:
                            // Ensure the cached health status is updated (server sets ok=false when credentials are cleared)
                            _a.sent();
                            return [3 /*break*/, 6];
                        case 3:
                            e_1 = _a.sent();
                            console.warn('Failed to clear Plex credentials:', e_1);
                            return [3 /*break*/, 6];
                        case 4:
                            // Immediately reflect cleared state in the UI, regardless of timing
                            if (this.plexClearCredentialsButton) {
                                this.plexClearCredentialsButton.style.display = 'none';
                            }
                            if (this.plexLoginButton) {
                                this.plexLoginButton.style.display = '';
                                this.plexLoginButton.disabled = false;
                            }
                            window.localStorage.removeItem('plexSelectedUserId');
                            return [4 /*yield*/, this.loadPlexConfig()];
                        case 5:
                            _a.sent();
                            void this.updatePlexClearCredentialsButton();
                            return [7 /*endfinally*/];
                        case 6: return [2 /*return*/];
                    }
                });
            }); });
        }
        if (this.plexUserSelect) {
            this.plexUserSelect.addEventListener('change', function () { return __awaiter(_this, void 0, void 0, function () {
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            window.localStorage.setItem('plexSelectedUserId', this.plexUserSelect.value);
                            return [4 /*yield*/, this.loadPlexPlaylists()];
                        case 1:
                            _a.sent();
                            return [2 /*return*/];
                    }
                });
            }); });
        }
        if (this.plexPinCopyButton) {
            this.plexPinCopyButton.addEventListener('click', function () {
                var _a;
                var pin = ((_a = _this.plexPinDisplay) === null || _a === void 0 ? void 0 : _a.textContent) || '';
                if (pin) {
                    navigator.clipboard.writeText(pin);
                    if (_this.plexPinStatus) {
                        _this.plexPinStatus.textContent = 'PIN copied!';
                        setTimeout(function () {
                            if (_this.plexPinStatus) {
                                _this.plexPinStatus.textContent = '';
                            }
                        }, 1500);
                    }
                }
            });
        }
        if (this.startPlexSyncButton) {
            this.startPlexSyncButton.addEventListener('click', function () { return _this.startPlexSync(); });
        }
        if (this.plexPlaylistOptions) {
            this.plexPlaylistOptions.addEventListener('change', function () {
                var selectedName = _this.plexPlaylistOptions.value.trim();
                if (selectedName === App.NEW_PLEX_PLAYLIST_OPTION) {
                    _this.setPlexPlaylistMode('new');
                    if (_this.plexPlaylistNameInput) {
                        _this.plexPlaylistNameInput.value = '';
                        _this.plexPlaylistNameInput.focus();
                    }
                    return;
                }
                if (selectedName && _this.plexPlaylistNameInput) {
                    _this.plexPlaylistNameInput.value = selectedName;
                }
                else if (_this.plexPlaylistNameInput) {
                    _this.plexPlaylistNameInput.value = '';
                }
                _this.setPlexPlaylistMode('existing');
            });
        }
        if (this.plexPlaylistBackButton) {
            this.plexPlaylistBackButton.addEventListener('click', function () {
                _this.setPlexPlaylistMode('existing');
                if (_this.plexPlaylistOptions) {
                    _this.plexPlaylistOptions.value = '';
                }
                if (_this.plexPlaylistNameInput) {
                    _this.plexPlaylistNameInput.value = '';
                }
            });
        }
        // Update placeholder text based on search type
        if (this.searchTypeSelect) {
            this.searchTypeSelect.addEventListener('change', function () { return _this.updateSearchPlaceholder(); });
        }
        // Download button and album card click delegation
        if (this.resultsContainer) {
            this.resultsContainer.addEventListener('click', function (e) {
                var target = e.target;
                // Check for grid play button clicks
                var gridPlayBtn = target.closest('.grid-play-btn');
                if (gridPlayBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var trackRow = gridPlayBtn.closest('.tracks-grid-row');
                    if (trackRow) {
                        var trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void _this.handlePlayToggle(parseInt(trackId, 10), trackRow, gridPlayBtn);
                            return;
                        }
                    }
                    // Check for album grid play button
                    var albumRow_1 = gridPlayBtn.closest('.albums-grid-row');
                    if (albumRow_1) {
                        var albumId = albumRow_1.getAttribute('data-album-id');
                        if (albumId) {
                            void _this.handlePlayAlbum(parseInt(albumId, 10), gridPlayBtn);
                            return;
                        }
                    }
                    return;
                }
                // Check for album row clicks (anywhere except actions column)
                var albumRow = target.closest('.albums-grid-row');
                if (albumRow && !target.closest('.grid-cell.grid-col-actions')) {
                    e.preventDefault();
                    e.stopPropagation();
                    var albumId = albumRow.getAttribute('data-album-id');
                    if (albumId) {
                        void _this.navigateToRoute({ view: 'album', albumId: parseInt(albumId, 10) }, true);
                    }
                    return;
                }
                // Check for grid add to playlist button clicks
                var gridAddPlaylistBtn = target.closest('.grid-add-playlist-btn');
                if (gridAddPlaylistBtn) {
                    var trackRow = gridAddPlaylistBtn.closest('.tracks-grid-row');
                    if (trackRow) {
                        var trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void _this.handleAddToPlaylist(parseInt(trackId, 10), trackRow, 'loose');
                            return;
                        }
                    }
                    // Check for album grid
                    var albumRow_2 = gridAddPlaylistBtn.closest('.albums-grid-row');
                    if (albumRow_2) {
                        var albumId = albumRow_2.getAttribute('data-album-id');
                        if (albumId) {
                            void _this.handleAddAlbumToPlaylist(parseInt(albumId, 10), albumRow_2);
                            return;
                        }
                    }
                    return;
                }
                // Check for grid add to library button clicks
                var gridAddLibraryBtn = target.closest('.grid-add-library-btn');
                if (gridAddLibraryBtn) {
                    var trackRow = gridAddLibraryBtn.closest('.tracks-grid-row');
                    if (trackRow) {
                        var trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void _this.handleDownload(parseInt(trackId, 10), trackRow, 'loose');
                            return;
                        }
                    }
                    // Check for album grid
                    var albumRow_3 = gridAddLibraryBtn.closest('.albums-grid-row');
                    if (albumRow_3) {
                        var albumId = albumRow_3.getAttribute('data-album-id');
                        if (albumId) {
                            void _this.handleDownloadAlbum(parseInt(albumId, 10), albumRow_3);
                            return;
                        }
                    }
                    return;
                }
                // Check for grid "More Like This" button clicks
                var gridMoreBtn = target.closest('.grid-more-btn');
                if (gridMoreBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var trackRow = gridMoreBtn.closest('.tracks-grid-row');
                    if (trackRow) {
                        var trackId = trackRow.getAttribute('data-track-id');
                        if (trackId) {
                            void _this.navigateToRoute({ view: 'similar_tracks', trackId: parseInt(trackId, 10) }, true);
                            return;
                        }
                    }
                    // Check for album grid
                    var albumRow_4 = gridMoreBtn.closest('.albums-grid-row');
                    if (albumRow_4) {
                        var albumId = albumRow_4.getAttribute('data-album-id');
                        if (albumId) {
                            void _this.navigateToRoute({ view: 'similar_albums', albumId: parseInt(albumId, 10) }, true);
                            return;
                        }
                    }
                }
                // Check for play button clicks first
                var playBtn = target.closest('.track-play-btn');
                if (playBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var trackCard = playBtn.closest('.track-card');
                    var trackId = trackCard === null || trackCard === void 0 ? void 0 : trackCard.getAttribute('data-track-id');
                    if (trackId) {
                        void _this.handlePlayToggle(parseInt(trackId, 10), trackCard, playBtn);
                    }
                    return;
                }
                // Check for add to playlist button clicks
                var addPlaylistBtn = target.closest('.track-add-playlist-btn');
                if (addPlaylistBtn) {
                    var trackCard = addPlaylistBtn.closest('.track-card');
                    var trackId = trackCard === null || trackCard === void 0 ? void 0 : trackCard.getAttribute('data-track-id');
                    if (trackId) {
                        void _this.handleAddToPlaylist(parseInt(trackId, 10), trackCard, 'loose');
                    }
                    return;
                }
                // Check for download button clicks
                var downloadBtn = target.closest('.track-download-btn');
                if (downloadBtn) {
                    var trackCard = downloadBtn.closest('.track-card');
                    var trackId = trackCard === null || trackCard === void 0 ? void 0 : trackCard.getAttribute('data-track-id');
                    if (trackId) {
                        void _this.handleDownload(parseInt(trackId, 10), trackCard, 'loose');
                    }
                    return; // Stop here if it was a download button
                }
                // Check for "More Like This" actions before generic card click handlers
                var moreLikeBtn = target.closest('.track-more-btn');
                if (moreLikeBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var card = moreLikeBtn.closest('.track-card');
                    if (!card) {
                        return;
                    }
                    var trackId = card.getAttribute('data-track-id');
                    if (trackId) {
                        void _this.navigateToRoute({ view: 'similar_tracks', trackId: parseInt(trackId, 10) }, true);
                        return;
                    }
                    if (card.classList.contains('album-card')) {
                        var albumId = card.getAttribute('data-album-id');
                        if (albumId) {
                            void _this.navigateToRoute({ view: 'similar_albums', albumId: parseInt(albumId, 10) }, true);
                        }
                        return;
                    }
                    if (card.classList.contains('artist-card')) {
                        var artistId = card.getAttribute('data-artist-id');
                        if (artistId) {
                            void _this.navigateToRoute({ view: 'similar_artists', artistId: parseInt(artistId, 10) }, true);
                        }
                        return;
                    }
                }
                // Check for artist card compact button clicks (Find Similar)
                var artistCardBtn = target.closest('.artist-card-btn');
                if (artistCardBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var artistCard = artistCardBtn.closest('.artist-card-compact');
                    if (artistCard) {
                        var artistId = artistCard.getAttribute('data-artist-id');
                        if (artistId) {
                            void _this.navigateToRoute({ view: 'similar_artists', artistId: parseInt(artistId, 10) }, true);
                        }
                    }
                    return;
                }
                // Check for artist card compact clicks (view artist albums)
                var artistCardCompact = target.closest('.artist-card-compact.clickable');
                if (artistCardCompact && !target.closest('.artist-card-btn')) {
                    e.preventDefault();
                    e.stopPropagation();
                    var artistId = artistCardCompact.getAttribute('data-artist-id');
                    if (artistId) {
                        void _this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                    }
                    return;
                }
                // Check for artist name clicks within grid rows
                var gridArtistName = target.closest('.tracks-grid-row .track-artist-name');
                if (gridArtistName) {
                    var trackRow = gridArtistName.closest('.tracks-grid-row');
                    var artistId = trackRow === null || trackRow === void 0 ? void 0 : trackRow.getAttribute('data-artist-id');
                    if (artistId) {
                        e.stopPropagation();
                        void _this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                        return;
                    }
                }
                // Check for artist name clicks within album hero header
                var heroArtistName = target.closest('.album-hero-content .track-artist-name');
                if (heroArtistName) {
                    var artistId = heroArtistName.getAttribute('data-artist-id');
                    if (artistId) {
                        e.stopPropagation();
                        void _this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                        return;
                    }
                }
                // Check for album name clicks within grid rows
                var gridAlbumName = target.closest('.tracks-grid-row .track-album-name');
                if (gridAlbumName) {
                    var trackRow = gridAlbumName.closest('.tracks-grid-row');
                    var albumId = trackRow === null || trackRow === void 0 ? void 0 : trackRow.getAttribute('data-album-id');
                    if (albumId) {
                        e.stopPropagation();
                        void _this.navigateToRoute({ view: 'album', albumId: parseInt(albumId, 10) }, true);
                        return;
                    }
                }
                // Check for artist name clicks within album grid rows
                var gridAlbumArtistName = target.closest('.albums-grid-row .album-artist-name');
                if (gridAlbumArtistName) {
                    var albumRow_5 = gridAlbumArtistName.closest('.albums-grid-row');
                    var artistId = albumRow_5 === null || albumRow_5 === void 0 ? void 0 : albumRow_5.getAttribute('data-artist-id');
                    if (artistId) {
                        e.stopPropagation();
                        void _this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                        return;
                    }
                }
                // Check for artist name clicks within track cards
                var artistName = target.closest('.track-card .track-artist-name');
                if (artistName) {
                    var trackCard = artistName.closest('.track-card');
                    var artistId = trackCard === null || trackCard === void 0 ? void 0 : trackCard.getAttribute('data-artist-id');
                    if (artistId) {
                        e.stopPropagation();
                        void _this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                        return;
                    }
                }
                // Check for album name clicks within track cards
                var albumName = target.closest('.track-card .track-album-name');
                if (albumName) {
                    var trackCard = albumName.closest('.track-card');
                    var albumId = trackCard === null || trackCard === void 0 ? void 0 : trackCard.getAttribute('data-album-id');
                    if (albumId) {
                        e.stopPropagation();
                        void _this.navigateToRoute({ view: 'album', albumId: parseInt(albumId, 10) }, true);
                        return;
                    }
                }
                // Check for playlist card clicks
                var playlistCard = target.closest('.playlist-card');
                if (playlistCard) {
                    var playlistId = playlistCard.getAttribute('data-playlist-id');
                    if (playlistId) {
                        void _this.navigateToRoute({ view: 'listenbrainz_playlist_tracks', playlistId: playlistId, username: _this.listenbrainzCurrentUsername || undefined }, true);
                        return;
                    }
                }
                // Check for search playlist card clicks
                var searchPlaylistCard = target.closest('.playlist-search-card');
                if (searchPlaylistCard) {
                    var playlistId = searchPlaylistCard.getAttribute('data-playlist-id');
                    if (playlistId) {
                        void _this.navigateToRoute({ view: 'playlist', playlistId: playlistId }, true);
                        return;
                    }
                }
                // Check for album card clicks (albums have both track-card and album-card classes)
                var clickedCard = target.closest('.track-card');
                if (clickedCard && clickedCard.classList.contains('album-card')) {
                    var albumId = clickedCard.getAttribute('data-album-id');
                    if (albumId) {
                        void _this.navigateToRoute({ view: 'album', albumId: parseInt(albumId, 10) }, true);
                    }
                }
                // Check for artist card clicks
                if (clickedCard && clickedCard.classList.contains('artist-card')) {
                    var artistId = clickedCard.getAttribute('data-artist-id');
                    if (artistId) {
                        void _this.navigateToRoute({ view: 'artist', artistId: parseInt(artistId, 10) }, true);
                    }
                }
            });
        }
        if (this.libraryResultsContainer) {
            this.libraryResultsContainer.addEventListener('click', function (e) {
                var _a, _b, _c, _d, _e;
                var target = e.target;
                var artistHeroPlayBtn = target.closest('.library-artist-hero-play-btn');
                if (artistHeroPlayBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var artistId = artistHeroPlayBtn.getAttribute('data-library-artist-id') || ((_a = _this.libraryCurrentArtist) === null || _a === void 0 ? void 0 : _a.id) || '';
                    if (artistId) {
                        void _this.handlePlayLibraryArtist(artistId, artistHeroPlayBtn);
                    }
                    return;
                }
                var albumHeroPlayBtn = target.closest('.library-album-hero-play-btn');
                if (albumHeroPlayBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var albumId = albumHeroPlayBtn.getAttribute('data-library-album-id') || ((_b = _this.libraryCurrentAlbum) === null || _b === void 0 ? void 0 : _b.id) || '';
                    if (albumId) {
                        void _this.handlePlayLibraryAlbum(albumId, albumHeroPlayBtn);
                    }
                    return;
                }
                var gridPlayBtn = target.closest('.grid-play-btn');
                if (gridPlayBtn) {
                    e.preventDefault();
                    e.stopPropagation();
                    var trackRow = gridPlayBtn.closest('[data-library-track-id]');
                    if (trackRow) {
                        var trackId = trackRow.getAttribute('data-library-track-id') || '';
                        if (trackId) {
                            void _this.handlePlayLibraryToggle(trackId, gridPlayBtn);
                        }
                        return;
                    }
                    var albumRow_6 = gridPlayBtn.closest('[data-library-album-id]');
                    if (albumRow_6) {
                        var albumId = albumRow_6.getAttribute('data-library-album-id') || '';
                        if (albumId) {
                            void _this.handlePlayLibraryAlbum(albumId, gridPlayBtn);
                        }
                        return;
                    }
                }
                var paginationButton = target.closest('[data-library-offset]');
                if (paginationButton) {
                    e.preventDefault();
                    if (paginationButton.disabled) {
                        return;
                    }
                    var offset = Number(paginationButton.getAttribute('data-library-offset') || '0');
                    if (Number.isFinite(offset) && offset >= 0) {
                        void _this.loadLibraryArtists(offset);
                    }
                    return;
                }
                var artistCard = target.closest('[data-library-artist-id]');
                if (artistCard) {
                    e.preventDefault();
                    var artistId = artistCard.getAttribute('data-library-artist-id') || '';
                    var artistName = artistCard.getAttribute('data-library-artist-name') || 'Artist';
                    if (artistId) {
                        void _this.loadLibraryArtistAlbums(artistId, artistName);
                    }
                    return;
                }
                var trackArtistName = target.closest('.tracks-grid-row .library-track-artist-name');
                if (trackArtistName) {
                    e.preventDefault();
                    e.stopPropagation();
                    var artistId = trackArtistName.getAttribute('data-library-artist-id') || ((_c = _this.libraryCurrentArtist) === null || _c === void 0 ? void 0 : _c.id) || '';
                    var artistName = trackArtistName.getAttribute('data-library-artist-name') || ((_d = _this.libraryCurrentArtist) === null || _d === void 0 ? void 0 : _d.name) || 'Artist';
                    if (artistId) {
                        void _this.loadLibraryArtistAlbums(artistId, artistName);
                    }
                    return;
                }
                var albumRow = target.closest('[data-library-album-id]');
                if (albumRow && !target.closest('.grid-cell.grid-col-actions')) {
                    e.preventDefault();
                    var albumId = albumRow.getAttribute('data-library-album-id') || '';
                    var albumTitle = albumRow.getAttribute('data-library-album-title') || 'Album';
                    var artistName = albumRow.getAttribute('data-library-artist-name') || ((_e = _this.libraryCurrentArtist) === null || _e === void 0 ? void 0 : _e.name) || '';
                    if (albumId) {
                        void _this.loadLibraryAlbumTracks(albumId, albumTitle, artistName || undefined);
                    }
                    return;
                }
                var albumHeroArtist = target.closest('.album-hero-content .track-artist-name');
                if (albumHeroArtist && _this.libraryCurrentArtist) {
                    e.preventDefault();
                    void _this.loadLibraryArtistAlbums(_this.libraryCurrentArtist.id, _this.libraryCurrentArtist.name);
                }
            });
        }
    };
    App.prototype.switchPage = function (pageName, updateHistory) {
        var _this = this;
        if (updateHistory === void 0) { updateHistory = true; }
        var normalizedPage = this.normalizePage(pageName);
        var previousPage = this.currentPage;
        // Cancel any pending requests when switching pages
        if (this.pendingRequestController) {
            this.pendingRequestController.abort();
            this.pendingRequestController = null;
        }
        // Hide all pages
        var allPages = document.querySelectorAll('.page');
        allPages.forEach(function (page) {
            page.classList.remove('active');
        });
        // Show the selected page
        var selectedPage = document.getElementById("".concat(normalizedPage, "Page"));
        if (selectedPage) {
            selectedPage.classList.add('active');
        }
        // Update active nav item
        var navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(function (item) {
            item.classList.remove('active');
            if (item.getAttribute('data-page') === normalizedPage) {
                item.classList.add('active');
            }
        });
        // Update current page
        this.currentPage = normalizedPage;
        // Update top bar title based on page
        var pageNames = {
            explore: 'Explore',
            library: 'Library',
            settings: 'Settings',
            mirrors: 'Hi-Fi Mirrors',
            matches: 'Match Review',
            jobs: 'Jobs'
        };
        if (normalizedPage === 'explore') {
            this.renderTopBarTitle('Explore');
            this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
            this.hideLibraryBreadcrumb();
        }
        else if (normalizedPage === 'library') {
            this.renderTopBarTitle('Library');
            if (this.exploreBreadcrumbContainer) {
                this.exploreBreadcrumbContainer.style.display = 'none';
                this.exploreBreadcrumbContainer.innerHTML = '';
            }
            this.renderLibraryBreadcrumb();
        }
        else {
            this.renderTopBarTitle(pageNames[normalizedPage] || 'Squidly');
            if (this.exploreBreadcrumbContainer) {
                this.exploreBreadcrumbContainer.style.display = 'none';
                this.exploreBreadcrumbContainer.innerHTML = '';
            }
            this.hideLibraryBreadcrumb();
        }
        // Refresh mirrors data when switching to mirrors page
        if (normalizedPage === 'mirrors') {
            void this.updateEndpointStatus();
        }
        // Load jobs when switching to jobs page
        if (normalizedPage === 'jobs') {
            this.currentJobsPage = 1;
            void this.loadJobs();
        }
        if (normalizedPage === 'matches') {
            void this.loadMatchActivity().then(function () {
                if (_this.currentPage !== 'matches') {
                    return;
                }
                if (!_this.isMatchScanActive()) {
                    void _this.loadMatchReview();
                }
            });
        }
        else {
            this.stopMatchReviewPollingInterval();
        }
        if (normalizedPage === 'library' && !this.libraryLoadedOnce && updateHistory) {
            void this.loadLibraryArtists(0, false);
        }
        if (updateHistory && !this.isHandlingPopState && previousPage !== normalizedPage) {
            this.pushHistoryTab(normalizedPage);
        }
    };
    App.prototype.setLibraryMessage = function (message) {
        if (!this.libraryResultsContainer) {
            return;
        }
        this.renderLibraryBreadcrumb();
        this.libraryResultsContainer.innerHTML = "\n            <div class=\"library-placeholder\">\n                <p>".concat(this.escapeHtml(message), "</p>\n            </div>\n        ");
    };
    App.prototype.formatLibraryBreadcrumb = function () {
        var artist = this.libraryCurrentArtist;
        var album = this.libraryCurrentAlbum;
        var trail = '<button class="library-crumb-btn" data-library-crumb="library">Library</button>';
        if (artist) {
            if (album) {
                trail += "<span class=\"library-crumb-separator\">&gt;</span><button class=\"library-crumb-btn\" data-library-crumb=\"artist\">".concat(this.escapeHtml(artist.name), "</button>");
            }
            else {
                trail += "<span class=\"library-crumb-separator\">&gt;</span><span class=\"library-crumb-current\">".concat(this.escapeHtml(artist.name), "</span>");
            }
        }
        if (album) {
            trail += "<span class=\"library-crumb-separator\">&gt;</span><span class=\"library-crumb-current\">".concat(this.escapeHtml(album.title), "</span>");
        }
        return trail;
    };
    App.prototype.renderLibraryBreadcrumb = function () {
        if (!this.libraryBreadcrumbContainer) {
            return;
        }
        var trail = this.formatLibraryBreadcrumb();
        this.libraryBreadcrumbContainer.innerHTML = trail;
        this.libraryBreadcrumbContainer.style.display = trail ? 'flex' : 'none';
    };
    App.prototype.hideLibraryBreadcrumb = function () {
        if (!this.libraryBreadcrumbContainer) {
            return;
        }
        this.libraryBreadcrumbContainer.innerHTML = '';
        this.libraryBreadcrumbContainer.style.display = 'none';
    };
    App.prototype.formatLibraryArtistCard = function (artist) {
        var artistName = this.escapeHtml(artist.name || 'Unknown Artist');
        return "\n            <div class=\"artist-card-compact clickable\" data-library-artist-id=\"".concat(this.escapeHtml(artist.id), "\" data-library-artist-name=\"").concat(artistName, "\" title=\"View albums by ").concat(artistName, "\">\n                <div class=\"artist-card-name\">").concat(artistName, "</div>\n                <div class=\"artist-card-image\">\n                    ").concat(artist.picture
            ? "<img src=\"".concat(artist.picture, "\" alt=\"").concat(artistName, "\" loading=\"lazy\">")
            : "<div class=\"artist-card-placeholder\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                                <circle cx=\"12\" cy=\"8\" r=\"4\"></circle>\n                                <path d=\"M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2\"></path>\n                            </svg>\n                           </div>", "\n                </div>\n            </div>\n        ");
    };
    App.prototype.formatLibraryAlbumRow = function (album) {
        var _a;
        var title = this.escapeHtml(album.title || 'Unknown Album');
        var artist = this.escapeHtml(album.artist || ((_a = this.libraryCurrentArtist) === null || _a === void 0 ? void 0 : _a.name) || 'Unknown Artist');
        var year = album.year ? String(album.year) : '—';
        var trackCount = typeof album.track_count === 'number' ? String(album.track_count) : '—';
        return "\n            <div class=\"albums-grid-row library-clickable-row\" data-library-album-id=\"".concat(this.escapeHtml(album.id), "\" data-library-album-title=\"").concat(title, "\" data-library-artist-name=\"").concat(artist, "\">\n                <div class=\"grid-cell grid-col-artwork\">\n                    ").concat(album.cover
            ? "<img src=\"".concat(album.cover, "\" alt=\"").concat(title, "\" loading=\"lazy\">")
            : "<div class=\"grid-artwork-placeholder\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                                <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"></rect>\n                                <circle cx=\"8.5\" cy=\"8.5\" r=\"1.5\"></circle>\n                                <polyline points=\"21 15 16 10 5 21\"></polyline>\n                            </svg>\n                           </div>", "\n                </div>\n                <div class=\"grid-cell grid-col-title\"><div class=\"track-title-with-badge\">").concat(title, "</div></div>\n                <div class=\"grid-cell grid-col-artist\"><span class=\"library-album-artist-name\">").concat(artist, "</span></div>\n                <div class=\"grid-cell grid-col-year\">").concat(year, "</div>\n                <div class=\"grid-cell grid-col-track-count\">").concat(trackCount, "</div>\n                <div class=\"grid-cell grid-col-actions\">\n                    <button class=\"grid-play-btn\" title=\"Play\" aria-label=\"Play\" data-library-album-id=\"").concat(this.escapeHtml(album.id), "\">\n                        ").concat(this.getPlayIconSvg(), "\n                    </button>\n                </div>\n            </div>\n        ");
    };
    App.prototype.formatLibraryTrackRow = function (track, showDiscPrefix) {
        var _a, _b;
        var title = this.escapeHtml(track.title || 'Unknown Track');
        var artist = this.escapeHtml(track.artist || ((_a = this.libraryCurrentArtist) === null || _a === void 0 ? void 0 : _a.name) || 'Unknown Artist');
        var artistId = this.escapeHtml(track.artist_id || ((_b = this.libraryCurrentArtist) === null || _b === void 0 ? void 0 : _b.id) || '');
        var trackNumber = typeof track.track_number === 'number' ? track.track_number : null;
        var discNumber = typeof track.disc_number === 'number' ? track.disc_number : 1;
        var numberLabel = trackNumber !== null
            ? (showDiscPrefix ? "".concat(discNumber, "-").concat(String(trackNumber).padStart(2, '0')) : String(trackNumber))
            : '—';
        var durationSeconds = typeof track.duration === 'number' ? Math.max(0, Math.round(track.duration / 1000)) : null;
        var durationLabel = durationSeconds !== null ? this.formatDuration(durationSeconds) : '—';
        var qualityFormat = (track.quality_format || '').trim().toUpperCase();
        var qualityBitrate = typeof track.quality_bitrate_kbps === 'number' ? "".concat(track.quality_bitrate_kbps, " kbps") : '';
        var qualityLabel = [qualityFormat, qualityBitrate].filter(Boolean).join(' • ') || '—';
        return "\n            <div class=\"tracks-grid-row\" data-plex-library-row=\"true\" data-library-track-id=\"".concat(this.escapeHtml(track.id), "\">\n                <div class=\"grid-cell grid-col-track-number\">").concat(numberLabel, "</div>\n                <div class=\"grid-cell grid-col-title\"><div class=\"track-title-with-badge\">").concat(title, "</div></div>\n                <div class=\"grid-cell grid-col-artist\"><span class=\"track-artist-name library-track-artist-name\" data-library-artist-id=\"").concat(artistId, "\" data-library-artist-name=\"").concat(artist, "\" title=\"View albums by ").concat(artist, "\">").concat(artist, "</span></div>\n                <div class=\"grid-cell grid-col-quality\">").concat(durationLabel, "</div>\n                <div class=\"grid-cell grid-col-quality\">").concat(qualityLabel, "</div>\n                <div class=\"grid-cell grid-col-actions\">\n                    <button class=\"grid-play-btn\" title=\"Play\" aria-label=\"Play\" data-library-track-id=\"").concat(this.escapeHtml(track.id), "\">\n                        ").concat(this.getPlayIconSvg(), "\n                    </button>\n                </div>\n            </div>\n        ");
    };
    App.prototype.getLibraryArtistPageWindow = function (currentPage, totalPages) {
        if (totalPages <= 1) {
            return [1];
        }
        var pages = new Set([1, totalPages]);
        var windowRadius = 2;
        for (var page = currentPage - windowRadius; page <= currentPage + windowRadius; page += 1) {
            if (page >= 1 && page <= totalPages) {
                pages.add(page);
            }
        }
        return Array.from(pages).sort(function (a, b) { return a - b; });
    };
    App.prototype.formatLibraryArtistPageButtons = function (currentPage, totalPages) {
        var pages = this.getLibraryArtistPageWindow(currentPage, totalPages);
        var parts = [];
        for (var idx = 0; idx < pages.length; idx += 1) {
            var page = pages[idx];
            var prev = idx > 0 ? pages[idx - 1] : null;
            if (prev !== null && page - prev > 1) {
                parts.push('<span class="library-page-gap" aria-hidden="true">...</span>');
            }
            var offset = (page - 1) * this.libraryArtistsPageSize;
            var isCurrent = page === currentPage;
            parts.push("\n                <button\n                    class=\"library-page-btn library-page-number".concat(isCurrent ? ' is-active' : '', "\"\n                    data-library-offset=\"").concat(offset, "\"\n                    ").concat(isCurrent ? 'disabled aria-current="page"' : '', "\n                >").concat(page, "</button>\n            "));
        }
        return parts.join('');
    };
    App.prototype.renderLibraryArtists = function (artists) {
        var _this = this;
        this.libraryLoadedOnce = true;
        this.renderLibraryBreadcrumb();
        var currentPage = Math.floor(this.libraryArtistsOffset / this.libraryArtistsPageSize) + 1;
        var totalPages = Math.max(1, Math.ceil(this.libraryArtistsTotal / this.libraryArtistsPageSize));
        var firstOffset = 0;
        var lastOffset = Math.max(0, (totalPages - 1) * this.libraryArtistsPageSize);
        var prevOffset = Math.max(0, this.libraryArtistsOffset - this.libraryArtistsPageSize);
        var nextOffset = this.libraryArtistsOffset + this.libraryArtistsPageSize;
        var hasPrev = this.libraryArtistsOffset > 0;
        var hasNext = nextOffset < this.libraryArtistsTotal;
        this.libraryResultsContainer.innerHTML = "\n            <div class=\"results-header\">\n                <div class=\"results-header-top\">\n                    <h2>Artists</h2>\n                </div>\n            </div>\n            <div class=\"results-list artist-results\">\n                ".concat(artists.length > 0
            ? artists.map(function (artist) { return _this.formatLibraryArtistCard(artist); }).join('')
            : '<div class="library-placeholder"><p>No artists found in Plex library.</p></div>', "\n            </div>\n            <div class=\"library-pagination\">\n                <button class=\"library-page-btn\" data-library-offset=\"").concat(firstOffset, "\" ").concat(hasPrev ? '' : 'disabled', ">First</button>\n                <button class=\"library-page-btn\" data-library-offset=\"").concat(prevOffset, "\" ").concat(hasPrev ? '' : 'disabled', ">Previous</button>\n                <span class=\"library-page-text\">Page ").concat(currentPage, " of ").concat(totalPages, "</span>\n                <div class=\"library-page-numbers\" aria-label=\"Library artist page navigation\">\n                    ").concat(this.formatLibraryArtistPageButtons(currentPage, totalPages), "\n                </div>\n                <button class=\"library-page-btn\" data-library-offset=\"").concat(nextOffset, "\" ").concat(hasNext ? '' : 'disabled', ">Next</button>\n                <button class=\"library-page-btn\" data-library-offset=\"").concat(lastOffset, "\" ").concat(hasNext ? '' : 'disabled', ">Last</button>\n            </div>\n        ");
    };
    App.prototype.renderLibraryArtistAlbums = function (artistName, albums, artistPicture) {
        var _this = this;
        var _a;
        this.libraryLoadedOnce = true;
        this.renderLibraryBreadcrumb();
        this.libraryResultsContainer.innerHTML = "\n            <div class=\"artist-hero-section\">\n                <div class=\"artist-hero-content\">\n                    <div class=\"artist-cover-container\">\n                        ".concat(artistPicture
            ? "<img src=\"".concat(artistPicture, "\" alt=\"").concat(this.escapeHtml(artistName), "\" class=\"artist-cover\">")
            : '<div class="artist-cover-placeholder"></div>', "\n                    </div>\n                    <div class=\"artist-info\">\n                        <h1 class=\"artist-hero-name\">").concat(this.escapeHtml(artistName), "</h1>\n                    </div>\n                </div>\n                <div class=\"artist-actions\">\n                    <button class=\"album-action-btn primary library-artist-hero-play-btn\" data-library-artist-id=\"").concat(this.escapeHtml(((_a = this.libraryCurrentArtist) === null || _a === void 0 ? void 0 : _a.id) || ''), "\" title=\"Play artist\" aria-label=\"Play artist\" ").concat(albums.length === 0 ? 'disabled' : '', ">\n                        ").concat(this.getPlayIconSvg(), "\n                    </button>\n                </div>\n            </div>\n            <div class=\"results-header\">\n                <div class=\"results-header-top\">\n                    <h2>Albums</h2>\n                </div>\n            </div>\n            <div class=\"albums-grid-wrapper\" data-view-mode=\"library-albums\">\n                <div class=\"albums-grid\">\n                    ").concat(this.formatAlbumGridHeader(false, false), "\n                    ").concat(albums.length > 0
            ? albums.map(function (album) { return _this.formatLibraryAlbumRow(album); }).join('')
            : '<div class="library-placeholder"><p>No albums found for this artist.</p></div>', "\n                </div>\n            </div>\n        ");
    };
    App.prototype.renderLibraryAlbumTracks = function (albumTitle, tracks, albumArtist, albumYear, albumCover) {
        var _this = this;
        var _a, _b, _c;
        this.libraryLoadedOnce = true;
        var maxDisc = tracks.reduce(function (maxValue, track) {
            var disc = typeof track.disc_number === 'number' ? track.disc_number : 1;
            return Math.max(maxValue, disc);
        }, 1);
        var totalDurationSeconds = tracks.reduce(function (sum, track) {
            var millis = typeof track.duration === 'number' ? track.duration : 0;
            return sum + Math.max(0, Math.round(millis / 1000));
        }, 0);
        var totalDurationMinutes = Math.floor(totalDurationSeconds / 60);
        var totalDurationHours = Math.floor(totalDurationMinutes / 60);
        var remainingMinutes = totalDurationMinutes % 60;
        var durationStr = totalDurationHours > 0
            ? "".concat(totalDurationHours, "h ").concat(remainingMinutes, "m")
            : "".concat(totalDurationMinutes, "m");
        this.renderLibraryBreadcrumb();
        this.libraryResultsContainer.innerHTML = "\n            <div class=\"album-hero-section\">\n                <div class=\"album-hero-content\">\n                    <div class=\"album-cover-container\">\n                        ".concat(albumCover
            ? "<img src=\"".concat(albumCover, "\" alt=\"").concat(this.escapeHtml(albumTitle), "\" class=\"album-cover\">")
            : '<div class="album-cover-placeholder"></div>', "\n                    </div>\n                    <div class=\"album-info\">\n                        <h1 class=\"album-title\">").concat(this.escapeHtml(albumTitle), "</h1>\n                        <p class=\"album-artist\"><span class=\"track-artist-name\" title=\"View albums by ").concat(this.escapeHtml(albumArtist || ((_a = this.libraryCurrentArtist) === null || _a === void 0 ? void 0 : _a.name) || 'Unknown Artist'), "\">").concat(this.escapeHtml(albumArtist || ((_b = this.libraryCurrentArtist) === null || _b === void 0 ? void 0 : _b.name) || 'Unknown Artist'), "</span></p>\n                        <div class=\"album-metadata\">\n                            ").concat(albumYear ? "<span class=\"metadata-item\">".concat(albumYear, "</span>") : '', "\n                            <span class=\"metadata-item\">").concat(tracks.length, " ").concat(tracks.length === 1 ? 'track' : 'tracks', "</span>\n                            <span class=\"metadata-item\">").concat(durationStr, "</span>\n                        </div>\n                    </div>\n                </div>\n                <div class=\"album-actions\">\n                    <button class=\"album-action-btn primary library-album-hero-play-btn\" data-library-album-id=\"").concat(this.escapeHtml(((_c = this.libraryCurrentAlbum) === null || _c === void 0 ? void 0 : _c.id) || ''), "\" title=\"Play album\" aria-label=\"Play album\" ").concat(tracks.length === 0 ? 'disabled' : '', ">\n                        ").concat(this.getPlayIconSvg(), "\n                    </button>\n                </div>\n            </div>\n            <div class=\"results-header\">\n                <div class=\"results-header-top\">\n                    <h2>Tracks</h2>\n                </div>\n            </div>\n            <div class=\"tracks-grid-wrapper\" data-view-mode=\"library-tracks\">\n                <div class=\"tracks-grid\">\n                    ").concat(this.formatTrackGridHeader(true, false, false), "\n                    ").concat(tracks.length > 0
            ? tracks.map(function (track) { return _this.formatLibraryTrackRow(track, maxDisc > 1); }).join('')
            : '<div class="library-placeholder"><p>No tracks found for this album.</p></div>', "\n                </div>\n            </div>\n        ");
    };
    App.prototype.loadLibraryArtists = function () {
        return __awaiter(this, arguments, void 0, function (offset, updateHistory) {
            var params, userId, response, data, error_1;
            var _a;
            if (offset === void 0) { offset = 0; }
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!this.libraryResultsContainer) {
                            return [2 /*return*/];
                        }
                        this.stopPlayback();
                        this.updatePlexPlaylistContainerVisibility(false);
                        this.libraryCurrentArtist = null;
                        this.libraryCurrentAlbum = null;
                        this.libraryArtistsOffset = Math.max(0, offset);
                        if (updateHistory) {
                            this.pushHistoryLibraryRoute({
                                view: 'artists',
                                offset: this.libraryArtistsOffset
                            });
                        }
                        this.setLibraryMessage('Loading Plex artists...');
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        params = new URLSearchParams();
                        params.set('offset', String(this.libraryArtistsOffset));
                        params.set('limit', String(this.libraryArtistsPageSize));
                        userId = this.getSelectedPlexUserId();
                        if (userId) {
                            params.set('user_id', userId);
                        }
                        return [4 /*yield*/, fetch("/api/plex/library/artists?".concat(params.toString()), {
                                cache: 'no-store',
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _b.sent();
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 3:
                        data = _b.sent();
                        if (!response.ok) {
                            this.setLibraryMessage(data.error || 'Failed to load Plex artists.');
                            return [2 /*return*/];
                        }
                        this.libraryArtistsTotal = typeof data.total === 'number' ? data.total : 0;
                        this.libraryArtistsOffset = typeof data.offset === 'number' ? data.offset : this.libraryArtistsOffset;
                        this.renderLibraryArtists(Array.isArray(data.artists) ? data.artists : []);
                        return [3 /*break*/, 5];
                    case 4:
                        error_1 = _b.sent();
                        if (error_1 instanceof DOMException && error_1.name === 'AbortError') {
                            return [2 /*return*/];
                        }
                        console.error('[LIBRARY] Failed to load artists:', error_1);
                        this.setLibraryMessage('Failed to load Plex artists.');
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.loadLibraryArtistAlbums = function (artistId_1, artistName_1) {
        return __awaiter(this, arguments, void 0, function (artistId, artistName, updateHistory) {
            var params, userId, response, data, resolvedArtistName, error_2;
            var _a, _b, _c;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        if (!this.libraryResultsContainer) {
                            return [2 /*return*/];
                        }
                        this.libraryCurrentArtist = { id: artistId, name: artistName };
                        this.libraryCurrentAlbum = null;
                        if (updateHistory) {
                            this.pushHistoryLibraryRoute({
                                view: 'artist_albums',
                                artistId: artistId,
                                artistName: artistName
                            });
                        }
                        this.setLibraryMessage("Loading albums for ".concat(artistName, "..."));
                        _d.label = 1;
                    case 1:
                        _d.trys.push([1, 4, , 5]);
                        params = new URLSearchParams();
                        userId = this.getSelectedPlexUserId();
                        if (userId) {
                            params.set('user_id', userId);
                        }
                        return [4 /*yield*/, fetch("/api/plex/library/artists/".concat(encodeURIComponent(artistId), "/albums?").concat(params.toString()), {
                                cache: 'no-store',
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _d.sent();
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 3:
                        data = _d.sent();
                        if (!response.ok) {
                            this.setLibraryMessage(data.error || 'Failed to load artist albums.');
                            return [2 /*return*/];
                        }
                        resolvedArtistName = ((_b = data.artist) === null || _b === void 0 ? void 0 : _b.name) || artistName;
                        this.libraryCurrentArtist = { id: artistId, name: resolvedArtistName };
                        this.renderLibraryArtistAlbums(resolvedArtistName, Array.isArray(data.albums) ? data.albums : [], (_c = data.artist) === null || _c === void 0 ? void 0 : _c.picture);
                        return [3 /*break*/, 5];
                    case 4:
                        error_2 = _d.sent();
                        if (error_2 instanceof DOMException && error_2.name === 'AbortError') {
                            return [2 /*return*/];
                        }
                        console.error('[LIBRARY] Failed to load artist albums:', error_2);
                        this.setLibraryMessage('Failed to load artist albums.');
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.loadLibraryAlbumTracks = function (albumId_1, albumTitle_1, artistName_1) {
        return __awaiter(this, arguments, void 0, function (albumId, albumTitle, artistName, updateHistory) {
            var params, userId, response, data, resolvedArtist, resolvedAlbumTitle, error_3;
            var _a, _b, _c, _d, _e, _f, _g, _h;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_j) {
                switch (_j.label) {
                    case 0:
                        if (!this.libraryResultsContainer) {
                            return [2 /*return*/];
                        }
                        this.libraryCurrentAlbum = { id: albumId, title: albumTitle, artist: artistName };
                        if (updateHistory) {
                            this.pushHistoryLibraryRoute({
                                view: 'album_tracks',
                                albumId: albumId,
                                albumTitle: albumTitle,
                                albumArtist: artistName,
                                artistId: (_a = this.libraryCurrentArtist) === null || _a === void 0 ? void 0 : _a.id,
                                artistName: (_b = this.libraryCurrentArtist) === null || _b === void 0 ? void 0 : _b.name
                            });
                        }
                        this.setLibraryMessage("Loading tracks for ".concat(albumTitle, "..."));
                        _j.label = 1;
                    case 1:
                        _j.trys.push([1, 4, , 5]);
                        params = new URLSearchParams();
                        userId = this.getSelectedPlexUserId();
                        if (userId) {
                            params.set('user_id', userId);
                        }
                        return [4 /*yield*/, fetch("/api/plex/library/albums/".concat(encodeURIComponent(albumId), "/tracks?").concat(params.toString()), {
                                cache: 'no-store',
                                signal: (_c = this.pendingRequestController) === null || _c === void 0 ? void 0 : _c.signal
                            })];
                    case 2:
                        response = _j.sent();
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 3:
                        data = _j.sent();
                        if (!response.ok) {
                            this.setLibraryMessage(data.error || 'Failed to load album tracks.');
                            return [2 /*return*/];
                        }
                        resolvedArtist = ((_d = data.album) === null || _d === void 0 ? void 0 : _d.artist) || artistName || ((_e = this.libraryCurrentArtist) === null || _e === void 0 ? void 0 : _e.name) || '';
                        if (this.libraryCurrentArtist && resolvedArtist) {
                            this.libraryCurrentArtist = __assign(__assign({}, this.libraryCurrentArtist), { name: resolvedArtist });
                        }
                        resolvedAlbumTitle = ((_f = data.album) === null || _f === void 0 ? void 0 : _f.title) || albumTitle;
                        this.libraryCurrentAlbum = { id: albumId, title: resolvedAlbumTitle, artist: resolvedArtist };
                        this.renderLibraryAlbumTracks(resolvedAlbumTitle, Array.isArray(data.tracks) ? data.tracks : [], resolvedArtist, (_g = data.album) === null || _g === void 0 ? void 0 : _g.year, (_h = data.album) === null || _h === void 0 ? void 0 : _h.cover);
                        return [3 /*break*/, 5];
                    case 4:
                        error_3 = _j.sent();
                        if (error_3 instanceof DOMException && error_3.name === 'AbortError') {
                            return [2 /*return*/];
                        }
                        console.error('[LIBRARY] Failed to load album tracks:', error_3);
                        this.setLibraryMessage('Failed to load album tracks.');
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.openUserDropdown = function () {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!this.userDropdownModal || !this.userDropdownOverlay) {
                            console.error('User dropdown elements not found');
                            return [2 /*return*/];
                        }
                        // Show the dropdown
                        this.userDropdownModal.style.display = 'block';
                        this.userDropdownOverlay.style.display = 'block';
                        // Load users
                        return [4 /*yield*/, this.loadPlexUsersForDropdown()];
                    case 1:
                        // Load users
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.closeUserDropdown = function () {
        if (!this.userDropdownModal || !this.userDropdownOverlay) {
            return;
        }
        this.userDropdownModal.style.display = 'none';
        this.userDropdownOverlay.style.display = 'none';
    };
    App.prototype.loadPlexUsersForDropdown = function () {
        return __awaiter(this, void 0, void 0, function () {
            var response, data, users, savedId_1, error_4;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!this.userDropdownList) {
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, fetch('/api/plex/users', { cache: 'no-store' })];
                    case 2:
                        response = _a.sent();
                        if (!response.ok) {
                            this.userDropdownList.innerHTML = '<li class="user-dropdown-loading">Failed to load users</li>';
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _a.sent();
                        users = Array.isArray(data.users) ? data.users : [];
                        if (users.length === 0) {
                            this.userDropdownList.innerHTML = '<li class="user-dropdown-loading">No users found</li>';
                            return [2 /*return*/];
                        }
                        savedId_1 = window.localStorage.getItem('plexSelectedUserId') || '';
                        this.userDropdownList.innerHTML = '';
                        users.forEach(function (user) {
                            var _a, _b, _c, _d;
                            var id = String((_d = (_c = (_b = (_a = user.client_id) !== null && _a !== void 0 ? _a : user.id) !== null && _b !== void 0 ? _b : user.username) !== null && _c !== void 0 ? _c : user.title) !== null && _d !== void 0 ? _d : '');
                            var label = String(user.username || user.title || id);
                            var isSelected = id === savedId_1;
                            var li = document.createElement('li');
                            li.className = "user-dropdown-item ".concat(isSelected ? 'selected' : '');
                            li.addEventListener('click', function () { return _this.selectPlexUser(id, label); });
                            // User icon
                            var icon = document.createElement('div');
                            icon.className = 'user-dropdown-icon';
                            icon.textContent = label.charAt(0).toUpperCase();
                            li.appendChild(icon);
                            // User name
                            var nameSpan = document.createElement('span');
                            nameSpan.textContent = label;
                            li.appendChild(nameSpan);
                            // Checkmark if selected
                            if (isSelected) {
                                var checkmark = document.createElement('span');
                                checkmark.className = 'user-dropdown-checkmark';
                                checkmark.textContent = '✓';
                                li.appendChild(checkmark);
                            }
                            _this.userDropdownList.appendChild(li);
                        });
                        return [3 /*break*/, 5];
                    case 4:
                        error_4 = _a.sent();
                        console.warn('Failed to load users:', error_4);
                        this.userDropdownList.innerHTML = '<li class="user-dropdown-loading">Error loading users</li>';
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.selectPlexUser = function (userId, userName) {
        // Save user selection (both ID and name for better restoration)
        window.localStorage.setItem('plexSelectedUserId', userId);
        window.localStorage.setItem('plexSelectedUserName', userName);
        // Update button text
        if (this.userButtonText) {
            this.userButtonText.textContent = userName;
        }
        // Close dropdown
        this.closeUserDropdown();
        // Update sidebar playlists
        void this.updateSidebarPlaylists();
        if (this.currentPage === 'library') {
            void this.loadLibraryArtists(0, false);
        }
    };
    App.prototype.updateSidebarPlaylists = function () {
        return __awaiter(this, void 0, void 0, function () {
            var userId, query, response, data, playlists, error_5;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 3, , 4]);
                        userId = window.localStorage.getItem('plexSelectedUserId');
                        query = userId ? "?user_id=".concat(encodeURIComponent(userId)) : '';
                        return [4 /*yield*/, fetch("/api/plex/playlists".concat(query), { cache: 'no-store' })];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            this.populateSidebarPlaylists([]);
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        playlists = Array.isArray(data.playlists) ? data.playlists : [];
                        this.populateSidebarPlaylists(playlists);
                        return [3 /*break*/, 4];
                    case 3:
                        error_5 = _a.sent();
                        console.warn('Failed to load playlists:', error_5);
                        this.populateSidebarPlaylists([]);
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.initializeUserButton = function () {
        return __awaiter(this, void 0, void 0, function () {
            var savedId_2, savedName_1, response, data, users, selectedUser, userName, owner, ownerName, ownerId, error_6;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        _c.trys.push([0, 9, , 10]);
                        console.log('[USER_INIT] Starting user button initialization');
                        savedId_2 = window.localStorage.getItem('plexSelectedUserId') || '';
                        savedName_1 = window.localStorage.getItem('plexSelectedUserName') || '';
                        console.log('[USER_INIT] Saved user:', { savedId: savedId_2, savedName: savedName_1 });
                        return [4 /*yield*/, fetch('/api/plex/users', { cache: 'no-store' })];
                    case 1:
                        response = _c.sent();
                        if (!response.ok) return [3 /*break*/, 7];
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _c.sent();
                        users = Array.isArray(data.users) ? data.users : [];
                        console.log('[USER_INIT] Fetched users:', users.length, users);
                        selectedUser = users.find(function (u) {
                            var _a, _b, _c, _d;
                            var id = String((_d = (_c = (_b = (_a = u.client_id) !== null && _a !== void 0 ? _a : u.id) !== null && _b !== void 0 ? _b : u.username) !== null && _c !== void 0 ? _c : u.title) !== null && _d !== void 0 ? _d : '');
                            console.log('[USER_INIT] Checking user ID:', id, 'against saved:', savedId_2);
                            return id === savedId_2;
                        });
                        // If not found by ID, try matching by name as fallback
                        if (!selectedUser && savedName_1) {
                            console.log('[USER_INIT] ID match failed, trying name match for:', savedName_1);
                            selectedUser = users.find(function (u) {
                                var name = String(u.username || u.title || '');
                                return name === savedName_1;
                            });
                        }
                        if (!selectedUser) return [3 /*break*/, 4];
                        userName = String(selectedUser.username || selectedUser.title || 'User');
                        console.log('[USER_INIT] Found selected user:', userName);
                        if (this.userButtonText) {
                            this.userButtonText.textContent = userName;
                            console.log('[USER_INIT] Updated button text to:', userName);
                        }
                        else {
                            console.error('[USER_INIT] userButtonText element not found!');
                        }
                        // Update saved name in case it was looked up by ID
                        window.localStorage.setItem('plexSelectedUserName', userName);
                        // Load playlists for this user
                        console.log('[USER_INIT] Loading playlists for user');
                        return [4 /*yield*/, this.updateSidebarPlaylists()];
                    case 3:
                        _c.sent();
                        return [3 /*break*/, 6];
                    case 4:
                        console.log('[USER_INIT] No selected user found, checking for owner');
                        if (!(users.length > 0)) return [3 /*break*/, 6];
                        owner = users.find(function (u) { return u.is_owner; });
                        ownerName = String((owner === null || owner === void 0 ? void 0 : owner.username) || (owner === null || owner === void 0 ? void 0 : owner.title) || 'User');
                        ownerId = String((_b = (_a = owner === null || owner === void 0 ? void 0 : owner.id) !== null && _a !== void 0 ? _a : owner === null || owner === void 0 ? void 0 : owner.username) !== null && _b !== void 0 ? _b : '');
                        console.log('[USER_INIT] Using owner:', { ownerId: ownerId, ownerName: ownerName });
                        if (!(ownerId && this.userButtonText)) return [3 /*break*/, 6];
                        this.userButtonText.textContent = ownerName;
                        window.localStorage.setItem('plexSelectedUserId', ownerId);
                        window.localStorage.setItem('plexSelectedUserName', ownerName);
                        return [4 /*yield*/, this.updateSidebarPlaylists()];
                    case 5:
                        _c.sent();
                        _c.label = 6;
                    case 6: return [3 /*break*/, 8];
                    case 7:
                        console.error('[USER_INIT] Failed to fetch users:', response.status);
                        _c.label = 8;
                    case 8: return [3 /*break*/, 10];
                    case 9:
                        error_6 = _c.sent();
                        console.error('[USER_INIT] Error during initialization:', error_6);
                        return [3 /*break*/, 10];
                    case 10: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.populateSidebarPlaylists = function (playlists) {
        var playlistNavItems = document.getElementById('playlistNavItems');
        if (!playlistNavItems) {
            return;
        }
        playlistNavItems.innerHTML = '';
        if (playlists.length === 0) {
            var li = document.createElement('li');
            li.style.padding = '0.5rem 0.75rem';
            li.style.color = 'var(--text-muted)';
            li.style.fontSize = '0.875rem';
            li.textContent = 'No playlists';
            playlistNavItems.appendChild(li);
            return;
        }
        playlists.forEach(function (playlistName) {
            var li = document.createElement('li');
            var a = document.createElement('a');
            a.href = '#';
            a.className = 'nav-item';
            a.textContent = playlistName;
            a.style.fontSize = '0.875rem';
            a.addEventListener('click', function (e) {
                e.preventDefault();
                // Playlist click handling could be added here
            });
            li.appendChild(a);
            playlistNavItems.appendChild(li);
        });
    };
    App.prototype.initializeHistoryNavigation = function () {
        var _this = this;
        window.addEventListener('popstate', function (event) {
            void _this.handlePopState(event);
        });
        var historyState = this.parseHistoryState(window.history.state);
        var initialState = historyState || this.parseStateFromUrl() || this.buildCurrentHistoryState('explore');
        this.replaceHistoryState(initialState);
        void this.applyHistoryState(initialState);
    };
    App.prototype.handlePopState = function (event) {
        return __awaiter(this, void 0, void 0, function () {
            var state;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        state = this.parseHistoryState(event.state) || this.parseStateFromUrl() || this.buildCurrentHistoryState(this.currentPage);
                        this.isHandlingPopState = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, , 3, 4]);
                        return [4 /*yield*/, this.applyHistoryState(state)];
                    case 2:
                        _a.sent();
                        return [3 /*break*/, 4];
                    case 3:
                        this.isHandlingPopState = false;
                        return [7 /*endfinally*/];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.normalizePage = function (page) {
        if (page === 'library' || page === 'settings' || page === 'mirrors' || page === 'matches' || page === 'jobs') {
            return page;
        }
        return 'explore';
    };
    App.prototype.getCurrentLibraryRoute = function () {
        var _a, _b;
        if (this.libraryCurrentAlbum) {
            return {
                view: 'album_tracks',
                albumId: this.libraryCurrentAlbum.id,
                albumTitle: this.libraryCurrentAlbum.title,
                albumArtist: this.libraryCurrentAlbum.artist,
                artistId: (_a = this.libraryCurrentArtist) === null || _a === void 0 ? void 0 : _a.id,
                artistName: (_b = this.libraryCurrentArtist) === null || _b === void 0 ? void 0 : _b.name
            };
        }
        if (this.libraryCurrentArtist) {
            return {
                view: 'artist_albums',
                artistId: this.libraryCurrentArtist.id,
                artistName: this.libraryCurrentArtist.name
            };
        }
        return {
            view: 'artists',
            offset: this.libraryArtistsOffset
        };
    };
    App.prototype.buildCurrentHistoryState = function (tab) {
        return {
            app: 'squidly',
            tab: tab,
            route: __assign({}, this.currentExploreRoute),
            libraryRoute: __assign({}, this.getCurrentLibraryRoute())
        };
    };
    App.prototype.parseHistoryState = function (rawState) {
        if (!rawState || typeof rawState !== 'object') {
            return null;
        }
        var state = rawState;
        if (state.app !== 'squidly' || !state.route || typeof state.route !== 'object') {
            return null;
        }
        var route = state.route;
        if (!route.view) {
            return null;
        }
        var libraryRouteRaw = state.libraryRoute;
        var libraryRoute = libraryRouteRaw && typeof libraryRouteRaw === 'object' && libraryRouteRaw.view
            ? {
                view: libraryRouteRaw.view,
                offset: libraryRouteRaw.offset,
                artistId: libraryRouteRaw.artistId,
                artistName: libraryRouteRaw.artistName,
                albumId: libraryRouteRaw.albumId,
                albumTitle: libraryRouteRaw.albumTitle,
                albumArtist: libraryRouteRaw.albumArtist
            }
            : this.getCurrentLibraryRoute();
        return {
            app: 'squidly',
            tab: this.normalizePage(state.tab),
            route: route,
            libraryRoute: libraryRoute
        };
    };
    App.prototype.parseRouteFromUrl = function (params) {
        var view = params.get('view');
        if (!view) {
            return null;
        }
        if (view === 'search') {
            var searchType = params.get('type') || 's';
            var query = params.get('q') || '';
            return { view: view, searchType: searchType, query: query };
        }
        if (view === 'artist') {
            var artistId = Number(params.get('id') || '0');
            return Number.isFinite(artistId) && artistId > 0 ? { view: view, artistId: artistId } : null;
        }
        if (view === 'album') {
            var albumId = Number(params.get('id') || '0');
            return Number.isFinite(albumId) && albumId > 0 ? { view: view, albumId: albumId } : null;
        }
        if (view === 'playlist') {
            var playlistId = params.get('id') || '';
            return playlistId ? { view: view, playlistId: playlistId } : null;
        }
        if (view === 'listenbrainz_playlists') {
            var username = params.get('username') || '';
            return username ? { view: view, username: username } : null;
        }
        if (view === 'listenbrainz_playlist_tracks') {
            var playlistId = params.get('id') || '';
            var username = params.get('username') || undefined;
            return playlistId ? { view: view, playlistId: playlistId, username: username } : null;
        }
        if (view === 'lastfm_playlist' || view === 'youtube_music_playlist') {
            var playlistUrl = params.get('url') || '';
            return playlistUrl ? { view: view, playlistUrl: playlistUrl } : null;
        }
        if (view === 'similar_tracks') {
            var trackId = Number(params.get('id') || '0');
            return Number.isFinite(trackId) && trackId > 0 ? { view: view, trackId: trackId } : null;
        }
        if (view === 'similar_albums') {
            var albumId = Number(params.get('id') || '0');
            return Number.isFinite(albumId) && albumId > 0 ? { view: view, albumId: albumId } : null;
        }
        if (view === 'similar_artists') {
            var artistId = Number(params.get('id') || '0');
            return Number.isFinite(artistId) && artistId > 0 ? { view: view, artistId: artistId } : null;
        }
        return view === 'home' ? { view: 'home' } : null;
    };
    App.prototype.parseLibraryRouteFromUrl = function (params) {
        var view = params.get('lib_view');
        if (!view) {
            return null;
        }
        if (view === 'artists') {
            var offset = Number(params.get('lib_offset') || '0');
            return {
                view: view,
                offset: Number.isFinite(offset) && offset >= 0 ? Math.floor(offset) : 0
            };
        }
        if (view === 'artist_albums') {
            var artistId = params.get('lib_artist_id') || '';
            if (!artistId) {
                return null;
            }
            return {
                view: view,
                artistId: artistId,
                artistName: params.get('lib_artist_name') || 'Artist'
            };
        }
        if (view === 'album_tracks') {
            var albumId = params.get('lib_album_id') || '';
            if (!albumId) {
                return null;
            }
            var artistId = params.get('lib_artist_id') || undefined;
            var artistName = params.get('lib_artist_name') || undefined;
            return {
                view: view,
                albumId: albumId,
                albumTitle: params.get('lib_album_title') || 'Album',
                albumArtist: params.get('lib_album_artist') || undefined,
                artistId: artistId,
                artistName: artistName
            };
        }
        return null;
    };
    App.prototype.parseStateFromUrl = function () {
        var params = new URLSearchParams(window.location.search);
        var exploreRoute = this.parseRouteFromUrl(params) || { view: 'home' };
        var libraryRoute = this.parseLibraryRouteFromUrl(params) || this.getCurrentLibraryRoute();
        var tab = this.normalizePage(params.get('tab') || 'explore');
        var hasTab = params.has('tab');
        var hasExplore = params.has('view');
        var hasLibrary = params.has('lib_view');
        if (!hasTab && !hasExplore && !hasLibrary) {
            return null;
        }
        return {
            app: 'squidly',
            tab: tab,
            route: exploreRoute,
            libraryRoute: libraryRoute
        };
    };
    App.prototype.buildHistoryUrl = function (state) {
        var tab = this.normalizePage(state.tab);
        var route = state.route;
        var libraryRoute = state.libraryRoute;
        var params = new URLSearchParams();
        if (tab === 'explore') {
            if (route.view !== 'home') {
                params.set('view', route.view);
            }
            if (route.view === 'search') {
                params.set('type', route.searchType || 's');
                if (route.query) {
                    params.set('q', route.query);
                }
            }
            if (route.view === 'artist' && route.artistId) {
                params.set('id', String(route.artistId));
            }
            if ((route.view === 'album' || route.view === 'similar_albums') && route.albumId) {
                params.set('id', String(route.albumId));
            }
            if (route.view === 'similar_tracks' && route.trackId) {
                params.set('id', String(route.trackId));
            }
            if ((route.view === 'playlist' || route.view === 'listenbrainz_playlist_tracks') && route.playlistId) {
                params.set('id', route.playlistId);
            }
            if (route.view === 'listenbrainz_playlists' && route.username) {
                params.set('username', route.username);
            }
            if (route.view === 'listenbrainz_playlist_tracks' && route.username) {
                params.set('username', route.username);
            }
            if ((route.view === 'lastfm_playlist' || route.view === 'youtube_music_playlist') && route.playlistUrl) {
                params.set('url', route.playlistUrl);
            }
            if (route.view === 'similar_artists' && route.artistId) {
                params.set('id', String(route.artistId));
            }
        }
        else {
            params.set('tab', tab);
            if (tab === 'library') {
                params.set('lib_view', libraryRoute.view);
                if (libraryRoute.view === 'artists') {
                    params.set('lib_offset', String(Math.max(0, Math.floor(libraryRoute.offset || 0))));
                }
                if (libraryRoute.artistId) {
                    params.set('lib_artist_id', libraryRoute.artistId);
                }
                if (libraryRoute.artistName) {
                    params.set('lib_artist_name', libraryRoute.artistName);
                }
                if (libraryRoute.albumId) {
                    params.set('lib_album_id', libraryRoute.albumId);
                }
                if (libraryRoute.albumTitle) {
                    params.set('lib_album_title', libraryRoute.albumTitle);
                }
                if (libraryRoute.albumArtist) {
                    params.set('lib_album_artist', libraryRoute.albumArtist);
                }
            }
        }
        var query = params.toString();
        return query ? "".concat(window.location.pathname, "?").concat(query) : window.location.pathname;
    };
    App.prototype.pushHistoryRoute = function (route) {
        if (this.isHandlingPopState) {
            return;
        }
        var state = __assign(__assign({}, this.buildCurrentHistoryState('explore')), { route: __assign({}, route), tab: 'explore' });
        window.history.pushState(state, '', this.buildHistoryUrl(state));
    };
    App.prototype.pushHistoryLibraryRoute = function (route) {
        if (this.isHandlingPopState) {
            return;
        }
        var state = __assign(__assign({}, this.buildCurrentHistoryState('library')), { libraryRoute: __assign({}, route), tab: 'library' });
        window.history.pushState(state, '', this.buildHistoryUrl(state));
    };
    App.prototype.pushHistoryTab = function (tab) {
        if (this.isHandlingPopState) {
            return;
        }
        var state = this.buildCurrentHistoryState(tab);
        window.history.pushState(state, '', this.buildHistoryUrl(state));
    };
    App.prototype.buildExploreHref = function (route) {
        var state = __assign(__assign({}, this.buildCurrentHistoryState('explore')), { route: __assign({}, route), tab: 'explore' });
        return this.buildHistoryUrl(state);
    };
    App.prototype.buildLibraryHref = function (route) {
        var state = __assign(__assign({}, this.buildCurrentHistoryState('library')), { libraryRoute: __assign({}, route), tab: 'library' });
        return this.buildHistoryUrl(state);
    };
    App.prototype.replaceHistoryState = function (state) {
        window.history.replaceState(state, '', this.buildHistoryUrl(state));
    };
    App.prototype.applyHistoryState = function (state) {
        return __awaiter(this, void 0, void 0, function () {
            var tab, exploreRoute, libraryRoute;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        tab = this.normalizePage(state.tab);
                        exploreRoute = ((_a = state.route) === null || _a === void 0 ? void 0 : _a.view) ? state.route : { view: 'home' };
                        libraryRoute = ((_b = state.libraryRoute) === null || _b === void 0 ? void 0 : _b.view) ? state.libraryRoute : this.getCurrentLibraryRoute();
                        this.currentExploreRoute = __assign({}, exploreRoute);
                        if (tab !== this.currentPage) {
                            this.switchPage(tab, false);
                        }
                        if (!(tab === 'explore')) return [3 /*break*/, 2];
                        return [4 /*yield*/, this.navigateToRoute(exploreRoute, false)];
                    case 1:
                        _c.sent();
                        return [2 /*return*/];
                    case 2:
                        if (!(tab === 'library')) return [3 /*break*/, 4];
                        return [4 /*yield*/, this.navigateLibraryToRoute(libraryRoute, false)];
                    case 3:
                        _c.sent();
                        _c.label = 4;
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.navigateLibraryToRoute = function (route, updateHistory) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!(route.view === 'artist_albums' && route.artistId)) return [3 /*break*/, 2];
                        return [4 /*yield*/, this.loadLibraryArtistAlbums(route.artistId, route.artistName || 'Artist', updateHistory)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                    case 2:
                        if (!(route.view === 'album_tracks' && route.albumId)) return [3 /*break*/, 4];
                        return [4 /*yield*/, this.loadLibraryAlbumTracks(route.albumId, route.albumTitle || 'Album', route.albumArtist, updateHistory)];
                    case 3:
                        _a.sent();
                        return [2 /*return*/];
                    case 4: return [4 /*yield*/, this.loadLibraryArtists(route.offset || 0, updateHistory)];
                    case 5:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.navigateToRoute = function (route, updateHistory) {
        return __awaiter(this, void 0, void 0, function () {
            var signal;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        // Abort all pending requests from the previous route
                        if (this.pendingRequestController) {
                            this.pendingRequestController.abort();
                        }
                        this.currentExploreRoute = __assign({}, route);
                        if (route.view === 'search') {
                            this.exploreSearchRoute = __assign({}, route);
                        }
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        // Create a new controller for this route's requests
                        this.pendingRequestController = new AbortController();
                        signal = this.pendingRequestController.signal;
                        if (route.view === 'home') {
                            this.stopPlayback();
                            this.updatePlexPlaylistContainerVisibility(false);
                            this.resultsContainer.innerHTML = '';
                            if (updateHistory) {
                                this.pushHistoryRoute({ view: 'home' });
                            }
                            return [2 /*return*/];
                        }
                        if (!(route.view === 'search')) return [3 /*break*/, 2];
                        this.searchTypeSelect.value = route.searchType || 's';
                        this.searchInput.value = route.query || '';
                        this.updateSearchPlaceholder();
                        return [4 /*yield*/, this.handleSearch(updateHistory)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                    case 2:
                        if (!(route.view === 'artist' && route.artistId)) return [3 /*break*/, 4];
                        return [4 /*yield*/, this.fetchArtistAlbums(route.artistId, updateHistory)];
                    case 3:
                        _a.sent();
                        return [2 /*return*/];
                    case 4:
                        if (!(route.view === 'album' && route.albumId)) return [3 /*break*/, 6];
                        return [4 /*yield*/, this.fetchAlbumTracks(route.albumId, updateHistory)];
                    case 5:
                        _a.sent();
                        return [2 /*return*/];
                    case 6:
                        if (!(route.view === 'playlist' && route.playlistId)) return [3 /*break*/, 8];
                        return [4 /*yield*/, this.fetchPlaylistTracks(route.playlistId, updateHistory)];
                    case 7:
                        _a.sent();
                        return [2 /*return*/];
                    case 8:
                        if (!(route.view === 'listenbrainz_playlists' && route.username)) return [3 /*break*/, 10];
                        this.searchTypeSelect.value = 'listenbrainz';
                        this.searchInput.value = route.username;
                        this.updateSearchPlaceholder();
                        return [4 /*yield*/, this.handleListenbrainzPlaylists(route.username, updateHistory)];
                    case 9:
                        _a.sent();
                        return [2 /*return*/];
                    case 10:
                        if (!(route.view === 'listenbrainz_playlist_tracks' && route.playlistId)) return [3 /*break*/, 12];
                        return [4 /*yield*/, this.fetchListenbrainzPlaylistTracks(route.playlistId, updateHistory, route.username)];
                    case 11:
                        _a.sent();
                        return [2 /*return*/];
                    case 12:
                        if (!(route.view === 'lastfm_playlist' && route.playlistUrl)) return [3 /*break*/, 14];
                        this.searchTypeSelect.value = 'lastfm';
                        this.searchInput.value = route.playlistUrl;
                        this.updateSearchPlaceholder();
                        return [4 /*yield*/, this.handleLastfmPlaylist(route.playlistUrl, updateHistory)];
                    case 13:
                        _a.sent();
                        return [2 /*return*/];
                    case 14:
                        if (!(route.view === 'youtube_music_playlist' && route.playlistUrl)) return [3 /*break*/, 16];
                        this.searchTypeSelect.value = 'youtube_music';
                        this.searchInput.value = route.playlistUrl;
                        this.updateSearchPlaceholder();
                        return [4 /*yield*/, this.handleYoutubeMusicPlaylist(route.playlistUrl, updateHistory)];
                    case 15:
                        _a.sent();
                        return [2 /*return*/];
                    case 16:
                        if (!(route.view === 'similar_tracks' && route.trackId)) return [3 /*break*/, 18];
                        return [4 /*yield*/, this.fetchSimilarTracks(route.trackId, updateHistory)];
                    case 17:
                        _a.sent();
                        return [2 /*return*/];
                    case 18:
                        if (!(route.view === 'similar_albums' && route.albumId)) return [3 /*break*/, 20];
                        return [4 /*yield*/, this.fetchSimilarAlbums(route.albumId, updateHistory)];
                    case 19:
                        _a.sent();
                        return [2 /*return*/];
                    case 20:
                        if (!(route.view === 'similar_artists' && route.artistId)) return [3 /*break*/, 22];
                        return [4 /*yield*/, this.fetchSimilarArtists(route.artistId, updateHistory)];
                    case 21:
                        _a.sent();
                        return [2 /*return*/];
                    case 22: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.openFlyout = function () {
        this.statusFlyout.classList.add('active');
        this.flyoutOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        this.updateEndpointStatus(); // Refresh on open
    };
    App.prototype.closeFlyout = function () {
        this.statusFlyout.classList.remove('active');
        this.flyoutOverlay.classList.remove('active');
        document.body.style.overflow = '';
    };
    App.prototype.openJobsFlyout = function () {
        this.jobsFlyout.classList.add('active');
        this.jobsOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        this.currentJobsPage = 1;
        this.updateJobsActionButtons(0, this.jobsFilterSelect.value, 0);
        void this.loadJobs();
        this.startJobsPollingInterval();
    };
    App.prototype.closeJobsFlyout = function () {
        this.jobsFlyout.classList.remove('active');
        this.jobsOverlay.classList.remove('active');
        document.body.style.overflow = '';
        if (this.jobsUpdateInterval) {
            window.clearInterval(this.jobsUpdateInterval);
            this.jobsUpdateInterval = null;
        }
    };
    App.prototype.loadJobs = function () {
        return __awaiter(this, void 0, void 0, function () {
            var filter, params, response, data, jobs, totals, totalCount, retryableCount, error_7;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        filter = this.jobsFilterSelect.value;
                        this.jobsContent.innerHTML = '<p class="loading-text">Loading jobs...</p>';
                        this.clearJobsPagination();
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        params = new URLSearchParams({
                            jobs_filter: filter,
                            exclude_plex_playlist_add: '1'
                        });
                        return [4 /*yield*/, fetch("/api/jobs?".concat(params.toString()))];
                    case 2:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch jobs');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _a.sent();
                        jobs = Array.isArray(data.jobs) ? data.jobs : [];
                        totals = this.normalizeJobFilterTotals(data.totals, jobs);
                        totalCount = typeof data.total_count === 'number' && Number.isFinite(data.total_count)
                            ? Math.max(0, Math.floor(data.total_count))
                            : jobs.length;
                        retryableCount = (filter === 'completed_with_errors' || filter === 'failed')
                            ? jobs.length
                            : 0;
                        this.jobsListCache = jobs;
                        this.jobsTotalCountCache = totalCount;
                        this.updateJobsFilterCounts(totals);
                        this.updateJobsActionButtons(totals.incomplete, filter, retryableCount);
                        this.renderJobs(jobs, totalCount);
                        return [3 /*break*/, 5];
                    case 4:
                        error_7 = _a.sent();
                        this.jobsListCache = [];
                        this.jobsTotalCountCache = 0;
                        this.jobsContent.innerHTML = '<p class="loading-text">Failed to load jobs.</p>';
                        this.clearJobsPagination();
                        this.updateJobsActionButtons(0, filter, 0);
                        console.error('Jobs load error:', error_7);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.updateJobsActionButtons = function (incompleteCount, filter, retryableCount) {
        var showCancelIncomplete = filter === 'incomplete';
        this.cancelPendingJobsButton.classList.toggle('hidden', !showCancelIncomplete);
        if (!showCancelIncomplete) {
            this.cancelPendingJobsButton.disabled = true;
            this.cancelPendingJobsButton.textContent = 'Cancel all incomplete';
        }
        else {
            this.cancelPendingJobsButton.disabled = incompleteCount === 0;
            this.cancelPendingJobsButton.textContent = incompleteCount > 0
                ? "Cancel all incomplete (".concat(incompleteCount, ")")
                : 'Cancel all incomplete';
        }
        var showRetryAll = filter === 'completed_with_errors' || filter === 'failed';
        this.retryAllJobsButton.classList.toggle('hidden', !showRetryAll);
        if (!showRetryAll) {
            this.retryAllJobsButton.disabled = true;
            this.retryAllJobsButton.textContent = 'Retry all';
            return;
        }
        this.retryAllJobsButton.disabled = retryableCount === 0;
        this.retryAllJobsButton.textContent = retryableCount > 0
            ? "Retry all (".concat(retryableCount, ")")
            : 'Retry all';
    };
    App.prototype.cancelAllPendingJobs = function () {
        return __awaiter(this, void 0, void 0, function () {
            var pendingCountLabel, shouldProceed, response, message, data, _a, error_8;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        pendingCountLabel = this.cancelPendingJobsButton.textContent || 'Cancel all incomplete';
                        if (this.cancelPendingJobsButton.disabled) {
                            return [2 /*return*/];
                        }
                        shouldProceed = window.confirm('Cancel and remove all incomplete jobs from the queue?');
                        if (!shouldProceed) {
                            return [2 /*return*/];
                        }
                        this.cancelPendingJobsButton.disabled = true;
                        this.cancelPendingJobsButton.textContent = 'Cancelling...';
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 9, , 10]);
                        return [4 /*yield*/, fetch('/api/jobs/cancel-pending', { method: 'POST' })];
                    case 2:
                        response = _b.sent();
                        if (!!response.ok) return [3 /*break*/, 7];
                        message = 'Failed to cancel incomplete jobs';
                        _b.label = 3;
                    case 3:
                        _b.trys.push([3, 5, , 6]);
                        return [4 /*yield*/, response.json()];
                    case 4:
                        data = _b.sent();
                        if (data === null || data === void 0 ? void 0 : data.error) {
                            message = data.error;
                        }
                        return [3 /*break*/, 6];
                    case 5:
                        _a = _b.sent();
                        return [3 /*break*/, 6];
                    case 6: throw new Error(message);
                    case 7: return [4 /*yield*/, this.loadJobs()];
                    case 8:
                        _b.sent();
                        return [3 /*break*/, 10];
                    case 9:
                        error_8 = _b.sent();
                        console.error('Cancel incomplete jobs failed:', error_8);
                        window.alert(error_8.message || 'Failed to cancel incomplete jobs');
                        this.cancelPendingJobsButton.disabled = false;
                        this.cancelPendingJobsButton.textContent = pendingCountLabel;
                        return [3 /*break*/, 10];
                    case 10: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.retryAllFilteredJobs = function () {
        return __awaiter(this, void 0, void 0, function () {
            var selectedFilter, retryableJobs, shouldProceed, originalText, failures, skippedExistingCount, _i, retryableJobs_1, job, response, message, data, _a, _b, retriedCount, summary, skipLine, failureLine;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        selectedFilter = this.jobsFilterSelect.value;
                        if (selectedFilter !== 'completed_with_errors' && selectedFilter !== 'failed') {
                            return [2 /*return*/];
                        }
                        retryableJobs = this.jobsListCache;
                        if (retryableJobs.length === 0 || this.retryAllJobsButton.disabled) {
                            return [2 /*return*/];
                        }
                        shouldProceed = window.confirm("Retry all ".concat(retryableJobs.length, " jobs in ").concat(selectedFilter.replace(/_/g, ' '), "?"));
                        if (!shouldProceed) {
                            return [2 /*return*/];
                        }
                        originalText = this.retryAllJobsButton.textContent || 'Retry all';
                        this.retryAllJobsButton.disabled = true;
                        this.retryAllJobsButton.textContent = 'Retrying...';
                        failures = [];
                        skippedExistingCount = 0;
                        _i = 0, retryableJobs_1 = retryableJobs;
                        _c.label = 1;
                    case 1:
                        if (!(_i < retryableJobs_1.length)) return [3 /*break*/, 11];
                        job = retryableJobs_1[_i];
                        _c.label = 2;
                    case 2:
                        _c.trys.push([2, 9, , 10]);
                        return [4 /*yield*/, fetch("/api/jobs/".concat(job.id, "/retry"), { method: 'POST' })];
                    case 3:
                        response = _c.sent();
                        if (!!response.ok) return [3 /*break*/, 8];
                        message = "Job ".concat(job.id);
                        _c.label = 4;
                    case 4:
                        _c.trys.push([4, 6, , 7]);
                        return [4 /*yield*/, response.json()];
                    case 5:
                        data = _c.sent();
                        if (response.status === 409 && (data === null || data === void 0 ? void 0 : data.status) === 'already_exists_in_plex') {
                            skippedExistingCount += 1;
                            return [3 /*break*/, 10];
                        }
                        if (data === null || data === void 0 ? void 0 : data.error) {
                            message = "Job ".concat(job.id, ": ").concat(data.error);
                        }
                        return [3 /*break*/, 7];
                    case 6:
                        _a = _c.sent();
                        return [3 /*break*/, 7];
                    case 7:
                        failures.push(message);
                        _c.label = 8;
                    case 8: return [3 /*break*/, 10];
                    case 9:
                        _b = _c.sent();
                        failures.push("Job ".concat(job.id, ": request failed"));
                        return [3 /*break*/, 10];
                    case 10:
                        _i++;
                        return [3 /*break*/, 1];
                    case 11: return [4 /*yield*/, this.loadJobs()];
                    case 12:
                        _c.sent();
                        if (failures.length > 0 || skippedExistingCount > 0) {
                            retriedCount = retryableJobs.length - failures.length - skippedExistingCount;
                            summary = failures.length <= 3 ? failures.join('\n') : "".concat(failures.slice(0, 3).join('\n'), "\n...");
                            skipLine = skippedExistingCount > 0
                                ? "\nSkipped ".concat(skippedExistingCount, " job").concat(skippedExistingCount === 1 ? '' : 's', " (already exists in Plex).")
                                : '';
                            failureLine = failures.length > 0 ? "\n".concat(summary) : '';
                            window.alert("Retried ".concat(retriedCount, " of ").concat(retryableJobs.length, " jobs.").concat(skipLine).concat(failureLine));
                            this.retryAllJobsButton.disabled = false;
                            this.retryAllJobsButton.textContent = originalText;
                        }
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.getEffectiveJobStatus = function (job) {
        var _a;
        if (job.job_type !== 'download_track') {
            return job.status;
        }
        var stages = (_a = job.result) === null || _a === void 0 ? void 0 : _a.stages;
        if ((stages === null || stages === void 0 ? void 0 : stages.written) === 'failed') {
            return 'failed';
        }
        if ((stages === null || stages === void 0 ? void 0 : stages.playlist_added) === 'failed') {
            return 'completed_with_errors';
        }
        if (job.status === 'succeeded' && (stages === null || stages === void 0 ? void 0 : stages.playlist_added) === 'queued') {
            return 'in_progress';
        }
        return job.status;
    };
    App.prototype.filterJobsByStatus = function (jobs, filter) {
        var _this = this;
        if (filter === 'failed') {
            return jobs.filter(function (job) { return _this.getEffectiveJobStatus(job) === 'failed'; });
        }
        if (filter === 'completed_with_errors') {
            return jobs.filter(function (job) { return _this.getEffectiveJobStatus(job) === 'completed_with_errors'; });
        }
        if (filter === 'complete') {
            return jobs.filter(function (job) { return ['succeeded'].includes(_this.getEffectiveJobStatus(job)); });
        }
        return jobs.filter(function (job) { return ['queued', 'in_progress'].includes(_this.getEffectiveJobStatus(job)); });
    };
    App.prototype.renderJobs = function (jobs, totalJobs) {
        var _this = this;
        if (totalJobs === 0 || jobs.length === 0) {
            this.jobsContent.innerHTML = '<p class="loading-text">No jobs found.</p>';
            this.clearJobsPagination();
            return;
        }
        var totalPages = Math.max(1, Math.ceil(totalJobs / this.jobsPageSize));
        this.currentJobsPage = Math.min(this.currentJobsPage, totalPages);
        var startIndex = (this.currentJobsPage - 1) * this.jobsPageSize;
        var endIndex = startIndex + this.jobsPageSize;
        var pageItems = jobs.slice(startIndex, endIndex);
        this.jobsContent.innerHTML = pageItems.map(function (job) { return _this.renderJobItem(job); }).join('');
        this.renderJobsPagination(totalJobs, totalPages);
    };
    App.prototype.renderJobsPagination = function (totalJobs, totalPages) {
        var _this = this;
        if (totalPages <= 1) {
            this.clearJobsPagination();
            return;
        }
        var start = (this.currentJobsPage - 1) * this.jobsPageSize + 1;
        var end = Math.min(this.currentJobsPage * this.jobsPageSize, totalJobs);
        this.jobsPagination.innerHTML = "\n            <button type=\"button\" class=\"jobs-pagination-button\" data-page-action=\"prev\" ".concat(this.currentJobsPage === 1 ? 'disabled' : '', ">Previous</button>\n            <span class=\"jobs-pagination-info\">").concat(start, "-").concat(end, " of ").concat(totalJobs, "</span>\n            <button type=\"button\" class=\"jobs-pagination-button\" data-page-action=\"next\" ").concat(this.currentJobsPage === totalPages ? 'disabled' : '', ">Next</button>\n        ");
        this.jobsPagination.classList.add('active');
        var prevButton = this.jobsPagination.querySelector('[data-page-action="prev"]');
        if (prevButton) {
            prevButton.addEventListener('click', function () {
                if (_this.currentJobsPage > 1) {
                    _this.currentJobsPage -= 1;
                    _this.renderJobs(_this.jobsListCache, _this.jobsTotalCountCache);
                }
            });
        }
        var nextButton = this.jobsPagination.querySelector('[data-page-action="next"]');
        if (nextButton) {
            nextButton.addEventListener('click', function () {
                if (_this.currentJobsPage < totalPages) {
                    _this.currentJobsPage += 1;
                    _this.renderJobs(_this.jobsListCache, _this.jobsTotalCountCache);
                }
            });
        }
    };
    App.prototype.clearJobsPagination = function () {
        this.jobsPagination.classList.remove('active');
        this.jobsPagination.innerHTML = '';
    };
    App.prototype.setMatchReviewStatus = function (message, isError) {
        if (isError === void 0) { isError = false; }
        if (!this.matchReviewStatusEl) {
            return;
        }
        this.matchReviewStatusEl.textContent = message;
        this.matchReviewStatusEl.style.color = isError ? '#ff9ab0' : 'var(--text-secondary)';
    };
    App.prototype.updateMatchReviewRunScanButton = function (isActive) {
        if (!this.matchReviewRunScanButton) {
            return;
        }
        this.matchReviewRunScanButton.disabled = false;
        this.matchReviewRunScanButton.classList.toggle('is-cancel', isActive);
        this.matchReviewRunScanButton.textContent = isActive
            ? 'Cancel Automatic Matching'
            : 'Start Automatic Matching';
    };
    App.prototype.startMatchReviewPollingInterval = function () {
        var _this = this;
        if (this.matchReviewPollingInterval) {
            return;
        }
        this.matchReviewPollingInterval = window.setInterval(function () {
            if (_this.currentPage !== 'matches') {
                _this.stopMatchReviewPollingInterval();
                return;
            }
            void _this.loadMatchActivity();
        }, 5000);
    };
    App.prototype.stopMatchReviewPollingInterval = function () {
        if (this.matchReviewPollingInterval) {
            window.clearInterval(this.matchReviewPollingInterval);
            this.matchReviewPollingInterval = null;
        }
    };
    App.prototype.isMatchScanActive = function () {
        return Boolean(this.activeMatchActivityJobId
            || this.lastMatchActivityStatus === 'queued'
            || this.lastMatchActivityStatus === 'in_progress');
    };
    App.prototype.renderMatchReviewBlockedByActiveScan = function () {
        if (!this.matchReviewContent || !this.matchReviewSummary) {
            return;
        }
        this.matchReviewSummary.innerHTML = '';
        this.matchReviewContent.innerHTML = "\n            <div class=\"match-review-empty\">Hifi Match is currently running. Review cards will load after the scan completes.</div>\n        ";
    };
    App.prototype.getMatchCoverageFromProgress = function (progress, entity) {
        var total = Number(progress["".concat(entity, "_total")] || 0);
        var missing = Number(progress["".concat(entity, "_missing_current")] || progress["".concat(entity, "_processed")] || 0);
        var matchedCurrent = Number(progress["".concat(entity, "_matched_current_job")] || progress["".concat(entity, "_matched")] || 0);
        return {
            total: Number.isFinite(total) ? total : 0,
            missing: Number.isFinite(missing) ? missing : 0,
            matched: Number.isFinite(matchedCurrent) ? matchedCurrent : 0,
        };
    };
    App.prototype.renderMatchActivityCard = function (job) {
        var _this = this;
        var _a, _b;
        var effectiveStatus = this.getEffectiveJobStatus(job);
        var statusLabel = this.formatJobStatus(effectiveStatus);
        var statusClass = "status-".concat(effectiveStatus.replace(/_/g, '-'));
        var stages = (((_a = job.result) === null || _a === void 0 ? void 0 : _a.stages) || {});
        var progress = (((_b = job.result) === null || _b === void 0 ? void 0 : _b.progress) || {});
        var stageRows = [
            { key: 'backfilling_track_seed_ids', label: 'Backfilling Track IDs' },
            { key: 'matching_albums', label: 'Matching Albums' },
            { key: 'updating_album_completeness', label: 'Updating Album Completeness' }
        ];
        var artistsCoverage = this.getMatchCoverageFromProgress(progress, 'artists');
        var albumsCoverage = this.getMatchCoverageFromProgress(progress, 'albums');
        var tracksCoverage = this.getMatchCoverageFromProgress(progress, 'tracks');
        return "\n            <div class=\"match-activity-card\">\n                <div class=\"match-activity-header\">\n                    <div>\n                        <h3 class=\"match-activity-title\">Latest Match Scan</h3>\n                    </div>\n                    <span class=\"match-review-status ".concat(statusClass, "\">").concat(statusLabel, "</span>\n                </div>\n                <div class=\"match-activity-meta\">\n                    <span class=\"match-activity-meta-item\">Job ").concat(job.id, "</span>\n                    <span class=\"match-activity-meta-item\">Artists: ").concat(artistsCoverage.total, " total \u2022 ").concat(artistsCoverage.missing, " unmatched \u2022 ").concat(artistsCoverage.matched, " matched this job</span>\n                    <span class=\"match-activity-meta-item\">Albums: ").concat(albumsCoverage.total, " total \u2022 ").concat(albumsCoverage.missing, " unmatched \u2022 ").concat(albumsCoverage.matched, " matched this job</span>\n                    <span class=\"match-activity-meta-item\">Tracks: ").concat(tracksCoverage.total, " total \u2022 ").concat(tracksCoverage.missing, " unmatched \u2022 ").concat(tracksCoverage.matched, " matched this job</span>\n                </div>\n                <div class=\"match-activity-stages\">\n                    ").concat(stageRows.map(function (stage) {
            var stageStatus = _this.resolvePlexSyncStageStatus(job, stage.key, stages);
            return "\n                            <div class=\"job-stage\">\n                                <span>".concat(stage.label, "</span>\n                                <span class=\"job-stage-status status-").concat(stageStatus, "\">").concat(_this.formatStageStatus(stageStatus), "</span>\n                            </div>\n                        ");
        }).join(''), "\n                </div>\n            </div>\n        ");
    };
    App.prototype.loadMatchActivity = function () {
        return __awaiter(this, void 0, void 0, function () {
            var params, response, data, jobs, latestJob, previousJobId, previousStatus, currentStatus, isActive, completedNow, error_9;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!this.matchReviewActivity || !this.matchReviewRunScanButton) {
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, , 7]);
                        params = new URLSearchParams({
                            job_type: 'hifi_match',
                            exclude_plex_playlist_add: '1',
                            limit: '1'
                        });
                        return [4 /*yield*/, fetch("/api/jobs?".concat(params.toString()))];
                    case 2:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to load match scan activity');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _a.sent();
                        jobs = Array.isArray(data.jobs) ? data.jobs : [];
                        latestJob = jobs[0] || null;
                        if (!latestJob) {
                            this.matchReviewActivity.innerHTML = '<div class="match-activity-empty">No match scans have been run yet.</div>';
                            this.activeMatchActivityJobId = null;
                            this.updateMatchReviewRunScanButton(false);
                            this.lastMatchActivityJobId = null;
                            this.lastMatchActivityStatus = null;
                            this.stopMatchReviewPollingInterval();
                            return [2 /*return*/];
                        }
                        previousJobId = this.lastMatchActivityJobId;
                        previousStatus = this.lastMatchActivityStatus;
                        currentStatus = this.getEffectiveJobStatus(latestJob);
                        isActive = currentStatus === 'queued' || currentStatus === 'in_progress';
                        this.matchReviewActivity.innerHTML = this.renderMatchActivityCard(latestJob);
                        this.activeMatchActivityJobId = isActive ? latestJob.id : null;
                        this.updateMatchReviewRunScanButton(isActive);
                        if (isActive) {
                            this.startMatchReviewPollingInterval();
                            this.setMatchReviewStatus("Manual scan ".concat(currentStatus === 'queued' ? 'queued' : 'running', "..."));
                            if (this.currentPage === 'matches') {
                                this.renderMatchReviewBlockedByActiveScan();
                            }
                        }
                        else {
                            this.stopMatchReviewPollingInterval();
                        }
                        this.lastMatchActivityJobId = latestJob.id;
                        this.lastMatchActivityStatus = currentStatus;
                        completedNow = previousJobId === latestJob.id
                            && (previousStatus === 'queued' || previousStatus === 'in_progress')
                            && currentStatus !== 'queued'
                            && currentStatus !== 'in_progress';
                        if (!completedNow) return [3 /*break*/, 5];
                        if (currentStatus === 'succeeded') {
                            this.setMatchReviewStatus("Manual scan completed for job ".concat(latestJob.id, ". Review results updated."));
                        }
                        else {
                            this.setMatchReviewStatus("Manual scan finished with status ".concat(currentStatus, "."), currentStatus === 'failed');
                        }
                        return [4 /*yield*/, this.loadMatchReview()];
                    case 4:
                        _a.sent();
                        _a.label = 5;
                    case 5: return [3 /*break*/, 7];
                    case 6:
                        error_9 = _a.sent();
                        console.error('Failed to load match activity:', error_9);
                        this.matchReviewActivity.innerHTML = '<div class="match-activity-empty">Failed to load match scan activity.</div>';
                        this.stopMatchReviewPollingInterval();
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.formatMatchConfidence = function (confidence) {
        if (typeof confidence !== 'number' || !Number.isFinite(confidence)) {
            return '—';
        }
        return "".concat(Math.round(confidence * 100), "%");
    };
    App.prototype.formatMatchStatusLabel = function (status) {
        var normalized = String(status || 'unmatched').trim().toLowerCase();
        if (normalized === 'confirmed') {
            return 'Confirmed';
        }
        if (normalized === 'proposed') {
            return 'Needs Review';
        }
        if (normalized === 'rejected') {
            return 'Rejected';
        }
        return 'Unmatched';
    };
    App.prototype.renderMatchSummaryCard = function (label, value) {
        return "\n            <div class=\"matches-summary-card\">\n                <span class=\"matches-summary-value\">".concat(value, "</span>\n                <span class=\"matches-summary-label\">").concat(this.escapeHtml(label), "</span>\n            </div>\n        ");
    };
    App.prototype.escapeAttribute = function (text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '&#10;');
    };
    App.prototype.renderMatchTrackList = function (trackTitles, emptyLabel) {
        var _this = this;
        if (emptyLabel === void 0) { emptyLabel = 'Track list unavailable.'; }
        var normalizedTitles = (trackTitles || [])
            .map(function (title) { return String(title || '').trim(); })
            .filter(Boolean);
        if (normalizedTitles.length === 0) {
            return "<div class=\"match-review-track-list is-empty\">".concat(this.escapeHtml(emptyLabel), "</div>");
        }
        return "\n            <div class=\"match-review-track-list\">\n                <div class=\"match-review-track-list-label\">Track List</div>\n                <ol class=\"match-review-track-list-items\">\n                    ".concat(normalizedTitles.map(function (title) { return "<li>".concat(_this.escapeHtml(title), "</li>"); }).join(''), "\n                </ol>\n            </div>\n        ");
    };
    App.prototype.renderMatchReviewArtwork = function (imageUrl, altText, kind) {
        if (kind === void 0) { kind = 'album'; }
        if (imageUrl) {
            return "\n                <div class=\"match-review-artwork match-review-artwork--".concat(kind, "\">\n                    <img src=\"").concat(this.escapeAttribute(imageUrl), "\" alt=\"").concat(this.escapeAttribute(altText), "\" loading=\"lazy\" width=\"350\" height=\"350\">\n                </div>\n            ");
        }
        var placeholderSvg = kind === 'artist'
            ? "\n                <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"28\" height=\"28\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                    <circle cx=\"12\" cy=\"8\" r=\"4\"></circle>\n                    <path d=\"M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2\"></path>\n                </svg>\n            "
            : "\n                <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"28\" height=\"28\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                    <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"></rect>\n                    <circle cx=\"8.5\" cy=\"8.5\" r=\"1.5\"></circle>\n                    <polyline points=\"21 15 16 10 5 21\"></polyline>\n                </svg>\n            ";
        return "\n            <div class=\"match-review-artwork match-review-artwork--".concat(kind, " is-placeholder\" aria-hidden=\"true\">\n                ").concat(placeholderSvg, "\n            </div>\n        ");
    };
    App.prototype.renderMatchReviewTitle = function (title, options) {
        if (options === void 0) { options = {}; }
        var className = options.className || 'match-review-pane-title';
        var titleContent = options.href
            ? "<a class=\"match-review-title-link\" href=\"".concat(this.escapeAttribute(options.href), "\">").concat(this.escapeHtml(title), "</a>")
            : "<span class=\"match-review-title-text\">".concat(this.escapeHtml(title), "</span>");
        return "\n            <div class=\"".concat(className, "\">\n                ").concat(titleContent, "\n                ").concat(options.explicit ? '<span class="explicit-badge" title="Explicit content">E</span>' : '', "\n            </div>\n        ");
    };
    App.prototype.getMatchCandidateSearchPlaceholder = function (entityType) {
        if (entityType === 'artist') {
            return 'Search artists in Explore';
        }
        if (entityType === 'album') {
            return 'Search albums in Explore';
        }
        return 'Search tracks in Explore';
    };
    App.prototype.renderMatchCandidateSearchControls = function (entityType, reviewId) {
        var cacheKey = "".concat(entityType, ":").concat(reviewId);
        var previousSearch = this.matchCandidateSearchTerms.get(cacheKey) || '';
        return "\n            <div class=\"match-review-candidate-search\">\n                <label class=\"match-review-candidate-search-label\" for=\"matchCandidateSearch-".concat(entityType, "-").concat(reviewId, "\">Search candidates</label>\n                <div class=\"match-review-candidate-search-controls\">\n                    <input\n                        id=\"matchCandidateSearch-").concat(entityType, "-").concat(reviewId, "\"\n                        type=\"text\"\n                        class=\"settings-input match-review-candidate-search-input\"\n                        data-match-search-input=\"").concat(entityType, ":").concat(reviewId, "\"\n                        placeholder=\"").concat(this.escapeAttribute(this.getMatchCandidateSearchPlaceholder(entityType)), "\"\n                        value=\"").concat(this.escapeAttribute(previousSearch), "\"\n                        spellcheck=\"false\"\n                    >\n                    <button\n                        type=\"button\"\n                        class=\"match-review-button\"\n                        data-match-action=\"search-candidates\"\n                        data-entity-type=\"").concat(entityType, "\"\n                        data-review-id=\"").concat(reviewId, "\"\n                    >Search</button>\n                </div>\n            </div>\n        ");
    };
    App.prototype.renderMatchCandidateList = function (entityType, reviewId) {
        var _this = this;
        var cacheKey = "".concat(entityType, ":").concat(reviewId);
        var candidates = this.matchCandidateCache.get(cacheKey);
        if (!candidates) {
            return '<div class="match-review-inline-status">Candidates load automatically when you open this card.</div>';
        }
        if (candidates.length === 0) {
            return '<div class="match-review-empty">No candidates found for this item.</div>';
        }
        return "\n            <div class=\"match-review-candidate-list\">\n                ".concat(candidates.map(function (candidate) { return "\n                    <div class=\"match-review-candidate\">\n                        <div class=\"match-review-candidate-meta\">\n                            <span class=\"match-review-confidence\">".concat(_this.formatMatchConfidence(candidate.confidence), "</span>\n                            <button\n                                type=\"button\"\n                                class=\"match-review-button primary\"\n                                data-match-action=\"confirm-candidate\"\n                                data-entity-type=\"").concat(entityType, "\"\n                                data-review-id=\"").concat(reviewId, "\"\n                                data-hifi-id=\"").concat(_this.escapeHtml(candidate.hifi_id), "\"\n                            >Use This Match</button>\n                        </div>\n                        <div class=\"match-review-candidate-main\">\n                            ").concat(entityType === 'album'
            ? "\n                                    <div class=\"match-review-album-header\">\n                                        ".concat(_this.renderMatchReviewTitle(candidate.title, {
                explicit: candidate.explicit,
                className: 'match-review-candidate-title',
                href: _this.getMatchExploreHref(entityType, candidate.hifi_id)
            }), "\n                                        <div class=\"match-review-album-artist\">").concat(_this.escapeHtml(candidate.subtitle || 'Unknown Artist'), "</div>\n                                    </div>\n                                    <div class=\"match-review-album-body\">\n                                        ").concat(_this.renderMatchReviewArtwork(candidate.image_url, candidate.title, 'album'), "\n                                        ").concat(_this.renderMatchTrackList(candidate.track_titles, 'Track list unavailable for this candidate.'), "\n                                    </div>\n                                ")
            : "\n                                    ".concat(_this.renderMatchReviewArtwork(candidate.image_url, candidate.title, entityType === 'artist' ? 'artist' : 'album'), "\n                                    <div class=\"match-review-candidate-copy\">\n                                        ").concat(_this.renderMatchReviewTitle(candidate.title, {
                explicit: candidate.explicit,
                className: 'match-review-candidate-title',
                href: _this.getMatchExploreHref(entityType, candidate.hifi_id)
            }), "\n                                        ").concat(candidate.subtitle ? "<div class=\"match-review-candidate-subtitle\">".concat(_this.escapeHtml(candidate.subtitle), "</div>") : '', "\n                                    </div>\n                                "), "\n                        </div>\n                    </div>\n                "); }).join(''), "\n            </div>\n        ");
    };
    App.prototype.renderMatchWorkflowCard = function (entityType, reviewId, entityLabel, title, subtitle, status, summaryHtml, sourcePaneHtml, candidatePaneHtml, actionsHtml) {
        var normalizedStatus = String(status || 'unmatched');
        return "\n            <div class=\"match-review-card\" data-entity-type=\"".concat(entityType, "\" data-review-id=\"").concat(reviewId, "\">\n                <div class=\"match-review-card-header\">\n                    <div class=\"match-review-card-summary\">\n                        <div class=\"match-review-title-wrap\">\n                            <span class=\"match-review-entity\">").concat(this.escapeHtml(entityLabel), "</span>\n                            <h4 class=\"match-review-title\">").concat(this.escapeHtml(title), "</h4>\n                            <div class=\"match-review-subtitle\">").concat(this.escapeHtml(subtitle), "</div>\n                        </div>\n                        <div class=\"match-review-meta\">").concat(summaryHtml, "</div>\n                    </div>\n                    <div class=\"match-review-card-controls\">\n                        <span class=\"match-review-status status-").concat(this.escapeHtml(normalizedStatus), "\">").concat(this.formatMatchStatusLabel(status), "</span>\n                        <button\n                            type=\"button\"\n                            class=\"match-review-toggle\"\n                            data-match-toggle=\"true\"\n                            aria-expanded=\"false\"\n                        >Review</button>\n                    </div>\n                </div>\n                <div class=\"match-review-card-body\">\n                    <div class=\"match-review-workflow\">\n                        ").concat(sourcePaneHtml, "\n                        ").concat(candidatePaneHtml, "\n                    </div>\n                    <div class=\"match-review-actions\">\n                        ").concat(actionsHtml, "\n                    </div>\n                </div>\n            </div>\n        ");
    };
    App.prototype.getMatchSourceHref = function (item, entityType) {
        if (entityType === 'artist') {
            var artist = item;
            if (!artist.library_id) {
                return null;
            }
            return this.buildLibraryHref({
                view: 'artist_albums',
                artistId: artist.library_id,
                artistName: artist.name || 'Artist'
            });
        }
        if (entityType === 'album') {
            var album = item;
            if (!album.library_id) {
                return null;
            }
            return this.buildLibraryHref({
                view: 'album_tracks',
                albumId: album.library_id,
                albumTitle: album.title || 'Album',
                albumArtist: album.artist_name || 'Artist'
            });
        }
        var track = item;
        if (track.album_library_id) {
            return this.buildLibraryHref({
                view: 'album_tracks',
                albumId: track.album_library_id,
                albumTitle: track.album_title || 'Album',
                albumArtist: track.artist_name || 'Artist'
            });
        }
        if (track.artist_library_id) {
            return this.buildLibraryHref({
                view: 'artist_albums',
                artistId: track.artist_library_id,
                artistName: track.artist_name || 'Artist'
            });
        }
        return null;
    };
    App.prototype.getMatchExploreHref = function (entityType, hifiId) {
        var normalizedHifiId = String(hifiId || '').trim();
        if (!normalizedHifiId) {
            return null;
        }
        if (entityType === 'track') {
            return this.buildExploreHref({
                view: 'search',
                searchType: 'trackid',
                query: normalizedHifiId
            });
        }
        var parsedId = Number.parseInt(normalizedHifiId, 10);
        if (!Number.isFinite(parsedId) || parsedId <= 0) {
            return null;
        }
        return this.buildExploreHref(__assign({ view: entityType }, (entityType === 'artist' ? { artistId: parsedId } : { albumId: parsedId })));
    };
    App.prototype.getManualMatchIdHint = function (entityType) {
        if (entityType === 'artist') {
            return 'Paste the Explore artist ID if search found nothing useful.';
        }
        if (entityType === 'album') {
            return 'Paste the Explore album ID to confirm this library album manually.';
        }
        return 'Paste the Explore track ID to confirm this library track manually.';
    };
    App.prototype.renderManualMatchEntry = function (entityType, reviewId) {
        return "\n            <div class=\"match-review-manual-entry\">\n                <label class=\"match-review-manual-label\" for=\"manualMatchId-".concat(entityType, "-").concat(reviewId, "\">Manual HiFi ID</label>\n                <div class=\"match-review-manual-controls\">\n                    <input\n                        id=\"manualMatchId-").concat(entityType, "-").concat(reviewId, "\"\n                        type=\"text\"\n                        class=\"settings-input match-review-manual-input\"\n                        data-match-manual-id=\"").concat(entityType, ":").concat(reviewId, "\"\n                        placeholder=\"Enter ").concat(entityType, " ID\"\n                        spellcheck=\"false\"\n                    >\n                    <button\n                        type=\"button\"\n                        class=\"match-review-button\"\n                        data-match-action=\"confirm-manual\"\n                        data-entity-type=\"").concat(entityType, "\"\n                        data-review-id=\"").concat(reviewId, "\"\n                    >Use ID</button>\n                </div>\n                <div class=\"match-review-manual-hint\">").concat(this.escapeHtml(this.getManualMatchIdHint(entityType)), "</div>\n            </div>\n        ");
    };
    App.prototype.renderMatchCurrentCandidate = function (entityType, hifiId, extraLabel) {
        if (!this.getMatchExploreHref(entityType, hifiId)) {
            return '';
        }
        return "\n            <div class=\"match-review-current\">\n                <span>Current candidate selected".concat(extraLabel ? " \u2022 ".concat(this.escapeHtml(extraLabel)) : '', "</span>\n            </div>\n        ");
    };
    App.prototype.renderArtistReviewCard = function (item) {
        var reviewId = item.artist_id;
        var currentMatch = this.renderMatchCurrentCandidate('artist', item.hifi_id);
        var sourceHref = this.getMatchSourceHref(item, 'artist');
        return this.renderMatchWorkflowCard('artist', reviewId, 'Artist', item.name || 'Unknown Artist', 'Compare the Plex library artist against Explore artist candidates.', item.match_status, [
            "<span class=\"match-review-meta-item\">Confidence ".concat(this.formatMatchConfidence(item.confidence), "</span>"),
            "<span class=\"match-review-meta-item\">Source ".concat(this.escapeHtml(item.match_source || '—'), "</span>")
        ].join(''), "\n                <section class=\"match-review-pane source-pane\">\n                    <div class=\"match-review-pane-label\">Library Source</div>\n                    <div class=\"match-review-pane-header\">\n                        ".concat(this.renderMatchReviewArtwork(item.picture, item.name || 'Unknown Artist', 'artist'), "\n                        <div class=\"match-review-pane-stack\">\n                            ").concat(this.renderMatchReviewTitle(item.name || 'Unknown Artist', { href: sourceHref }), "\n                            <div class=\"match-review-pane-copy\">This is the artist currently indexed from your Plex library.</div>\n                        </div>\n                    </div>\n                </section>\n            "), "\n                <section class=\"match-review-pane candidate-pane\">\n                    <div class=\"match-review-pane-label\">Explore Candidates</div>\n                    ".concat(currentMatch, "\n                    ").concat(this.renderMatchCandidateSearchControls('artist', reviewId), "\n                    <div class=\"match-review-candidates\" data-match-candidates-key=\"artist:").concat(reviewId, "\">\n                        ").concat(this.renderMatchCandidateList('artist', reviewId), "\n                    </div>\n                    ").concat(this.renderManualMatchEntry('artist', reviewId), "\n                </section>\n            "), [
            item.hifi_id ? "<button type=\"button\" class=\"match-review-button primary\" data-match-action=\"confirm-current\" data-entity-type=\"artist\" data-review-id=\"".concat(reviewId, "\">Confirm Current</button>") : '',
            "<button type=\"button\" class=\"match-review-button danger\" data-match-action=\"reject\" data-entity-type=\"artist\" data-review-id=\"".concat(reviewId, "\">Reject</button>")
        ].filter(Boolean).join(''));
    };
    App.prototype.renderAlbumReviewCard = function (item) {
        var reviewId = item.album_id;
        var currentMatch = this.renderMatchCurrentCandidate('album', item.hifi_id, item.complete ? 'complete in library' : undefined);
        var sourceHref = this.getMatchSourceHref(item, 'album');
        return this.renderMatchWorkflowCard('album', reviewId, 'Album', item.title || 'Unknown Album', "".concat(item.artist_name || 'Unknown Artist', " \u2022 Review the library album against Explore releases."), item.match_status, [
            "<span class=\"match-review-meta-item\">Confidence ".concat(this.formatMatchConfidence(item.confidence), "</span>"),
            "<span class=\"match-review-meta-item\">Tracks ".concat(item.matched_track_count || 0, "/").concat(item.expected_track_count || 0, "</span>"),
            "<span class=\"match-review-meta-item\">Source ".concat(this.escapeHtml(item.match_source || '—'), "</span>")
        ].join(''), "\n                <section class=\"match-review-pane source-pane\">\n                    <div class=\"match-review-pane-label\">Library Source</div>\n                    <div class=\"match-review-pane-header\">\n                        <div class=\"match-review-album-header\">\n                            ".concat(this.renderMatchReviewTitle(item.title || 'Unknown Album', { href: sourceHref }), "\n                            <div class=\"match-review-album-artist\">").concat(this.escapeHtml(item.artist_name || 'Unknown Artist'), "</div>\n                        </div>\n                        <div class=\"match-review-album-body\">\n                            ").concat(this.renderMatchReviewArtwork(item.cover, item.title || 'Unknown Album', 'album'), "\n                            ").concat(this.renderMatchTrackList(item.track_titles, 'Track list unavailable for this library album.'), "\n                        </div>\n                    </div>\n                </section>\n            "), "\n                <section class=\"match-review-pane candidate-pane\">\n                    <div class=\"match-review-pane-label\">Explore Candidates</div>\n                    ".concat(currentMatch, "\n                    ").concat(this.renderMatchCandidateSearchControls('album', reviewId), "\n                    <div class=\"match-review-candidates\" data-match-candidates-key=\"album:").concat(reviewId, "\">\n                        ").concat(this.renderMatchCandidateList('album', reviewId), "\n                    </div>\n                    ").concat(this.renderManualMatchEntry('album', reviewId), "\n                </section>\n            "), [
            item.hifi_id ? "<button type=\"button\" class=\"match-review-button primary\" data-match-action=\"confirm-current\" data-entity-type=\"album\" data-review-id=\"".concat(reviewId, "\">Confirm Current</button>") : '',
            "<button type=\"button\" class=\"match-review-button danger\" data-match-action=\"reject\" data-entity-type=\"album\" data-review-id=\"".concat(reviewId, "\">Reject</button>")
        ].filter(Boolean).join(''));
    };
    App.prototype.renderTrackReviewCard = function (item) {
        var reviewId = item.track_id;
        var subtitleParts = [item.artist_name, item.album_title].filter(Boolean);
        var currentMatch = this.renderMatchCurrentCandidate('track', item.hifi_id);
        var sourceHref = this.getMatchSourceHref(item, 'track');
        return this.renderMatchWorkflowCard('track', reviewId, 'Track', item.title || 'Unknown Track', "".concat(subtitleParts.join(' • ') || 'Unknown', " \u2022 Compare the library file against Explore tracks."), item.match_status, [
            "<span class=\"match-review-meta-item\">Confidence ".concat(this.formatMatchConfidence(item.confidence), "</span>"),
            "<span class=\"match-review-meta-item\">Format ".concat(this.escapeHtml((item.format || '—').toUpperCase()), "</span>"),
            "<span class=\"match-review-meta-item\">Bitrate ".concat(typeof item.bitrate === 'number' ? "".concat(item.bitrate, " kbps") : '—', "</span>")
        ].join(''), "\n                <section class=\"match-review-pane source-pane\">\n                    <div class=\"match-review-pane-label\">Library Source</div>\n                    <div class=\"match-review-pane-header\">\n                        ".concat(this.renderMatchReviewArtwork(item.cover, item.album_title || item.title || 'Unknown Track', 'album'), "\n                        <div class=\"match-review-pane-stack\">\n                            ").concat(this.renderMatchReviewTitle(item.title || 'Unknown Track', { href: sourceHref }), "\n                            <div class=\"match-review-pane-copy\">").concat(this.escapeHtml(subtitleParts.join(' • ') || 'Unknown'), "</div>\n                            <div class=\"match-review-pane-copy\">Path: ").concat(this.escapeHtml(item.path || '—'), "</div>\n                        </div>\n                    </div>\n                </section>\n            "), "\n                <section class=\"match-review-pane candidate-pane\">\n                    <div class=\"match-review-pane-label\">Explore Candidates</div>\n                    ".concat(currentMatch, "\n                    ").concat(this.renderMatchCandidateSearchControls('track', reviewId), "\n                    <div class=\"match-review-candidates\" data-match-candidates-key=\"track:").concat(reviewId, "\">\n                        ").concat(this.renderMatchCandidateList('track', reviewId), "\n                    </div>\n                    ").concat(this.renderManualMatchEntry('track', reviewId), "\n                </section>\n            "), [
            item.hifi_id ? "<button type=\"button\" class=\"match-review-button primary\" data-match-action=\"confirm-current\" data-entity-type=\"track\" data-review-id=\"".concat(reviewId, "\">Confirm Current</button>") : '',
            "<button type=\"button\" class=\"match-review-button danger\" data-match-action=\"reject\" data-entity-type=\"track\" data-review-id=\"".concat(reviewId, "\">Reject</button>")
        ].filter(Boolean).join(''));
    };
    App.prototype.renderMatchReviewSection = function (title, count, itemsHtml) {
        if (count === 0) {
            return '';
        }
        return "\n            <section class=\"match-review-section\">\n                <div class=\"match-review-section-header\">\n                    <h3>".concat(this.escapeHtml(title), "</h3>\n                    <span class=\"match-review-count\">").concat(count, " item").concat(count === 1 ? '' : 's', "</span>\n                </div>\n                <div class=\"match-review-list\">").concat(itemsHtml, "</div>\n            </section>\n        ");
    };
    App.prototype.loadMatchReview = function () {
        return __awaiter(this, void 0, void 0, function () {
            var entityType, maxConfidence, loadingMessage, params, response, data, artists, albums, tracks, artistTotal, albumTotal, trackTotal, content, error_10;
            var _this = this;
            var _a, _b, _c, _d, _e;
            return __generator(this, function (_f) {
                switch (_f.label) {
                    case 0:
                        if (!this.matchReviewContent || !this.matchReviewSummary) {
                            return [2 /*return*/];
                        }
                        if (this.isMatchScanActive()) {
                            this.renderMatchReviewBlockedByActiveScan();
                            return [2 /*return*/];
                        }
                        entityType = ((_a = this.matchReviewEntityFilter) === null || _a === void 0 ? void 0 : _a.value) || 'all';
                        maxConfidence = ((_b = this.matchReviewMaxConfidenceInput) === null || _b === void 0 ? void 0 : _b.value) || '0.94';
                        loadingMessage = 'Loading match review items...';
                        this.matchReviewContent.innerHTML = "<p class=\"loading-text\">".concat(this.escapeHtml(loadingMessage), "</p>");
                        this.matchReviewSummary.innerHTML = '';
                        this.setMatchReviewStatus('');
                        _f.label = 1;
                    case 1:
                        _f.trys.push([1, 4, , 5]);
                        params = new URLSearchParams({
                            entity_type: entityType,
                            max_confidence: maxConfidence,
                            limit: '100'
                        });
                        return [4 /*yield*/, fetch("/api/hifi/matches/review?".concat(params.toString()))];
                    case 2:
                        response = _f.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch match review items');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _f.sent();
                        artists = Array.isArray(data.artists) ? data.artists : [];
                        albums = Array.isArray(data.albums) ? data.albums : [];
                        tracks = Array.isArray(data.tracks) ? data.tracks : [];
                        artistTotal = typeof ((_c = data.summary) === null || _c === void 0 ? void 0 : _c.artists) === 'number' ? data.summary.artists : artists.length;
                        albumTotal = typeof ((_d = data.summary) === null || _d === void 0 ? void 0 : _d.albums) === 'number' ? data.summary.albums : albums.length;
                        trackTotal = typeof ((_e = data.summary) === null || _e === void 0 ? void 0 : _e.tracks) === 'number' ? data.summary.tracks : tracks.length;
                        this.matchReviewSummary.innerHTML = [
                            this.renderMatchSummaryCard('Artists to review', artistTotal),
                            this.renderMatchSummaryCard('Albums to review', albumTotal),
                            this.renderMatchSummaryCard('Tracks to review', trackTotal)
                        ].join('');
                        content = [
                            this.renderMatchReviewSection('Artists', artists.length, artists.map(function (item) { return _this.renderArtistReviewCard(item); }).join('')),
                            this.renderMatchReviewSection('Albums', albums.length, albums.map(function (item) { return _this.renderAlbumReviewCard(item); }).join('')),
                            this.renderMatchReviewSection('Tracks', tracks.length, tracks.map(function (item) { return _this.renderTrackReviewCard(item); }).join(''))
                        ].filter(Boolean).join('');
                        this.matchReviewContent.innerHTML = content || '<div class="match-review-empty">No review items found for the current filters.</div>';
                        this.openInitialMatchReviewCards();
                        return [3 /*break*/, 5];
                    case 4:
                        error_10 = _f.sent();
                        console.error('Failed to load match review items:', error_10);
                        this.matchReviewContent.innerHTML = '<div class="match-review-empty">Failed to load match review items.</div>';
                        this.setMatchReviewStatus(error_10.message || 'Failed to load match review items', true);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.startHifiMatchScan = function () {
        return __awaiter(this, void 0, void 0, function () {
            var originalText, queuedJobIsActive, response, data, queuedJobId, queuedStatus, error_11;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!this.matchReviewRunScanButton) {
                            return [2 /*return*/];
                        }
                        originalText = this.matchReviewRunScanButton.textContent || 'Start Automatic Matching';
                        this.matchReviewRunScanButton.disabled = true;
                        this.matchReviewRunScanButton.textContent = 'Queueing...';
                        this.setMatchReviewStatus('');
                        queuedJobIsActive = false;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 6, 7, 8]);
                        return [4 /*yield*/, fetch('/api/hifi/matches', { method: 'POST' })];
                    case 2:
                        response = _a.sent();
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 3:
                        data = _a.sent();
                        if (!response.ok) {
                            throw new Error(data.error || 'Failed to queue manual scan');
                        }
                        queuedJobId = Number(data.job_id);
                        queuedStatus = String(data.status || '').trim().toLowerCase();
                        queuedJobIsActive = !queuedStatus || queuedStatus === 'queued' || queuedStatus === 'in_progress';
                        if (queuedJobIsActive && Number.isFinite(queuedJobId) && queuedJobId > 0) {
                            this.activeMatchActivityJobId = queuedJobId;
                            this.updateMatchReviewRunScanButton(true);
                        }
                        this.setMatchReviewStatus("Manual scan queued as job ".concat(data.job_id || 'unknown', ". Check Jobs for progress."));
                        return [4 /*yield*/, this.loadMatchActivity()];
                    case 4:
                        _a.sent();
                        return [4 /*yield*/, this.loadJobs()];
                    case 5:
                        _a.sent();
                        return [3 /*break*/, 8];
                    case 6:
                        error_11 = _a.sent();
                        console.error('Failed to queue hifi match scan:', error_11);
                        this.setMatchReviewStatus(error_11.message || 'Failed to queue manual scan', true);
                        return [3 /*break*/, 8];
                    case 7:
                        if (queuedJobIsActive || this.activeMatchActivityJobId) {
                            this.updateMatchReviewRunScanButton(true);
                        }
                        else {
                            this.matchReviewRunScanButton.disabled = false;
                            this.matchReviewRunScanButton.textContent = originalText;
                        }
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.cancelHifiMatchScan = function (jobId) {
        return __awaiter(this, void 0, void 0, function () {
            var originalText, response, message, data, _a, error_12;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!this.matchReviewRunScanButton) {
                            return [2 /*return*/];
                        }
                        originalText = this.matchReviewRunScanButton.textContent || 'Cancel Automatic Matching';
                        this.matchReviewRunScanButton.disabled = true;
                        this.matchReviewRunScanButton.textContent = 'Cancelling...';
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 10, , 11]);
                        return [4 /*yield*/, fetch("/api/jobs/".concat(jobId, "/cancel"), { method: 'POST' })];
                    case 2:
                        response = _b.sent();
                        if (!!response.ok) return [3 /*break*/, 7];
                        message = 'Failed to cancel automatic matching';
                        _b.label = 3;
                    case 3:
                        _b.trys.push([3, 5, , 6]);
                        return [4 /*yield*/, response.json()];
                    case 4:
                        data = _b.sent();
                        if (data === null || data === void 0 ? void 0 : data.error) {
                            message = data.error;
                        }
                        return [3 /*break*/, 6];
                    case 5:
                        _a = _b.sent();
                        return [3 /*break*/, 6];
                    case 6: throw new Error(message);
                    case 7:
                        this.activeMatchActivityJobId = null;
                        this.updateMatchReviewRunScanButton(false);
                        this.setMatchReviewStatus("Automatic matching cancelled for job ".concat(jobId, "."));
                        return [4 /*yield*/, this.loadMatchActivity()];
                    case 8:
                        _b.sent();
                        return [4 /*yield*/, this.loadJobs()];
                    case 9:
                        _b.sent();
                        return [3 /*break*/, 11];
                    case 10:
                        error_12 = _b.sent();
                        console.error('Failed to cancel hifi match scan:', error_12);
                        this.matchReviewRunScanButton.disabled = false;
                        this.matchReviewRunScanButton.textContent = originalText;
                        this.setMatchReviewStatus(error_12.message || 'Failed to cancel automatic matching', true);
                        return [3 /*break*/, 11];
                    case 11: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.loadMatchCandidates = function (entityType, reviewId, container, queryOverride) {
        return __awaiter(this, void 0, void 0, function () {
            var cacheKey, normalizedQuery, isManualSearch, params, response, data, error_13;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        cacheKey = "".concat(entityType, ":").concat(reviewId);
                        normalizedQuery = String(queryOverride || '').trim();
                        isManualSearch = normalizedQuery.length > 0;
                        if (!isManualSearch && this.matchCandidateCache.has(cacheKey)) {
                            container.innerHTML = this.renderMatchCandidateList(entityType, reviewId);
                            return [2 /*return*/];
                        }
                        if (!isManualSearch && this.matchCandidateRequestsInFlight.has(cacheKey)) {
                            return [2 /*return*/];
                        }
                        this.matchCandidateRequestsInFlight.add(cacheKey);
                        container.innerHTML = isManualSearch
                            ? "<div class=\"match-review-inline-status\">Searching for \"".concat(this.escapeHtml(normalizedQuery), "\"...</div>")
                            : '<div class="match-review-inline-status">Searching candidates...</div>';
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, 5, 6]);
                        params = new URLSearchParams({
                            entity_type: entityType,
                            id: String(reviewId),
                            limit: '3'
                        });
                        if (normalizedQuery) {
                            params.set('query', normalizedQuery);
                        }
                        return [4 /*yield*/, fetch("/api/hifi/matches/candidates?".concat(params.toString()))];
                    case 2:
                        response = _a.sent();
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _a.sent();
                        if (!response.ok) {
                            throw new Error(data.error || 'Failed to search candidates');
                        }
                        if (isManualSearch) {
                            this.matchCandidateSearchTerms.set(cacheKey, normalizedQuery);
                        }
                        this.matchCandidateCache.set(cacheKey, Array.isArray(data.candidates) ? data.candidates : []);
                        container.innerHTML = this.renderMatchCandidateList(entityType, reviewId);
                        return [3 /*break*/, 6];
                    case 4:
                        error_13 = _a.sent();
                        console.error('Failed to load match candidates:', error_13);
                        container.innerHTML = "<div class=\"match-review-empty\">".concat(this.escapeHtml(error_13.message || 'Failed to search candidates'), "</div>");
                        return [3 /*break*/, 6];
                    case 5:
                        this.matchCandidateRequestsInFlight.delete(cacheKey);
                        return [7 /*endfinally*/];
                    case 6: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.toggleMatchReviewCard = function (card, forceOpen) {
        return __awaiter(this, void 0, void 0, function () {
            var isOpen, nextOpen, toggleButton, entityType, reviewId, candidatesContainer;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        isOpen = card.classList.contains('is-open');
                        nextOpen = typeof forceOpen === 'boolean' ? forceOpen : !isOpen;
                        toggleButton = card.querySelector('[data-match-toggle]');
                        entityType = String(card.getAttribute('data-entity-type') || '').trim();
                        reviewId = Number(card.getAttribute('data-review-id') || '0');
                        candidatesContainer = card.querySelector("[data-match-candidates-key=\"".concat(entityType, ":").concat(reviewId, "\"]"));
                        card.classList.toggle('is-open', nextOpen);
                        if (toggleButton) {
                            toggleButton.setAttribute('aria-expanded', String(nextOpen));
                            toggleButton.textContent = nextOpen ? 'Hide' : 'Review';
                        }
                        if (!(nextOpen && candidatesContainer && entityType && Number.isFinite(reviewId) && reviewId > 0)) return [3 /*break*/, 2];
                        return [4 /*yield*/, this.loadMatchCandidates(entityType, reviewId, candidatesContainer)];
                    case 1:
                        _a.sent();
                        _a.label = 2;
                    case 2: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.openInitialMatchReviewCards = function () {
        var _this = this;
        if (!this.matchReviewContent) {
            return;
        }
        var firstCards = Array.from(this.matchReviewContent.querySelectorAll('.match-review-section .match-review-card:first-child'));
        firstCards.slice(0, 3).forEach(function (card) {
            void _this.toggleMatchReviewCard(card, true);
        });
    };
    App.prototype.submitMatchReviewAction = function (entityType, reviewId, action, hifiId) {
        return __awaiter(this, void 0, void 0, function () {
            var response, data;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, fetch('/api/hifi/matches/review', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                entity_type: entityType,
                                id: reviewId,
                                action: action,
                                hifi_id: hifiId
                            })
                        })];
                    case 1:
                        response = _a.sent();
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 2:
                        data = _a.sent();
                        if (!response.ok) {
                            throw new Error(data.error || 'Failed to update review item');
                        }
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.reloadMatchReviewPreserveScroll = function () {
        return __awaiter(this, void 0, void 0, function () {
            var previousScrollY;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        previousScrollY = window.scrollY;
                        return [4 /*yield*/, this.loadMatchReview()];
                    case 1:
                        _a.sent();
                        window.scrollTo({ top: previousScrollY, behavior: 'auto' });
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleMatchReviewClick = function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var target, toggleButton, card_1, actionButton, action, entityType, reviewId, hifiId, card, candidatesContainer, manualIdInput, candidateSearchInput, query, error_14, confirmed, manualId, error_15;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        target = e.target;
                        toggleButton = target.closest('[data-match-toggle]');
                        if (!toggleButton) return [3 /*break*/, 3];
                        card_1 = toggleButton.closest('.match-review-card');
                        if (!card_1) return [3 /*break*/, 2];
                        return [4 /*yield*/, this.toggleMatchReviewCard(card_1)];
                    case 1:
                        _a.sent();
                        _a.label = 2;
                    case 2: return [2 /*return*/];
                    case 3:
                        actionButton = target.closest('[data-match-action]');
                        if (!actionButton) {
                            return [2 /*return*/];
                        }
                        action = String(actionButton.getAttribute('data-match-action') || '').trim();
                        entityType = String(actionButton.getAttribute('data-entity-type') || '').trim();
                        reviewId = Number(actionButton.getAttribute('data-review-id') || '0');
                        hifiId = String(actionButton.getAttribute('data-hifi-id') || '').trim() || undefined;
                        if (!entityType || !Number.isFinite(reviewId) || reviewId <= 0) {
                            return [2 /*return*/];
                        }
                        card = actionButton.closest('.match-review-card');
                        candidatesContainer = card === null || card === void 0 ? void 0 : card.querySelector("[data-match-candidates-key=\"".concat(entityType, ":").concat(reviewId, "\"]"));
                        manualIdInput = card === null || card === void 0 ? void 0 : card.querySelector("[data-match-manual-id=\"".concat(entityType, ":").concat(reviewId, "\"]"));
                        candidateSearchInput = card === null || card === void 0 ? void 0 : card.querySelector("[data-match-search-input=\"".concat(entityType, ":").concat(reviewId, "\"]"));
                        if (!(action === 'search-candidates')) return [3 /*break*/, 9];
                        if (!candidatesContainer) {
                            return [2 /*return*/];
                        }
                        query = String((candidateSearchInput === null || candidateSearchInput === void 0 ? void 0 : candidateSearchInput.value) || '').trim();
                        if (!query) {
                            this.setMatchReviewStatus('Enter a search query to find candidates.', true);
                            return [2 /*return*/];
                        }
                        _a.label = 4;
                    case 4:
                        _a.trys.push([4, 6, 7, 8]);
                        actionButton.disabled = true;
                        return [4 /*yield*/, this.loadMatchCandidates(entityType, reviewId, candidatesContainer, query)];
                    case 5:
                        _a.sent();
                        this.setMatchReviewStatus('Search complete. Showing up to 3 candidates.');
                        return [3 /*break*/, 8];
                    case 6:
                        error_14 = _a.sent();
                        console.error('Failed to search match candidates:', error_14);
                        this.setMatchReviewStatus(error_14.message || 'Failed to search candidates', true);
                        return [3 /*break*/, 8];
                    case 7:
                        actionButton.disabled = false;
                        return [7 /*endfinally*/];
                    case 8: return [2 /*return*/];
                    case 9:
                        _a.trys.push([9, 19, , 20]);
                        actionButton.disabled = true;
                        if (!(action === 'reject')) return [3 /*break*/, 11];
                        confirmed = window.confirm('Reject this match candidate?');
                        if (!confirmed) {
                            actionButton.disabled = false;
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.submitMatchReviewAction(entityType, reviewId, 'reject')];
                    case 10:
                        _a.sent();
                        this.setMatchReviewStatus('Match rejected.');
                        return [3 /*break*/, 17];
                    case 11:
                        if (!(action === 'confirm-current')) return [3 /*break*/, 13];
                        return [4 /*yield*/, this.submitMatchReviewAction(entityType, reviewId, 'confirm')];
                    case 12:
                        _a.sent();
                        this.setMatchReviewStatus('Match confirmed.');
                        return [3 /*break*/, 17];
                    case 13:
                        if (!(action === 'confirm-manual')) return [3 /*break*/, 15];
                        manualId = String((manualIdInput === null || manualIdInput === void 0 ? void 0 : manualIdInput.value) || '').trim();
                        if (!manualId) {
                            throw new Error('Enter a HiFi ID before confirming manually.');
                        }
                        return [4 /*yield*/, this.submitMatchReviewAction(entityType, reviewId, 'confirm', manualId)];
                    case 14:
                        _a.sent();
                        this.setMatchReviewStatus("Manual ".concat(entityType, " ID confirmed."));
                        return [3 /*break*/, 17];
                    case 15:
                        if (!(action === 'confirm-candidate')) return [3 /*break*/, 17];
                        return [4 /*yield*/, this.submitMatchReviewAction(entityType, reviewId, 'confirm', hifiId)];
                    case 16:
                        _a.sent();
                        this.setMatchReviewStatus('Candidate selected and confirmed.');
                        _a.label = 17;
                    case 17:
                        this.matchCandidateCache.delete("".concat(entityType, ":").concat(reviewId));
                        return [4 /*yield*/, this.reloadMatchReviewPreserveScroll()];
                    case 18:
                        _a.sent();
                        return [3 /*break*/, 20];
                    case 19:
                        error_15 = _a.sent();
                        console.error('Failed to update match review item:', error_15);
                        this.setMatchReviewStatus(error_15.message || 'Failed to update match review item', true);
                        actionButton.disabled = false;
                        return [3 /*break*/, 20];
                    case 20: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleMatchReviewKeydown = function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var target, input, key, _a, entityTypeRaw, reviewIdRaw, entityType, reviewId, card, searchButton;
            return __generator(this, function (_b) {
                if (e.key !== 'Enter') {
                    return [2 /*return*/];
                }
                target = e.target;
                input = target.closest('[data-match-search-input]');
                if (!input) {
                    return [2 /*return*/];
                }
                key = String(input.getAttribute('data-match-search-input') || '').trim();
                _a = key.split(':'), entityTypeRaw = _a[0], reviewIdRaw = _a[1];
                entityType = entityTypeRaw;
                reviewId = Number(reviewIdRaw || '0');
                if (!entityType || !Number.isFinite(reviewId) || reviewId <= 0) {
                    return [2 /*return*/];
                }
                card = input.closest('.match-review-card');
                searchButton = card === null || card === void 0 ? void 0 : card.querySelector("[data-match-action=\"search-candidates\"][data-entity-type=\"".concat(entityType, "\"][data-review-id=\"").concat(reviewId, "\"]"));
                if (!searchButton) {
                    return [2 /*return*/];
                }
                e.preventDefault();
                searchButton.click();
                return [2 /*return*/];
            });
        });
    };
    App.prototype.handleJobsContentClick = function (e) {
        return __awaiter(this, void 0, void 0, function () {
            var target, cancelButton, jobId_1, retryButton, jobId;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        target = e.target;
                        cancelButton = target.closest('.job-cancel-button');
                        if (!cancelButton) return [3 /*break*/, 2];
                        jobId_1 = Number(cancelButton.getAttribute('data-job-id') || '0');
                        if (!Number.isFinite(jobId_1) || jobId_1 <= 0) {
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.cancelJob(jobId_1, cancelButton)];
                    case 1:
                        _a.sent();
                        return [2 /*return*/];
                    case 2:
                        retryButton = target.closest('.job-retry-button');
                        if (!retryButton) {
                            return [2 /*return*/];
                        }
                        jobId = Number(retryButton.getAttribute('data-job-id') || '0');
                        if (!Number.isFinite(jobId) || jobId <= 0) {
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.retryJob(jobId, retryButton)];
                    case 3:
                        _a.sent();
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.cancelJob = function (jobId, button) {
        return __awaiter(this, void 0, void 0, function () {
            var originalText, response, message, data, _a, error_16;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        originalText = button.textContent || 'Cancel';
                        button.disabled = true;
                        button.textContent = 'Cancelling...';
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 9, , 10]);
                        return [4 /*yield*/, fetch("/api/jobs/".concat(jobId, "/cancel"), { method: 'POST' })];
                    case 2:
                        response = _b.sent();
                        if (!!response.ok) return [3 /*break*/, 7];
                        message = 'Failed to cancel job';
                        _b.label = 3;
                    case 3:
                        _b.trys.push([3, 5, , 6]);
                        return [4 /*yield*/, response.json()];
                    case 4:
                        data = _b.sent();
                        if (data === null || data === void 0 ? void 0 : data.error) {
                            message = data.error;
                        }
                        return [3 /*break*/, 6];
                    case 5:
                        _a = _b.sent();
                        return [3 /*break*/, 6];
                    case 6: throw new Error(message);
                    case 7: return [4 /*yield*/, this.loadJobs()];
                    case 8:
                        _b.sent();
                        return [3 /*break*/, 10];
                    case 9:
                        error_16 = _b.sent();
                        console.error('Cancel job failed:', error_16);
                        window.alert(error_16.message || 'Failed to cancel job');
                        button.disabled = false;
                        button.textContent = originalText;
                        return [3 /*break*/, 10];
                    case 10: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.retryJob = function (jobId, button) {
        return __awaiter(this, void 0, void 0, function () {
            var originalText, response, message, data, _a, error_17;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        originalText = button.textContent || 'Retry';
                        button.disabled = true;
                        button.textContent = 'Retrying...';
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 11, , 12]);
                        return [4 /*yield*/, fetch("/api/jobs/".concat(jobId, "/retry"), { method: 'POST' })];
                    case 2:
                        response = _b.sent();
                        if (!!response.ok) return [3 /*break*/, 9];
                        message = 'Failed to retry job';
                        _b.label = 3;
                    case 3:
                        _b.trys.push([3, 7, , 8]);
                        return [4 /*yield*/, response.json()];
                    case 4:
                        data = _b.sent();
                        if (!(response.status === 409 && (data === null || data === void 0 ? void 0 : data.status) === 'already_exists_in_plex')) return [3 /*break*/, 6];
                        window.alert('Retry skipped: track already exists in Plex for the selected format.');
                        return [4 /*yield*/, this.loadJobs()];
                    case 5:
                        _b.sent();
                        return [2 /*return*/];
                    case 6:
                        if (data === null || data === void 0 ? void 0 : data.error) {
                            message = data.error;
                        }
                        return [3 /*break*/, 8];
                    case 7:
                        _a = _b.sent();
                        return [3 /*break*/, 8];
                    case 8: throw new Error(message);
                    case 9: return [4 /*yield*/, this.loadJobs()];
                    case 10:
                        _b.sent();
                        return [3 /*break*/, 12];
                    case 11:
                        error_17 = _b.sent();
                        console.error('Retry job failed:', error_17);
                        window.alert(error_17.message || 'Failed to retry job');
                        button.disabled = false;
                        button.textContent = originalText;
                        return [3 /*break*/, 12];
                    case 12: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.renderJobItem = function (job) {
        var _this = this;
        var _a, _b, _c, _d, _e, _f, _g, _h;
        var title = this.getJobDisplayTitle(job);
        var effectiveStatus = this.getEffectiveJobStatus(job);
        var statusLabel = this.formatJobStatus(effectiveStatus);
        var statusClass = "status-".concat(effectiveStatus.replace(/_/g, '-'));
        var showCancelButton = effectiveStatus === 'queued' || effectiveStatus === 'in_progress';
        var showRetryButton = job.job_type === 'download_track' && (effectiveStatus === 'failed' || effectiveStatus === 'completed_with_errors');
        var actionsClass = "job-main-actions".concat(showCancelButton ? ' cancel-on-hover' : '');
        var stages = ((_a = job.result) === null || _a === void 0 ? void 0 : _a.stages) || {};
        var playlistName = ((_b = job.result) === null || _b === void 0 ? void 0 : _b.playlist_name) || ((_c = job.payload) === null || _c === void 0 ? void 0 : _c.plex_playlist) || null;
        var skippedExisting = job.job_type === 'download_track' && Boolean(job.result && job.result.download_skipped_existing);
        var upgradedExisting = job.job_type === 'download_track' && Boolean(job.result && job.result.download_upgraded_existing);
        var upgradedFromBitrate = upgradedExisting ? ((_e = (_d = job.result) === null || _d === void 0 ? void 0 : _d.upgraded_from_bitrate) !== null && _e !== void 0 ? _e : null) : null;
        if (job.job_type === 'plex_library_sync') {
            var stageRows_1 = [
                { key: 'reading_plex_library', label: 'Reading Plex Library' },
                { key: 'updating_local_index', label: 'Updating Local Index' }
            ];
            var stageHtml_1 = stageRows_1.map(function (stage) {
                var status = _this.resolvePlexSyncStageStatus(job, stage.key, stages);
                var stageLabel = _this.formatStageStatus(status);
                return "\n                    <div class=\"job-stage\">\n                        <span>".concat(stage.label, "</span>\n                        <span class=\"job-stage-status status-").concat(status, "\">").concat(stageLabel, "</span>\n                    </div>\n                ");
            }).join('');
            var progress = ((_f = job.result) === null || _f === void 0 ? void 0 : _f.progress) || {};
            var processed = Number(progress.processed_tracks || 0);
            var total = Number(progress.total_tracks || 0);
            var upserted = Number(progress.upserted_songs || 0);
            var deleted = Number(progress.deleted_songs || 0);
            var progressText = total > 0
                ? "".concat(processed, "/").concat(total, " tracks processed \u2022 ").concat(upserted, " songs upserted \u2022 ").concat(deleted, " removed")
                : "".concat(upserted, " songs upserted \u2022 ").concat(deleted, " removed");
            return "\n                <div class=\"job-item\">\n                    <div class=\"job-main\">\n                        <div class=\"job-title\">".concat(this.escapeHtml(title), "</div>\n                        <div class=\"").concat(actionsClass, "\">\n                            <div class=\"job-status ").concat(statusClass, "\">").concat(statusLabel, "</div>\n                            ").concat(showCancelButton ? "<button type=\"button\" class=\"job-cancel-button\" data-job-id=\"".concat(job.id, "\">Cancel</button>") : '', "\n                            ").concat(showRetryButton ? "<button type=\"button\" class=\"job-retry-button\" data-job-id=\"".concat(job.id, "\">Retry</button>") : '', "\n                        </div>\n                    </div>\n                    <div class=\"job-sync-progress\">").concat(this.escapeHtml(progressText), "</div>\n                    <div class=\"job-stages\">\n                        ").concat(stageHtml_1, "\n                    </div>\n                </div>\n            ");
        }
        if (job.job_type === 'plex_library_update') {
            var stageRows_2 = [
                { key: 'scanning_plex_library', label: 'Scanning Plex Library' }
            ];
            var stageHtml_2 = stageRows_2.map(function (stage) {
                var status = _this.resolvePlexLibraryUpdateStageStatus(job, stage.key, stages);
                var stageLabel = _this.formatStageStatus(status);
                return "\n                    <div class=\"job-stage\">\n                        <span>".concat(stage.label, "</span>\n                        <span class=\"job-stage-status status-").concat(status, "\">").concat(stageLabel, "</span>\n                    </div>\n                ");
            }).join('');
            var progress = (((_g = job.result) === null || _g === void 0 ? void 0 : _g.progress) || {});
            var scanCompleted = progress.scan_completed === true;
            var syncQueueStatus = String(progress.sync_queue_status || 'pending');
            var syncJobId = Number(progress.sync_job_id || 0);
            var progressText = scanCompleted ? 'Library scan completed' : '';
            return "\n                <div class=\"job-item\">\n                    <div class=\"job-main\">\n                        <div class=\"job-title\">".concat(this.escapeHtml(title), "</div>\n                        <div class=\"").concat(actionsClass, "\">\n                            <div class=\"job-status ").concat(statusClass, "\">").concat(statusLabel, "</div>\n                            ").concat(showCancelButton ? "<button type=\"button\" class=\"job-cancel-button\" data-job-id=\"".concat(job.id, "\">Cancel</button>") : '', "\n                            ").concat(showRetryButton ? "<button type=\"button\" class=\"job-retry-button\" data-job-id=\"".concat(job.id, "\">Retry</button>") : '', "\n                        </div>\n                    </div>\n                    <div class=\"job-sync-progress\">").concat(this.escapeHtml(progressText), "</div>\n                    <div class=\"job-stages\">\n                        ").concat(stageHtml_2, "\n                    </div>\n                </div>\n            ");
        }
        if (job.job_type === 'hifi_match') {
            var stageRows_3 = [
                { key: 'backfilling_track_seed_ids', label: 'Backfilling Track IDs' },
                { key: 'matching_albums', label: 'Matching Albums' },
                { key: 'updating_album_completeness', label: 'Updating Album Completeness' }
            ];
            var stageHtml_3 = stageRows_3.map(function (stage) {
                var status = _this.resolvePlexSyncStageStatus(job, stage.key, stages);
                var stageLabel = _this.formatStageStatus(status);
                return "\n                    <div class=\"job-stage\">\n                        <span>".concat(stage.label, "</span>\n                        <span class=\"job-stage-status status-").concat(status, "\">").concat(stageLabel, "</span>\n                    </div>\n                ");
            }).join('');
            var progress = (((_h = job.result) === null || _h === void 0 ? void 0 : _h.progress) || {});
            var artistsCoverage = this.getMatchCoverageFromProgress(progress, 'artists');
            var albumsCoverage = this.getMatchCoverageFromProgress(progress, 'albums');
            var tracksCoverage = this.getMatchCoverageFromProgress(progress, 'tracks');
            var progressText = "Artists: ".concat(artistsCoverage.total, " total \u2022 ").concat(artistsCoverage.missing, " unmatched \u2022 ").concat(artistsCoverage.matched, " matched this job \u2022 Albums: ").concat(albumsCoverage.total, " total \u2022 ").concat(albumsCoverage.missing, " unmatched \u2022 ").concat(albumsCoverage.matched, " matched this job \u2022 Tracks: ").concat(tracksCoverage.total, " total \u2022 ").concat(tracksCoverage.missing, " unmatched \u2022 ").concat(tracksCoverage.matched, " matched this job");
            return "\n                <div class=\"job-item\">\n                    <div class=\"job-main\">\n                        <div class=\"job-title\">".concat(this.escapeHtml(title), "</div>\n                        <div class=\"").concat(actionsClass, "\">\n                            <div class=\"job-status ").concat(statusClass, "\">").concat(statusLabel, "</div>\n                            ").concat(showCancelButton ? "<button type=\"button\" class=\"job-cancel-button\" data-job-id=\"".concat(job.id, "\">Cancel</button>") : '', "\n                            ").concat(showRetryButton ? "<button type=\"button\" class=\"job-retry-button\" data-job-id=\"".concat(job.id, "\">Retry</button>") : '', "\n                        </div>\n                    </div>\n                    <div class=\"job-sync-progress\">").concat(this.escapeHtml(progressText), "</div>\n                    <div class=\"job-stages\">\n                        ").concat(stageHtml_3, "\n                    </div>\n                </div>\n            ");
        }
        var stageRows = __spreadArray(__spreadArray([
            { key: 'downloaded', label: 'Downloaded' },
            { key: 'id3_tagged', label: 'ID3 Tag Created' },
            { key: 'converted', label: 'Converted to MP3' },
            { key: 'written', label: 'Written to Disk' }
        ], (upgradedExisting ? [{ key: 'upgraded_existing', label: 'Upgraded Existing File' }] : []), true), [
            {
                key: 'playlist_added',
                label: playlistName ? "Added to Playlist \"".concat(this.escapeHtml(String(playlistName)), "\"") : 'Added to Playlist'
            }
        ], false);
        var stageHtml = stageRows.map(function (stage) {
            var status = _this.resolveStageStatus(job, stage.key, stages);
            var stageLabel = _this.formatStageStatus(status);
            var stageDisplayLabel = stage.label;
            if (stage.key === 'converted' && status === 'skipped') {
                stageDisplayLabel = 'Conversion not required';
            }
            if (stage.key === 'playlist_added' && status === 'skipped') {
                stageDisplayLabel = 'Playlist add not requested';
            }
            return "\n                <div class=\"job-stage\">\n                    <span>".concat(stageDisplayLabel, "</span>\n                    <span class=\"job-stage-status status-").concat(status, "\">").concat(stageLabel, "</span>\n                </div>\n            ");
        }).join('');
        return "\n            <div class=\"job-item\">\n                <div class=\"job-main\">\n                    <div class=\"job-title\">".concat(this.escapeHtml(title), "</div>\n                    <div class=\"").concat(actionsClass, "\">\n                        <div class=\"job-status ").concat(statusClass, "\">").concat(statusLabel, "</div>\n                        ").concat(showCancelButton ? "<button type=\"button\" class=\"job-cancel-button\" data-job-id=\"".concat(job.id, "\">Cancel</button>") : '', "\n                        ").concat(showRetryButton ? "<button type=\"button\" class=\"job-retry-button\" data-job-id=\"".concat(job.id, "\">Retry</button>") : '', "\n                    </div>\n                </div>\n                ").concat(skippedExisting ? '<div class="job-sync-progress">Used existing file (download skipped)</div>' : '', "\n                ").concat(upgradedExisting ? "<div class=\"job-sync-progress\">Upgraded existing file".concat(upgradedFromBitrate ? " (was ".concat(upgradedFromBitrate, " kbps)") : '', "</div>") : '', "\n                <div class=\"job-stages\">\n                    ").concat(stageHtml, "\n                </div>\n            </div>\n        ");
    };
    App.prototype.getJobDisplayTitle = function (job) {
        var _a, _b, _c, _d, _e, _f, _g, _h, _j;
        if (job.job_type === 'plex_library_update') {
            var trigger = String(((_a = job.result) === null || _a === void 0 ? void 0 : _a.trigger) || ((_b = job.payload) === null || _b === void 0 ? void 0 : _b.trigger) || '').trim();
            if (trigger === 'scheduled') {
                return 'Plex Library Update (Scheduled)';
            }
            if (trigger === 'manual') {
                return 'Plex Library Update (Manual)';
            }
            return 'Plex Library Update';
        }
        if (job.job_type === 'plex_library_sync') {
            var trigger = String(((_c = job.result) === null || _c === void 0 ? void 0 : _c.trigger) || ((_d = job.payload) === null || _d === void 0 ? void 0 : _d.trigger) || '').trim();
            if (trigger === 'interval') {
                return 'Plex Library Sync (Interval)';
            }
            if (trigger === 'manual') {
                return 'Plex Library Sync (Manual)';
            }
            return 'Plex Library Sync';
        }
        if (job.job_type === 'hifi_match') {
            var trigger = String(((_e = job.result) === null || _e === void 0 ? void 0 : _e.trigger) || ((_f = job.payload) === null || _f === void 0 ? void 0 : _f.trigger) || '').trim();
            if (trigger === 'manual') {
                return 'Hifi Match (Manual)';
            }
            return 'Hifi Match';
        }
        var artist = (_g = job.result) === null || _g === void 0 ? void 0 : _g.artist;
        var title = (_h = job.result) === null || _h === void 0 ? void 0 : _h.title;
        if (artist && title) {
            return "".concat(artist, " - ").concat(title);
        }
        var trackId = (_j = job.payload) === null || _j === void 0 ? void 0 : _j.trackId;
        if (trackId) {
            return "Track ".concat(trackId);
        }
        return "Job ".concat(job.id);
    };
    App.prototype.formatJobStatus = function (status) {
        if (status === 'in_progress') {
            return 'In-Progress';
        }
        if (status === 'completed_with_errors') {
            return 'Completed with errors';
        }
        return status.charAt(0).toUpperCase() + status.slice(1);
    };
    App.prototype.resolveStageStatus = function (job, key, stages) {
        var _a, _b;
        var value = stages[key];
        if (value) {
            return value;
        }
        if (job.status === 'succeeded') {
            if (key === 'converted') {
                var requestedFormat = String(((_a = job.result) === null || _a === void 0 ? void 0 : _a.format) || ((_b = job.payload) === null || _b === void 0 ? void 0 : _b.format) || 'original').toLowerCase();
                return requestedFormat === 'mp3' ? 'done' : 'skipped';
            }
            return key === 'playlist_added' ? 'skipped' : 'done';
        }
        if (job.status === 'cancelled') {
            return 'skipped';
        }
        return 'pending';
    };
    App.prototype.formatStageStatus = function (status) {
        if (!status) {
            return 'Pending';
        }
        return status.replace('_', ' ').replace(/\b\w/g, function (char) { return char.toUpperCase(); });
    };
    App.prototype.resolvePlexSyncStageStatus = function (job, key, stages) {
        var value = stages[key];
        if (value) {
            return value;
        }
        if (job.status === 'succeeded') {
            return 'done';
        }
        if (job.status === 'cancelled') {
            return 'skipped';
        }
        return 'pending';
    };
    App.prototype.resolvePlexLibraryUpdateStageStatus = function (job, key, stages) {
        var value = stages[key];
        if (value) {
            return value;
        }
        if (job.status === 'succeeded') {
            return 'done';
        }
        if (job.status === 'cancelled') {
            return 'skipped';
        }
        return 'pending';
    };
    App.prototype.openSettingsFlyout = function () {
        this.settingsFlyout.classList.add('active');
        this.settingsOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    };
    App.prototype.closeSettingsFlyout = function () {
        this.settingsFlyout.classList.remove('active');
        this.settingsOverlay.classList.remove('active');
        document.body.style.overflow = '';
    };
    App.prototype.defaultDownloadSettings = function () {
        return {
            quality: 'LOSSLESS',
            fileNamingAlbum: '{artist}/{album}/{track} - {title}.{ext}',
            jobsRefreshIntervalSeconds: 30,
            ignoreMatches: false
        };
    };
    App.prototype.normalizeSettings = function (raw) {
        var _a;
        var fallback = this.defaultDownloadSettings();
        var fileNaming = raw.file_naming;
        var fileNamingAlbum = raw.file_naming_album;
        var legacyFileNaming = raw.fileNaming;
        var jobsRefreshIntervalSecondsRaw = raw.jobs_refresh_interval_seconds;
        var jobsRefreshIntervalSeconds = this.normalizeJobsRefreshIntervalSeconds((_a = raw.jobsRefreshIntervalSeconds) !== null && _a !== void 0 ? _a : jobsRefreshIntervalSecondsRaw);
        var quality = fallback.quality;
        var rawQuality = String(raw.quality || raw.format || '').trim().toUpperCase();
        if (['LOSSLESS', 'HIGH', 'LOW'].includes(rawQuality)) {
            quality = rawQuality;
        }
        else if (String(raw.format).trim().toLowerCase() === 'original') {
            quality = 'LOSSLESS';
        }
        else if (String(raw.format).trim().toLowerCase() === 'mp3') {
            quality = 'HIGH';
        }
        return {
            quality: quality,
            fileNamingAlbum: typeof raw.fileNamingAlbum === 'string'
                ? raw.fileNamingAlbum
                : typeof fileNamingAlbum === 'string'
                    ? fileNamingAlbum
                    : typeof legacyFileNaming === 'string'
                        ? legacyFileNaming
                        : typeof fileNaming === 'string'
                            ? fileNaming
                            : fallback.fileNamingAlbum,
            jobsRefreshIntervalSeconds: jobsRefreshIntervalSeconds !== null && jobsRefreshIntervalSeconds !== void 0 ? jobsRefreshIntervalSeconds : fallback.jobsRefreshIntervalSeconds,
            ignoreMatches: typeof raw.ignoreMatches === 'boolean'
                ? raw.ignoreMatches
                : Boolean(raw.ignore_matches)
        };
    };
    App.prototype.fetchDownloadSettingsFromServer = function () {
        return __awaiter(this, void 0, void 0, function () {
            var response, data, error_18;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 3, , 4]);
                        return [4 /*yield*/, fetch('/api/settings')];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        this.downloadSettings = this.normalizeSettings(data);
                        this.applySettingsToForm(this.downloadSettings);
                        return [3 /*break*/, 4];
                    case 3:
                        error_18 = _a.sent();
                        console.warn('Failed to load download settings.', error_18);
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.applySettingsToForm = function (settings) {
        this.qualityLosslessInput.checked = settings.quality === 'LOSSLESS';
        this.qualityHighInput.checked = settings.quality === 'HIGH';
        this.qualityLowInput.checked = settings.quality === 'LOW';
        this.fileNamingAlbumInput.value = settings.fileNamingAlbum;
        this.jobsRefreshIntervalSecondsInput.value = String(settings.jobsRefreshIntervalSeconds);
        this.ignoreMatchesCheckbox.checked = settings.ignoreMatches === true;
        this.syncQualityToggleStyles();
    };
    App.prototype.readSettingsFromForm = function () {
        var _a, _b;
        var fallbackIntervalSeconds = (_b = (_a = this.downloadSettings) === null || _a === void 0 ? void 0 : _a.jobsRefreshIntervalSeconds) !== null && _b !== void 0 ? _b : this.defaultDownloadSettings().jobsRefreshIntervalSeconds;
        var parsedJobsRefreshIntervalSeconds = this.normalizeJobsRefreshIntervalSeconds(this.jobsRefreshIntervalSecondsInput.value);
        var quality = 'LOSSLESS';
        if (this.qualityHighInput.checked) {
            quality = 'HIGH';
        }
        else if (this.qualityLowInput.checked) {
            quality = 'LOW';
        }
        return {
            quality: quality,
            fileNamingAlbum: this.fileNamingAlbumInput.value.trim(),
            jobsRefreshIntervalSeconds: parsedJobsRefreshIntervalSeconds !== null && parsedJobsRefreshIntervalSeconds !== void 0 ? parsedJobsRefreshIntervalSeconds : fallbackIntervalSeconds,
            ignoreMatches: this.ignoreMatchesCheckbox.checked
        };
    };
    App.prototype.updateSettingsFromForm = function () {
        this.downloadSettings = this.readSettingsFromForm();
        this.jobsRefreshIntervalSecondsInput.value = String(this.downloadSettings.jobsRefreshIntervalSeconds);
        this.queueSettingsSave();
        this.syncQualityToggleStyles();
        if (this.jobsFlyout.classList.contains('active')) {
            this.startJobsPollingInterval();
        }
    };
    App.prototype.normalizeJobsRefreshIntervalSeconds = function (value) {
        if (typeof value === 'number' && Number.isFinite(value)) {
            var parsed = Math.floor(value);
            return parsed >= 1 ? parsed : null;
        }
        if (typeof value === 'string') {
            var parsed = parseInt(value, 10);
            return Number.isFinite(parsed) && parsed >= 1 ? parsed : null;
        }
        return null;
    };
    App.prototype.startJobsPollingInterval = function () {
        var _this = this;
        var _a, _b;
        if (this.jobsUpdateInterval) {
            window.clearInterval(this.jobsUpdateInterval);
            this.jobsUpdateInterval = null;
        }
        var intervalSeconds = (_b = (_a = this.downloadSettings) === null || _a === void 0 ? void 0 : _a.jobsRefreshIntervalSeconds) !== null && _b !== void 0 ? _b : this.defaultDownloadSettings().jobsRefreshIntervalSeconds;
        this.jobsUpdateInterval = window.setInterval(function () {
            void _this.loadJobs();
        }, intervalSeconds * 1000);
    };
    App.prototype.normalizeJobFilterTotals = function (totals, fallbackJobs) {
        var fallback = {
            incomplete: this.filterJobsByStatus(fallbackJobs, 'incomplete').length,
            complete: this.filterJobsByStatus(fallbackJobs, 'complete').length,
            completed_with_errors: this.filterJobsByStatus(fallbackJobs, 'completed_with_errors').length,
            failed: this.filterJobsByStatus(fallbackJobs, 'failed').length
        };
        if (!totals || typeof totals !== 'object') {
            return fallback;
        }
        var raw = totals;
        var parseCount = function (value, fallbackValue) {
            if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
                return Math.floor(value);
            }
            return fallbackValue;
        };
        return {
            incomplete: parseCount(raw.incomplete, fallback.incomplete),
            complete: parseCount(raw.complete, fallback.complete),
            completed_with_errors: parseCount(raw.completed_with_errors, fallback.completed_with_errors),
            failed: parseCount(raw.failed, fallback.failed)
        };
    };
    App.prototype.updateJobsFilterCounts = function (totals) {
        var incompleteCount = totals.incomplete;
        var completeCount = totals.complete;
        var completedWithErrorsCount = totals.completed_with_errors;
        var failedCount = totals.failed;
        var incompleteOption = this.jobsFilterSelect.querySelector('option[value="incomplete"]');
        if (incompleteOption) {
            incompleteOption.textContent = "Incomplete (".concat(incompleteCount, ")");
        }
        var completeOption = this.jobsFilterSelect.querySelector('option[value="complete"]');
        if (completeOption) {
            completeOption.textContent = "Complete (".concat(completeCount, ")");
        }
        var completedWithErrorsOption = this.jobsFilterSelect.querySelector('option[value="completed_with_errors"]');
        if (completedWithErrorsOption) {
            completedWithErrorsOption.textContent = "Completed with errors (".concat(completedWithErrorsCount, ")");
        }
        var failedOption = this.jobsFilterSelect.querySelector('option[value="failed"]');
        if (failedOption) {
            failedOption.textContent = "Failed (".concat(failedCount, ")");
        }
    };
    App.prototype.getCookieValue = function (name) {
        var match = document.cookie.match(new RegExp("(?:^|; )".concat(name.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&'), "=([^;]*)")));
        return match ? decodeURIComponent(match[1]) : null;
    };
    App.prototype.queueSettingsSave = function () {
        var _this = this;
        if (this.settingsSaveTimer) {
            window.clearTimeout(this.settingsSaveTimer);
        }
        this.settingsSaveTimer = window.setTimeout(function () {
            void _this.saveSettingsToServer(_this.downloadSettings);
        }, this.settingsSaveDelayMs);
    };
    App.prototype.saveSettingsToServer = function (settings) {
        return __awaiter(this, void 0, void 0, function () {
            var error_19;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 2, , 3]);
                        return [4 /*yield*/, fetch('/api/settings', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(settings)
                            })];
                    case 1:
                        _a.sent();
                        return [3 /*break*/, 3];
                    case 2:
                        error_19 = _a.sent();
                        console.warn('Failed to save download settings.', error_19);
                        return [3 /*break*/, 3];
                    case 3: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.syncQualityToggleStyles = function () {
        var losslessLabel = this.qualityLosslessInput.closest('label');
        var highLabel = this.qualityHighInput.closest('label');
        var lowLabel = this.qualityLowInput.closest('label');
        if (losslessLabel) {
            losslessLabel.classList.toggle('active', this.qualityLosslessInput.checked);
        }
        if (highLabel) {
            highLabel.classList.toggle('active', this.qualityHighInput.checked);
        }
        if (lowLabel) {
            lowLabel.classList.toggle('active', this.qualityLowInput.checked);
        }
    };
    App.prototype.loadListenbrainzConfig = function () {
        return __awaiter(this, void 0, void 0, function () {
            var response, data, error_20;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 4, , 5]);
                        return [4 /*yield*/, fetch('/api/listenbrainz/config')];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) return [3 /*break*/, 3];
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        this.lbConfigStatusEl.textContent = data.has_token ? '✓ Token configured' : '';
                        this.lbConfigStatusEl.style.color = data.has_token ? 'var(--accent-primary)' : '';
                        _a.label = 3;
                    case 3: return [3 /*break*/, 5];
                    case 4:
                        error_20 = _a.sent();
                        console.warn('Failed to load ListenBrainz config.', error_20);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.saveListenbrainzConfig = function () {
        return __awaiter(this, void 0, void 0, function () {
            var userToken, response, error_21;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        userToken = this.listenbrainzTokenInput.value.trim();
                        if (!userToken) {
                            this.lbConfigStatusEl.textContent = '⚠ User token is required';
                            this.lbConfigStatusEl.style.color = 'var(--text-secondary)';
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, fetch('/api/listenbrainz/config', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    user_token: userToken
                                })
                            })];
                    case 2:
                        response = _a.sent();
                        if (response.ok) {
                            this.lbConfigStatusEl.textContent = '✓ Configuration saved';
                            this.lbConfigStatusEl.style.color = 'var(--accent-primary)';
                            this.listenbrainzTokenInput.value = '';
                            // Clear status message after 3 seconds
                            setTimeout(function () {
                                _this.lbConfigStatusEl.textContent = '';
                            }, 3000);
                        }
                        else {
                            this.lbConfigStatusEl.textContent = '✗ Failed to save configuration';
                            this.lbConfigStatusEl.style.color = 'var(--text-secondary)';
                        }
                        return [3 /*break*/, 4];
                    case 3:
                        error_21 = _a.sent();
                        console.error('Error saving ListenBrainz config:', error_21);
                        this.lbConfigStatusEl.textContent = '✗ Error saving configuration';
                        this.lbConfigStatusEl.style.color = 'var(--text-secondary)';
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.loadPlexConfig = function () {
        return __awaiter(this, void 0, void 0, function () {
            var response, data, defaultOption, option, intervalHours, shouldShowLibraryConfig, error_22;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 4, , 5]);
                        return [4 /*yield*/, fetch('/api/plex/config')];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) return [3 /*break*/, 3];
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        // Populate library dropdown with saved library
                        this.plexLibraryNameSelect.innerHTML = '';
                        defaultOption = document.createElement('option');
                        defaultOption.value = '';
                        defaultOption.textContent = 'Select a library...';
                        this.plexLibraryNameSelect.appendChild(defaultOption);
                        if (data.library_name) {
                            option = document.createElement('option');
                            option.value = data.library_name;
                            option.textContent = data.library_name;
                            this.plexLibraryNameSelect.appendChild(option);
                            this.plexLibraryNameSelect.value = data.library_name;
                        }
                        intervalHours = Number(data.sync_interval_hours);
                        this.plexSyncIntervalHoursInput.value = Number.isFinite(intervalHours) && intervalHours > 0
                            ? String(intervalHours)
                            : '24';
                        this.isPlexConfigured = data.has_config ? true : false;
                        this.updatePlexConfigStatus(data.has_config ? '✓ Configured' : '');
                        shouldShowLibraryConfig = Boolean(data.has_config) && !Boolean(data.library_name);
                        if (this.plexLibraryConfigContainer) {
                            this.plexLibraryConfigContainer.style.display = shouldShowLibraryConfig ? '' : 'none';
                        }
                        this.updatePlexPlaylistContainerVisibility(false);
                        if (this.isPlexConfigured) {
                            void this.loadPlexLibraries();
                        }
                        else {
                            this.populatePlexPlaylistOptions([]);
                        }
                        _a.label = 3;
                    case 3: return [3 /*break*/, 5];
                    case 4:
                        error_22 = _a.sent();
                        console.warn('Failed to load Plex config.', error_22);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.loadPlexLibraries = function () {
        return __awaiter(this, void 0, void 0, function () {
            var response, data, libraries, current, defaultOption, error_23;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 3, , 4]);
                        return [4 /*yield*/, fetch('/api/plex/libraries')];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch Plex libraries');
                        }
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        libraries = Array.isArray(data.libraries) ? data.libraries : [];
                        current = this.plexLibraryNameSelect.value || '';
                        this.plexLibraryNameSelect.innerHTML = '';
                        defaultOption = document.createElement('option');
                        defaultOption.value = '';
                        defaultOption.textContent = 'Select a library...';
                        this.plexLibraryNameSelect.appendChild(defaultOption);
                        libraries.forEach(function (library) {
                            var option = document.createElement('option');
                            option.value = library;
                            option.textContent = library;
                            _this.plexLibraryNameSelect.appendChild(option);
                        });
                        if (current) {
                            this.plexLibraryNameSelect.value = current;
                        }
                        return [3 /*break*/, 4];
                    case 3:
                        error_23 = _a.sent();
                        console.warn('Failed to load Plex libraries.', error_23);
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.savePlexConfig = function () {
        return __awaiter(this, void 0, void 0, function () {
            var libraryName, payload, response, data, library, serverLabel, serverName, libraryText, error_24;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        libraryName = this.plexLibraryNameSelect.value.trim();
                        if (!libraryName) {
                            window.alert('Please select a library before saving.');
                            return [2 /*return*/];
                        }
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, , 7]);
                        payload = {
                            library_name: libraryName
                        };
                        return [4 /*yield*/, fetch('/api/plex/config', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(payload)
                            })];
                    case 2:
                        response = _b.sent();
                        if (!!response.ok) return [3 /*break*/, 4];
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 3:
                        data = _b.sent();
                        throw new Error(data.error || 'Failed to save Plex configuration');
                    case 4: return [4 /*yield*/, this.loadPlexConfig()];
                    case 5:
                        _b.sent();
                        void this.updatePlexClearCredentialsButton();
                        library = this.plexLibraryNameSelect.value.trim();
                        if (this.plexConnectedStatusEl) {
                            serverLabel = ((_a = this.plexConnectedStatusEl.textContent) === null || _a === void 0 ? void 0 : _a.replace(/^Connected to\s*/, '')) || '';
                            serverName = serverLabel || '';
                            libraryText = library ? " (library: ".concat(library, ")") : '';
                            this.plexConnectedStatusEl.textContent = "Connected to ".concat(serverName).concat(libraryText).trim();
                            this.plexConnectedStatusEl.style.display = 'block';
                        }
                        if (this.plexLibraryConfigContainer) {
                            this.plexLibraryConfigContainer.style.display = 'none';
                        }
                        window.alert('Plex configuration saved.');
                        return [3 /*break*/, 7];
                    case 6:
                        error_24 = _b.sent();
                        console.error('Failed to save Plex config:', error_24);
                        window.alert(error_24.message || 'Failed to save Plex configuration');
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    };
    // --- PIN OAuth logic ---
    App.prototype.startPlexPinLogin = function () {
        return __awaiter(this, void 0, void 0, function () {
            var resp, data, e_2;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        console.debug('[PLEX_UI] startPlexPinLogin called');
                        // Prepare UI for PIN-based login flow
                        if (this.plexLoginButton) {
                            this.plexLoginButton.disabled = true;
                            this.plexLoginButton.style.display = 'none';
                        }
                        if (this.plexLibraryConfigContainer) {
                            this.plexLibraryConfigContainer.style.display = 'none';
                        }
                        if (this.plexConnectedStatusEl) {
                            this.plexConnectedStatusEl.style.display = 'none';
                        }
                        this.plexPinStatus.textContent = '';
                        this.plexPinDisplay.textContent = '';
                        this.plexPinContainer.style.display = 'block';
                        this.plexPinStatus.textContent = 'Requesting PIN...';
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 5, , 6]);
                        return [4 /*yield*/, fetch('/api/plex/pin/start', { method: 'POST' })];
                    case 2:
                        resp = _a.sent();
                        console.debug('[PLEX_UI] /api/plex/pin/start response', resp.status);
                        return [4 /*yield*/, resp.json()];
                    case 3:
                        data = _a.sent();
                        console.debug('[PLEX_UI] /api/plex/pin/start data', data);
                        if (!data.ok)
                            throw new Error(data.error || 'Failed to start PIN login');
                        this.plexPinDisplay.textContent = data.pin;
                        this.plexPinStatus.textContent = '';
                        return [4 /*yield*/, this.pollPlexPinStatus(data.client_id, data.pin, 300)];
                    case 4:
                        _a.sent();
                        return [3 /*break*/, 6];
                    case 5:
                        e_2 = _a.sent();
                        console.debug('[PLEX_UI] startPlexPinLogin error', e_2);
                        this.plexPinStatus.textContent = 'Failed to start PIN login.';
                        // Restore login button so user can retry
                        if (this.plexLoginButton) {
                            this.plexLoginButton.disabled = false;
                            this.plexLoginButton.style.display = '';
                        }
                        return [3 /*break*/, 6];
                    case 6: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.pollPlexPinStatus = function (client_id, pin, timeoutSeconds) {
        return __awaiter(this, void 0, void 0, function () {
            var elapsed, pollInterval, resp, data, e_3;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        console.debug('[PLEX_UI] pollPlexPinStatus started', { client_id: client_id, pin: pin });
                        elapsed = 0;
                        pollInterval = 2000;
                        _a.label = 1;
                    case 1:
                        if (!(elapsed < timeoutSeconds * 1000)) return [3 /*break*/, 12];
                        return [4 /*yield*/, new Promise(function (r) { return setTimeout(r, pollInterval); })];
                    case 2:
                        _a.sent();
                        elapsed += pollInterval;
                        _a.label = 3;
                    case 3:
                        _a.trys.push([3, 10, , 11]);
                        return [4 /*yield*/, fetch('/api/plex/pin/status', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ client_id: client_id, pin: pin })
                            })];
                    case 4:
                        resp = _a.sent();
                        console.debug('[PLEX_UI] /api/plex/pin/status response', resp.status);
                        return [4 /*yield*/, resp.json()];
                    case 5:
                        data = _a.sent();
                        console.debug('[PLEX_UI] /api/plex/pin/status data', data);
                        if (!(data.ok && data.token && data.baseurl)) return [3 /*break*/, 8];
                        this.plexPinStatus.textContent = '✓ Plex login successful!';
                        this.plexPinDisplay.textContent = '';
                        this.plexPinContainer.style.display = 'none';
                        this.isPlexConfigured = true;
                        this.updatePlexConfigStatus('✓ Configured');
                        return [4 /*yield*/, this.loadPlexConfig()];
                    case 6:
                        _a.sent();
                        // Refresh cached health status so the UI can update properly
                        return [4 /*yield*/, fetch('/api/plex/healthcheck', { cache: 'no-store' }).catch(function () { return null; })];
                    case 7:
                        // Refresh cached health status so the UI can update properly
                        _a.sent();
                        return [2 /*return*/];
                    case 8:
                        if (data.expired) {
                            this.plexPinStatus.textContent = 'PIN expired. Please try again.';
                            this.plexPinDisplay.textContent = '';
                            if (this.plexLoginButton) {
                                this.plexLoginButton.disabled = false;
                                this.plexLoginButton.style.display = '';
                            }
                            return [2 /*return*/];
                        }
                        _a.label = 9;
                    case 9: return [3 /*break*/, 11];
                    case 10:
                        e_3 = _a.sent();
                        console.debug('[PLEX_UI] pollPlexPinStatus error', e_3);
                        this.plexPinStatus.textContent = 'Error polling PIN status.';
                        if (this.plexLoginButton) {
                            this.plexLoginButton.disabled = false;
                            this.plexLoginButton.style.display = '';
                        }
                        return [2 /*return*/];
                    case 11: return [3 /*break*/, 1];
                    case 12:
                        console.debug('[PLEX_UI] pollPlexPinStatus timed out');
                        this.plexPinStatus.textContent = 'Login timed out. Please try again.';
                        this.plexPinDisplay.textContent = '';
                        if (this.plexLoginButton) {
                            this.plexLoginButton.disabled = false;
                            this.plexLoginButton.style.display = '';
                        }
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.startPlexSync = function () {
        return __awaiter(this, void 0, void 0, function () {
            var libUpdateResponse, data, error_25;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        this.plexSyncStatusEl.textContent = 'Starting library update...';
                        this.plexSyncStatusEl.style.color = 'var(--text-secondary)';
                        this.startPlexSyncButton.disabled = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 7, 8, 9]);
                        return [4 /*yield*/, fetch('/api/plex/library-updates', {
                                method: 'POST'
                            })];
                    case 2:
                        libUpdateResponse = _a.sent();
                        if (!(libUpdateResponse.status !== 202)) return [3 /*break*/, 4];
                        return [4 /*yield*/, libUpdateResponse.json().catch(function () { return ({}); })];
                    case 3:
                        data = _a.sent();
                        this.plexSyncStatusEl.textContent = "\u2717 ".concat(data.error || 'Failed to start library update');
                        this.plexSyncStatusEl.style.color = 'var(--text-secondary)';
                        return [2 /*return*/];
                    case 4:
                        this.plexSyncStatusEl.textContent = '✓ Plex library update queued; sync will follow automatically';
                        this.plexSyncStatusEl.style.color = 'var(--accent-primary)';
                        if (!(this.jobsFlyout && this.jobsFlyout.classList.contains('active'))) return [3 /*break*/, 6];
                        return [4 /*yield*/, this.loadJobs()];
                    case 5:
                        _a.sent();
                        _a.label = 6;
                    case 6: return [3 /*break*/, 9];
                    case 7:
                        error_25 = _a.sent();
                        console.error('Error starting Plex sync:', error_25);
                        this.plexSyncStatusEl.textContent = '✗ Error starting library update';
                        this.plexSyncStatusEl.style.color = 'var(--text-secondary)';
                        return [3 /*break*/, 9];
                    case 8:
                        this.startPlexSyncButton.disabled = false;
                        return [7 /*endfinally*/];
                    case 9: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.updatePlexConfigStatus = function (message) {
        if (!this.plexConfigStatusEl) {
            console.debug('[PLEX_UI] updatePlexConfigStatus: plexConfigStatusEl not found');
            return;
        }
        this.plexConfigStatusEl.textContent = message;
        this.plexConfigStatusEl.style.color = message.includes('✓') ? 'var(--accent-primary)' : 'var(--text-secondary)';
    };
    App.prototype.updatePlexClearCredentialsButton = function () {
        return __awaiter(this, void 0, void 0, function () {
            var configResp, configData, _a, hasConfig, hasLibrary, showPlexControls, healthResp, healthData, _b, healthOk, library, libraryText, err_1;
            var _c, _d;
            return __generator(this, function (_e) {
                switch (_e.label) {
                    case 0:
                        if (!this.plexClearCredentialsButton) {
                            console.debug('[PLEX_UI] plexClearCredentialsButton not found in DOM');
                            return [2 /*return*/];
                        }
                        _e.label = 1;
                    case 1:
                        _e.trys.push([1, 13, , 14]);
                        return [4 /*yield*/, fetch('/api/plex/config', { cache: 'no-store' })];
                    case 2:
                        configResp = _e.sent();
                        if (!configResp.ok) return [3 /*break*/, 4];
                        return [4 /*yield*/, configResp.json()];
                    case 3:
                        _a = _e.sent();
                        return [3 /*break*/, 5];
                    case 4:
                        _a = { has_config: false };
                        _e.label = 5;
                    case 5:
                        configData = _a;
                        hasConfig = Boolean(configData && configData.has_config);
                        hasLibrary = Boolean(configData && configData.library_name);
                        // Show the Login button when Plex has not been configured yet.
                        if (this.plexLoginButton) {
                            this.plexLoginButton.disabled = false;
                            this.plexLoginButton.style.display = hasConfig ? 'none' : '';
                        }
                        showPlexControls = hasConfig && hasLibrary;
                        if (!showPlexControls) return [3 /*break*/, 7];
                        this.plexClearCredentialsButton.style.display = 'inline-block';
                        this.updatePlexPlaylistContainerVisibility(true);
                        return [4 /*yield*/, this.loadPlexUsers()];
                    case 6:
                        _e.sent();
                        return [3 /*break*/, 8];
                    case 7:
                        this.plexClearCredentialsButton.style.display = 'none';
                        this.updatePlexPlaylistContainerVisibility(false);
                        _e.label = 8;
                    case 8: return [4 /*yield*/, fetch('/api/plex/healthcheck', { cache: 'no-store' })];
                    case 9:
                        healthResp = _e.sent();
                        if (!healthResp.ok) return [3 /*break*/, 11];
                        return [4 /*yield*/, healthResp.json()];
                    case 10:
                        _b = _e.sent();
                        return [3 /*break*/, 12];
                    case 11:
                        _b = { ok: false };
                        _e.label = 12;
                    case 12:
                        healthData = _b;
                        healthOk = Boolean(healthData && healthData.ok);
                        if (this.plexConnectedStatusEl) {
                            if (healthOk && typeof healthData.server_name === 'string' && healthData.server_name.trim()) {
                                library = ((_d = (_c = this.plexLibraryNameSelect) === null || _c === void 0 ? void 0 : _c.value) === null || _d === void 0 ? void 0 : _d.trim()) || '';
                                libraryText = library ? " (library: ".concat(library, ")") : '';
                                this.plexConnectedStatusEl.textContent = "Connected to ".concat(healthData.server_name).concat(libraryText);
                                this.plexConnectedStatusEl.style.display = 'block';
                            }
                            else {
                                this.plexConnectedStatusEl.textContent = '';
                                this.plexConnectedStatusEl.style.display = 'none';
                            }
                        }
                        return [3 /*break*/, 14];
                    case 13:
                        err_1 = _e.sent();
                        console.debug('[PLEX_UI] updatePlexClearCredentialsButton error', err_1);
                        if (this.plexConnectedStatusEl) {
                            this.plexConnectedStatusEl.textContent = '';
                            this.plexConnectedStatusEl.style.display = 'none';
                        }
                        this.plexClearCredentialsButton.style.display = 'none';
                        this.updatePlexPlaylistContainerVisibility(false);
                        if (this.plexLoginButton) {
                            this.plexLoginButton.disabled = false;
                            this.plexLoginButton.style.display = '';
                        }
                        return [3 /*break*/, 14];
                    case 14: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.loadPlexUsers = function () {
        return __awaiter(this, void 0, void 0, function () {
            var response, data, users, placeholder, savedId_3, selectedSet_1, owner, ownerId_1, ownerOption, error_26;
            var _this = this;
            var _a, _b;
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        if (!this.plexUserSelect) {
                            return [2 /*return*/];
                        }
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, fetch('/api/plex/users', { cache: 'no-store' })];
                    case 2:
                        response = _c.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch Plex users');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _c.sent();
                        users = Array.isArray(data.users) ? data.users : [];
                        this.plexUserSelect.innerHTML = '';
                        placeholder = document.createElement('option');
                        placeholder.value = '';
                        placeholder.textContent = users.length ? 'Select a user...' : '(no users found)';
                        placeholder.disabled = users.length === 0;
                        this.plexUserSelect.appendChild(placeholder);
                        savedId_3 = window.localStorage.getItem('plexSelectedUserId') || '';
                        selectedSet_1 = false;
                        users.forEach(function (user) {
                            var _a, _b, _c, _d;
                            var id = String((_d = (_c = (_b = (_a = user.client_id) !== null && _a !== void 0 ? _a : user.id) !== null && _b !== void 0 ? _b : user.username) !== null && _c !== void 0 ? _c : user.title) !== null && _d !== void 0 ? _d : '');
                            var label = String(user.username || user.title || id);
                            var option = document.createElement('option');
                            option.value = id;
                            option.textContent = label;
                            _this.plexUserSelect.appendChild(option);
                            if (!selectedSet_1 && savedId_3 && id === savedId_3) {
                                option.selected = true;
                                selectedSet_1 = true;
                            }
                        });
                        if (!selectedSet_1 && users.length > 0) {
                            owner = users.find(function (u) { return u.is_owner; });
                            ownerId_1 = owner ? String((_b = (_a = owner.id) !== null && _a !== void 0 ? _a : owner.username) !== null && _b !== void 0 ? _b : '') : '';
                            if (ownerId_1) {
                                ownerOption = Array.from(this.plexUserSelect.options).find(function (opt) { return opt.value === ownerId_1; });
                                if (ownerOption) {
                                    ownerOption.selected = true;
                                    window.localStorage.setItem('plexSelectedUserId', ownerId_1);
                                }
                            }
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        error_26 = _c.sent();
                        console.warn('Failed to load Plex users:', error_26);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.updatePlexPlaylistContainerVisibility = function (show) {
        if (!this.plexPlaylistContainer)
            return;
        if (this.isPlexConfigured && show) {
            this.restorePlexPlaylistContainerToHome();
            this.plexPlaylistContainer.style.display = 'flex';
            void this.loadPlexPlaylists();
        }
        else {
            this.restorePlexPlaylistContainerToHome();
            this.plexPlaylistContainer.style.display = 'none';
        }
    };
    App.prototype.movePlexPlaylistContainerBeneathDownloadAll = function () {
        if (!this.plexPlaylistContainer)
            return;
        var buttonsContainer = this.resultsContainer.querySelector('.add-all-buttons-container');
        if (!buttonsContainer || !buttonsContainer.parentElement) {
            return;
        }
        var headerTop = buttonsContainer.parentElement;
        var header = headerTop.parentElement;
        if (header) {
            header.insertBefore(this.plexPlaylistContainer, headerTop.nextSibling);
        }
        else {
            headerTop.insertBefore(this.plexPlaylistContainer, buttonsContainer.nextSibling);
        }
        this.plexPlaylistContainer.style.padding = '0';
        this.plexPlaylistContainer.style.marginTop = '0.75rem';
    };
    App.prototype.restorePlexPlaylistContainerToHome = function () {
        if (!this.plexPlaylistContainer || !this.plexPlaylistContainerHomeParent)
            return;
        if (this.plexPlaylistContainer.parentElement !== this.plexPlaylistContainerHomeParent) {
            if (this.plexPlaylistContainerHomeNextSibling &&
                this.plexPlaylistContainerHomeNextSibling.parentNode === this.plexPlaylistContainerHomeParent) {
                this.plexPlaylistContainerHomeParent.insertBefore(this.plexPlaylistContainer, this.plexPlaylistContainerHomeNextSibling);
            }
            else {
                this.plexPlaylistContainerHomeParent.appendChild(this.plexPlaylistContainer);
            }
        }
        this.plexPlaylistContainer.style.padding = '1rem';
        this.plexPlaylistContainer.style.marginTop = '0';
    };
    App.prototype.populatePlexPlaylistOptions = function (playlists, showEmptyPlaceholder) {
        var _this = this;
        if (showEmptyPlaceholder === void 0) { showEmptyPlaceholder = true; }
        var currentInputValue = this.plexPlaylistNameInput.value;
        var currentMode = this.plexPlaylistNameInput.style.display === 'none' ? 'existing' : 'new';
        this.plexPlaylistOptions.innerHTML = '';
        var defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'No Playlist';
        this.plexPlaylistOptions.appendChild(defaultOption);
        if (playlists.length === 0 && showEmptyPlaceholder) {
            var emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '(no existing playlists found)';
            emptyOption.disabled = true;
            this.plexPlaylistOptions.appendChild(emptyOption);
        }
        playlists.forEach(function (playlistName) {
            var option = document.createElement('option');
            option.value = playlistName;
            option.textContent = playlistName;
            _this.plexPlaylistOptions.appendChild(option);
        });
        var newOption = document.createElement('option');
        newOption.value = App.NEW_PLEX_PLAYLIST_OPTION;
        newOption.textContent = 'New playlist...';
        this.plexPlaylistOptions.appendChild(newOption);
        this.plexPlaylistNameInput.value = currentInputValue;
        if (currentMode === 'new') {
            this.setPlexPlaylistMode('new');
            this.plexPlaylistOptions.value = App.NEW_PLEX_PLAYLIST_OPTION;
            return;
        }
        var hasMatchingExisting = playlists.includes(currentInputValue);
        this.plexPlaylistOptions.value = hasMatchingExisting ? currentInputValue : '';
        this.setPlexPlaylistMode('existing');
    };
    App.prototype.setPlexPlaylistMode = function (mode) {
        if (mode === 'new') {
            this.plexPlaylistOptions.style.display = 'none';
            this.plexPlaylistNameInput.style.display = 'block';
            this.plexPlaylistBackButton.style.display = 'inline-flex';
            return;
        }
        this.plexPlaylistOptions.style.display = 'block';
        this.plexPlaylistNameInput.style.display = 'none';
        this.plexPlaylistBackButton.style.display = 'none';
    };
    App.prototype.getSelectedPlexUserId = function () {
        var stored = window.localStorage.getItem('plexSelectedUserId');
        if (stored && stored.trim()) {
            return stored.trim();
        }
        return null;
    };
    App.prototype.loadPlexPlaylists = function () {
        return __awaiter(this, void 0, void 0, function () {
            var userId, query, response, data, playlists, error_27;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (!this.isPlexConfigured) {
                            this.populatePlexPlaylistOptions([]);
                            return [2 /*return*/];
                        }
                        userId = this.getSelectedPlexUserId();
                        query = userId ? "?user_id=".concat(encodeURIComponent(userId)) : '';
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, fetch("/api/plex/playlists".concat(query), { cache: 'no-store' })];
                    case 2:
                        response = _a.sent();
                        if (!response.ok) {
                            this.populatePlexPlaylistOptions([], false);
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _a.sent();
                        playlists = Array.isArray(data.playlists) ? data.playlists : [];
                        this.populatePlexPlaylistOptions(playlists);
                        return [3 /*break*/, 5];
                    case 4:
                        error_27 = _a.sent();
                        console.warn('Failed to load Plex playlists.', error_27);
                        this.populatePlexPlaylistOptions([], false);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.updateEndpointStatus = function () {
        return __awaiter(this, void 0, void 0, function () {
            var response, data, error_28;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 3, , 4]);
                        return [4 /*yield*/, fetch('/api/endpoints/status')];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch status');
                        }
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        this.displayEndpointStatus(data);
                        return [3 /*break*/, 4];
                    case 3:
                        error_28 = _a.sent();
                        console.error('Error fetching endpoint status:', error_28);
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.displayEndpointStatus = function (data) {
        // Update button
        var statusCount = document.querySelector('.status-count');
        if (statusCount) {
            statusCount.textContent = "".concat(data.summary.online, "/").concat(data.summary.total);
        }
        // Update summary
        var totalCount = document.getElementById('totalCount');
        var onlineCount = document.getElementById('onlineCount');
        var offlineCount = document.getElementById('offlineCount');
        if (totalCount)
            totalCount.textContent = data.summary.total.toString();
        if (onlineCount)
            onlineCount.textContent = data.summary.online.toString();
        if (offlineCount)
            offlineCount.textContent = data.summary.offline.toString();
        var rateLimit = data.mirrorRateLimitStatus;
        var safeRateLabel = rateLimit
            ? "".concat(rateLimit.safe_rpm.toFixed(2), " RPM (").concat(rateLimit.safe_rps.toFixed(2), " RPS)")
            : 'Unknown';
        var rateLimitState = !rateLimit
            ? 'Unknown'
            : rateLimit.safe_interval >= 30 || rateLimit.error_rate_429 > 0.05
                ? 'Backoff active'
                : rateLimit.safe_interval > 0.5 || rateLimit.error_rate_429 > 0
                    ? 'Recovering'
                    : 'Normal';
        var rateLimit429Percent = rateLimit
            ? "".concat((rateLimit.error_rate_429 * 100).toFixed(2), "%")
            : 'Unknown';
        var currentIntervalLabel = rateLimit
            ? "".concat(rateLimit.safe_interval.toFixed(2), "s")
            : 'Unknown';
        // Update endpoint list
        if (!this.flyoutContent) {
            console.warn('Flyout content element not found');
            return;
        }
        var rateLimitSummary = rateLimit
            ? "\n                <div class=\"endpoint-item\">\n                    <div class=\"endpoint-header\">\n                        <span class=\"endpoint-name\">Mirror Rate Limiter</span>\n                        <div class=\"endpoint-status ".concat(rateLimitState === 'Normal' ? 'online' : 'offline', "\">\n                            <span class=\"status-indicator ").concat(rateLimitState === 'Normal' ? 'online' : 'offline', "\"></span>\n                            ").concat(rateLimitState, "\n                        </div>\n                    </div>\n                    <div class=\"endpoint-details\">\n                        <div class=\"endpoint-detail\">\n                            <span class=\"detail-label\">Current Interval</span>\n                            <span class=\"detail-value\">").concat(currentIntervalLabel, "</span>\n                        </div>\n                        <div class=\"endpoint-detail\">\n                            <span class=\"detail-label\">Current Safe Rate</span>\n                            <span class=\"detail-value\">").concat(safeRateLabel, "</span>\n                        </div>\n                        <div class=\"endpoint-detail\">\n                            <span class=\"detail-label\">429 Rate</span>\n                            <span class=\"detail-value\">").concat(rateLimit429Percent, "</span>\n                        </div>\n                        <div class=\"endpoint-detail\">\n                            <span class=\"detail-label\">Sample Size</span>\n                            <span class=\"detail-value\">").concat(rateLimit.sample_size, "</span>\n                        </div>\n                    </div>\n                </div>\n            ")
            : '';
        var endpointMarkup = data.endpoints.map(function (endpoint) {
            var url = atob(endpoint.encodedUrl);
            var statusClass = endpoint.online ? 'online' : 'offline';
            var statusText = endpoint.online ? 'Online' : 'Offline';
            var responseTime = endpoint.responseTime
                ? "".concat(endpoint.responseTime.toFixed(0), "ms")
                : 'N/A';
            var lastChecked = endpoint.lastChecked
                ? new Date(endpoint.lastChecked).toLocaleTimeString()
                : 'Never';
            return "\n                <div class=\"endpoint-item\">\n                    <div class=\"endpoint-header\">\n                        <span class=\"endpoint-name\">".concat(endpoint.name, "</span>\n                        <div class=\"endpoint-status ").concat(statusClass, "\">\n                            <span class=\"status-indicator ").concat(statusClass, "\"></span>\n                            ").concat(statusText, "\n                        </div>\n                    </div>\n                    <div class=\"endpoint-url\">").concat(url, "</div>\n                    <div class=\"endpoint-details\">\n                        <div class=\"endpoint-detail\">\n                            <span class=\"detail-label\">Response Time</span>\n                            <span class=\"detail-value response-time\">").concat(responseTime, "</span>\n                        </div>\n                        <div class=\"endpoint-detail\">\n                            <span class=\"detail-label\">Last Checked</span>\n                            <span class=\"detail-value\">").concat(lastChecked, "</span>\n                        </div>\n                        <div class=\"endpoint-detail\">\n                            <span class=\"detail-label\">Safe Rate</span>\n                            <span class=\"detail-value\">").concat(safeRateLabel, "</span>\n                        </div>\n                    </div>\n                </div>\n            ");
        }).join('');
        this.flyoutContent.innerHTML = "".concat(rateLimitSummary).concat(endpointMarkup);
    };
    App.prototype.updateSearchPlaceholder = function () {
        var searchType = this.searchTypeSelect.value;
        if (searchType === 'lastfm') {
            this.searchInput.placeholder = 'Enter Last.fm playlist URL...';
        }
        else if (searchType === 'youtube_music') {
            this.searchInput.placeholder = 'Enter YouTube Music playlist URL...';
        }
        else if (searchType === 'listenbrainz') {
            this.searchInput.placeholder = 'Enter ListenBrainz username...';
        }
        else if (searchType === 'a') {
            this.searchInput.placeholder = 'Search for artists...';
        }
        else if (searchType === 'al') {
            this.searchInput.placeholder = 'Search for albums...';
        }
        else if (searchType === 'p') {
            this.searchInput.placeholder = 'Search for playlists...';
        }
        else if (searchType === 'trackid') {
            this.searchInput.placeholder = 'Enter numeric Track ID...';
        }
        else {
            this.searchInput.placeholder = 'Search for tracks...';
        }
    };
    App.prototype.handleSearch = function () {
        return __awaiter(this, arguments, void 0, function (updateHistory) {
            var searchType, query, response, data, error_29;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        searchType = this.searchTypeSelect.value;
                        query = this.searchInput.value.trim();
                        if (!(searchType === 'listenbrainz')) return [3 /*break*/, 2];
                        // Handle ListenBrainz playlists without requiring query
                        return [4 /*yield*/, this.handleListenbrainzPlaylists(undefined, updateHistory)];
                    case 1:
                        // Handle ListenBrainz playlists without requiring query
                        _a.sent();
                        return [2 /*return*/];
                    case 2:
                        if (!query) {
                            this.displayMessage('Please enter a search query');
                            return [2 /*return*/];
                        }
                        if (searchType === 'trackid' && !/^[0-9]+$/.test(query)) {
                            this.displayMessage('Track ID must be a numeric value');
                            return [2 /*return*/];
                        }
                        if (!(searchType === 'lastfm')) return [3 /*break*/, 4];
                        // Handle Last.fm playlist with progressive search
                        return [4 /*yield*/, this.handleLastfmPlaylist(query, updateHistory)];
                    case 3:
                        // Handle Last.fm playlist with progressive search
                        _a.sent();
                        return [2 /*return*/];
                    case 4:
                        if (!(searchType === 'youtube_music')) return [3 /*break*/, 6];
                        // Handle YouTube Music playlist with progressive search
                        return [4 /*yield*/, this.handleYoutubeMusicPlaylist(query, updateHistory)];
                    case 5:
                        // Handle YouTube Music playlist with progressive search
                        _a.sent();
                        return [2 /*return*/];
                    case 6:
                        if (updateHistory) {
                            this.pushHistoryRoute({
                                view: 'search',
                                searchType: searchType,
                                query: query
                            });
                        }
                        this.currentExploreRoute = { view: 'search', searchType: searchType, query: query };
                        this.exploreSearchRoute = __assign({}, this.currentExploreRoute);
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        this.displayMessage('Searching...');
                        _a.label = 7;
                    case 7:
                        _a.trys.push([7, 10, , 11]);
                        return [4 /*yield*/, this.fetchWithRetry("/api/hifi/search?".concat(searchType, "=").concat(encodeURIComponent(query)))];
                    case 8:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Search failed');
                        }
                        return [4 /*yield*/, response.json()];
                    case 9:
                        data = _a.sent();
                        this.displayResults(data, query, searchType);
                        return [3 /*break*/, 11];
                    case 10:
                        error_29 = _a.sent();
                        this.displayMessage('Error performing search. Please try again.');
                        console.error('Search error:', error_29);
                        return [3 /*break*/, 11];
                    case 11: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleLastfmPlaylist = function (playlistUrl_1) {
        return __awaiter(this, arguments, void 0, function (playlistUrl, updateHistory) {
            var scrapeResponse, errorData, scrapeData, playlistName, tracks, totalTracks, resultsList, foundCount, matchedTracks, notFoundTracks, i, track, searchQuery, searchResponse, searchData, items, trackRow, error_30, resultsHeaderTop, buttonsContainer, addPlaylistBtn, addLibraryBtn, error_31;
            var _this = this;
            var _a, _b, _c;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        this.downloadAllScope = 'loose';
                        this.currentExploreRoute = { view: 'lastfm_playlist', playlistUrl: playlistUrl };
                        this.exploreLastfmPlaylistName = null;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'lastfm_playlist', playlistUrl: playlistUrl });
                        }
                        this.displayMessage('Scraping Last.fm playlist...');
                        _d.label = 1;
                    case 1:
                        _d.trys.push([1, 15, , 16]);
                        return [4 /*yield*/, fetch('/api/lastfm/playlist', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({ playlistUrl: playlistUrl }),
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        scrapeResponse = _d.sent();
                        if (!!scrapeResponse.ok) return [3 /*break*/, 4];
                        return [4 /*yield*/, scrapeResponse.json().catch(function () { return ({}); })];
                    case 3:
                        errorData = _d.sent();
                        throw new Error(errorData.error || 'Failed to scrape playlist');
                    case 4: return [4 /*yield*/, scrapeResponse.json()];
                    case 5:
                        scrapeData = _d.sent();
                        playlistName = scrapeData.playlistName || 'Last.fm Playlist';
                        this.exploreLastfmPlaylistName = playlistName;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        tracks = scrapeData.tracks || [];
                        totalTracks = tracks.length;
                        if (totalTracks === 0) {
                            this.displayMessage('No tracks found in playlist');
                            return [2 /*return*/];
                        }
                        this.updatePlexPlaylistContainerVisibility(true);
                        // Set up progress display with grid structure
                        this.resultsContainer.innerHTML = "\n                <div class=\"results-header\">\n                    <div class=\"results-header-top\">\n                        <h2>Last.fm Playlist - \"".concat(this.escapeHtml(playlistName), "\"</h2>\n                    </div>\n                </div>\n                <div class=\"results-list\">\n                    <div class=\"tracks-grid-wrapper\" data-view-mode=\"multi-album\">\n                        <div class=\"tracks-grid\">\n                            ").concat(this.formatTrackGridHeader(false, true, false), "\n                            <div id=\"lastfmResultsList\"></div>\n                        </div>\n                    </div>\n                </div>\n            ");
                        resultsList = document.getElementById('lastfmResultsList');
                        foundCount = 0;
                        matchedTracks = [];
                        notFoundTracks = [];
                        i = 0;
                        _d.label = 6;
                    case 6:
                        if (!(i < tracks.length)) return [3 /*break*/, 14];
                        track = tracks[i];
                        searchQuery = "".concat(track.name, " ").concat(track.artist);
                        _d.label = 7;
                    case 7:
                        _d.trys.push([7, 12, , 13]);
                        return [4 /*yield*/, fetch("/api/hifi/search?s=".concat(encodeURIComponent(searchQuery)), {
                                signal: (_b = this.pendingRequestController) === null || _b === void 0 ? void 0 : _b.signal
                            })];
                    case 8:
                        searchResponse = _d.sent();
                        if (!searchResponse.ok) return [3 /*break*/, 10];
                        return [4 /*yield*/, searchResponse.json()];
                    case 9:
                        searchData = _d.sent();
                        items = ((_c = searchData.data) === null || _c === void 0 ? void 0 : _c.items) || [];
                        if (items.length > 0) {
                            trackRow = this.formatTrackGridRow(items[0], false, undefined, true, true);
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackRow);
                            }
                            matchedTracks.push(items[0]);
                            foundCount++;
                        }
                        else {
                            notFoundTracks.push({
                                artist: track.artist,
                                name: track.name
                            });
                        }
                        return [3 /*break*/, 11];
                    case 10:
                        notFoundTracks.push({
                            artist: track.artist,
                            name: track.name
                        });
                        _d.label = 11;
                    case 11: return [3 /*break*/, 13];
                    case 12:
                        error_30 = _d.sent();
                        console.error("Failed to search for ".concat(searchQuery, ":"), error_30);
                        notFoundTracks.push({
                            artist: track.artist,
                            name: track.name
                        });
                        return [3 /*break*/, 13];
                    case 13:
                        i++;
                        return [3 /*break*/, 6];
                    case 14:
                        resultsHeaderTop = document.querySelector('.results-header-top');
                        if (resultsHeaderTop) {
                            buttonsContainer = document.createElement('div');
                            buttonsContainer.className = 'add-all-buttons-container';
                            addPlaylistBtn = document.createElement('button');
                            addPlaylistBtn.id = 'addAllPlaylistBtn';
                            addPlaylistBtn.className = 'add-all-btn';
                            addPlaylistBtn.title = 'Add all tracks to a playlist';
                            addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
                            addPlaylistBtn.addEventListener('click', function () { return _this.addAllToPlaylist(); });
                            buttonsContainer.appendChild(addPlaylistBtn);
                            addLibraryBtn = document.createElement('button');
                            addLibraryBtn.id = 'addAllLibraryBtn';
                            addLibraryBtn.className = 'add-all-btn';
                            addLibraryBtn.title = 'Add all tracks to library';
                            addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
                            addLibraryBtn.addEventListener('click', function () { return _this.addAllToLibrary(); });
                            buttonsContainer.appendChild(addLibraryBtn);
                            resultsHeaderTop.appendChild(buttonsContainer);
                            this.movePlexPlaylistContainerBeneathDownloadAll();
                        }
                        if (matchedTracks.length > 0) {
                            void this.annotateTrackCardsWithPlexStatus(matchedTracks);
                        }
                        return [3 /*break*/, 16];
                    case 15:
                        error_31 = _d.sent();
                        this.displayMessage("Error: ".concat(error_31 instanceof Error ? error_31.message : 'Failed to process Last.fm playlist'));
                        console.error('Last.fm playlist error:', error_31);
                        return [3 /*break*/, 16];
                    case 16: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleYoutubeMusicPlaylist = function (playlistUrl_1) {
        return __awaiter(this, arguments, void 0, function (playlistUrl, updateHistory) {
            var scrapeResponse, errorData, scrapeData, playlistName, tracks, totalTracks, resultsList, foundCount, matchedTracks, notFoundTracks, i, track, searchQuery, searchResponse, searchData, items, trackRow, error_32, resultsHeaderTop, buttonsContainer, addPlaylistBtn, addLibraryBtn, error_33;
            var _this = this;
            var _a, _b, _c;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        this.downloadAllScope = 'loose';
                        this.currentExploreRoute = { view: 'youtube_music_playlist', playlistUrl: playlistUrl };
                        this.exploreYoutubePlaylistName = null;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'youtube_music_playlist', playlistUrl: playlistUrl });
                        }
                        this.displayMessage('Loading YouTube Music playlist...');
                        _d.label = 1;
                    case 1:
                        _d.trys.push([1, 15, , 16]);
                        return [4 /*yield*/, fetch('/api/youtube_music/playlist', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({ playlistUrl: playlistUrl }),
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        scrapeResponse = _d.sent();
                        if (!!scrapeResponse.ok) return [3 /*break*/, 4];
                        return [4 /*yield*/, scrapeResponse.json().catch(function () { return ({}); })];
                    case 3:
                        errorData = _d.sent();
                        throw new Error(errorData.error || 'Failed to load playlist');
                    case 4: return [4 /*yield*/, scrapeResponse.json()];
                    case 5:
                        scrapeData = _d.sent();
                        playlistName = scrapeData.playlistName || 'YouTube Music Playlist';
                        this.exploreYoutubePlaylistName = playlistName;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        tracks = scrapeData.tracks || [];
                        totalTracks = tracks.length;
                        if (totalTracks === 0) {
                            this.displayMessage('No tracks found in playlist');
                            return [2 /*return*/];
                        }
                        this.updatePlexPlaylistContainerVisibility(true);
                        this.resultsContainer.innerHTML = "\n                <div class=\"results-header\">\n                    <div class=\"results-header-top\">\n                        <h2>YouTube Music Playlist - \"".concat(this.escapeHtml(playlistName), "\"</h2>\n                    </div>\n                </div>\n                <div class=\"results-list\">\n                    <div class=\"tracks-grid-wrapper\" data-view-mode=\"multi-album\">\n                        <div class=\"tracks-grid\">\n                            ").concat(this.formatTrackGridHeader(false, true, false), "\n                            <div id=\"lastfmResultsList\"></div>\n                        </div>\n                    </div>\n                </div>\n            ");
                        resultsList = document.getElementById('lastfmResultsList');
                        foundCount = 0;
                        matchedTracks = [];
                        notFoundTracks = [];
                        i = 0;
                        _d.label = 6;
                    case 6:
                        if (!(i < tracks.length)) return [3 /*break*/, 14];
                        track = tracks[i];
                        searchQuery = "".concat(track.name, " ").concat(track.artist);
                        _d.label = 7;
                    case 7:
                        _d.trys.push([7, 12, , 13]);
                        return [4 /*yield*/, fetch("/api/hifi/search?s=".concat(encodeURIComponent(searchQuery)), {
                                signal: (_b = this.pendingRequestController) === null || _b === void 0 ? void 0 : _b.signal
                            })];
                    case 8:
                        searchResponse = _d.sent();
                        if (!searchResponse.ok) return [3 /*break*/, 10];
                        return [4 /*yield*/, searchResponse.json()];
                    case 9:
                        searchData = _d.sent();
                        items = ((_c = searchData.data) === null || _c === void 0 ? void 0 : _c.items) || [];
                        if (items.length > 0) {
                            trackRow = this.formatTrackGridRow(items[0], false, undefined, true, true);
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackRow);
                            }
                            matchedTracks.push(items[0]);
                            foundCount++;
                        }
                        else {
                            notFoundTracks.push({
                                artist: track.artist,
                                name: track.name
                            });
                        }
                        return [3 /*break*/, 11];
                    case 10:
                        notFoundTracks.push({
                            artist: track.artist,
                            name: track.name
                        });
                        _d.label = 11;
                    case 11: return [3 /*break*/, 13];
                    case 12:
                        error_32 = _d.sent();
                        console.error("Failed to search for ".concat(searchQuery, ":"), error_32);
                        notFoundTracks.push({
                            artist: track.artist,
                            name: track.name
                        });
                        return [3 /*break*/, 13];
                    case 13:
                        i++;
                        return [3 /*break*/, 6];
                    case 14:
                        resultsHeaderTop = document.querySelector('.results-header-top');
                        if (resultsHeaderTop) {
                            buttonsContainer = document.createElement('div');
                            buttonsContainer.className = 'add-all-buttons-container';
                            addPlaylistBtn = document.createElement('button');
                            addPlaylistBtn.id = 'addAllPlaylistBtn';
                            addPlaylistBtn.className = 'add-all-btn';
                            addPlaylistBtn.title = 'Add all tracks to a playlist';
                            addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
                            addPlaylistBtn.addEventListener('click', function () { return _this.addAllToPlaylist(); });
                            buttonsContainer.appendChild(addPlaylistBtn);
                            addLibraryBtn = document.createElement('button');
                            addLibraryBtn.id = 'addAllLibraryBtn';
                            addLibraryBtn.className = 'add-all-btn';
                            addLibraryBtn.title = 'Add all tracks to library';
                            addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
                            addLibraryBtn.addEventListener('click', function () { return _this.addAllToLibrary(); });
                            buttonsContainer.appendChild(addLibraryBtn);
                            resultsHeaderTop.appendChild(buttonsContainer);
                            this.movePlexPlaylistContainerBeneathDownloadAll();
                        }
                        if (matchedTracks.length > 0) {
                            void this.annotateTrackCardsWithPlexStatus(matchedTracks);
                        }
                        return [3 /*break*/, 16];
                    case 15:
                        error_33 = _d.sent();
                        this.displayMessage("Error: ".concat(error_33 instanceof Error ? error_33.message : 'Failed to process YouTube Music playlist'));
                        console.error('YouTube Music playlist error:', error_33);
                        return [3 /*break*/, 16];
                    case 16: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleListenbrainzPlaylists = function (usernameOverride_1) {
        return __awaiter(this, arguments, void 0, function (usernameOverride, updateHistory) {
            var username, response, errorData, data, playlistsData, playlists, error_34;
            var _this = this;
            var _a;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        username = (usernameOverride !== null && usernameOverride !== void 0 ? usernameOverride : this.searchInput.value).trim();
                        if (!username) {
                            this.displayMessage('Please enter ListenBrainz username');
                            return [2 /*return*/];
                        }
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'listenbrainz_playlists', username: username });
                        }
                        this.currentExploreRoute = { view: 'listenbrainz_playlists', username: username };
                        this.listenbrainzCurrentUsername = username;
                        this.listenbrainzCurrentPlaylist = null;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        this.displayMessage('Loading ListenBrainz playlists...');
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 6, , 7]);
                        return [4 /*yield*/, fetch("/api/listenbrainz/playlists?username=".concat(encodeURIComponent(username)), {
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _b.sent();
                        if (!!response.ok) return [3 /*break*/, 4];
                        return [4 /*yield*/, response.json().catch(function () { return ({ error: 'Failed to fetch playlists' }); })];
                    case 3:
                        errorData = _b.sent();
                        throw new Error(errorData.error || 'Failed to fetch ListenBrainz playlists');
                    case 4: return [4 /*yield*/, response.json()];
                    case 5:
                        data = _b.sent();
                        playlistsData = data.playlists || [];
                        if (playlistsData.length === 0) {
                            this.displayMessage('No recommended playlists found on ListenBrainz');
                            return [2 /*return*/];
                        }
                        playlists = playlistsData
                            .map(function (item) { return item.playlist; })
                            .filter(function (playlist) { return playlist && playlist.title; });
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        this.resultsContainer.innerHTML = "\n                <div class=\"results-header\">\n                    <h2>ListenBrainz Playlists (".concat(playlists.length, ")</h2>\n                </div>\n                <div class=\"results-list\">\n                    ").concat(playlists.map(function (playlist) { return _this.formatPlaylistCard(playlist); }).join(''), "\n                </div>\n            ");
                        return [3 /*break*/, 7];
                    case 6:
                        error_34 = _b.sent();
                        this.displayMessage("Error: ".concat(error_34 instanceof Error ? error_34.message : 'Failed to load ListenBrainz playlists'));
                        console.error('ListenBrainz playlists error:', error_34);
                        return [3 /*break*/, 7];
                    case 7: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.formatPlaylistCard = function (playlist) {
        var _a, _b;
        var title = this.escapeHtml(playlist.title || 'Unknown');
        var creator = this.escapeHtml(playlist.creator || 'Unknown');
        var annotation = this.escapeHtml(playlist.annotation || '');
        // Extract public status from extension
        var isPublic = ((_b = (_a = playlist.extension) === null || _a === void 0 ? void 0 : _a['https://musicbrainz.org/doc/jspf#playlist']) === null || _b === void 0 ? void 0 : _b.public) || false;
        // Extract identifier (which is the full URL)
        var playlistId = playlist.identifier ? playlist.identifier : '';
        return "\n            <div class=\"playlist-card\" data-playlist-id=\"".concat(this.escapeHtml(playlistId), "\">\n                <div class=\"playlist-info\">\n                    <h3 class=\"playlist-title\">").concat(title, "</h3>\n                    <p class=\"playlist-creator\">by ").concat(creator, "</p>\n                    ").concat(annotation ? "<p class=\"playlist-description\">".concat(annotation, "</p>") : '', "\n                    ").concat(isPublic ? '<span class="playlist-badge">Public</span>' : '', "\n                </div>\n            </div>\n        ");
    };
    App.prototype.fetchListenbrainzPlaylistTracks = function (playlistId_1) {
        return __awaiter(this, arguments, void 0, function (playlistId, updateHistory, usernameOverride) {
            var username, mbidMatch, playlistMbid, response, errorData, data, playlist, tracks, playlistTitle, playlistCreator, resultsList, foundCount, matchedTracks, notFoundTracks, i, lbTrack, artists, searchQuery, searchResponse, searchData, items, trackRow, error_35, resultsHeaderTop, buttonsContainer, addPlaylistBtn, addLibraryBtn, error_36;
            var _this = this;
            var _a, _b, _c;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_d) {
                switch (_d.label) {
                    case 0:
                        this.downloadAllScope = 'loose';
                        username = (usernameOverride || this.listenbrainzCurrentUsername || '').trim();
                        if (username) {
                            this.listenbrainzCurrentUsername = username;
                        }
                        this.currentExploreRoute = { view: 'listenbrainz_playlist_tracks', playlistId: playlistId, username: this.listenbrainzCurrentUsername || undefined };
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'listenbrainz_playlist_tracks', playlistId: playlistId, username: this.listenbrainzCurrentUsername || undefined });
                        }
                        this.stopPlayback();
                        this.displayMessage('Loading ListenBrainz playlist tracks...');
                        _d.label = 1;
                    case 1:
                        _d.trys.push([1, 15, , 16]);
                        mbidMatch = playlistId.match(/playlist\/([a-f0-9-]+)$/i);
                        if (!mbidMatch || !mbidMatch[1]) {
                            throw new Error('Invalid playlist identifier format');
                        }
                        playlistMbid = mbidMatch[1];
                        return [4 /*yield*/, fetch("/api/listenbrainz/playlist/".concat(encodeURIComponent(playlistMbid)), {
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _d.sent();
                        if (!!response.ok) return [3 /*break*/, 4];
                        return [4 /*yield*/, response.json().catch(function () { return ({ error: 'Failed to fetch playlist' }); })];
                    case 3:
                        errorData = _d.sent();
                        throw new Error(errorData.error || 'Failed to fetch ListenBrainz playlist');
                    case 4: return [4 /*yield*/, response.json()];
                    case 5:
                        data = _d.sent();
                        playlist = data.playlist;
                        if (!playlist) {
                            this.displayMessage('No playlist data found');
                            return [2 /*return*/];
                        }
                        tracks = playlist.track || [];
                        if (tracks.length === 0) {
                            this.displayMessage('No tracks found in this playlist');
                            return [2 /*return*/];
                        }
                        this.updatePlexPlaylistContainerVisibility(true);
                        playlistTitle = playlist.title || 'Untitled Playlist';
                        playlistCreator = playlist.creator || 'Unknown';
                        this.listenbrainzCurrentPlaylist = { id: playlistId, title: playlistTitle };
                        this.explorePlaylistTitle = playlistTitle;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        // Set up initial display with progress bar for searching
                        this.resultsContainer.innerHTML = "\n                <div class=\"results-header\">\n                    <div class=\"results-header-top\">\n                        <h2>".concat(this.escapeHtml(playlistTitle), "</h2>\n                        <p class=\"playlist-creator-display\">by ").concat(this.escapeHtml(playlistCreator), "</p>\n                    </div>\n                </div>\n                <div class=\"results-list\">\n                    <div class=\"tracks-grid-wrapper\" data-view-mode=\"multi-album\">\n                        <div class=\"tracks-grid\">\n                            ").concat(this.formatTrackGridHeader(false, true, false), "\n                            <div id=\"listenbrainzResultsList\"></div>\n                        </div>\n                    </div>\n                </div>\n            ");
                        resultsList = document.getElementById('listenbrainzResultsList');
                        foundCount = 0;
                        matchedTracks = [];
                        notFoundTracks = [];
                        i = 0;
                        _d.label = 6;
                    case 6:
                        if (!(i < tracks.length)) return [3 /*break*/, 14];
                        lbTrack = tracks[i];
                        artists = lbTrack.creator || 'Unknown';
                        searchQuery = "".concat(lbTrack.title, " ").concat(artists);
                        _d.label = 7;
                    case 7:
                        _d.trys.push([7, 12, , 13]);
                        return [4 /*yield*/, fetch("/api/hifi/search?s=".concat(encodeURIComponent(searchQuery)), {
                                signal: (_b = this.pendingRequestController) === null || _b === void 0 ? void 0 : _b.signal
                            })];
                    case 8:
                        searchResponse = _d.sent();
                        if (!searchResponse.ok) return [3 /*break*/, 10];
                        return [4 /*yield*/, searchResponse.json()];
                    case 9:
                        searchData = _d.sent();
                        items = ((_c = searchData.data) === null || _c === void 0 ? void 0 : _c.items) || [];
                        if (items.length > 0) {
                            trackRow = this.formatTrackGridRow(items[0], false, undefined, true, true);
                            if (resultsList) {
                                resultsList.insertAdjacentHTML('beforeend', trackRow);
                            }
                            matchedTracks.push(items[0]);
                            foundCount++;
                        }
                        else {
                            notFoundTracks.push({
                                artist: artists,
                                name: lbTrack.title || 'Unknown'
                            });
                        }
                        return [3 /*break*/, 11];
                    case 10:
                        notFoundTracks.push({
                            artist: artists,
                            name: lbTrack.title || 'Unknown'
                        });
                        _d.label = 11;
                    case 11: return [3 /*break*/, 13];
                    case 12:
                        error_35 = _d.sent();
                        console.error("Failed to search for ".concat(searchQuery, ":"), error_35);
                        notFoundTracks.push({
                            artist: artists,
                            name: lbTrack.title || 'Unknown'
                        });
                        return [3 /*break*/, 13];
                    case 13:
                        i++;
                        return [3 /*break*/, 6];
                    case 14:
                        resultsHeaderTop = document.querySelector('.results-header-top');
                        if (resultsHeaderTop) {
                            buttonsContainer = document.createElement('div');
                            buttonsContainer.className = 'add-all-buttons-container';
                            addPlaylistBtn = document.createElement('button');
                            addPlaylistBtn.id = 'addAllPlaylistBtn';
                            addPlaylistBtn.className = 'add-all-btn';
                            addPlaylistBtn.title = 'Add all tracks to a playlist';
                            addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
                            addPlaylistBtn.addEventListener('click', function () { return _this.addAllToPlaylist(); });
                            buttonsContainer.appendChild(addPlaylistBtn);
                            addLibraryBtn = document.createElement('button');
                            addLibraryBtn.id = 'addAllLibraryBtn';
                            addLibraryBtn.className = 'add-all-btn';
                            addLibraryBtn.title = 'Add all tracks to library';
                            addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
                            addLibraryBtn.addEventListener('click', function () { return _this.addAllToLibrary(); });
                            buttonsContainer.appendChild(addLibraryBtn);
                            resultsHeaderTop.appendChild(buttonsContainer);
                            this.movePlexPlaylistContainerBeneathDownloadAll();
                        }
                        if (matchedTracks.length > 0) {
                            void this.annotateTrackCardsWithPlexStatus(matchedTracks);
                        }
                        return [3 /*break*/, 16];
                    case 15:
                        error_36 = _d.sent();
                        this.displayMessage("Error: ".concat(error_36 instanceof Error ? error_36.message : 'Failed to load ListenBrainz playlist'));
                        console.error('ListenBrainz playlist error:', error_36);
                        return [3 /*break*/, 16];
                    case 16: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.convertListenbrainzTrackToTrack = function (lbTrack) {
        // ListenBrainz track format from JSPF
        // Example: { identifier: "https://musicbrainz.org/track/...", title: "...", creator: "...", duration: ... }
        if (!lbTrack.title) {
            return null;
        }
        return {
            id: Math.random() * 1000000, // Generate a temporary ID since ListenBrainz doesn't provide numeric IDs
            title: lbTrack.title || 'Unknown',
            duration: lbTrack.duration ? Math.floor(lbTrack.duration / 1000) : undefined,
            artists: lbTrack.creator
                ? [{ id: 0, name: lbTrack.creator }]
                : [],
            artist: lbTrack.creator
                ? { id: 0, name: lbTrack.creator }
                : undefined,
            album: undefined,
            quality: undefined,
            audioQuality: undefined,
            cover: undefined,
            trackNumber: undefined
        };
    };
    App.prototype.displayResults = function (data, query, searchType) {
        var _this = this;
        var _a, _b, _c, _d, _e, _f, _g, _h;
        this.downloadAllScope = 'loose';
        this.currentExploreRoute = { view: 'search', searchType: searchType, query: query };
        this.exploreSearchRoute = __assign({}, this.currentExploreRoute);
        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
        this.stopPlayback();
        this.updatePlexPlaylistContainerVisibility(true);
        if (data.error) {
            this.displayMessage("Error: ".concat(data.error).concat(data.details ? ' - ' + data.details : ''));
            return;
        }
        // Extract items based on search type
        var items = [];
        if (searchType === 'al') {
            items = ((_b = (_a = data.data) === null || _a === void 0 ? void 0 : _a.albums) === null || _b === void 0 ? void 0 : _b.items) || [];
        }
        else if (searchType === 'a') {
            items = ((_d = (_c = data.data) === null || _c === void 0 ? void 0 : _c.artists) === null || _d === void 0 ? void 0 : _d.items) || [];
        }
        else if (searchType === 'p') {
            items = ((_f = (_e = data.data) === null || _e === void 0 ? void 0 : _e.playlists) === null || _f === void 0 ? void 0 : _f.items) || ((_g = data.data) === null || _g === void 0 ? void 0 : _g.items) || [];
        }
        else {
            items = ((_h = data.data) === null || _h === void 0 ? void 0 : _h.items) || [];
        }
        if (items.length === 0) {
            this.displayMessage("No results found for \"".concat(query, "\"").concat(data.proxied_via ? ' (via ' + data.proxied_via + ')' : ''));
            return;
        }
        // Display results with proxy info
        var searchTypeName = searchType === 's' ? 'Tracks' :
            searchType === 'a' ? 'Artists' :
                searchType === 'al' ? 'Albums' :
                    searchType === 'p' ? 'Playlists' :
                        searchType === 'trackid' ? 'Track ID' :
                            'Results';
        this.resultsContainer.innerHTML = "\n            <div class=\"results-header\">\n                <h2>".concat(searchTypeName, " - \"").concat(this.escapeHtml(query), "\"</h2>\n                ").concat(data.proxied_via ? "<p class=\"proxy-info\">Proxied via: <span class=\"proxy-name\">".concat(data.proxied_via, "</span></p>") : '', "\n            </div>\n            ").concat(searchType === 'al'
            ? this.formatAlbumsGrid(items)
            : searchType === 's' || searchType === 'trackid'
                ? this.formatTracksGrid(items)
                : "<div class=\"results-list".concat(searchType === 'a' ? ' artist-results' : '', "\">\n                    ").concat(items.map(function (item) {
                    if (searchType === 'a')
                        return _this.formatArtistCard(item);
                    if (searchType === 'p')
                        return _this.formatSearchPlaylistCard(item);
                    return _this.formatTrackCard(item);
                }).join(''), "\n                </div>"), "\n        ");
        if (searchType === 's' || searchType === 'trackid') {
            void this.annotateTrackCardsWithPlexStatus(items);
        }
        else if (searchType === 'al') {
            void this.annotateAlbumGridsWithPlexStatus(items);
        }
        else if (searchType === 'a') {
            void this.annotateArtistCardsWithPlexStatus(items);
        }
    };
    App.prototype.lookupStoredMatches = function (trackIds, albumIds, artistIds, signal) {
        return __awaiter(this, void 0, void 0, function () {
            var normalizedTrackIds, normalizedAlbumIds, normalizedArtistIds, response;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        normalizedTrackIds = trackIds
                            .map(function (trackId) { return String(trackId).trim(); })
                            .filter(Boolean);
                        normalizedAlbumIds = albumIds
                            .map(function (albumId) { return String(albumId).trim(); })
                            .filter(Boolean);
                        normalizedArtistIds = artistIds
                            .map(function (artistId) { return String(artistId).trim(); })
                            .filter(Boolean);
                        if (normalizedTrackIds.length === 0 && normalizedAlbumIds.length === 0 && normalizedArtistIds.length === 0) {
                            return [2 /*return*/, { tracks: [], albums: [], artists: [] }];
                        }
                        return [4 /*yield*/, fetch('/api/hifi/matches/lookup', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    track_ids: normalizedTrackIds,
                                    album_ids: normalizedAlbumIds,
                                    artist_ids: normalizedArtistIds
                                }),
                                signal: signal
                            })];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to look up stored matches');
                        }
                        return [4 /*yield*/, response.json()];
                    case 2: return [2 /*return*/, _a.sent()];
                }
            });
        });
    };
    App.prototype.isLowQualityPlexMatch = function (variants) {
        if (variants === void 0) { variants = []; }
        return Array.isArray(variants)
            && variants.length > 0
            && variants.every(function (variant) {
                return (variant.format === 'mp3' || variant.format === 'mpeg')
                    && typeof variant.bitrate === 'number'
                    && variant.bitrate <= 192;
            });
    };
    App.prototype.buildStoredMatchTooltip = function (matchStatus, confidence, variants, incomplete) {
        if (variants === void 0) { variants = []; }
        if (incomplete === void 0) { incomplete = false; }
        var heading = incomplete ? 'Exists in Plex (incomplete)' : 'Exists in Plex';
        if (!Array.isArray(variants) || variants.length === 0) {
            return heading;
        }
        var details = variants.map(function (variant) {
            var bitrate = typeof variant.bitrate === 'number' && Number.isFinite(variant.bitrate)
                ? " (".concat(variant.bitrate, " kbps)")
                : '';
            return variant.file_path
                ? "  ".concat(variant.file_path).concat(bitrate)
                : "  ".concat((variant.format || 'unknown').toUpperCase()).concat(bitrate);
        });
        return "".concat(heading, "\n").concat(details.join('\n'));
    };
    App.prototype.createPlexMatchChip = function (match, options) {
        var chip = document.createElement('span');
        var lowQuality = this.isLowQualityPlexMatch(match.variants || []);
        var incomplete = (options === null || options === void 0 ? void 0 : options.incomplete) === true;
        var classNames = ['plex-existing-chip'];
        if (options === null || options === void 0 ? void 0 : options.inActions) {
            classNames.push('plex-existing-chip--in-actions');
        }
        if (options === null || options === void 0 ? void 0 : options.bulk) {
            classNames.push('plex-existing-chip--bulk');
        }
        if (lowQuality) {
            classNames.push('plex-existing-chip--low-quality');
        }
        if (options === null || options === void 0 ? void 0 : options.hero) {
            classNames.push('plex-existing-chip--hero');
        }
        if (incomplete) {
            classNames.push('plex-existing-chip--incomplete');
        }
        chip.className = classNames.join(' ');
        var label = 'In Plex';
        if (lowQuality) {
            label += ' · low quality';
        }
        chip.textContent = label;
        chip.title = this.buildStoredMatchTooltip(match.match_status, match.confidence, match.variants || [], incomplete);
        return chip;
    };
    App.prototype.annotateTrackCardsWithPlexStatus = function (tracks) {
        return __awaiter(this, void 0, void 0, function () {
            var signal, trackIds, lookup, trackMatches, matchById, gridRows, cards, _i, cards_1, card, trackId, match, metadataEl, sep, error_37;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!Array.isArray(tracks) || tracks.length === 0) {
                            return [2 /*return*/];
                        }
                        signal = (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal;
                        trackIds = tracks.map(function (track) { return track.id; }).filter(function (trackId) { return Number.isFinite(trackId); });
                        if (trackIds.length === 0) {
                            return [2 /*return*/];
                        }
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 5, , 6]);
                        return [4 /*yield*/, this.lookupStoredMatches(trackIds, [], [], signal)];
                    case 2:
                        lookup = _b.sent();
                        trackMatches = Array.isArray(lookup.tracks) ? lookup.tracks : [];
                        matchById = new Map(trackMatches.map(function (match) { return [String(match.track_id), match]; }));
                        gridRows = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row'));
                        if (!(gridRows.length > 0)) return [3 /*break*/, 4];
                        return [4 /*yield*/, this.annotateGridRowsWithPlexStatus(gridRows, matchById)];
                    case 3:
                        _b.sent();
                        return [2 /*return*/];
                    case 4:
                        cards = Array.from(this.resultsContainer.querySelectorAll('.results-list .track-card'));
                        for (_i = 0, cards_1 = cards; _i < cards_1.length; _i++) {
                            card = cards_1[_i];
                            trackId = String(card.getAttribute('data-track-id') || '').trim();
                            match = matchById.get(trackId);
                            if (!match || !match.exists) {
                                continue;
                            }
                            metadataEl = card.querySelector('.track-metadata');
                            if (!metadataEl || metadataEl.querySelector('.plex-existing-chip')) {
                                continue;
                            }
                            if (metadataEl.children.length > 0) {
                                sep = document.createElement('span');
                                sep.className = 'plex-chip-separator';
                                sep.textContent = '•';
                                metadataEl.appendChild(sep);
                            }
                            metadataEl.appendChild(this.createPlexMatchChip(match));
                        }
                        return [3 /*break*/, 6];
                    case 5:
                        error_37 = _b.sent();
                        if (error_37 instanceof Error && error_37.name === 'AbortError') {
                            return [2 /*return*/];
                        }
                        console.warn('Failed to annotate Plex inventory matches.', error_37);
                        return [3 /*break*/, 6];
                    case 6: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.annotateGridRowsWithPlexStatus = function (gridRows, matchById) {
        return __awaiter(this, void 0, void 0, function () {
            var resolvedMatches, _i, gridRows_1, row, trackId, match, actionsCell, addLibraryBtn, allRowsInPlex;
            return __generator(this, function (_a) {
                resolvedMatches = [];
                for (_i = 0, gridRows_1 = gridRows; _i < gridRows_1.length; _i++) {
                    row = gridRows_1[_i];
                    trackId = String(row.getAttribute('data-track-id') || '').trim();
                    match = matchById.get(trackId);
                    if (!match || !match.exists) {
                        continue;
                    }
                    resolvedMatches.push(match);
                    row.setAttribute('data-plex-exists', 'true');
                    actionsCell = row.querySelector('.grid-col-actions');
                    addLibraryBtn = actionsCell === null || actionsCell === void 0 ? void 0 : actionsCell.querySelector('.grid-add-library-btn');
                    if (!actionsCell || !addLibraryBtn) {
                        continue;
                    }
                    addLibraryBtn.replaceWith(this.createPlexMatchChip(match, { inActions: true }));
                }
                allRowsInPlex = gridRows.length > 0 && resolvedMatches.length === gridRows.length;
                if (allRowsInPlex) {
                    this.replaceAddAllLibraryWithPlexBadge(resolvedMatches);
                }
                return [2 /*return*/];
            });
        });
    };
    App.prototype.annotateAlbumGridsWithPlexStatus = function (albums) {
        return __awaiter(this, void 0, void 0, function () {
            var signal, albumIds, lookup, albumMatches, matchById, gridRows, _i, gridRows_2, row, albumId, match, actionsCell, addLibraryBtn, error_38;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!Array.isArray(albums) || albums.length === 0) {
                            return [2 /*return*/];
                        }
                        signal = (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal;
                        albumIds = albums.map(function (album) { return album.id; }).filter(function (albumId) { return Number.isFinite(albumId); });
                        if (albumIds.length === 0) {
                            return [2 /*return*/];
                        }
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, this.lookupStoredMatches([], albumIds, [], signal)];
                    case 2:
                        lookup = _b.sent();
                        albumMatches = Array.isArray(lookup.albums) ? lookup.albums : [];
                        matchById = new Map(albumMatches.map(function (match) { return [String(match.album_id), match]; }));
                        gridRows = Array.from(this.resultsContainer.querySelectorAll('.albums-grid-row'));
                        for (_i = 0, gridRows_2 = gridRows; _i < gridRows_2.length; _i++) {
                            row = gridRows_2[_i];
                            albumId = String(row.getAttribute('data-album-id') || '').trim();
                            match = matchById.get(albumId);
                            if (!match || !match.exists) {
                                continue;
                            }
                            row.setAttribute('data-plex-exists', 'true');
                            actionsCell = row.querySelector('.grid-col-actions');
                            addLibraryBtn = actionsCell === null || actionsCell === void 0 ? void 0 : actionsCell.querySelector('.grid-add-library-btn');
                            if (!actionsCell || !addLibraryBtn) {
                                continue;
                            }
                            addLibraryBtn.replaceWith(this.createPlexMatchChip(match, { inActions: true, incomplete: !match.complete }));
                        }
                        return [3 /*break*/, 4];
                    case 3:
                        error_38 = _b.sent();
                        if (error_38 instanceof Error && error_38.name === 'AbortError') {
                            return [2 /*return*/];
                        }
                        console.warn('Failed to annotate album grid rows with Plex status.', error_38);
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.insertHeroPlexChip = function (container, match, options) {
        if (!container || !match || !match.exists) {
            return;
        }
        if (container.querySelector('.plex-existing-chip')) {
            return;
        }
        var chip = this.createPlexMatchChip(match, {
            inActions: options === null || options === void 0 ? void 0 : options.inActions,
            bulk: options === null || options === void 0 ? void 0 : options.bulk,
            incomplete: match.complete === false
        });
        var heading = container.querySelector('h1, .artist-hero-name, .album-title');
        if (heading) {
            heading.insertAdjacentElement('afterend', chip);
            return;
        }
        container.appendChild(chip);
    };
    App.prototype.annotateArtistCardsWithPlexStatus = function (artists) {
        return __awaiter(this, void 0, void 0, function () {
            var signal, artistIds, lookup, artistMatches, matchById, cards, _i, cards_1, card, artistId, match, nameEl, chip, error_39;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!Array.isArray(artists) || artists.length === 0) {
                            return [2 /*return*/];
                        }
                        signal = (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal;
                        artistIds = artists.map(function (artist) { return artist.id; }).filter(function (artistId) { return Number.isFinite(artistId); });
                        if (artistIds.length === 0) {
                            return [2 /*return*/];
                        }
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, this.lookupStoredMatches([], [], artistIds, signal)];
                    case 2:
                        lookup = _b.sent();
                        artistMatches = Array.isArray(lookup.artists) ? lookup.artists : [];
                        matchById = new Map(artistMatches.map(function (match) { return [String(match.artist_id), match]; }));
                        cards = Array.from(this.resultsContainer.querySelectorAll('.artist-card-compact'));
                        for (_i = 0, cards_1 = cards; _i < cards_1.length; _i++) {
                            card = cards_1[_i];
                            artistId = String(card.getAttribute('data-artist-id') || '').trim();
                            match = matchById.get(artistId);
                            if (!match || !match.exists || card.querySelector('.plex-existing-chip')) {
                                continue;
                            }
                            nameEl = card.querySelector('.artist-card-name');
                            if (!nameEl) {
                                continue;
                            }
                            chip = this.createPlexMatchChip(match, { inActions: true, incomplete: !match.complete });
                            nameEl.insertAdjacentElement('afterend', chip);
                        }
                        return [3 /*break*/, 5];
                    case 4:
                        error_39 = _b.sent();
                        if (error_39 instanceof Error && error_39.name === 'AbortError') {
                            return [2 /*return*/];
                        }
                        console.warn('Failed to annotate artist cards with Plex status.', error_39);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.annotateAlbumHeroWithPlexStatus = function (albumId) {
        return __awaiter(this, void 0, void 0, function () {
            var signal, lookup, albumMatch, container, error_40;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!Number.isFinite(albumId)) {
                            return [2 /*return*/];
                        }
                        signal = (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal;
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, this.lookupStoredMatches([], [albumId], [], signal)];
                    case 2:
                        lookup = _b.sent();
                        albumMatch = Array.isArray(lookup.albums) ? lookup.albums[0] : undefined;
                        if (!albumMatch || !albumMatch.exists) {
                            return [2 /*return*/];
                        }
                        container = document.querySelector('.album-actions');
                        this.insertHeroPlexChip(container, albumMatch, { inActions: true, bulk: true });
                        return [3 /*break*/, 5];
                    case 4:
                        error_40 = _b.sent();
                        if (error_40 instanceof Error && error_40.name === 'AbortError') {
                            return [2 /*return*/];
                        }
                        console.warn('Failed to annotate album hero with Plex status.', error_40);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.annotateArtistHeroWithPlexStatus = function (artistId) {
        return __awaiter(this, void 0, void 0, function () {
            var signal, lookup, artistMatch, container, error_41;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        if (!Number.isFinite(artistId)) {
                            return [2 /*return*/];
                        }
                        signal = (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal;
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, this.lookupStoredMatches([], [], [artistId], signal)];
                    case 2:
                        lookup = _b.sent();
                        artistMatch = Array.isArray(lookup.artists) ? lookup.artists[0] : undefined;
                        if (!artistMatch || !artistMatch.exists) {
                            return [2 /*return*/];
                        }
                        container = document.querySelector('.artist-actions');
                        this.insertHeroPlexChip(container, artistMatch, { inActions: true, bulk: true });
                        return [3 /*break*/, 5];
                    case 4:
                        error_41 = _b.sent();
                        if (error_41 instanceof Error && error_41.name === 'AbortError') {
                            return [2 /*return*/];
                        }
                        console.warn('Failed to annotate artist hero with Plex status.', error_41);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.replaceAddAllLibraryWithPlexBadge = function (matches) {
        var addAllLibraryBtn = document.getElementById('addAllLibraryBtn');
        if (!addAllLibraryBtn || !addAllLibraryBtn.parentElement) {
            return;
        }
        var albumActions = document.querySelector('.album-actions');
        if (albumActions === null || albumActions === void 0 ? void 0 : albumActions.querySelector('.plex-existing-chip')) {
            addAllLibraryBtn.remove();
            return;
        }
        var aggregateMatch = {
            exists: true,
            match_status: matches.every(function (match) { return String(match.match_status || '').toLowerCase() === 'confirmed'; }) ? 'confirmed' : 'proposed',
            confidence: matches.reduce(function (highest, match) { return Math.max(highest, typeof match.confidence === 'number' ? match.confidence : 0); }, 0),
            variants: matches.flatMap(function (match) { return match.variants || []; })
        };
        if (albumActions) {
            addAllLibraryBtn.remove();
            albumActions.appendChild(this.createPlexMatchChip(aggregateMatch, { inActions: true, bulk: true }));
            return;
        }
        addAllLibraryBtn.replaceWith(this.createPlexMatchChip(aggregateMatch, { inActions: true, bulk: true }));
    };
    App.prototype.formatSearchPlaylistCard = function (playlist) {
        var _a;
        var playlistId = this.escapeHtml(this.getPlaylistId(playlist));
        var playlistName = this.escapeHtml(playlist.title || 'Unknown Playlist');
        var playlistDescription = this.escapeHtml((playlist.description || '').trim());
        var trackTotal = (_a = playlist.numberOfTracks) !== null && _a !== void 0 ? _a : playlist.numberOfItems;
        var trackCount = typeof trackTotal === 'number'
            ? "".concat(trackTotal, " track").concat(trackTotal !== 1 ? 's' : '')
            : '';
        var quality = playlist.audioQuality || '';
        var qualityDisplay = this.formatQuality(quality);
        var coverImage = this.getPlaylistCoverUrl(playlist);
        return "\n            <div class=\"track-card album-card playlist-search-card clickable\" data-playlist-id=\"".concat(playlistId, "\" title=\"Click to view tracks\">\n                <div class=\"track-artwork\">\n                    ").concat(coverImage
            ? "<img src=\"".concat(coverImage, "\" alt=\"").concat(playlistName, "\" loading=\"lazy\">")
            : "<div class=\"track-artwork-placeholder\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                                <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"></rect>\n                                <path d=\"M9 9h6\"></path>\n                                <path d=\"M9 13h6\"></path>\n                                <path d=\"M9 17h4\"></path>\n                            </svg>\n                           </div>", "\n                </div>\n                <div class=\"track-info\">\n                    <div class=\"track-title\">").concat(playlistName, "</div>\n                    ").concat(playlistDescription ? "<div class=\"track-artist\"><span class=\"playlist-description-text\">".concat(playlistDescription, "</span></div>") : '', "\n                    <div class=\"track-metadata\">\n                        ").concat(trackCount ? "<span>".concat(trackCount, "</span>") : '', "\n                        ").concat(trackCount && qualityDisplay ? "<span>\u2022</span>" : '', "\n                        ").concat(qualityDisplay ? "<span>".concat(qualityDisplay, "</span>") : '', "\n                    </div>\n                </div>\n            </div>\n        ");
    };
    App.prototype.getPlaylistId = function (playlist) {
        if (typeof playlist.uuid === 'string' && playlist.uuid.trim()) {
            return playlist.uuid.trim();
        }
        if (typeof playlist.id === 'string' && playlist.id.trim()) {
            var normalized = this.normalizePlaylistId(playlist.id.trim());
            return normalized || playlist.id.trim();
        }
        if (typeof playlist.id === 'number' && Number.isFinite(playlist.id)) {
            return String(playlist.id);
        }
        if (typeof playlist.url === 'string' && playlist.url.trim()) {
            var normalized = this.normalizePlaylistId(playlist.url.trim());
            return normalized || playlist.url.trim();
        }
        return '';
    };
    App.prototype.getPlaylistAuthorName = function (playlist) {
        var _a, _b, _c;
        if (typeof playlist.creator === 'string' && playlist.creator.trim()) {
            return playlist.creator;
        }
        if (playlist.creator && typeof playlist.creator === 'object' && ((_a = playlist.creator.name) === null || _a === void 0 ? void 0 : _a.trim())) {
            return playlist.creator.name;
        }
        var promotedArtistName = (_c = (_b = playlist.promotedArtists) === null || _b === void 0 ? void 0 : _b.find(function (artist) { var _a; return (_a = artist === null || artist === void 0 ? void 0 : artist.name) === null || _a === void 0 ? void 0 : _a.trim(); })) === null || _c === void 0 ? void 0 : _c.name;
        if (promotedArtistName) {
            return promotedArtistName;
        }
        if (playlist.type === 'EDITORIAL') {
            return 'TIDAL';
        }
        return 'Unknown';
    };
    App.prototype.getAddAllPlaylistIconSvg = function () {
        return "\n            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\">\n                <g transform=\"translate(2,1)\">\n                    <path d=\"M5 0v10\"></path>\n                    <path d=\"M0 5h10\"></path>\n                </g>\n                <g transform=\"translate(8,7)\" opacity=\"0.7\">\n                    <path d=\"M5 0v10\"></path>\n                    <path d=\"M0 5h10\"></path>\n                </g>\n            </svg>\n        ";
    };
    App.prototype.getAddAllLibraryIconSvg = function () {
        return "\n            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\">\n                <rect x=\"2\" y=\"2\" width=\"14\" height=\"4\" rx=\"1\"></rect>\n                <path d=\"M3 6v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V6\"></path>\n                <rect x=\"6\" y=\"10\" width=\"14\" height=\"4\" rx=\"1\" opacity=\"0.6\"></rect>\n                <path d=\"M7 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5\" opacity=\"0.6\"></path>\n            </svg>\n        ";
    };
    App.prototype.setBulkActionButtonState = function (button, buttonType, state) {
        if (!button) {
            return;
        }
        button.classList.remove('queued', 'in-progress', 'completed', 'failed');
        if (state === 'loading') {
            button.disabled = true;
            button.classList.add('in-progress');
            button.innerHTML = this.getSpinnerIconSvg();
            return;
        }
        button.disabled = false;
        if (state === 'success') {
            button.classList.add('completed');
            button.innerHTML = this.getCheckmarkIconSvg();
            return;
        }
        if (state === 'failed') {
            button.classList.add('failed');
            button.innerHTML = this.getExclamationIconSvg();
            return;
        }
        button.innerHTML = buttonType === 'playlist'
            ? this.getAddAllPlaylistIconSvg()
            : this.getAddAllLibraryIconSvg();
    };
    App.prototype.getPlaylistCoverUrl = function (playlist) {
        var rawCover = playlist.customImageUrl || playlist.squareImage || playlist.image || playlist.cover || '';
        if (!rawCover) {
            return '';
        }
        return this.getHifiImageUrl(rawCover, 640);
    };
    App.prototype.normalizePlaylistId = function (value) {
        var trimmed = value.trim();
        var uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (uuidRegex.test(trimmed)) {
            return trimmed;
        }
        var match = trimmed.match(/playlist\/([0-9a-f-]{36})/i);
        if (match && match[1]) {
            return match[1];
        }
        return '';
    };
    App.prototype.fetchPlaylistTracks = function (playlistId_1) {
        return __awaiter(this, arguments, void 0, function (playlistId, updateHistory) {
            var normalizedPlaylistId_1, response, data, payload, playlistMeta, rawItems, tracks, playlistTitle, resultsHeaderTop, buttonsContainer, addPlaylistBtn, addLibraryBtn, error_39;
            var _this = this;
            var _a;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        this.downloadAllScope = 'loose';
                        this.currentExploreRoute = { view: 'playlist', playlistId: playlistId };
                        this.explorePlaylistTitle = null;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'playlist', playlistId: playlistId });
                        }
                        this.stopPlayback();
                        this.displayMessage('Loading playlist tracks...');
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        normalizedPlaylistId_1 = this.normalizePlaylistId(playlistId) || playlistId;
                        return [4 /*yield*/, fetch("/api/hifi/playlists/".concat(encodeURIComponent(normalizedPlaylistId_1)), {
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _b.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch playlist');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _b.sent();
                        if (data.error) {
                            this.displayMessage("Error: ".concat(data.error), function () { return _this.fetchPlaylistTracks(normalizedPlaylistId_1); });
                            return [2 /*return*/];
                        }
                        payload = (data === null || data === void 0 ? void 0 : data.data) && typeof data.data === 'object' ? data.data : data;
                        if (!payload || typeof payload !== 'object') {
                            this.displayMessage('No playlist data found');
                            return [2 /*return*/];
                        }
                        playlistMeta = payload.playlist && typeof payload.playlist === 'object'
                            ? payload.playlist
                            : payload;
                        rawItems = Array.isArray(payload.items)
                            ? payload.items
                            : Array.isArray(payload.tracks)
                                ? payload.tracks
                                : Array.isArray(playlistMeta.items)
                                    ? playlistMeta.items
                                    : Array.isArray(playlistMeta.tracks)
                                        ? playlistMeta.tracks
                                        : [];
                        tracks = rawItems
                            .map(function (item) {
                            if (item &&
                                typeof item === 'object' &&
                                item.item &&
                                typeof item.item === 'object' &&
                                'id' in item.item &&
                                'title' in item.item) {
                                return item.item;
                            }
                            if (item && typeof item === 'object' && 'id' in item && 'title' in item) {
                                return item;
                            }
                            return null;
                        })
                            .filter(function (track) { return track !== null; });
                        if (tracks.length === 0) {
                            this.displayMessage('No tracks found in this playlist');
                            return [2 /*return*/];
                        }
                        this.updatePlexPlaylistContainerVisibility(true);
                        playlistTitle = playlistMeta.title || playlistMeta.name || 'Playlist';
                        this.explorePlaylistTitle = playlistTitle;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        this.resultsContainer.innerHTML = "\n                <div class=\"results-header\">\n                    <div class=\"results-header-top\">\n                        <h2>".concat(this.escapeHtml(playlistTitle), "</h2>\n                    </div>\n                    ").concat(data.proxied_via ? "<p class=\"proxy-info\">Proxied via: <span class=\"proxy-name\">".concat(data.proxied_via, "</span></p>") : '', "\n                </div>\n                <div class=\"results-list\">\n                    ").concat(this.formatTracksGrid(tracks), "\n                </div>\n            ");
                        resultsHeaderTop = document.querySelector('.results-header-top');
                        if (resultsHeaderTop) {
                            buttonsContainer = document.createElement('div');
                            buttonsContainer.className = 'add-all-buttons-container';
                            addPlaylistBtn = document.createElement('button');
                            addPlaylistBtn.id = 'addAllPlaylistBtn';
                            addPlaylistBtn.className = 'add-all-btn';
                            addPlaylistBtn.title = 'Add all tracks to a playlist';
                            addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
                            addPlaylistBtn.addEventListener('click', function () { return _this.addAllToPlaylist(); });
                            buttonsContainer.appendChild(addPlaylistBtn);
                            addLibraryBtn = document.createElement('button');
                            addLibraryBtn.id = 'addAllLibraryBtn';
                            addLibraryBtn.className = 'add-all-btn';
                            addLibraryBtn.title = 'Add all tracks to library';
                            addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
                            addLibraryBtn.addEventListener('click', function () { return _this.addAllToLibrary(); });
                            buttonsContainer.appendChild(addLibraryBtn);
                            resultsHeaderTop.appendChild(buttonsContainer);
                            this.movePlexPlaylistContainerBeneathDownloadAll();
                        }
                        void this.annotateTrackCardsWithPlexStatus(tracks);
                        return [3 /*break*/, 5];
                    case 4:
                        error_39 = _b.sent();
                        this.displayMessage('Error loading playlist tracks. Please try again.', function () { return _this.fetchPlaylistTracks(playlistId); });
                        console.error('Playlist fetch error:', error_39);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.formatTrackCard = function (track, showTrackNumber, numberOfVolumes) {
        var _a, _b, _c, _d, _e, _f, _g;
        if (showTrackNumber === void 0) { showTrackNumber = false; }
        // Get artist names and IDs
        var artistNames = track.artists && track.artists.length > 0
            ? track.artists.map(function (a) { return a.name; }).join(', ')
            : ((_a = track.artist) === null || _a === void 0 ? void 0 : _a.name) || 'Unknown Artist';
        var primaryArtistId = ((_c = (_b = track.artists) === null || _b === void 0 ? void 0 : _b[0]) === null || _c === void 0 ? void 0 : _c.id) || ((_d = track.artist) === null || _d === void 0 ? void 0 : _d.id);
        // Get album info
        var albumTitle = ((_e = track.album) === null || _e === void 0 ? void 0 : _e.title) || 'Unknown Album';
        var albumCover = ((_f = track.album) === null || _f === void 0 ? void 0 : _f.cover) || track.cover;
        var albumId = (_g = track.album) === null || _g === void 0 ? void 0 : _g.id;
        // Format duration
        var duration = track.duration
            ? this.formatDuration(track.duration)
            : '';
        // Get quality info - prefer the normalized maxAudioQuality field
        var quality = track.maxAudioQuality || track.audioQuality || track.quality || '';
        var qualityDisplay = this.formatQuality(quality);
        // Format track title with optional track number and version
        // For multi-disc albums, prepend disc number (e.g., "1-03" for disc 1, track 3)
        var trackTitle = this.escapeHtml(track.title);
        // Append version info if available
        if (track.version && typeof track.version === 'string' && track.version.trim()) {
            trackTitle += " (".concat(this.escapeHtml(track.version), ")");
        }
        if (showTrackNumber && track.trackNumber) {
            var volumeNumber = track.volumeNumber || 1;
            var displayTrackNumber = numberOfVolumes && numberOfVolumes > 1
                ? "".concat(volumeNumber, "-").concat(String(track.trackNumber).padStart(2, '0'))
                : String(track.trackNumber);
            trackTitle = "".concat(displayTrackNumber, ". ").concat(trackTitle);
        }
        return "\n            <div class=\"track-card\" data-track-id=\"".concat(track.id, "\" ").concat(primaryArtistId ? "data-artist-id=\"".concat(primaryArtistId, "\"") : '', " ").concat(albumId ? "data-album-id=\"".concat(albumId, "\"") : '', ">\n                <button class=\"track-play-btn\" title=\"Play\" aria-label=\"Play\" aria-pressed=\"false\" data-track-id=\"").concat(track.id, "\">\n                    ").concat(this.getPlayIconSvg(), "\n                </button>\n                <div class=\"track-artwork\">\n                    ").concat(albumCover
            ? "<img src=\"".concat(this.formatTidalImageUrl(albumCover, 1280), "\" alt=\"").concat(track.title, "\" loading=\"lazy\">")
            : "<div class=\"track-artwork-placeholder\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                                <circle cx=\"12\" cy=\"12\" r=\"10\"></circle>\n                                <circle cx=\"12\" cy=\"12\" r=\"3\"></circle>\n                            </svg>\n                           </div>", "\n                </div>\n                <div class=\"track-info\">\n                    <div class=\"track-title\">").concat(trackTitle, "</div>\n                    <div class=\"track-artist\">\n                        <span class=\"track-artist-name\" ").concat(primaryArtistId ? "title=\"View albums by ".concat(this.escapeHtml(artistNames), "\"") : '', ">").concat(this.escapeHtml(artistNames), "</span>\n                    </div>\n                    <div class=\"track-metadata\">\n                        <span class=\"track-album-name\" ").concat(albumId ? "title=\"View tracks on ".concat(this.escapeHtml(albumTitle), "\"") : '', ">").concat(this.escapeHtml(albumTitle), "</span>\n                        ").concat(qualityDisplay ? "<span>\u2022</span><span>".concat(qualityDisplay, "</span>") : '', "\n                        ").concat(track.explicit ? "<span>\u2022</span><span class=\"explicit-badge\" title=\"Explicit content\">E</span>" : '', "\n                    </div>\n                </div>\n                <div class=\"track-actions\">\n                    <button class=\"track-more-btn\" title=\"More Like This\" aria-label=\"More Like This\">\n                        ").concat(this.getMoreLikeIconSvg(), "\n                    </button>\n                    <button class=\"track-add-playlist-btn\" title=\"Add to Playlist\" data-track-id=\"").concat(track.id, "\">\n                        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n                            <path d=\"M12 5v14\"></path>\n                            <path d=\"M5 12h14\"></path>\n                        </svg>\n                    </button>\n                    <button class=\"track-download-btn\" title=\"Download to Library\" data-track-id=\"").concat(track.id, "\">\n                        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n                            <rect x=\"2\" y=\"3\" width=\"20\" height=\"5\" rx=\"1\"></rect>\n                            <path d=\"M4 8v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8\"></path>\n                            <rect x=\"8\" y=\"12\" width=\"8\" height=\"1\"></rect>\n                        </svg>\n                    </button>\n                </div>\n            </div>\n        ");
    };
    App.prototype.allTracksFromSameAlbum = function (tracks) {
        var _a;
        if (tracks.length <= 1)
            return true;
        var firstAlbumId = (_a = tracks[0].album) === null || _a === void 0 ? void 0 : _a.id;
        return tracks.every(function (track) { var _a; return ((_a = track.album) === null || _a === void 0 ? void 0 : _a.id) === firstAlbumId; });
    };
    App.prototype.formatTracksGrid = function (tracks, numberOfVolumes, includeTrackNumbers) {
        var _this = this;
        if (includeTrackNumbers === void 0) { includeTrackNumbers = true; }
        var isSingleAlbum = this.allTracksFromSameAlbum(tracks);
        var showTrackNumberColumn = includeTrackNumbers && isSingleAlbum;
        var showArtworkInSingleAlbum = !includeTrackNumbers && isSingleAlbum;
        if (isSingleAlbum) {
            // Single album view - optionally show track number column or album artwork, hide album column
            return "\n                <div class=\"tracks-grid-wrapper\" data-view-mode=\"single-album\">\n                    <div class=\"tracks-grid\">\n                        ".concat(this.formatTrackGridHeader(showTrackNumberColumn, false, showArtworkInSingleAlbum), "\n                        ").concat(tracks.map(function (track) { return _this.formatTrackGridRow(track, showTrackNumberColumn, numberOfVolumes, false, showArtworkInSingleAlbum); }).join(''), "\n                    </div>\n                </div>\n            ");
        }
        else {
            // Multi-album view - hide track number column, show album column
            return "\n                <div class=\"tracks-grid-wrapper\" data-view-mode=\"multi-album\">\n                    <div class=\"tracks-grid\">\n                        ".concat(this.formatTrackGridHeader(false, true, true), "\n                        ").concat(tracks.map(function (track) { return _this.formatTrackGridRow(track, false, numberOfVolumes, true, true); }).join(''), "\n                    </div>\n                </div>\n            ");
        }
    };
    App.prototype.formatTrackGridRow = function (track, showTrackNumber, numberOfVolumes, showAlbumColumn, showArtwork) {
        var _a, _b, _c, _d, _e, _f, _g;
        // Get artist names and IDs
        var artistNames = track.artists && track.artists.length > 0
            ? track.artists.map(function (a) { return a.name; }).join(', ')
            : ((_a = track.artist) === null || _a === void 0 ? void 0 : _a.name) || 'Unknown Artist';
        var primaryArtistId = ((_c = (_b = track.artists) === null || _b === void 0 ? void 0 : _b[0]) === null || _c === void 0 ? void 0 : _c.id) || ((_d = track.artist) === null || _d === void 0 ? void 0 : _d.id);
        // Get album info
        var albumTitle = ((_e = track.album) === null || _e === void 0 ? void 0 : _e.title) || 'Unknown Album';
        var albumCover = ((_f = track.album) === null || _f === void 0 ? void 0 : _f.cover) || track.cover;
        var albumId = (_g = track.album) === null || _g === void 0 ? void 0 : _g.id;
        // Get quality info - prefer the normalized maxAudioQuality field
        var quality = track.maxAudioQuality || track.audioQuality || track.quality || '';
        var qualityDisplay = this.formatQuality(quality);
        var durationDisplay = track.duration ? this.formatDuration(track.duration) : '—';
        // Format track title with optional version
        var trackTitle = this.escapeHtml(track.title);
        if (track.version && typeof track.version === 'string' && track.version.trim()) {
            trackTitle += " (".concat(this.escapeHtml(track.version), ")");
        }
        // Format track number if needed
        var trackNumberDisplay = '';
        if (showTrackNumber && track.trackNumber) {
            var volumeNumber = track.volumeNumber || 1;
            trackNumberDisplay = numberOfVolumes && numberOfVolumes > 1
                ? "".concat(volumeNumber, "-").concat(String(track.trackNumber).padStart(2, '0'))
                : String(track.trackNumber);
        }
        return "\n            <div class=\"tracks-grid-row\" data-track-id=\"".concat(track.id, "\" ").concat(primaryArtistId ? "data-artist-id=\"".concat(primaryArtistId, "\"") : '', " ").concat(albumId ? "data-album-id=\"".concat(albumId, "\"") : '', ">\n                ").concat(showArtwork ? "<div class=\"grid-cell grid-col-artwork\">\n                    ".concat(albumCover
            ? "<img src=\"".concat(this.getHifiImageUrl(albumCover, 1280), "\" alt=\"").concat(track.title, "\" loading=\"lazy\">")
            : "<div class=\"grid-artwork-placeholder\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                                <circle cx=\"12\" cy=\"12\" r=\"10\"></circle>\n                                <circle cx=\"12\" cy=\"12\" r=\"3\"></circle>\n                            </svg>\n                           </div>", "\n                </div>") : '', "\n                ").concat(showTrackNumber ? "<div class=\"grid-cell grid-col-track-number\">".concat(trackNumberDisplay, "</div>") : '', "\n                <div class=\"grid-cell grid-col-title\">\n                    <div class=\"track-title-with-badge\">\n                        ").concat(trackTitle, "\n                        ").concat(track.explicit ? "<span class=\"explicit-badge\" title=\"Explicit content\">E</span>" : '', "\n                    </div>\n                </div>\n                <div class=\"grid-cell grid-col-artist\">\n                    <span class=\"track-artist-name\" ").concat(primaryArtistId ? "title=\"View albums by ".concat(this.escapeHtml(artistNames), "\"") : '', ">").concat(this.escapeHtml(artistNames), "</span>\n                </div>\n                ").concat(showAlbumColumn ? "<div class=\"grid-cell grid-col-album\">\n                    <span class=\"track-album-name\" ".concat(albumId ? "title=\"View tracks on ".concat(this.escapeHtml(albumTitle), "\"") : '', ">").concat(this.escapeHtml(albumTitle), "</span>\n                </div>") : '', "\n                <div class=\"grid-cell grid-col-duration\">").concat(durationDisplay, "</div>\n                <div class=\"grid-cell grid-col-quality\">").concat(qualityDisplay || '—', "</div>\n                <div class=\"grid-cell grid-col-actions\">\n                    <button class=\"grid-play-btn\" title=\"Play\" aria-label=\"Play\" data-track-id=\"").concat(track.id, "\">\n                        ").concat(this.getPlayIconSvg(), "\n                    </button>\n                    <button class=\"grid-more-btn\" title=\"Find Similar\" aria-label=\"Find Similar\">\n                        ").concat(this.getMoreLikeIconSvg(), "\n                    </button>\n                    <button class=\"grid-add-playlist-btn\" title=\"Add to Playlist\" data-track-id=\"").concat(track.id, "\">\n                        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n                            <path d=\"M12 5v14\"></path>\n                            <path d=\"M5 12h14\"></path>\n                        </svg>\n                    </button>\n                    <button class=\"grid-add-library-btn\" title=\"Add to Library\" data-track-id=\"").concat(track.id, "\">\n                        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n                            <rect x=\"2\" y=\"3\" width=\"20\" height=\"5\" rx=\"1\"></rect>\n                            <path d=\"M4 8v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8\"></path>\n                            <rect x=\"8\" y=\"12\" width=\"8\" height=\"1\"></rect>\n                        </svg>\n                    </button>\n                </div>\n            </div>\n        ");
    };
    App.prototype.formatTrackGridHeader = function (showTrackNumber, showAlbumColumn, showArtwork) {
        return "\n            <div class=\"tracks-grid-header\">\n                ".concat(showTrackNumber ? '<div class="grid-cell grid-col-track-number">#</div>' : '', "\n                ").concat(showArtwork ? '<div class="grid-cell grid-col-artwork"></div>' : '', "\n                <div class=\"grid-cell grid-col-title\">Title</div>\n                <div class=\"grid-cell grid-col-artist\">Artist</div>\n                ").concat(showAlbumColumn ? '<div class="grid-cell grid-col-album">Album</div>' : '', "\n                <div class=\"grid-cell grid-col-duration\">Duration</div>\n                <div class=\"grid-cell grid-col-quality\">MAX QUALITY</div>\n                <div class=\"grid-cell grid-col-actions\">Actions</div>\n            </div>\n        ");
    };
    App.prototype.formatAlbumGridHeader = function (hideArtist, includeQuality) {
        if (hideArtist === void 0) { hideArtist = false; }
        if (includeQuality === void 0) { includeQuality = true; }
        return "\n            <div class=\"albums-grid-header".concat(hideArtist ? ' hide-artist' : '', "\">\n                <div class=\"grid-cell grid-col-artwork\"></div>\n                <div class=\"grid-cell grid-col-title\">ALBUM</div>\n                ").concat(!hideArtist ? '<div class="grid-cell grid-col-artist">ARTIST</div>' : '', "\n                <div class=\"grid-cell grid-col-year\">YEAR</div>\n                <div class=\"grid-cell grid-col-track-count\">TRACKS</div>\n                ").concat(includeQuality ? '<div class="grid-cell grid-col-quality">MAX QUALITY</div>' : '', "\n                <div class=\"grid-cell grid-col-actions\">ACTIONS</div>\n            </div>\n        ");
    };
    App.prototype.getPlayIconSvg = function () {
        return "\n            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"currentColor\" aria-hidden=\"true\">\n                <polygon points=\"6 4 20 12 6 20\"></polygon>\n            </svg>\n        ";
    };
    App.prototype.getStopIconSvg = function () {
        return "\n            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"currentColor\" aria-hidden=\"true\">\n                <rect x=\"6\" y=\"6\" width=\"12\" height=\"12\"></rect>\n            </svg>\n        ";
    };
    App.prototype.getSpinnerIconSvg = function () {
        return "\n            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" aria-hidden=\"true\">\n                <circle cx=\"12\" cy=\"12\" r=\"10\" opacity=\"0.2\"></circle>\n                <path d=\"M22 12a10 10 0 0 1-10 10\" stroke-linecap=\"round\">\n                    <animateTransform attributeName=\"transform\" attributeType=\"XML\" type=\"rotate\" values=\"0 12 12;360 12 12\" dur=\"1s\" repeatCount=\"indefinite\"></animateTransform>\n                </path>\n            </svg>\n        ";
    };
    App.prototype.getCheckmarkIconSvg = function () {
        return "\n            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\">\n                <polyline points=\"20 6 9 17 4 12\"></polyline>\n            </svg>\n        ";
    };
    App.prototype.getExclamationIconSvg = function () {
        return "\n            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\">\n                <path d=\"M12 2v20\"></path>\n                <circle cx=\"12\" cy=\"20\" r=\"1\"></circle>\n            </svg>\n        ";
    };
    App.prototype.setPlayButtonState = function (button, isPlaying) {
        button.classList.toggle('is-playing', isPlaying);
        button.classList.remove('is-loading');
        button.setAttribute('aria-pressed', isPlaying ? 'true' : 'false');
        button.title = isPlaying ? 'Stop' : 'Play';
        button.innerHTML = isPlaying ? this.getStopIconSvg() : this.getPlayIconSvg();
    };
    App.prototype.setPlayButtonLoading = function (button, isLoading) {
        button.classList.toggle('is-loading', isLoading);
        button.disabled = isLoading;
    };
    App.prototype.stopPlayback = function () {
        if (this.currentAudioCleanup) {
            var _a = this.currentAudioCleanup, audio = _a.audio, onEnded = _a.onEnded, onError = _a.onError;
            audio.removeEventListener('ended', onEnded);
            audio.removeEventListener('error', onError);
            this.currentAudioCleanup = null;
        }
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.src = '';
            this.currentAudio.load();
        }
        if (this.currentPlayButton) {
            this.setPlayButtonState(this.currentPlayButton, false);
        }
        this.currentAudio = null;
        this.currentPlayingTrackId = null;
        this.currentPlayButton = null;
    };
    App.prototype.handlePlayToggle = function (trackId, trackCard, playButton) {
        return __awaiter(this, void 0, void 0, function () {
            var playbackTrackId, audio, onEnded, onError, streamUrl, error_40;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        playbackTrackId = "deezer:".concat(trackId);
                        if (this.currentPlayingTrackId === playbackTrackId) {
                            this.stopPlayback();
                            return [2 /*return*/];
                        }
                        this.stopPlayback();
                        this.setPlayButtonState(playButton, true);
                        this.setPlayButtonLoading(playButton, true);
                        this.currentPlayingTrackId = playbackTrackId;
                        this.currentPlayButton = playButton;
                        audio = new Audio();
                        audio.preload = 'none';
                        audio.crossOrigin = 'anonymous';
                        this.currentAudio = audio;
                        onEnded = function () {
                            if (_this.currentAudio === audio) {
                                _this.stopPlayback();
                            }
                        };
                        onError = function () {
                            if (_this.currentAudio === audio) {
                                _this.stopPlayback();
                            }
                        };
                        audio.addEventListener('ended', onEnded);
                        audio.addEventListener('error', onError);
                        this.currentAudioCleanup = { audio: audio, onEnded: onEnded, onError: onError };
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, this.fetchTrackStreamUrl(trackId)];
                    case 2:
                        streamUrl = _a.sent();
                        audio.src = streamUrl;
                        this.setPlayButtonLoading(playButton, false);
                        return [4 /*yield*/, audio.play()];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 5];
                    case 4:
                        error_40 = _a.sent();
                        console.warn('[PLAYBACK] Failed to start playback:', error_40);
                        this.setPlayButtonLoading(playButton, false);
                        this.stopPlayback();
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.fetchTrackStreamUrl = function (trackId) {
        return __awaiter(this, void 0, void 0, function () {
            return __generator(this, function (_a) {
                return [2 /*return*/, "/api/hifi/tracks/".concat(encodeURIComponent(String(trackId)), "/stream?quality=LOW")];
            });
        });
    };
    App.prototype.handlePlayLibraryToggle = function (trackId, playButton) {
        return __awaiter(this, void 0, void 0, function () {
            var playbackTrackId, audio, onEnded, onError, streamUrl, error_41;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        playbackTrackId = "plex:".concat(trackId);
                        if (this.currentPlayingTrackId === playbackTrackId) {
                            this.stopPlayback();
                            return [2 /*return*/];
                        }
                        this.stopPlayback();
                        this.setPlayButtonState(playButton, true);
                        this.setPlayButtonLoading(playButton, true);
                        this.currentPlayingTrackId = playbackTrackId;
                        this.currentPlayButton = playButton;
                        audio = new Audio();
                        audio.preload = 'none';
                        audio.crossOrigin = 'anonymous';
                        this.currentAudio = audio;
                        onEnded = function () {
                            if (_this.currentAudio === audio) {
                                _this.stopPlayback();
                            }
                        };
                        onError = function () {
                            if (_this.currentAudio === audio) {
                                _this.stopPlayback();
                            }
                        };
                        audio.addEventListener('ended', onEnded);
                        audio.addEventListener('error', onError);
                        this.currentAudioCleanup = { audio: audio, onEnded: onEnded, onError: onError };
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, this.fetchLibraryTrackStreamUrl(trackId)];
                    case 2:
                        streamUrl = _a.sent();
                        audio.src = streamUrl;
                        this.setPlayButtonLoading(playButton, false);
                        return [4 /*yield*/, audio.play()];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 5];
                    case 4:
                        error_41 = _a.sent();
                        console.warn('[PLAYBACK] Failed to start Plex library playback:', error_41);
                        this.setPlayButtonLoading(playButton, false);
                        this.stopPlayback();
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.fetchLibraryTrackStreamUrl = function (trackId) {
        return __awaiter(this, void 0, void 0, function () {
            var params, userId, query, response, data, streamUrl;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        params = new URLSearchParams();
                        userId = this.getSelectedPlexUserId();
                        if (userId) {
                            params.set('user_id', userId);
                        }
                        query = params.toString();
                        return [4 /*yield*/, fetch("/api/plex/library/tracks/".concat(encodeURIComponent(trackId), "/stream").concat(query ? "?".concat(query) : ''))];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error("Failed to fetch Plex library stream URL (HTTP ".concat(response.status, ")"));
                        }
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 2:
                        data = _a.sent();
                        streamUrl = data.stream_url;
                        if (typeof streamUrl !== 'string' || !streamUrl) {
                            throw new Error('Plex library stream URL missing from response');
                        }
                        return [2 /*return*/, streamUrl];
                }
            });
        });
    };
    App.prototype.decodeManifest = function (manifestBase64) {
        try {
            var normalized = manifestBase64.replace(/-/g, '+').replace(/_/g, '/');
            var manifestJson = atob(normalized);
            return JSON.parse(manifestJson);
        }
        catch (error) {
            console.warn('[PLAYBACK] Failed to decode manifest:', error);
            return null;
        }
    };
    App.prototype.formatAlbumCard = function (album) {
        var _a, _b, _c, _d, _e, _f, _g;
        // Get artist names and IDs
        var artistNames = album.artists && album.artists.length > 0
            ? album.artists.map(function (a) { return a.name; }).join(', ')
            : ((_a = album.artist) === null || _a === void 0 ? void 0 : _a.name) || 'Unknown Artist';
        var primaryArtistId = ((_c = (_b = album.artists) === null || _b === void 0 ? void 0 : _b[0]) === null || _c === void 0 ? void 0 : _c.id) || ((_d = album.artist) === null || _d === void 0 ? void 0 : _d.id);
        // Format release year if available
        var releaseYear = album.releaseDate
            ? new Date(album.releaseDate).getFullYear()
            : '';
        // Format track count
        var trackCount = ((_e = album.numberOfTracks) !== null && _e !== void 0 ? _e : album.numberOfItems)
            ? "".concat((_f = album.numberOfTracks) !== null && _f !== void 0 ? _f : album.numberOfItems, " track").concat(((_g = album.numberOfTracks) !== null && _g !== void 0 ? _g : album.numberOfItems) !== 1 ? 's' : '')
            : '';
        // Format audio quality if available - prefer the normalized maxAudioQuality field
        var quality = album.maxAudioQuality || album.audioQuality || '';
        var qualityDisplay = this.formatQuality(quality);
        return "\n            <div class=\"track-card album-card clickable\" data-album-id=\"".concat(album.id, "\" ").concat(primaryArtistId ? "data-artist-id=\"".concat(primaryArtistId, "\"") : '', " title=\"Click to view tracks\">\n                <div class=\"track-artwork\">\n                    ").concat(album.cover
            ? "<img src=\"".concat(this.getHifiImageUrl(album.cover, 1280), "\" alt=\"").concat(album.title, "\" loading=\"lazy\">")
            : "<div class=\"track-artwork-placeholder\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                                <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"></rect>\n                                <circle cx=\"8.5\" cy=\"8.5\" r=\"1.5\"></circle>\n                                <polyline points=\"21 15 16 10 5 21\"></polyline>\n                            </svg>\n                           </div>", "\n                </div>\n                <div class=\"track-info\">\n                    <div class=\"track-title\">").concat(this.escapeHtml(album.title), "</div>\n                    <div class=\"track-artist\">\n                        <span class=\"track-artist-name\" ").concat(primaryArtistId ? "title=\"View albums by ".concat(this.escapeHtml(artistNames), "\"") : '', ">").concat(this.escapeHtml(artistNames), "</span>\n                    </div>\n                    <div class=\"track-metadata\">\n                        ").concat(releaseYear ? "<span>".concat(releaseYear, "</span>") : '', "\n                        ").concat(releaseYear && trackCount ? "<span>\u2022</span>" : '', "\n                        ").concat(trackCount ? "<span>".concat(trackCount, "</span>") : '', "\n                        ").concat(trackCount && qualityDisplay ? "<span>\u2022</span>" : '', "\n                        ").concat(qualityDisplay ? "<span>".concat(qualityDisplay, "</span>") : '', "\n                        ").concat(album.explicit ? "<span>\u2022</span><span class=\"explicit-badge\" title=\"Explicit content\">E</span>" : '', "\n                    </div>\n                </div>\n                <div class=\"track-actions\">\n                    <button class=\"track-more-btn\" title=\"More Like This\" aria-label=\"More Like This\">\n                        ").concat(this.getMoreLikeIconSvg(), "\n                    </button>\n                </div>\n            </div>\n        ");
    };
    App.prototype.formatAlbumGridRow = function (album, hideArtist) {
        var _a, _b, _c, _d, _e, _f;
        if (hideArtist === void 0) { hideArtist = false; }
        // Get artist names and IDs
        var artistNames = album.artists && album.artists.length > 0
            ? album.artists.map(function (a) { return a.name; }).join(', ')
            : ((_a = album.artist) === null || _a === void 0 ? void 0 : _a.name) || 'Unknown Artist';
        var primaryArtistId = ((_c = (_b = album.artists) === null || _b === void 0 ? void 0 : _b[0]) === null || _c === void 0 ? void 0 : _c.id) || ((_d = album.artist) === null || _d === void 0 ? void 0 : _d.id);
        // Format release year if available
        var releaseYear = album.releaseDate
            ? new Date(album.releaseDate).getFullYear()
            : '';
        // Format track count - just the number
        var trackCount = ((_e = album.numberOfTracks) !== null && _e !== void 0 ? _e : album.numberOfItems)
            ? "".concat((_f = album.numberOfTracks) !== null && _f !== void 0 ? _f : album.numberOfItems)
            : '';
        // Format audio quality if available - prefer the normalized maxAudioQuality field
        var quality = album.maxAudioQuality || album.audioQuality || '';
        var qualityDisplay = this.formatQuality(quality);
        var albumCover = album.cover;
        return "\n            <div class=\"albums-grid-row ".concat(hideArtist ? 'hide-artist' : '', "\" data-album-id=\"").concat(album.id, "\" ").concat(primaryArtistId ? "data-artist-id=\"".concat(primaryArtistId, "\"") : '', ">\n                <div class=\"grid-cell grid-col-artwork\">\n                    ").concat(albumCover
            ? "<img src=\"".concat(this.getHifiImageUrl(albumCover, 1280), "\" alt=\"").concat(album.title, "\" loading=\"lazy\">")
            : "<div class=\"grid-artwork-placeholder\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                                <rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"></rect>\n                                <circle cx=\"8.5\" cy=\"8.5\" r=\"1.5\"></circle>\n                                <polyline points=\"21 15 16 10 5 21\"></polyline>\n                            </svg>\n                           </div>", "\n                </div>\n                <div class=\"grid-cell grid-col-title\">\n                    <div class=\"track-title-with-badge\">\n                        ").concat(this.escapeHtml(album.title), "\n                        ").concat(album.explicit ? "<span class=\"explicit-badge\" title=\"Explicit content\">E</span>" : '', "\n                    </div>\n                </div>\n                ").concat(!hideArtist ? "<div class=\"grid-cell grid-col-artist\">\n                    <span class=\"album-artist-name\" ".concat(primaryArtistId ? "title=\"View albums by ".concat(this.escapeHtml(artistNames), "\"") : '', ">").concat(this.escapeHtml(artistNames), "</span>\n                </div>") : '', "\n                <div class=\"grid-cell grid-col-year\">").concat(releaseYear || '—', "</div>\n                <div class=\"grid-cell grid-col-track-count\">").concat(trackCount || '—', "</div>\n                <div class=\"grid-cell grid-col-quality\">").concat(qualityDisplay || '—', "</div>\n                <div class=\"grid-cell grid-col-actions\">\n                    <button class=\"grid-play-btn\" title=\"View Tracks\" aria-label=\"View Tracks\" data-album-id=\"").concat(album.id, "\">\n                        ").concat(this.getPlayIconSvg(), "\n                    </button>\n                    <button class=\"grid-more-btn\" title=\"Find Similar\" aria-label=\"Find Similar\">\n                        ").concat(this.getMoreLikeIconSvg(), "\n                    </button>\n                    <button class=\"grid-add-playlist-btn\" title=\"Add to Playlist\" data-album-id=\"").concat(album.id, "\">\n                        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n                            <path d=\"M12 5v14\"></path>\n                            <path d=\"M5 12h14\"></path>\n                        </svg>\n                    </button>\n                    <button class=\"grid-add-library-btn\" title=\"Add to Library\" data-album-id=\"").concat(album.id, "\">\n                        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n                            <rect x=\"2\" y=\"3\" width=\"20\" height=\"5\" rx=\"1\"></rect>\n                            <path d=\"M4 8v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8\"></path>\n                            <rect x=\"8\" y=\"12\" width=\"8\" height=\"1\"></rect>\n                        </svg>\n                    </button>\n                </div>\n            </div>\n        ");
    };
    App.prototype.formatArtistCard = function (artist) {
        return "\n            <div class=\"artist-card-compact clickable\" data-artist-id=\"".concat(artist.id, "\" title=\"Click to view albums\">\n                <div class=\"artist-card-name\">").concat(this.escapeHtml(artist.name), "</div>\n                <div class=\"artist-card-image\">\n                    ").concat(artist.picture
            ? "<img src=\"".concat(this.getHifiImageUrl(artist.picture, 750), "\" alt=\"").concat(this.escapeHtml(artist.name), "\" loading=\"lazy\">")
            : "<div class=\"artist-card-placeholder\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\">\n                                <circle cx=\"12\" cy=\"8\" r=\"4\"></circle>\n                                <path d=\"M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2\"></path>\n                            </svg>\n                           </div>", "\n                </div>\n                <button class=\"artist-card-btn\" title=\"Find Similar Artists\" aria-label=\"Find Similar Artists\">\n                    ").concat(this.getMoreLikeIconSvg(), "\n                </button>\n            </div>\n        ");
    };
    App.prototype.getMoreLikeIconSvg = function () {
        return "\n            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\">\n                <path d=\"M12 2v6\"></path>\n                <path d=\"M12 16v6\"></path>\n                <path d=\"M4.93 4.93l4.24 4.24\"></path>\n                <path d=\"M14.83 14.83l4.24 4.24\"></path>\n                <path d=\"M2 12h6\"></path>\n                <path d=\"M16 12h6\"></path>\n                <path d=\"M4.93 19.07l4.24-4.24\"></path>\n                <path d=\"M14.83 9.17l4.24-4.24\"></path>\n            </svg>\n        ";
    };
    App.prototype.formatDuration = function (seconds) {
        var mins = Math.floor(seconds / 60);
        var secs = seconds % 60;
        return "".concat(mins, ":").concat(secs.toString().padStart(2, '0'));
    };
    App.prototype.formatQuality = function (quality) {
        var qualityMap = {
            'DOLBY_ATMOS': 'DOLBY ATMOS',
            'HI_RES_LOSSLESS': 'HI-RES FLAC',
            'HIRES_LOSSLESS': 'HI-RES FLAC',
            'LOSSLESS': 'LOSSLESS FLAC',
            'HIGH': 'HIGH AAC',
            'LOW': 'LOW AAC'
        };
        return qualityMap[quality] || quality;
    };
    App.prototype.getHifiImageUrl = function (imageIdOrPath, size) {
        if (!imageIdOrPath) {
            return '';
        }
        var normalized = imageIdOrPath.trim();
        if (normalized.startsWith('http://') || normalized.startsWith('https://')) {
            return normalized;
        }
        if (normalized.startsWith('//')) {
            return "https:".concat(normalized);
        }
        if (normalized.startsWith('resources.tidal.com/')) {
            return "https://".concat(normalized);
        }
        if (normalized.startsWith('/images/')) {
            return "https://resources.tidal.com".concat(normalized);
        }
        return this.formatTidalImageUrl(normalized, size);
    };
    App.prototype.formatTidalImageUrl = function (imageIdOrPath, size) {
        var imagePath = imageIdOrPath.replace(/-/g, '/');
        return "https://resources.tidal.com/images/".concat(imagePath, "/").concat(size, "x").concat(size, ".jpg");
    };
    App.prototype.escapeHtml = function (text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };
    App.prototype.fetchWithRetry = function (url_1, options_1) {
        return __awaiter(this, arguments, void 0, function (url, options, maxRetries) {
            var lastError, finalOptions, _loop_1, attempt, state_1;
            var _a;
            if (maxRetries === void 0) { maxRetries = 3; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        lastError = null;
                        finalOptions = __assign(__assign({}, options), { signal: (options === null || options === void 0 ? void 0 : options.signal) || ((_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal) });
                        _loop_1 = function (attempt) {
                            var response, delay_1, error_42, delay_2;
                            return __generator(this, function (_c) {
                                switch (_c.label) {
                                    case 0:
                                        _c.trys.push([0, 4, , 7]);
                                        return [4 /*yield*/, fetch(url, finalOptions)];
                                    case 1:
                                        response = _c.sent();
                                        // Only retry on 5xx errors or connection issues
                                        if (response.status < 500) {
                                            return [2 /*return*/, { value: response }];
                                        }
                                        // 5xx error - log and retry
                                        lastError = new Error("HTTP ".concat(response.status));
                                        if (!(attempt < maxRetries)) return [3 /*break*/, 3];
                                        delay_1 = 1000 * Math.pow(2, attempt);
                                        console.log("[RETRY] HTTP ".concat(response.status, " on attempt ").concat(attempt + 1, "/").concat(maxRetries + 1, ". Retrying in ").concat(delay_1, "ms..."));
                                        return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, delay_1); })];
                                    case 2:
                                        _c.sent();
                                        return [2 /*return*/, "continue"];
                                    case 3: return [2 /*return*/, { value: response }];
                                    case 4:
                                        error_42 = _c.sent();
                                        lastError = error_42;
                                        if (!(attempt < maxRetries)) return [3 /*break*/, 6];
                                        delay_2 = 1000 * Math.pow(2, attempt);
                                        console.log("[RETRY] ".concat(error_42.message, " on attempt ").concat(attempt + 1, "/").concat(maxRetries + 1, ". Retrying in ").concat(delay_2, "ms..."));
                                        return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, delay_2); })];
                                    case 5:
                                        _c.sent();
                                        return [2 /*return*/, "continue"];
                                    case 6: 
                                    // Last attempt, throw the error
                                    throw error_42;
                                    case 7: return [2 /*return*/];
                                }
                            });
                        };
                        attempt = 0;
                        _b.label = 1;
                    case 1:
                        if (!(attempt <= maxRetries)) return [3 /*break*/, 4];
                        return [5 /*yield**/, _loop_1(attempt)];
                    case 2:
                        state_1 = _b.sent();
                        if (typeof state_1 === "object")
                            return [2 /*return*/, state_1.value];
                        _b.label = 3;
                    case 3:
                        attempt++;
                        return [3 /*break*/, 1];
                    case 4: throw lastError || new Error('Fetch failed');
                }
            });
        });
    };
    App.prototype.displayMessage = function (message, retryFn) {
        this.stopPlayback();
        this.updatePlexPlaylistContainerVisibility(false);
        this.lastRetryFunction = retryFn || null;
        var retryButton = retryFn
            ? "<button class=\"retry-button\" id=\"retryButton\">Retry</button>"
            : '';
        this.resultsContainer.innerHTML = "\n            <div class=\"message\">\n                <p>".concat(message, "</p>\n                ").concat(retryButton, "\n            </div>\n        ");
        if (retryFn) {
            var retryBtn = document.getElementById('retryButton');
            if (retryBtn) {
                retryBtn.addEventListener('click', function () {
                    void retryFn();
                });
            }
        }
    };
    App.prototype.fetchArtistAlbums = function (artistId_1) {
        return __awaiter(this, arguments, void 0, function (artistId, updateHistory) {
            var response, data, artistData, albums_1, topTracks_1, artistName, artistPictureUrl, playBtn_1, findSimilarArtistBtn, error_43;
            var _this = this;
            var _a;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        this.downloadAllScope = 'loose';
                        this.currentExploreRoute = { view: 'artist', artistId: artistId };
                        this.exploreArtistName = null;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'artist', artistId: artistId });
                        }
                        this.stopPlayback();
                        this.displayMessage('Loading artist albums...');
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, fetch("/api/hifi/artists/".concat(encodeURIComponent(String(artistId)), "?include_albums=true&include_tracks=true"), {
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _b.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch artist');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _b.sent();
                        if (data.error) {
                            this.displayMessage("Error: ".concat(data.error), function () { return _this.fetchArtistAlbums(artistId); });
                            return [2 /*return*/];
                        }
                        artistData = data.artist || {};
                        albums_1 = Array.isArray(artistData.albums) ? artistData.albums : [];
                        topTracks_1 = Array.isArray(artistData.top_tracks) ? artistData.top_tracks.slice(0, 5) : [];
                        if (albums_1.length === 0 && topTracks_1.length === 0) {
                            this.displayMessage('No albums or top tracks found for this artist');
                            return [2 /*return*/];
                        }
                        artistName = artistData.name || 'Artist';
                        artistPictureUrl = artistData.picture || null;
                        this.exploreArtistName = artistName;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        // Display artist hero with top tracks and albums
                        this.resultsContainer.innerHTML = "\n                <div class=\"artist-hero-section\">\n                    <div class=\"artist-hero-content\">\n                        <div class=\"artist-cover-container\">\n                            ".concat(artistPictureUrl ? "<img src=\"".concat(artistPictureUrl, "\" alt=\"").concat(this.escapeHtml(artistName), "\" class=\"artist-cover\">") : '<div class="artist-cover-placeholder"></div>', "\n                        </div>\n                        <div class=\"artist-info\">\n                            <h1 class=\"artist-hero-name\">").concat(this.escapeHtml(artistName), "</h1>\n                            ").concat(data.proxied_via ? "<p class=\"proxy-info\">Proxied via: <span class=\"proxy-name\">".concat(data.proxied_via, "</span></p>") : '', "\n                        </div>\n                    </div>\n                    <div class=\"artist-actions\">\n                        <button class=\"album-action-btn primary\" id=\"artistPlayBtn\" title=\"Play artist\" ").concat(topTracks_1.length === 0 && albums_1.length === 0 ? 'disabled' : '', ">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"currentColor\"><path d=\"M8 5v14l11-7z\"></path></svg>\n                        </button>\n                        <button class=\"album-action-btn hero-bottom-right\" id=\"findSimilarArtistBtn\" title=\"Find similar artists\" data-artist-id=\"").concat(artistId, "\">\n                            ").concat(this.getMoreLikeIconSvg(), "\n                        </button>\n                    </div>\n                </div>\n                ").concat(topTracks_1.length > 0 ? "\n                    <div class=\"results-header\">\n                        <div class=\"results-header-top\">\n                            <h2>Top Tracks</h2>\n                        </div>\n                    </div>\n                    ".concat(this.formatTracksGrid(topTracks_1, undefined, false), "\n                ") : '', "\n                <div class=\"results-header\">\n                    <div class=\"results-header-top\">\n                        <h2>Albums</h2>\n                    </div>\n                </div>\n                <div class=\"albums-grid-wrapper\" data-view-mode=\"artist-albums\">\n                    <div class=\"albums-grid\">\n                        ").concat(this.formatAlbumGridHeader(true, true), "\n                        ").concat(albums_1.map(function (album) { return _this.formatAlbumGridRow(album, true); }).join(''), "\n                    </div>\n                </div>\n            ");
                        playBtn_1 = document.getElementById('artistPlayBtn');
                        if (playBtn_1) {
                            playBtn_1.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                                var firstAlbumId, response_1, albumData, trackItems, tracks, error_44;
                                var _a, _b;
                                return __generator(this, function (_c) {
                                    switch (_c.label) {
                                        case 0:
                                            if (topTracks_1.length > 0) {
                                                void this.handlePlayToggle(topTracks_1[0].id, undefined, playBtn_1);
                                                return [2 /*return*/];
                                            }
                                            if (!(albums_1.length > 0)) return [3 /*break*/, 5];
                                            firstAlbumId = albums_1[0].id;
                                            _c.label = 1;
                                        case 1:
                                            _c.trys.push([1, 4, , 5]);
                                            return [4 /*yield*/, fetch("/api/hifi/albums/".concat(encodeURIComponent(String(firstAlbumId))), {
                                                    signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                                                })];
                                        case 2:
                                            response_1 = _c.sent();
                                            if (!response_1.ok) {
                                                throw new Error('Failed to fetch album');
                                            }
                                            return [4 /*yield*/, response_1.json()];
                                        case 3:
                                            albumData = _c.sent();
                                            trackItems = ((_b = albumData.data) === null || _b === void 0 ? void 0 : _b.items) || [];
                                            tracks = trackItems.filter(function (item) { return item.type === 'track'; }).map(function (item) { return item.item; });
                                            if (tracks.length > 0) {
                                                void this.handlePlayToggle(tracks[0].id, undefined, playBtn_1);
                                            }
                                            return [3 /*break*/, 5];
                                        case 4:
                                            error_44 = _c.sent();
                                            console.error('Error playing artist:', error_44);
                                            return [3 /*break*/, 5];
                                        case 5: return [2 /*return*/];
                                    }
                                });
                            }); });
                        }
                        findSimilarArtistBtn = document.getElementById('findSimilarArtistBtn');
                        if (findSimilarArtistBtn) {
                            findSimilarArtistBtn.addEventListener('click', function () {
                                void _this.navigateToRoute({ view: 'similar_artists', artistId: artistId }, true);
                            });
                        }
                        // Annotate with Plex status
                        void this.annotateAlbumGridsWithPlexStatus(albums_1);
                        void this.annotateArtistHeroWithPlexStatus(artistId);
                        return [3 /*break*/, 5];
                    case 4:
                        error_43 = _b.sent();
                        this.displayMessage('Error loading artist albums. Please try again.', function () { return _this.fetchArtistAlbums(artistId); });
                        console.error('Artist fetch error:', error_43);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.fetchAlbumTracks = function (albumId_1) {
        return __awaiter(this, arguments, void 0, function (albumId, updateHistory) {
            var response, data, albumData, tracks_1, volumeNumbers_1, numberOfVolumes, albumTitle, artistNames, primaryArtistId, totalDurationSeconds, totalDurationMinutes, totalDurationHours, remainingMinutes, durationStr, releaseDate, albumIsExplicit, coverArt, addPlaylistBtn, addLibraryBtn, findSimilarBtn, playBtn_2, error_45;
            var _this = this;
            var _a, _b, _c, _d, _e, _f, _g;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_h) {
                switch (_h.label) {
                    case 0:
                        this.downloadAllScope = 'album';
                        this.currentExploreRoute = { view: 'album', albumId: albumId };
                        this.exploreAlbumTitle = null;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'album', albumId: albumId });
                        }
                        this.stopPlayback();
                        this.displayMessage('Loading album tracks...');
                        _h.label = 1;
                    case 1:
                        _h.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, fetch("/api/hifi/albums/".concat(encodeURIComponent(String(albumId))), {
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _h.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch album');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _h.sent();
                        if (data.error) {
                            this.displayMessage("Error: ".concat(data.error), function () { return _this.fetchAlbumTracks(albumId); });
                            return [2 /*return*/];
                        }
                        albumData = data.album;
                        if (!albumData) {
                            this.displayMessage('No album data found');
                            return [2 /*return*/];
                        }
                        tracks_1 = albumData.tracks || [];
                        if (tracks_1.length === 0) {
                            this.displayMessage('No tracks found in this album');
                            return [2 /*return*/];
                        }
                        volumeNumbers_1 = new Set();
                        tracks_1.forEach(function (track) {
                            if (track.volumeNumber !== undefined && track.volumeNumber !== null) {
                                volumeNumbers_1.add(track.volumeNumber);
                            }
                        });
                        numberOfVolumes = volumeNumbers_1.size > 0 ? volumeNumbers_1.size : 1;
                        this.updatePlexPlaylistContainerVisibility(true);
                        albumTitle = albumData.title || 'Album';
                        this.exploreAlbumTitle = albumTitle;
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        artistNames = albumData.artists && albumData.artists.length > 0
                            ? albumData.artists.map(function (a) { return a.name; }).join(', ')
                            : ((_b = albumData.artist) === null || _b === void 0 ? void 0 : _b.name) || 'Unknown Artist';
                        primaryArtistId = ((_d = (_c = albumData.artists) === null || _c === void 0 ? void 0 : _c[0]) === null || _d === void 0 ? void 0 : _d.id) || ((_e = albumData.artist) === null || _e === void 0 ? void 0 : _e.id);
                        totalDurationSeconds = tracks_1.reduce(function (sum, track) {
                            return sum + (track.duration || 0);
                        }, 0);
                        totalDurationMinutes = Math.floor(totalDurationSeconds / 60);
                        totalDurationHours = Math.floor(totalDurationMinutes / 60);
                        remainingMinutes = totalDurationMinutes % 60;
                        durationStr = totalDurationHours > 0
                            ? "".concat(totalDurationHours, "h ").concat(remainingMinutes, "m")
                            : "".concat(totalDurationMinutes, "m");
                        releaseDate = albumData.releaseDate
                            ? new Date(albumData.releaseDate).getFullYear()
                            : '';
                        albumIsExplicit = Boolean(albumData.explicit ||
                            ((_g = (_f = albumData.mediaMetadata) === null || _f === void 0 ? void 0 : _f.tags) === null || _g === void 0 ? void 0 : _g.includes('EXPLICIT')) ||
                            tracks_1.some(function (track) { return track.explicit; }));
                        coverArt = albumData.cover
                            ? this.getHifiImageUrl(albumData.cover, 1280)
                            : '';
                        // Display tracks with TIDAL-style album header
                        this.resultsContainer.innerHTML = "\n                <div class=\"album-hero-section\">\n                    <div class=\"album-hero-content\">\n                        <div class=\"album-cover-container\">\n                            ".concat(coverArt ? "<img src=\"".concat(coverArt, "\" alt=\"").concat(this.escapeHtml(albumTitle), "\" class=\"album-cover\">") : '<div class="album-cover-placeholder"></div>', "\n                        </div>\n                        <div class=\"album-info\">\n                            <h1 class=\"album-title\">\n                                ").concat(this.escapeHtml(albumTitle), "\n                                ").concat(albumIsExplicit ? "<span class=\"explicit-badge\" title=\"Explicit content\">E</span>" : '', "\n                            </h1>\n                            <p class=\"album-artist\">\n                                <span class=\"track-artist-name\" ").concat(primaryArtistId ? "data-artist-id=\"".concat(primaryArtistId, "\" title=\"View albums by ").concat(this.escapeHtml(artistNames), "\"") : '', ">").concat(this.escapeHtml(artistNames), "</span>\n                            </p>\n                            <div class=\"album-metadata\">\n                                ").concat(releaseDate ? "<span class=\"metadata-item\">".concat(releaseDate, "</span>") : '', "\n                                <span class=\"metadata-item\">").concat(tracks_1.length, " ").concat(tracks_1.length === 1 ? 'track' : 'tracks', "</span>\n                                <span class=\"metadata-item\">").concat(durationStr, "</span>\n                            </div>\n                            ").concat(data.proxied_via ? "<p class=\"proxy-info\">Proxied via: <span class=\"proxy-name\">".concat(data.proxied_via, "</span></p>") : '', "\n                        </div>\n                    </div>\n                    <div class=\"album-actions\">\n                        <button class=\"album-action-btn primary\" id=\"albumPlayBtn\" title=\"Play album\">\n                            <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"currentColor\"><path d=\"M8 5v14l11-7z\"></path></svg>\n                        </button>\n                        <button class=\"album-action-btn\" id=\"findSimilarAlbumBtn\" title=\"Find similar albums\" data-album-id=\"").concat(albumId, "\">\n                            ").concat(this.getMoreLikeIconSvg(), "\n                        </button>\n                        <button class=\"album-action-btn\" id=\"addAllPlaylistBtn\" title=\"Add all tracks to a playlist\">\n                            ").concat(this.getAddAllPlaylistIconSvg(), "\n                        </button>\n                        <button class=\"album-action-btn\" id=\"addAllLibraryBtn\" title=\"Add all tracks to library\">\n                            ").concat(this.getAddAllLibraryIconSvg(), "\n                        </button>\n                    </div>\n                </div>\n                <div class=\"results-list\">\n                    ").concat(this.formatTracksGrid(tracks_1, numberOfVolumes), "\n                </div>\n            ");
                        addPlaylistBtn = document.getElementById('addAllPlaylistBtn');
                        if (addPlaylistBtn) {
                            addPlaylistBtn.addEventListener('click', function () { return _this.addAllToPlaylist(); });
                        }
                        addLibraryBtn = document.getElementById('addAllLibraryBtn');
                        if (addLibraryBtn) {
                            addLibraryBtn.addEventListener('click', function () { return _this.addAllToLibrary(); });
                        }
                        findSimilarBtn = document.getElementById('findSimilarAlbumBtn');
                        if (findSimilarBtn) {
                            findSimilarBtn.addEventListener('click', function () {
                                void _this.navigateToRoute({ view: 'similar_albums', albumId: albumId }, true);
                            });
                        }
                        playBtn_2 = document.getElementById('albumPlayBtn');
                        if (playBtn_2) {
                            playBtn_2.addEventListener('click', function () {
                                // Play the first track from the album
                                if (tracks_1.length > 0) {
                                    void _this.handlePlayToggle(tracks_1[0].id, undefined, playBtn_2);
                                }
                            });
                        }
                        this.movePlexPlaylistContainerBeneathDownloadAll();
                        void this.annotateTrackCardsWithPlexStatus(tracks_1);
                        void this.annotateAlbumHeroWithPlexStatus(albumId);
                        return [3 /*break*/, 5];
                    case 4:
                        error_45 = _h.sent();
                        this.displayMessage('Error loading album tracks. Please try again.', function () { return _this.fetchAlbumTracks(albumId); });
                        console.error('Album fetch error:', error_45);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.fetchAlbumObject = function (albumId) {
        return __awaiter(this, void 0, void 0, function () {
            var response, data;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0: return [4 /*yield*/, fetch("/api/hifi/albums/".concat(encodeURIComponent(String(albumId))))];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch album');
                        }
                        return [4 /*yield*/, response.json()];
                    case 2:
                        data = _a.sent();
                        if (data.error) {
                            throw new Error(data.error);
                        }
                        if (!data.album) {
                            throw new Error('No album data found');
                        }
                        return [2 /*return*/, data.album];
                }
            });
        });
    };
    App.prototype.fetchSimilarTracks = function (trackId_1) {
        return __awaiter(this, arguments, void 0, function (trackId, updateHistory) {
            var response, data, recommendationItems, tracks, resultsHeaderTop, buttonsContainer, addPlaylistBtn, addLibraryBtn, error_46;
            var _this = this;
            var _a, _b;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_c) {
                switch (_c.label) {
                    case 0:
                        this.downloadAllScope = 'loose';
                        this.currentExploreRoute = { view: 'similar_tracks', trackId: trackId };
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'similar_tracks', trackId: trackId });
                        }
                        this.stopPlayback();
                        this.displayMessage('Loading track recommendations...');
                        _c.label = 1;
                    case 1:
                        _c.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, fetch("/api/hifi/tracks/".concat(encodeURIComponent(String(trackId)), "/similar"), {
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _c.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch recommendations');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _c.sent();
                        if (data.error) {
                            this.displayMessage("Error: ".concat(data.error), function () { return _this.fetchSimilarTracks(trackId); });
                            return [2 /*return*/];
                        }
                        recommendationItems = Array.isArray((_b = data === null || data === void 0 ? void 0 : data.data) === null || _b === void 0 ? void 0 : _b.items) ? data.data.items : [];
                        tracks = recommendationItems
                            .map(function (item) { return (item === null || item === void 0 ? void 0 : item.track) || (item === null || item === void 0 ? void 0 : item.item) || item; })
                            .filter(function (track) { return track && typeof track === 'object' && 'id' in track && 'title' in track; });
                        if (tracks.length === 0) {
                            this.displayMessage('No recommendations found for this track');
                            return [2 /*return*/];
                        }
                        this.updatePlexPlaylistContainerVisibility(true);
                        this.resultsContainer.innerHTML = "\n                <div class=\"results-header\">\n                    <div class=\"results-header-top\">\n                        <h2>More Like This - Similar Tracks</h2>\n                    </div>\n                    ".concat(data.proxied_via ? "<p class=\"proxy-info\">Proxied via: <span class=\"proxy-name\">".concat(data.proxied_via, "</span></p>") : '', "\n                </div>\n                <div class=\"results-list\">\n                    ").concat(this.formatTracksGrid(tracks), "\n                </div>\n            ");
                        resultsHeaderTop = document.querySelector('.results-header-top');
                        if (resultsHeaderTop) {
                            buttonsContainer = document.createElement('div');
                            buttonsContainer.className = 'add-all-buttons-container';
                            addPlaylistBtn = document.createElement('button');
                            addPlaylistBtn.id = 'addAllPlaylistBtn';
                            addPlaylistBtn.className = 'add-all-btn';
                            addPlaylistBtn.title = 'Add all tracks to a playlist';
                            addPlaylistBtn.innerHTML = this.getAddAllPlaylistIconSvg();
                            addPlaylistBtn.addEventListener('click', function () { return _this.addAllToPlaylist(); });
                            buttonsContainer.appendChild(addPlaylistBtn);
                            addLibraryBtn = document.createElement('button');
                            addLibraryBtn.id = 'addAllLibraryBtn';
                            addLibraryBtn.className = 'add-all-btn';
                            addLibraryBtn.title = 'Add all tracks to library';
                            addLibraryBtn.innerHTML = this.getAddAllLibraryIconSvg();
                            addLibraryBtn.addEventListener('click', function () { return _this.addAllToLibrary(); });
                            buttonsContainer.appendChild(addLibraryBtn);
                            resultsHeaderTop.appendChild(buttonsContainer);
                            this.movePlexPlaylistContainerBeneathDownloadAll();
                        }
                        void this.annotateTrackCardsWithPlexStatus(tracks);
                        return [3 /*break*/, 5];
                    case 4:
                        error_46 = _c.sent();
                        this.displayMessage('Error loading recommendations. Please try again.', function () { return _this.fetchSimilarTracks(trackId); });
                        console.error('Recommendations fetch error:', error_46);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.fetchSimilarAlbums = function (albumId_1) {
        return __awaiter(this, arguments, void 0, function (albumId, updateHistory) {
            var response, data, albums, error_47;
            var _this = this;
            var _a;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        this.downloadAllScope = 'loose';
                        this.currentExploreRoute = { view: 'similar_albums', albumId: albumId };
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'similar_albums', albumId: albumId });
                        }
                        this.stopPlayback();
                        this.displayMessage('Loading similar albums...');
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, fetch("/api/hifi/albums/".concat(encodeURIComponent(String(albumId)), "/similar"), {
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _b.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch similar albums');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _b.sent();
                        if (data.error) {
                            this.displayMessage("Error: ".concat(data.error), function () { return _this.fetchSimilarAlbums(albumId); });
                            return [2 /*return*/];
                        }
                        albums = Array.isArray(data === null || data === void 0 ? void 0 : data.albums) ? data.albums : [];
                        if (albums.length === 0) {
                            this.displayMessage('No similar albums found');
                            return [2 /*return*/];
                        }
                        this.updatePlexPlaylistContainerVisibility(true);
                        this.resultsContainer.innerHTML = "\n                <div class=\"results-header\">\n                    <h2>More Like This - Similar Albums</h2>\n                    ".concat(data.proxied_via ? "<p class=\"proxy-info\">Proxied via: <span class=\"proxy-name\">".concat(data.proxied_via, "</span></p>") : '', "\n                </div>\n                <div class=\"albums-grid-wrapper\" data-view-mode=\"similar-albums\">\n                    <div class=\"albums-grid\">\n                        ").concat(this.formatAlbumGridHeader(false, true), "\n                        ").concat(albums.map(function (album) { return _this.formatAlbumGridRow(album, false); }).join(''), "\n                    </div>\n                </div>\n            ");
                        // Annotate with Plex status
                        void this.annotateAlbumGridsWithPlexStatus(albums);
                        return [3 /*break*/, 5];
                    case 4:
                        error_47 = _b.sent();
                        this.displayMessage('Error loading similar albums. Please try again.', function () { return _this.fetchSimilarAlbums(albumId); });
                        console.error('Similar albums fetch error:', error_47);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.fetchSimilarArtists = function (artistId_1) {
        return __awaiter(this, arguments, void 0, function (artistId, updateHistory) {
            var response, data, artists, error_48;
            var _this = this;
            var _a;
            if (updateHistory === void 0) { updateHistory = true; }
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        this.downloadAllScope = 'loose';
                        this.currentExploreRoute = { view: 'similar_artists', artistId: artistId };
                        this.renderExploreTopBarBreadcrumb(this.currentExploreRoute);
                        if (updateHistory) {
                            this.pushHistoryRoute({ view: 'similar_artists', artistId: artistId });
                        }
                        this.stopPlayback();
                        this.displayMessage('Loading similar artists...');
                        _b.label = 1;
                    case 1:
                        _b.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, fetch("/api/hifi/artists/".concat(encodeURIComponent(String(artistId)), "/similar"), {
                                signal: (_a = this.pendingRequestController) === null || _a === void 0 ? void 0 : _a.signal
                            })];
                    case 2:
                        response = _b.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch similar artists');
                        }
                        return [4 /*yield*/, response.json()];
                    case 3:
                        data = _b.sent();
                        if (data.error) {
                            this.displayMessage("Error: ".concat(data.error), function () { return _this.fetchSimilarArtists(artistId); });
                            return [2 /*return*/];
                        }
                        artists = Array.isArray(data === null || data === void 0 ? void 0 : data.artists) ? data.artists : [];
                        if (artists.length === 0) {
                            this.displayMessage('No similar artists found');
                            return [2 /*return*/];
                        }
                        this.updatePlexPlaylistContainerVisibility(true);
                        this.resultsContainer.innerHTML = "\n                <div class=\"results-header\">\n                    <h2>More Like This - Similar Artists</h2>\n                    ".concat(data.proxied_via ? "<p class=\"proxy-info\">Proxied via: <span class=\"proxy-name\">".concat(data.proxied_via, "</span></p>") : '', "\n                </div>\n                <div class=\"results-list artist-results\">\n                    ").concat(artists.map(function (artist) { return _this.formatArtistCard(artist); }).join(''), "\n                </div>\n            ");
                        void this.annotateArtistCardsWithPlexStatus(artists);
                        return [3 /*break*/, 5];
                    case 4:
                        error_48 = _b.sent();
                        this.displayMessage('Error loading similar artists. Please try again.', function () { return _this.fetchSimilarArtists(artistId); });
                        console.error('Similar artists fetch error:', error_48);
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleDownload = function (trackId_1, trackCard_1) {
        return __awaiter(this, arguments, void 0, function (trackId, trackCard, downloadType) {
            var downloadBtn, originalContent, originalDisabled, jobId, error_49;
            if (downloadType === void 0) { downloadType = 'loose'; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        downloadBtn = trackCard.querySelector('.grid-add-library-btn');
                        if (!downloadBtn) {
                            console.error('[DOWNLOAD] Download button not found');
                            return [2 /*return*/];
                        }
                        console.log("[DOWNLOAD] Starting download to library for track ".concat(trackId));
                        originalContent = downloadBtn.innerHTML;
                        originalDisabled = downloadBtn.disabled;
                        if (!downloadBtn.dataset.originalContent) {
                            downloadBtn.dataset.originalContent = originalContent;
                        }
                        downloadBtn.disabled = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        console.log("[DOWNLOAD] Calling downloadTrackToLibrary with quality: ".concat(this.downloadSettings.quality));
                        return [4 /*yield*/, this.downloadTrackToLibrary(trackId, downloadType)];
                    case 2:
                        jobId = _a.sent();
                        console.log("[DOWNLOAD] Job queued successfully: ".concat(jobId));
                        this.setDownloadButtonQueued(downloadBtn);
                        this.registerActiveJob(jobId, trackCard, downloadBtn, downloadBtn);
                        return [3 /*break*/, 4];
                    case 3:
                        error_49 = _a.sent();
                        console.error('[DOWNLOAD] Download error:', error_49);
                        // Check if this was an abort
                        if (error_49 instanceof Error && error_49.name === 'AbortError') {
                            console.log('[DOWNLOAD] Download was aborted, restoring button');
                            this.restoreDownloadButton(downloadBtn);
                        }
                        else {
                            // Restore button on error
                            downloadBtn.disabled = originalDisabled;
                            downloadBtn.innerHTML = originalContent;
                            if (downloadBtn.dataset.originalContent) {
                                delete downloadBtn.dataset.originalContent;
                            }
                        }
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleAddToPlaylist = function (trackId_1, trackCard_1) {
        return __awaiter(this, arguments, void 0, function (trackId, trackCard, downloadType) {
            var addPlaylistBtn, playlists, error_50;
            if (downloadType === void 0) { downloadType = 'loose'; }
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        addPlaylistBtn = trackCard.querySelector('.grid-add-playlist-btn');
                        if (!addPlaylistBtn) {
                            console.error('[PLAYLIST] Add to playlist button not found');
                            return [2 /*return*/];
                        }
                        console.log("[PLAYLIST] Fetching playlists for track ".concat(trackId));
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, this.fetchPlaylists()];
                    case 2:
                        playlists = _a.sent();
                        if (!playlists || playlists.length === 0) {
                            this.displayMessage('No Plex playlists found. Please create a playlist in Plex first.');
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.showPlaylistSelector(playlists, trackId, trackCard, downloadType)];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 5];
                    case 4:
                        error_50 = _a.sent();
                        console.error('[PLAYLIST] Error handling add to playlist:', error_50);
                        this.displayMessage('Error fetching playlists. Please try again.');
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.fetchPlaylists = function () {
        return __awaiter(this, void 0, void 0, function () {
            var userId, queryParam, response, errorData, errorMsg, data, error_51;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 5, , 6]);
                        userId = this.getSelectedPlexUserId();
                        queryParam = userId ? "?user_id=".concat(userId) : '';
                        return [4 /*yield*/, this.fetchWithRetry("/api/plex/playlists".concat(queryParam), {
                                method: 'GET',
                                headers: {
                                    'Content-Type': 'application/json'
                                }
                            }, 3)];
                    case 1:
                        response = _a.sent();
                        if (!!response.ok) return [3 /*break*/, 3];
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 2:
                        errorData = _a.sent();
                        errorMsg = errorData.error || "HTTP ".concat(response.status);
                        console.error("[PLAYLIST] Failed to fetch playlists: ".concat(errorMsg));
                        throw new Error(errorMsg);
                    case 3: return [4 /*yield*/, response.json()];
                    case 4:
                        data = _a.sent();
                        return [2 /*return*/, data.playlists || []];
                    case 5:
                        error_51 = _a.sent();
                        console.error('[PLAYLIST] Error fetching playlists:', error_51);
                        throw error_51;
                    case 6: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.showPlaylistSelector = function (playlists, trackId, trackCard, downloadType) {
        return __awaiter(this, void 0, void 0, function () {
            var _this = this;
            return __generator(this, function (_a) {
                return [2 /*return*/, new Promise(function (resolve) {
                        var overlay = document.createElement('div');
                        overlay.className = 'playlist-modal-overlay';
                        var modal = document.createElement('div');
                        modal.className = 'playlist-modal';
                        // Header
                        var header = document.createElement('div');
                        header.className = 'playlist-modal-header';
                        var title = document.createElement('h3');
                        title.textContent = 'Select a Playlist';
                        var closeBtn = document.createElement('button');
                        closeBtn.className = 'playlist-modal-close';
                        closeBtn.innerHTML = '×';
                        closeBtn.addEventListener('click', function () {
                            overlay.remove();
                            resolve();
                        });
                        header.appendChild(title);
                        header.appendChild(closeBtn);
                        // Content
                        var content = document.createElement('div');
                        content.className = 'playlist-modal-content';
                        // Existing playlists
                        if (playlists.length > 0) {
                            playlists.forEach(function (playlistName) {
                                var button = document.createElement('button');
                                button.className = 'playlist-item-btn';
                                button.innerHTML = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><line x1=\"8\" y1=\"6\" x2=\"21\" y2=\"6\"></line><line x1=\"8\" y1=\"12\" x2=\"21\" y2=\"12\"></line><line x1=\"8\" y1=\"18\" x2=\"21\" y2=\"18\"></line><line x1=\"3\" y1=\"6\" x2=\"3.01\" y2=\"6\"></line><line x1=\"3\" y1=\"12\" x2=\"3.01\" y2=\"12\"></line><line x1=\"3\" y1=\"18\" x2=\"3.01\" y2=\"18\"></line></svg><span>".concat(playlistName, "</span>");
                                button.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                                    return __generator(this, function (_a) {
                                        switch (_a.label) {
                                            case 0:
                                                overlay.remove();
                                                return [4 /*yield*/, this.handlePlaylistSelected(playlistName, trackId, trackCard, downloadType)];
                                            case 1:
                                                _a.sent();
                                                resolve();
                                                return [2 /*return*/];
                                        }
                                    });
                                }); });
                                content.appendChild(button);
                            });
                        }
                        // Create new playlist section
                        var createSection = document.createElement('div');
                        createSection.className = 'playlist-create-section';
                        var divider = document.createElement('div');
                        divider.className = 'playlist-create-divider';
                        divider.textContent = 'or';
                        var inputGroup = document.createElement('div');
                        inputGroup.className = 'playlist-create-inline-group';
                        var input = document.createElement('input');
                        input.type = 'text';
                        input.className = 'playlist-create-inline-input';
                        input.placeholder = 'New playlist name...';
                        var okBtn = document.createElement('button');
                        okBtn.className = 'playlist-create-inline-btn';
                        okBtn.textContent = 'OK';
                        okBtn.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                            var playlistName;
                            return __generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0:
                                        playlistName = input.value.trim();
                                        if (!playlistName) return [3 /*break*/, 2];
                                        overlay.remove();
                                        return [4 /*yield*/, this.handlePlaylistSelected(playlistName, trackId, trackCard, downloadType)];
                                    case 1:
                                        _a.sent();
                                        resolve();
                                        _a.label = 2;
                                    case 2: return [2 /*return*/];
                                }
                            });
                        }); });
                        input.addEventListener('keypress', function (e) {
                            if (e.key === 'Enter') {
                                var playlistName = input.value.trim();
                                if (playlistName) {
                                    overlay.remove();
                                    void _this.handlePlaylistSelected(playlistName, trackId, trackCard, downloadType);
                                    resolve();
                                }
                            }
                        });
                        inputGroup.appendChild(input);
                        inputGroup.appendChild(okBtn);
                        if (playlists.length > 0) {
                            createSection.appendChild(divider);
                        }
                        createSection.appendChild(inputGroup);
                        content.appendChild(createSection);
                        // Footer
                        var footer = document.createElement('div');
                        footer.className = 'playlist-modal-footer';
                        var cancelBtn = document.createElement('button');
                        cancelBtn.className = 'playlist-modal-cancel';
                        cancelBtn.textContent = 'Cancel';
                        cancelBtn.addEventListener('click', function () {
                            overlay.remove();
                            resolve();
                        });
                        footer.appendChild(cancelBtn);
                        modal.appendChild(header);
                        modal.appendChild(content);
                        modal.appendChild(footer);
                        overlay.appendChild(modal);
                        overlay.addEventListener('click', function (e) {
                            if (e.target === overlay) {
                                overlay.remove();
                                resolve();
                            }
                        });
                        document.body.appendChild(overlay);
                        input.focus();
                    })];
            });
        });
    };
    App.prototype.handlePlaylistSelected = function (playlistName, trackId, trackCard, downloadType) {
        return __awaiter(this, void 0, void 0, function () {
            var addPlaylistBtn, originalContent, originalDisabled, jobId, error_52;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        addPlaylistBtn = trackCard.querySelector('.track-add-playlist-btn');
                        if (!addPlaylistBtn) {
                            console.error('[PLAYLIST] Add to playlist button not found');
                            return [2 /*return*/];
                        }
                        console.log("[PLAYLIST] Selected playlist: ".concat(playlistName, " for track ").concat(trackId));
                        originalContent = addPlaylistBtn.innerHTML;
                        originalDisabled = addPlaylistBtn.disabled;
                        if (!addPlaylistBtn.dataset.originalContent) {
                            addPlaylistBtn.dataset.originalContent = originalContent;
                        }
                        addPlaylistBtn.disabled = true;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 3, , 4]);
                        return [4 /*yield*/, this.downloadTrackWithPlaylist(trackId, downloadType, playlistName)];
                    case 2:
                        jobId = _a.sent();
                        console.log("[PLAYLIST] Job queued successfully: ".concat(jobId));
                        this.setDownloadButtonQueued(addPlaylistBtn);
                        this.registerActiveJob(jobId, trackCard, addPlaylistBtn, addPlaylistBtn);
                        return [3 /*break*/, 4];
                    case 3:
                        error_52 = _a.sent();
                        console.error('[PLAYLIST] Error downloading with playlist:', error_52);
                        // Restore button on error
                        addPlaylistBtn.disabled = originalDisabled;
                        addPlaylistBtn.innerHTML = originalContent;
                        if (addPlaylistBtn.dataset.originalContent) {
                            delete addPlaylistBtn.dataset.originalContent;
                        }
                        this.displayMessage('Error adding track to playlist. Please try again.');
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.downloadTrackWithPlaylist = function (trackId, downloadType, playlistName) {
        return __awaiter(this, void 0, void 0, function () {
            var plexUserId, response, errorData, errorMsg, data, error_53;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _b.trys.push([0, 5, , 6]);
                        console.log("[PLAYLIST] Sending download with playlist request for track ".concat(trackId));
                        console.log("[PLAYLIST] Settings: quality=".concat(this.downloadSettings.quality));
                        console.log("[PLAYLIST] Download type: ".concat(downloadType, ", Playlist: ").concat(playlistName));
                        plexUserId = this.getSelectedPlexUserId();
                        return [4 /*yield*/, this.fetchWithRetry('/api/downloads', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    trackId: trackId,
                                    format: 'original',
                                    quality: this.downloadSettings.quality,
                                    downloadType: downloadType,
                                    fileNaming: this.downloadSettings.fileNamingAlbum,
                                    fileNamingAlbum: this.downloadSettings.fileNamingAlbum,
                                    plex_playlist: playlistName,
                                    plex_user_id: plexUserId,
                                    ignore_matches: this.downloadSettings.ignoreMatches
                                }),
                                signal: (_a = this.currentDownloadController) === null || _a === void 0 ? void 0 : _a.signal
                            }, 3)];
                    case 1:
                        response = _b.sent();
                        console.log("[PLAYLIST] Response status: ".concat(response.status));
                        if (!!response.ok) return [3 /*break*/, 3];
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 2:
                        errorData = _b.sent();
                        errorMsg = errorData.error || "HTTP ".concat(response.status);
                        console.error("[PLAYLIST] Download failed: ".concat(errorMsg));
                        throw new Error(errorMsg);
                    case 3: return [4 /*yield*/, response.json()];
                    case 4:
                        data = _b.sent();
                        console.log("[PLAYLIST] Server response:", data);
                        if (!data.success) {
                            throw new Error(data.error || 'Download failed');
                        }
                        if (!data.job_id) {
                            throw new Error('Download job id missing from response');
                        }
                        console.log("[PLAYLIST] Playlist download job queued: ".concat(data.job_id));
                        return [2 /*return*/, data.job_id];
                    case 5:
                        error_53 = _b.sent();
                        if (error_53 instanceof Error && error_53.name === 'AbortError') {
                            console.log('[PLAYLIST] Download was aborted');
                            throw error_53;
                        }
                        console.error('[PLAYLIST] Error in downloadTrackWithPlaylist:', error_53);
                        throw error_53;
                    case 6: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleAddAlbumToPlaylist = function (albumId, albumRow) {
        return __awaiter(this, void 0, void 0, function () {
            var addPlaylistBtn, originalContent, originalDisabled, albumData, tracks, playlists, selectedPlaylist, error_54, error_55;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        addPlaylistBtn = albumRow.querySelector('.grid-add-playlist-btn');
                        if (!addPlaylistBtn) {
                            console.error('[ALBUM_PLAYLIST] Add to playlist button not found');
                            return [2 /*return*/];
                        }
                        originalContent = addPlaylistBtn.innerHTML;
                        originalDisabled = addPlaylistBtn.disabled;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 8, , 9]);
                        return [4 /*yield*/, this.fetchAlbumObject(albumId)];
                    case 2:
                        albumData = _a.sent();
                        tracks = albumData.tracks || [];
                        if (tracks.length === 0) {
                            this.displayMessage('No tracks found in this album');
                            return [2 /*return*/];
                        }
                        _a.label = 3;
                    case 3:
                        _a.trys.push([3, 6, , 7]);
                        return [4 /*yield*/, this.fetchPlaylists()];
                    case 4:
                        playlists = _a.sent();
                        if (!playlists || playlists.length === 0) {
                            this.displayMessage('No Plex playlists found. Please create a playlist in Plex first.');
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.showPlaylistSelectorForAlbum(playlists, tracks, albumRow, addPlaylistBtn)];
                    case 5:
                        selectedPlaylist = _a.sent();
                        if (!selectedPlaylist) {
                            // User cancelled, restore button
                            addPlaylistBtn.disabled = originalDisabled;
                            addPlaylistBtn.innerHTML = originalContent;
                        }
                        return [3 /*break*/, 7];
                    case 6:
                        error_54 = _a.sent();
                        console.error('[ALBUM_PLAYLIST] Error handling add to playlist:', error_54);
                        addPlaylistBtn.disabled = originalDisabled;
                        addPlaylistBtn.innerHTML = originalContent;
                        this.displayMessage('Error fetching playlists. Please try again.');
                        return [3 /*break*/, 7];
                    case 7: return [3 /*break*/, 9];
                    case 8:
                        error_55 = _a.sent();
                        console.error('[ALBUM_PLAYLIST] Error adding album to playlist:', error_55);
                        addPlaylistBtn.disabled = originalDisabled;
                        addPlaylistBtn.innerHTML = originalContent;
                        this.displayMessage('Error adding album to playlist. Please try again.');
                        return [3 /*break*/, 9];
                    case 9: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.showPlaylistSelectorForAlbum = function (playlists, tracks, albumRow, addPlaylistBtn) {
        var _this = this;
        return new Promise(function (resolve) {
            var overlay = document.createElement('div');
            overlay.className = 'playlist-modal-overlay';
            var modal = document.createElement('div');
            modal.className = 'playlist-modal';
            // Header
            var header = document.createElement('div');
            header.className = 'playlist-modal-header';
            var title = document.createElement('h3');
            title.textContent = 'Select a Playlist';
            var closeBtn = document.createElement('button');
            closeBtn.className = 'playlist-modal-close';
            closeBtn.innerHTML = '×';
            closeBtn.addEventListener('click', function () {
                overlay.remove();
                resolve(null);
            });
            header.appendChild(title);
            header.appendChild(closeBtn);
            // Content
            var content = document.createElement('div');
            content.className = 'playlist-modal-content';
            // Existing playlists
            if (playlists.length > 0) {
                playlists.forEach(function (playlistName) {
                    var button = document.createElement('button');
                    button.className = 'playlist-item-btn';
                    button.innerHTML = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><line x1=\"8\" y1=\"6\" x2=\"21\" y2=\"6\"></line><line x1=\"8\" y1=\"12\" x2=\"21\" y2=\"12\"></line><line x1=\"8\" y1=\"18\" x2=\"21\" y2=\"18\"></line><line x1=\"3\" y1=\"6\" x2=\"3.01\" y2=\"6\"></line><line x1=\"3\" y1=\"12\" x2=\"3.01\" y2=\"12\"></line><line x1=\"3\" y1=\"18\" x2=\"3.01\" y2=\"18\"></line></svg><span>".concat(playlistName, "</span>");
                    button.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                        return __generator(this, function (_a) {
                            switch (_a.label) {
                                case 0:
                                    overlay.remove();
                                    return [4 /*yield*/, this.handlePlaylistSelectedForAlbum(playlistName, tracks, albumRow, addPlaylistBtn)];
                                case 1:
                                    _a.sent();
                                    resolve(playlistName);
                                    return [2 /*return*/];
                            }
                        });
                    }); });
                    content.appendChild(button);
                });
            }
            // Create new playlist section
            var createSection = document.createElement('div');
            createSection.className = 'playlist-create-section';
            var divider = document.createElement('div');
            divider.className = 'playlist-create-divider';
            divider.textContent = 'or';
            var inputGroup = document.createElement('div');
            inputGroup.className = 'playlist-create-inline-group';
            var input = document.createElement('input');
            input.type = 'text';
            input.className = 'playlist-create-inline-input';
            input.placeholder = 'New playlist name...';
            var okBtn = document.createElement('button');
            okBtn.className = 'playlist-create-inline-btn';
            okBtn.textContent = 'OK';
            okBtn.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                var playlistName;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            playlistName = input.value.trim();
                            if (!playlistName) return [3 /*break*/, 2];
                            overlay.remove();
                            return [4 /*yield*/, this.handlePlaylistSelectedForAlbum(playlistName, tracks, albumRow, addPlaylistBtn)];
                        case 1:
                            _a.sent();
                            resolve(playlistName);
                            _a.label = 2;
                        case 2: return [2 /*return*/];
                    }
                });
            }); });
            input.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') {
                    var playlistName = input.value.trim();
                    if (playlistName) {
                        overlay.remove();
                        void _this.handlePlaylistSelectedForAlbum(playlistName, tracks, albumRow, addPlaylistBtn);
                        resolve(playlistName);
                    }
                }
            });
            inputGroup.appendChild(input);
            inputGroup.appendChild(okBtn);
            if (playlists.length > 0) {
                createSection.appendChild(divider);
            }
            createSection.appendChild(inputGroup);
            content.appendChild(createSection);
            // Footer
            var footer = document.createElement('div');
            footer.className = 'playlist-modal-footer';
            var cancelBtn = document.createElement('button');
            cancelBtn.className = 'playlist-modal-cancel';
            cancelBtn.textContent = 'Cancel';
            cancelBtn.addEventListener('click', function () {
                overlay.remove();
                resolve(null);
            });
            footer.appendChild(cancelBtn);
            modal.appendChild(header);
            modal.appendChild(content);
            modal.appendChild(footer);
            overlay.appendChild(modal);
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) {
                    overlay.remove();
                    resolve(null);
                }
            });
            document.body.appendChild(overlay);
            input.focus();
        });
    };
    App.prototype.handlePlaylistSelectedForAlbum = function (playlistName, tracks, albumRow, addPlaylistBtn) {
        return __awaiter(this, void 0, void 0, function () {
            var originalContent, originalDisabled, jobIds, _i, tracks_2, track, jobId, error_56, error_57;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        originalContent = addPlaylistBtn.innerHTML;
                        originalDisabled = addPlaylistBtn.disabled;
                        // Show spinner on button
                        this.setDownloadButtonQueued(addPlaylistBtn);
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 8, , 9]);
                        jobIds = [];
                        _i = 0, tracks_2 = tracks;
                        _a.label = 2;
                    case 2:
                        if (!(_i < tracks_2.length)) return [3 /*break*/, 7];
                        track = tracks_2[_i];
                        _a.label = 3;
                    case 3:
                        _a.trys.push([3, 5, , 6]);
                        return [4 /*yield*/, this.downloadTrackWithPlaylist(track.id, 'album', playlistName)];
                    case 4:
                        jobId = _a.sent();
                        jobIds.push(jobId);
                        return [3 /*break*/, 6];
                    case 5:
                        error_56 = _a.sent();
                        console.error("[PLAYLIST] Failed to queue track ".concat(track.id, ":"), error_56);
                        return [3 /*break*/, 6];
                    case 6:
                        _i++;
                        return [3 /*break*/, 2];
                    case 7:
                        if (jobIds.length === 0) {
                            throw new Error('No jobs were queued');
                        }
                        console.log("[PLAYLIST] Queued ".concat(jobIds.length, " tracks to playlist: ").concat(playlistName));
                        // Register all jobs for polling, but track them all under the button
                        // We'll monitor the first one for now and mark success when all are done
                        jobIds.forEach(function (jobId, index) {
                            if (index === 0) {
                                // Register first job with the button for visual feedback
                                _this.registerActiveJob(jobId, albumRow, addPlaylistBtn, addPlaylistBtn);
                            }
                            else {
                                // Register other jobs but don't update button - they're tracked internally
                                _this.activeJobMap.set(jobId, { trackCard: albumRow, downloadBtn: addPlaylistBtn, statusEl: addPlaylistBtn });
                            }
                        });
                        this.startJobStatusPolling();
                        return [3 /*break*/, 9];
                    case 8:
                        error_57 = _a.sent();
                        console.error('[PLAYLIST] Error adding tracks to playlist:', error_57);
                        addPlaylistBtn.disabled = originalDisabled;
                        addPlaylistBtn.innerHTML = originalContent;
                        this.setDownloadButtonFailed(addPlaylistBtn);
                        this.displayMessage('Error adding album to playlist. Please try again.');
                        return [3 /*break*/, 9];
                    case 9: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handleDownloadAlbum = function (albumId, albumRow) {
        return __awaiter(this, void 0, void 0, function () {
            var addLibraryBtn, originalContent, originalDisabled, albumData, tracks, jobIds, _i, tracks_3, track, jobId, error_58, error_59;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        addLibraryBtn = albumRow.querySelector('.grid-add-library-btn');
                        if (!addLibraryBtn) {
                            console.error('[ALBUM_DOWNLOAD] Add to library button not found');
                            return [2 /*return*/];
                        }
                        originalContent = addLibraryBtn.innerHTML;
                        originalDisabled = addLibraryBtn.disabled;
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 9, , 10]);
                        return [4 /*yield*/, this.fetchAlbumObject(albumId)];
                    case 2:
                        albumData = _a.sent();
                        tracks = albumData.tracks || [];
                        if (tracks.length === 0) {
                            this.displayMessage('No tracks found in this album');
                            return [2 /*return*/];
                        }
                        // Show spinner on button
                        this.setDownloadButtonQueued(addLibraryBtn);
                        jobIds = [];
                        _i = 0, tracks_3 = tracks;
                        _a.label = 3;
                    case 3:
                        if (!(_i < tracks_3.length)) return [3 /*break*/, 8];
                        track = tracks_3[_i];
                        _a.label = 4;
                    case 4:
                        _a.trys.push([4, 6, , 7]);
                        return [4 /*yield*/, this.downloadTrackToLibrary(track.id, 'album')];
                    case 5:
                        jobId = _a.sent();
                        jobIds.push(jobId);
                        return [3 /*break*/, 7];
                    case 6:
                        error_58 = _a.sent();
                        console.error("[ALBUM_DOWNLOAD] Failed to queue track ".concat(track.id, ":"), error_58);
                        return [3 /*break*/, 7];
                    case 7:
                        _i++;
                        return [3 /*break*/, 3];
                    case 8:
                        if (jobIds.length === 0) {
                            throw new Error('No jobs were queued');
                        }
                        console.log("[ALBUM_DOWNLOAD] Queued ".concat(jobIds.length, " tracks to library"));
                        // Register all jobs for polling, tracking them all under the button
                        jobIds.forEach(function (jobId, index) {
                            if (index === 0) {
                                // Register first job with the button for visual feedback
                                _this.registerActiveJob(jobId, albumRow, addLibraryBtn, addLibraryBtn);
                            }
                            else {
                                // Register other jobs but don't update button - they're tracked internally
                                _this.activeJobMap.set(jobId, { trackCard: albumRow, downloadBtn: addLibraryBtn, statusEl: addLibraryBtn });
                            }
                        });
                        this.startJobStatusPolling();
                        return [3 /*break*/, 10];
                    case 9:
                        error_59 = _a.sent();
                        console.error('[ALBUM_DOWNLOAD] Error downloading album to library:', error_59);
                        addLibraryBtn.disabled = originalDisabled;
                        addLibraryBtn.innerHTML = originalContent;
                        this.setDownloadButtonFailed(addLibraryBtn);
                        this.displayMessage('Error adding album to library. Please try again.');
                        return [3 /*break*/, 10];
                    case 10: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handlePlayAlbum = function (albumId, playButton) {
        return __awaiter(this, void 0, void 0, function () {
            var albumData, tracks, albumRow, error_60;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 2, , 3]);
                        return [4 /*yield*/, this.fetchAlbumObject(albumId)];
                    case 1:
                        albumData = _a.sent();
                        tracks = albumData.tracks || [];
                        if (tracks.length === 0) {
                            this.displayMessage('No tracks found in this album');
                            return [2 /*return*/];
                        }
                        albumRow = playButton.closest('.albums-grid-row');
                        void this.handlePlayToggle(tracks[0].id, albumRow, playButton);
                        return [3 /*break*/, 3];
                    case 2:
                        error_60 = _a.sent();
                        console.error('[ALBUM_PLAYBACK] Error playing album:', error_60);
                        this.displayMessage('Error playing album. Please try again.');
                        return [3 /*break*/, 3];
                    case 3: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handlePlayLibraryAlbum = function (albumId, playButton) {
        return __awaiter(this, void 0, void 0, function () {
            var params, userId, response, data, tracks, error_61;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 3, , 4]);
                        params = new URLSearchParams();
                        userId = this.getSelectedPlexUserId();
                        if (userId) {
                            params.set('user_id', userId);
                        }
                        return [4 /*yield*/, fetch("/api/plex/library/albums/".concat(encodeURIComponent(albumId), "/tracks?").concat(params.toString()))];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch Plex album tracks');
                        }
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 2:
                        data = _a.sent();
                        tracks = Array.isArray(data.tracks) ? data.tracks : [];
                        if (tracks.length === 0 || !tracks[0].id) {
                            this.displayMessage('No tracks found in this album');
                            return [2 /*return*/];
                        }
                        void this.handlePlayLibraryToggle(tracks[0].id, playButton);
                        return [3 /*break*/, 4];
                    case 3:
                        error_61 = _a.sent();
                        console.error('[ALBUM_PLAYBACK] Error playing Plex library album:', error_61);
                        this.displayMessage('Error playing album. Please try again.');
                        return [3 /*break*/, 4];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.handlePlayLibraryArtist = function (artistId, playButton) {
        return __awaiter(this, void 0, void 0, function () {
            var params, userId, response, data, albums, error_62;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        _a.trys.push([0, 4, , 5]);
                        params = new URLSearchParams();
                        userId = this.getSelectedPlexUserId();
                        if (userId) {
                            params.set('user_id', userId);
                        }
                        return [4 /*yield*/, fetch("/api/plex/library/artists/".concat(encodeURIComponent(artistId), "/albums?").concat(params.toString()))];
                    case 1:
                        response = _a.sent();
                        if (!response.ok) {
                            throw new Error('Failed to fetch Plex artist albums');
                        }
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 2:
                        data = _a.sent();
                        albums = Array.isArray(data.albums) ? data.albums : [];
                        if (albums.length === 0 || !albums[0].id) {
                            this.displayMessage('No albums found for this artist');
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.handlePlayLibraryAlbum(albums[0].id, playButton)];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 5];
                    case 4:
                        error_62 = _a.sent();
                        console.error('[ARTIST_PLAYBACK] Error playing Plex library artist:', error_62);
                        this.displayMessage('Error playing artist. Please try again.');
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.formatAlbumsGrid = function (albums) {
        var _this = this;
        return "\n            <div class=\"albums-grid-wrapper\" data-view-mode=\"search-albums\">\n                <div class=\"albums-grid\">\n                    ".concat(this.formatAlbumGridHeader(false, true), "\n                    ").concat(albums.map(function (album) { return _this.formatAlbumGridRow(album, false); }).join(''), "\n                </div>\n            </div>\n        ");
    };
    App.prototype.downloadTrackToLibrary = function (trackId, downloadType) {
        return __awaiter(this, void 0, void 0, function () {
            var response, errorData, errorMsg, data, error_63;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _b.trys.push([0, 5, , 6]);
                        console.log("[DOWNLOAD] Sending download-to-library request for track ".concat(trackId));
                        console.log("[DOWNLOAD] Settings: quality=".concat(this.downloadSettings.quality));
                        console.log("[DOWNLOAD] Download type: ".concat(downloadType));
                        return [4 /*yield*/, this.fetchWithRetry('/api/downloads', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    trackId: trackId,
                                    format: 'original',
                                    quality: this.downloadSettings.quality,
                                    downloadType: downloadType,
                                    fileNaming: this.downloadSettings.fileNamingAlbum,
                                    fileNamingAlbum: this.downloadSettings.fileNamingAlbum,
                                    ignore_matches: this.downloadSettings.ignoreMatches
                                }),
                                signal: (_a = this.currentDownloadController) === null || _a === void 0 ? void 0 : _a.signal
                            }, 3)];
                    case 1:
                        response = _b.sent();
                        console.log("[DOWNLOAD] Response status: ".concat(response.status));
                        if (!!response.ok) return [3 /*break*/, 3];
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 2:
                        errorData = _b.sent();
                        errorMsg = errorData.error || "HTTP ".concat(response.status);
                        console.error("[DOWNLOAD] Download failed: ".concat(errorMsg));
                        throw new Error(errorMsg);
                    case 3: return [4 /*yield*/, response.json()];
                    case 4:
                        data = _b.sent();
                        console.log("[DOWNLOAD] Server response:", data);
                        if (!data.success) {
                            throw new Error(data.error || 'Download failed');
                        }
                        if (!data.job_id) {
                            throw new Error('Download job id missing from response');
                        }
                        console.log("[DOWNLOAD] Library download job queued: ".concat(data.job_id));
                        return [2 /*return*/, data.job_id];
                    case 5:
                        error_63 = _b.sent();
                        // Check if error is due to abort
                        if (error_63 instanceof Error && error_63.name === 'AbortError') {
                            console.log('[DOWNLOAD] Download was aborted');
                            throw error_63;
                        }
                        console.error('[DOWNLOAD] Error in downloadTrackToLibrary:', error_63);
                        throw error_63;
                    case 6: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.downloadTrack = function (trackId, downloadType, plexPlaylistName) {
        return __awaiter(this, void 0, void 0, function () {
            var plexUserId, response, errorData, errorMsg, data, error_64;
            var _a;
            return __generator(this, function (_b) {
                switch (_b.label) {
                    case 0:
                        _b.trys.push([0, 5, , 6]);
                        console.log("[DOWNLOAD] Sending download request for track ".concat(trackId));
                        console.log("[DOWNLOAD] Settings: quality=".concat(this.downloadSettings.quality));
                        console.log("[DOWNLOAD] Download type: ".concat(downloadType));
                        plexUserId = this.getSelectedPlexUserId();
                        return [4 /*yield*/, this.fetchWithRetry('/api/downloads', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    trackId: trackId,
                                    format: 'original',
                                    quality: this.downloadSettings.quality,
                                    downloadType: downloadType,
                                    fileNaming: this.downloadSettings.fileNamingAlbum,
                                    fileNamingAlbum: this.downloadSettings.fileNamingAlbum,
                                    plex_playlist: plexPlaylistName,
                                    plex_user_id: plexUserId,
                                    ignore_matches: this.downloadSettings.ignoreMatches
                                }),
                                signal: (_a = this.currentDownloadController) === null || _a === void 0 ? void 0 : _a.signal
                            }, 3)];
                    case 1:
                        response = _b.sent();
                        console.log("[DOWNLOAD] Response status: ".concat(response.status));
                        if (!!response.ok) return [3 /*break*/, 3];
                        return [4 /*yield*/, response.json().catch(function () { return ({}); })];
                    case 2:
                        errorData = _b.sent();
                        errorMsg = errorData.error || "HTTP ".concat(response.status);
                        console.error("[DOWNLOAD] Download failed: ".concat(errorMsg));
                        throw new Error(errorMsg);
                    case 3: return [4 /*yield*/, response.json()];
                    case 4:
                        data = _b.sent();
                        console.log("[DOWNLOAD] Server response:", data);
                        if (!data.success) {
                            throw new Error(data.error || 'Download failed');
                        }
                        if (!data.job_id) {
                            throw new Error('Download job id missing from response');
                        }
                        console.log("[DOWNLOAD] Job queued: ".concat(data.job_id));
                        return [2 /*return*/, data.job_id];
                    case 5:
                        error_64 = _b.sent();
                        // Check if error is due to abort
                        if (error_64 instanceof Error && error_64.name === 'AbortError') {
                            console.log('[DOWNLOAD] Download was aborted');
                            throw error_64;
                        }
                        console.error('[DOWNLOAD] Error in downloadTrack:', error_64);
                        throw error_64;
                    case 6: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.restoreDownloadButton = function (downloadBtn) {
        downloadBtn.disabled = false;
        downloadBtn.classList.remove('completed');
        if (downloadBtn.dataset.originalContent) {
            downloadBtn.innerHTML = downloadBtn.dataset.originalContent;
            delete downloadBtn.dataset.originalContent;
        }
        else {
            // Fallback: recreate the archive icon
            downloadBtn.innerHTML = "\n                <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"20\" height=\"20\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n                    <rect x=\"2\" y=\"3\" width=\"20\" height=\"5\" rx=\"1\"></rect>\n                    <path d=\"M4 8v9a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8\"></path>\n                    <rect x=\"8\" y=\"12\" width=\"8\" height=\"1\"></rect>\n                </svg>\n            ";
        }
    };
    App.prototype.setJobStatusIcon = function (downloadBtn, status) {
        var effectiveStatus = status.replace('_', '-');
        downloadBtn.classList.remove('queued', 'in-progress', 'completed', 'failed');
        downloadBtn.classList.add(effectiveStatus);
        if (effectiveStatus === 'queued' || effectiveStatus === 'in-progress') {
            downloadBtn.innerHTML = this.getSpinnerIconSvg();
        }
        else if (effectiveStatus === 'succeeded' || effectiveStatus === 'completed-with-errors') {
            downloadBtn.innerHTML = this.getCheckmarkIconSvg();
        }
        else if (effectiveStatus === 'failed') {
            downloadBtn.innerHTML = this.getExclamationIconSvg();
            downloadBtn.disabled = false;
        }
    };
    App.prototype.registerActiveJob = function (jobId, trackCard, downloadBtn, statusEl) {
        this.activeJobMap.set(jobId, { trackCard: trackCard, downloadBtn: downloadBtn, statusEl: statusEl });
        this.startJobStatusPolling();
    };
    App.prototype.startJobStatusPolling = function () {
        var _this = this;
        if (this.jobStatusInterval) {
            return;
        }
        this.jobStatusInterval = window.setInterval(function () {
            void _this.pollActiveJobs();
        }, 4000);
    };
    App.prototype.stopJobStatusPolling = function () {
        if (this.jobStatusInterval && this.activeJobMap.size === 0) {
            window.clearInterval(this.jobStatusInterval);
            this.jobStatusInterval = null;
        }
    };
    App.prototype.pollActiveJobs = function () {
        return __awaiter(this, void 0, void 0, function () {
            var entries;
            var _this = this;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.jobStatusPolling) {
                            return [2 /*return*/];
                        }
                        if (this.activeJobMap.size === 0) {
                            this.stopJobStatusPolling();
                            return [2 /*return*/];
                        }
                        this.jobStatusPolling = true;
                        entries = Array.from(this.activeJobMap.entries());
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, , 3, 4]);
                        return [4 /*yield*/, Promise.all(entries.map(function (_a) { return __awaiter(_this, [_a], void 0, function (_b) {
                                var response, job, error_65;
                                var jobId = _b[0], context = _b[1];
                                return __generator(this, function (_c) {
                                    switch (_c.label) {
                                        case 0:
                                            _c.trys.push([0, 3, , 4]);
                                            return [4 /*yield*/, fetch("/api/jobs/".concat(jobId))];
                                        case 1:
                                            response = _c.sent();
                                            if (!response.ok) {
                                                return [2 /*return*/];
                                            }
                                            return [4 /*yield*/, response.json()];
                                        case 2:
                                            job = _c.sent();
                                            this.updateJobStatusForCard(job, context);
                                            return [3 /*break*/, 4];
                                        case 3:
                                            error_65 = _c.sent();
                                            console.warn('Job status fetch failed:', error_65);
                                            return [3 /*break*/, 4];
                                        case 4: return [2 /*return*/];
                                    }
                                });
                            }); }))];
                    case 2:
                        _a.sent();
                        return [3 /*break*/, 4];
                    case 3:
                        this.jobStatusPolling = false;
                        this.stopJobStatusPolling();
                        return [7 /*endfinally*/];
                    case 4: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.updateJobStatusForCard = function (job, context) {
        var effectiveStatus = this.getEffectiveJobStatus(job);
        this.setJobStatusIcon(context.downloadBtn, effectiveStatus);
        if (effectiveStatus === 'succeeded' || effectiveStatus === 'completed_with_errors') {
            this.setDownloadButtonCompleted(context.downloadBtn);
            context.downloadBtn.disabled = true;
            this.activeJobMap.delete(job.id);
            return;
        }
        if (effectiveStatus === 'failed' || effectiveStatus === 'cancelled') {
            this.restoreDownloadButton(context.downloadBtn);
            this.activeJobMap.delete(job.id);
            return;
        }
        if (job.status === 'succeeded') {
            this.setDownloadButtonCompleted(context.downloadBtn);
            context.downloadBtn.disabled = true;
            this.activeJobMap.delete(job.id);
            return;
        }
        context.downloadBtn.disabled = true;
    };
    App.prototype.setDownloadButtonCompleted = function (downloadBtn) {
        downloadBtn.disabled = true;
        downloadBtn.classList.add('completed');
        downloadBtn.innerHTML = this.getCheckmarkIconSvg();
    };
    App.prototype.setDownloadButtonQueued = function (downloadBtn) {
        downloadBtn.disabled = true;
        downloadBtn.classList.add('queued');
        downloadBtn.innerHTML = this.getSpinnerIconSvg();
    };
    App.prototype.setDownloadButtonFailed = function (downloadBtn) {
        downloadBtn.disabled = false;
        downloadBtn.classList.add('failed');
        downloadBtn.innerHTML = this.getExclamationIconSvg();
    };
    App.prototype.downloadAllTracks = function () {
        return __awaiter(this, void 0, void 0, function () {
            var downloadAllBtn, trackCards, totalTracks, downloadedCount, i, j, trackCard_1, downloadBtn, trackCard, trackId, downloadBtn, error_66, error_67;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.isDownloadingAll) {
                            // Cancel the download all process immediately
                            this.downloadAllCancelRequested = true;
                            // Abort the current download
                            if (this.currentDownloadController) {
                                this.currentDownloadController.abort();
                            }
                            return [2 /*return*/];
                        }
                        this.isDownloadingAll = true;
                        this.downloadAllCancelRequested = false;
                        downloadAllBtn = document.getElementById('downloadAllBtn');
                        if (downloadAllBtn) {
                            downloadAllBtn.textContent = 'Cancel';
                            downloadAllBtn.classList.add('cancelling');
                            downloadAllBtn.disabled = false;
                        }
                        trackCards = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row[data-track-id]'));
                        totalTracks = trackCards.length;
                        downloadedCount = 0;
                        console.log("[DOWNLOAD_ALL] Starting batch download of ".concat(totalTracks, " tracks"));
                        i = 0;
                        _a.label = 1;
                    case 1:
                        if (!(i < trackCards.length)) return [3 /*break*/, 9];
                        // Check if cancel was requested
                        if (this.downloadAllCancelRequested) {
                            console.log('[DOWNLOAD_ALL] Download all cancelled by user');
                            // Restore buttons for incomplete downloads
                            for (j = i; j < trackCards.length; j++) {
                                trackCard_1 = trackCards[j];
                                downloadBtn = trackCard_1.querySelector('.grid-add-library-btn');
                                if (downloadBtn && !downloadBtn.classList.contains('completed')) {
                                    this.restoreDownloadButton(downloadBtn);
                                }
                            }
                            return [3 /*break*/, 9];
                        }
                        trackCard = trackCards[i];
                        trackId = trackCard.getAttribute('data-track-id');
                        if (!trackId) return [3 /*break*/, 8];
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 7, , 8]);
                        console.log("[DOWNLOAD_ALL] Downloading track ".concat(i + 1, "/").concat(totalTracks));
                        downloadBtn = trackCard.querySelector('.grid-add-library-btn');
                        if (!(downloadBtn && !downloadBtn.classList.contains('completed'))) return [3 /*break*/, 6];
                        this.currentDownloadController = new AbortController();
                        _a.label = 3;
                    case 3:
                        _a.trys.push([3, 5, , 6]);
                        return [4 /*yield*/, this.handleDownload(parseInt(trackId, 10), trackCard, this.downloadAllScope)];
                    case 4:
                        _a.sent();
                        return [3 /*break*/, 6];
                    case 5:
                        error_66 = _a.sent();
                        console.error("[DOWNLOAD_ALL] Download error for track ".concat(trackId, ":"), error_66);
                        return [3 /*break*/, 6];
                    case 6:
                        // Count as queued whether processed or not (including skipped/already completed)
                        downloadedCount++;
                        return [3 /*break*/, 8];
                    case 7:
                        error_67 = _a.sent();
                        console.error("[DOWNLOAD_ALL] Error processing track ".concat(trackId, ":"), error_67);
                        return [3 /*break*/, 8];
                    case 8:
                        i++;
                        return [3 /*break*/, 1];
                    case 9:
                        // Reset button state
                        this.isDownloadingAll = false;
                        this.downloadAllCancelRequested = false;
                        this.currentDownloadController = null;
                        if (downloadAllBtn) {
                            downloadAllBtn.textContent = 'Download All';
                            downloadAllBtn.classList.remove('cancelling');
                            downloadAllBtn.disabled = false;
                        }
                        console.log("[DOWNLOAD_ALL] Queued ".concat(downloadedCount, "/").concat(totalTracks, " tracks"));
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.addAllToLibrary = function () {
        return __awaiter(this, void 0, void 0, function () {
            var addAllLibraryBtn, trackCards, totalTracks, addedCount, failedCount, i, trackCard, trackId, libraryBtn, wasQueued, isQueued, error_68;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.isDownloadingAll) {
                            return [2 /*return*/];
                        }
                        this.isDownloadingAll = true;
                        this.downloadAllCancelRequested = false;
                        addAllLibraryBtn = document.getElementById('addAllLibraryBtn');
                        this.setBulkActionButtonState(addAllLibraryBtn, 'library', 'loading');
                        trackCards = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row[data-track-id]'));
                        totalTracks = trackCards.length;
                        addedCount = 0;
                        failedCount = 0;
                        console.log("[ADD_ALL_LIBRARY] Starting batch add to library of ".concat(totalTracks, " tracks"));
                        i = 0;
                        _a.label = 1;
                    case 1:
                        if (!(i < trackCards.length)) return [3 /*break*/, 7];
                        trackCard = trackCards[i];
                        trackId = trackCard.getAttribute('data-track-id');
                        if (!trackId) return [3 /*break*/, 6];
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 5, , 6]);
                        console.log("[ADD_ALL_LIBRARY] Adding to library ".concat(i + 1, "/").concat(totalTracks));
                        libraryBtn = trackCard.querySelector('.grid-add-library-btn');
                        if (!(libraryBtn && !libraryBtn.classList.contains('completed'))) return [3 /*break*/, 4];
                        wasQueued = libraryBtn.classList.contains('queued');
                        return [4 /*yield*/, this.handleDownload(parseInt(trackId, 10), trackCard, this.downloadAllScope)];
                    case 3:
                        _a.sent();
                        isQueued = libraryBtn.classList.contains('queued');
                        if (!wasQueued && isQueued) {
                            addedCount++;
                        }
                        else if (!isQueued && !libraryBtn.classList.contains('completed')) {
                            failedCount++;
                        }
                        _a.label = 4;
                    case 4: return [3 /*break*/, 6];
                    case 5:
                        error_68 = _a.sent();
                        console.error("[ADD_ALL_LIBRARY] Error processing track ".concat(trackId, ":"), error_68);
                        failedCount++;
                        return [3 /*break*/, 6];
                    case 6:
                        i++;
                        return [3 /*break*/, 1];
                    case 7:
                        this.isDownloadingAll = false;
                        this.downloadAllCancelRequested = false;
                        this.currentDownloadController = null;
                        this.setBulkActionButtonState(addAllLibraryBtn, 'library', failedCount > 0 ? 'failed' : 'success');
                        console.log("[ADD_ALL_LIBRARY] Queued ".concat(addedCount, "/").concat(totalTracks, " tracks"));
                        return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.addAllToPlaylist = function () {
        return __awaiter(this, void 0, void 0, function () {
            var playlists, error_69;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.isDownloadingAll) {
                            return [2 /*return*/];
                        }
                        _a.label = 1;
                    case 1:
                        _a.trys.push([1, 4, , 5]);
                        return [4 /*yield*/, this.fetchPlaylists()];
                    case 2:
                        playlists = _a.sent();
                        if (!playlists || playlists.length === 0) {
                            this.displayMessage('No Plex playlists found. Please create a playlist in Plex first.');
                            return [2 /*return*/];
                        }
                        return [4 /*yield*/, this.showPlaylistSelectorForAll(playlists)];
                    case 3:
                        _a.sent();
                        return [3 /*break*/, 5];
                    case 4:
                        error_69 = _a.sent();
                        console.error('[PLAYLIST_ALL] Error handling add all to playlist:', error_69);
                        this.displayMessage('Error fetching playlists. Please try again.');
                        return [3 /*break*/, 5];
                    case 5: return [2 /*return*/];
                }
            });
        });
    };
    App.prototype.showPlaylistSelectorForAll = function (playlists) {
        return __awaiter(this, void 0, void 0, function () {
            var _this = this;
            return __generator(this, function (_a) {
                return [2 /*return*/, new Promise(function (resolve) {
                        var overlay = document.createElement('div');
                        overlay.className = 'playlist-modal-overlay';
                        var modal = document.createElement('div');
                        modal.className = 'playlist-modal';
                        var header = document.createElement('div');
                        header.className = 'playlist-modal-header';
                        var title = document.createElement('h3');
                        title.textContent = 'Add All Tracks to Playlist';
                        var closeBtn = document.createElement('button');
                        closeBtn.className = 'playlist-modal-close';
                        closeBtn.innerHTML = '×';
                        closeBtn.addEventListener('click', function () {
                            overlay.remove();
                            resolve();
                        });
                        header.appendChild(title);
                        header.appendChild(closeBtn);
                        var content = document.createElement('div');
                        content.className = 'playlist-modal-content';
                        if (playlists.length > 0) {
                            playlists.forEach(function (playlistName) {
                                var button = document.createElement('button');
                                button.className = 'playlist-item-btn';
                                button.innerHTML = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><line x1=\"8\" y1=\"6\" x2=\"21\" y2=\"6\"></line><line x1=\"8\" y1=\"12\" x2=\"21\" y2=\"12\"></line><line x1=\"8\" y1=\"18\" x2=\"21\" y2=\"18\"></line><line x1=\"3\" y1=\"6\" x2=\"3.01\" y2=\"6\"></line><line x1=\"3\" y1=\"12\" x2=\"3.01\" y2=\"12\"></line><line x1=\"3\" y1=\"18\" x2=\"3.01\" y2=\"18\"></line></svg><span>".concat(playlistName, "</span>");
                                button.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                                    return __generator(this, function (_a) {
                                        switch (_a.label) {
                                            case 0:
                                                overlay.remove();
                                                return [4 /*yield*/, this.handleAddAllToPlaylist(playlistName)];
                                            case 1:
                                                _a.sent();
                                                resolve();
                                                return [2 /*return*/];
                                        }
                                    });
                                }); });
                                content.appendChild(button);
                            });
                        }
                        var createSection = document.createElement('div');
                        createSection.className = 'playlist-create-section';
                        var divider = document.createElement('div');
                        divider.className = 'playlist-create-divider';
                        divider.textContent = 'or';
                        var inputGroup = document.createElement('div');
                        inputGroup.className = 'playlist-create-inline-group';
                        var input = document.createElement('input');
                        input.type = 'text';
                        input.className = 'playlist-create-inline-input';
                        input.placeholder = 'New playlist name...';
                        var okBtn = document.createElement('button');
                        okBtn.className = 'playlist-create-inline-btn';
                        okBtn.textContent = 'OK';
                        okBtn.addEventListener('click', function () { return __awaiter(_this, void 0, void 0, function () {
                            var playlistName;
                            return __generator(this, function (_a) {
                                switch (_a.label) {
                                    case 0:
                                        playlistName = input.value.trim();
                                        if (!playlistName) return [3 /*break*/, 2];
                                        overlay.remove();
                                        return [4 /*yield*/, this.handleAddAllToPlaylist(playlistName)];
                                    case 1:
                                        _a.sent();
                                        resolve();
                                        _a.label = 2;
                                    case 2: return [2 /*return*/];
                                }
                            });
                        }); });
                        input.addEventListener('keypress', function (e) {
                            if (e.key === 'Enter') {
                                var playlistName = input.value.trim();
                                if (playlistName) {
                                    overlay.remove();
                                    void _this.handleAddAllToPlaylist(playlistName);
                                    resolve();
                                }
                            }
                        });
                        inputGroup.appendChild(input);
                        inputGroup.appendChild(okBtn);
                        if (playlists.length > 0) {
                            createSection.appendChild(divider);
                        }
                        createSection.appendChild(inputGroup);
                        content.appendChild(createSection);
                        var footer = document.createElement('div');
                        footer.className = 'playlist-modal-footer';
                        var cancelBtn = document.createElement('button');
                        cancelBtn.className = 'playlist-modal-cancel';
                        cancelBtn.textContent = 'Cancel';
                        cancelBtn.addEventListener('click', function () {
                            overlay.remove();
                            resolve();
                        });
                        footer.appendChild(cancelBtn);
                        modal.appendChild(header);
                        modal.appendChild(content);
                        modal.appendChild(footer);
                        overlay.appendChild(modal);
                        overlay.addEventListener('click', function (e) {
                            if (e.target === overlay) {
                                overlay.remove();
                                resolve();
                            }
                        });
                        document.body.appendChild(overlay);
                        input.focus();
                    })];
            });
        });
    };
    App.prototype.handleAddAllToPlaylist = function (playlistName) {
        return __awaiter(this, void 0, void 0, function () {
            var addAllPlaylistBtn, trackCards, totalTracks, addedCount, failedCount, i, trackCard, trackId, addPlaylistBtn, originalContent, originalDisabled, jobId, error_70, error_71;
            return __generator(this, function (_a) {
                switch (_a.label) {
                    case 0:
                        if (this.isDownloadingAll) {
                            return [2 /*return*/];
                        }
                        this.isDownloadingAll = true;
                        addAllPlaylistBtn = document.getElementById('addAllPlaylistBtn');
                        this.setBulkActionButtonState(addAllPlaylistBtn, 'playlist', 'loading');
                        trackCards = Array.from(this.resultsContainer.querySelectorAll('.tracks-grid-row[data-track-id]'));
                        totalTracks = trackCards.length;
                        addedCount = 0;
                        failedCount = 0;
                        console.log("[PLAYLIST_ALL] Adding all ".concat(totalTracks, " tracks to playlist: ").concat(playlistName));
                        i = 0;
                        _a.label = 1;
                    case 1:
                        if (!(i < trackCards.length)) return [3 /*break*/, 9];
                        trackCard = trackCards[i];
                        trackId = trackCard.getAttribute('data-track-id');
                        if (!trackId) return [3 /*break*/, 8];
                        _a.label = 2;
                    case 2:
                        _a.trys.push([2, 7, , 8]);
                        console.log("[PLAYLIST_ALL] Adding track ".concat(i + 1, "/").concat(totalTracks));
                        addPlaylistBtn = trackCard.querySelector('.grid-add-playlist-btn');
                        if (!(addPlaylistBtn && !addPlaylistBtn.classList.contains('completed'))) return [3 /*break*/, 6];
                        originalContent = addPlaylistBtn.innerHTML;
                        originalDisabled = addPlaylistBtn.disabled;
                        if (!addPlaylistBtn.dataset.originalContent) {
                            addPlaylistBtn.dataset.originalContent = originalContent;
                        }
                        addPlaylistBtn.disabled = true;
                        _a.label = 3;
                    case 3:
                        _a.trys.push([3, 5, , 6]);
                        return [4 /*yield*/, this.downloadTrackWithPlaylist(parseInt(trackId, 10), this.downloadAllScope, playlistName)];
                    case 4:
                        jobId = _a.sent();
                        console.log("[PLAYLIST_ALL] Job queued successfully: ".concat(jobId));
                        this.setDownloadButtonQueued(addPlaylistBtn);
                        this.registerActiveJob(jobId, trackCard, addPlaylistBtn, addPlaylistBtn);
                        addedCount++;
                        return [3 /*break*/, 6];
                    case 5:
                        error_70 = _a.sent();
                        console.error('[PLAYLIST_ALL] Error adding track to playlist:', error_70);
                        addPlaylistBtn.disabled = originalDisabled;
                        addPlaylistBtn.innerHTML = originalContent;
                        if (addPlaylistBtn.dataset.originalContent) {
                            delete addPlaylistBtn.dataset.originalContent;
                        }
                        failedCount++;
                        return [3 /*break*/, 6];
                    case 6: return [3 /*break*/, 8];
                    case 7:
                        error_71 = _a.sent();
                        console.error("[PLAYLIST_ALL] Error processing track ".concat(trackId, ":"), error_71);
                        failedCount++;
                        return [3 /*break*/, 8];
                    case 8:
                        i++;
                        return [3 /*break*/, 1];
                    case 9:
                        this.isDownloadingAll = false;
                        this.setBulkActionButtonState(addAllPlaylistBtn, 'playlist', failedCount > 0 ? 'failed' : 'success');
                        console.log("[PLAYLIST_ALL] Queued ".concat(addedCount, "/").concat(totalTracks, " tracks"));
                        return [2 /*return*/];
                }
            });
        });
    };
    App.NEW_PLEX_PLAYLIST_OPTION = '__new_playlist__';
    return App;
}());
// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    new App();
});
