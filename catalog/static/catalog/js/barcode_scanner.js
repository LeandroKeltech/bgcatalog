/**
 * Barcode Scanner Module for Board Game Catalog
 * Adapted from generic barcode scanner for BGG product search
 * Supports barcode scanning to search BoardGameGeek database
 */

class BoardGameBarcodeScanner {
    constructor(options = {}) {
        // Configuration options
        this.options = {
            modalId: options.modalId || 'barcodeScannerModal',
            videoId: options.videoId || 'barcode-video',
            canvasId: options.canvasId || 'barcodeScannerCanvas',
            resultId: options.resultId || 'barcode-result',
            title: options.title || 'Scan Barcode',
            instruction: options.instruction || 'Position the barcode within the scanning area',
            closeButtonText: options.closeButtonText || 'Close',
            autoClose: options.autoClose !== false,
            showResult: options.showResult !== false,
            cameraConstraints: options.cameraConstraints || {
                facingMode: "environment",
                width: { min: 1280, ideal: 1920, max: 1920 },
                height: { min: 720, ideal: 1080, max: 1080 },
                focusMode: "continuous",
                exposureMode: "continuous",
                whiteBalanceMode: "continuous"
            },
            scanInterval: options.scanInterval || 50,
            supportedFormats: options.supportedFormats || [
                'CODE_128', 'CODE_39', 'EAN_13', 'EAN_8', 'UPC_A', 'UPC_E',
                'CODABAR', 'ITF', 'RSS_14', 'RSS_EXPANDED'
            ],
            searchEndpoint: options.searchEndpoint || '/admin/bgg_search_barcode/',
            ...options
        };

        // Internal state
        this.isScanning = false;
        this.stream = null;
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.modal = null;
        this.videoTrack = null;
        this.scanTimer = null;
        this.lastResult = null;
        this.resultElement = null;
        
        // Event callbacks
        this.callbacks = {
            onScan: options.onScan || this.defaultOnScan.bind(this),
            onError: options.onError || this.defaultOnError.bind(this),
            onOpen: options.onOpen || null,
            onClose: options.onClose || null
        };
        
        // Initialize modal
        this.initializeModal();
    }

    /**
     * Default scan handler - search BGG by barcode
     */
    async defaultOnScan(barcode, result = null) {
        try {
            this.showStatus('Searching BoardGameGeek...', 'info');
            
            // Make request to BGG search endpoint
            const response = await fetch(this.options.searchEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ barcode: barcode })
            });
            
            const data = await response.json();
            
            if (data.success) {
                if (data.games && data.games.length > 0) {
                    this.showStatus(`Found ${data.games.length} game(s)`, 'success');
                    this.handleSearchResults(data.games, barcode);
                } else {
                    this.showStatus('No games found for this barcode', 'warning');
                    await this.restartScanning();
                }
            } else {
                this.showStatus('Search failed: ' + (data.error || 'Unknown error'), 'error');
                await this.restartScanning();
            }
            
        } catch (error) {
            this.showStatus('Search error: ' + error.message, 'error');
            await this.restartScanning();
        }
    }

    /**
     * Handle search results from BGG
     */
    handleSearchResults(games, barcode) {
        if (games.length === 1) {
            // Single result - redirect directly to import
            const game = games[0];
            window.location.href = `/admin/bgg_import/${game.id}/?barcode=${encodeURIComponent(barcode)}`;
        } else {
            // Multiple results - show selection modal
            this.showGameSelectionModal(games, barcode);
        }
    }

    /**
     * Show modal for selecting from multiple games
     */
    showGameSelectionModal(games, barcode) {
        // Close scanner first
        this.close();
        
        const modalHTML = `
            <div id="gameSelectionModal" class="modal fade" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="bi bi-upc-scan"></i> 
                                Multiple Games Found for Barcode: ${barcode}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row">
                                ${games.map(game => `
                                    <div class="col-md-6 mb-3">
                                        <div class="card game-selection-card" onclick="selectGame('${game.id}', '${encodeURIComponent(barcode)}')">
                                            <div class="card-body">
                                                <h6 class="card-title">${game.name}</h6>
                                                <p class="card-text">
                                                    <small class="text-muted">
                                                        Year: ${game.year || 'Unknown'}<br>
                                                        BGG ID: ${game.id}
                                                    </small>
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Cancel
                            </button>
                            <button type="button" class="btn btn-primary" onclick="window.boardGameScanner.open()">
                                <i class="bi bi-camera"></i> Scan Another
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if present
        const existingModal = document.getElementById('gameSelectionModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add new modal
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('gameSelectionModal'));
        modal.show();
        
        // Add global function for game selection
        window.selectGame = (gameId, encodedBarcode) => {
            modal.hide();
            window.location.href = `/admin/bgg_import/${gameId}/?barcode=${encodedBarcode}`;
        };
    }

    /**
     * Default error handler
     */
    defaultOnError(message, error = null) {
        console.error('Barcode Scanner Error:', message, error);
        this.showStatus(message, 'error');
    }

    /**
     * Get CSRF token for Django requests
     */
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    /**
     * Create and initialize the scanner modal
     */
    initializeModal() {
        // Check if modal already exists
        if (document.getElementById(this.options.modalId)) {
            this.modal = document.getElementById(this.options.modalId);
            this.video = document.getElementById(this.options.videoId);
            this.canvas = document.getElementById(this.options.canvasId);
            this.context = this.canvas?.getContext('2d');
            if (this.context) {
                this.context.willReadFrequently = true;
            }
            return;
        }

        // Create modal HTML with Bootstrap styling
        const modalHTML = `
            <div id="${this.options.modalId}" class="modal fade" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-camera"></i> ${this.options.title}
                            </h5>
                            <button type="button" class="btn-close btn-close-white" onclick="window.boardGameScanner.close()"></button>
                        </div>
                        <div class="modal-body p-0">
                            <div class="scanner-video-container position-relative">
                                <video id="${this.options.videoId}" autoplay muted playsinline 
                                       class="w-100" style="height: 400px; object-fit: cover;"></video>
                                <canvas id="${this.options.canvasId}" style="display: none;"></canvas>
                                <div class="scanner-overlay position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center">
                                    <div class="scanner-frame border border-light border-3 bg-transparent" 
                                         style="width: 300px; height: 150px; border-style: dashed !important; opacity: 0.8;">
                                    </div>
                                </div>
                            </div>
                            <div class="scanner-instructions p-3 bg-light">
                                <p class="mb-2 text-center">
                                    <i class="bi bi-info-circle text-primary"></i> 
                                    ${this.options.instruction}
                                </p>
                                <div id="scanner-status" class="alert alert-info" style="display: none;"></div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" onclick="window.boardGameScanner.close()">
                                <i class="bi bi-x-circle"></i> ${this.options.closeButtonText}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Get references
        this.modal = document.getElementById(this.options.modalId);
        this.video = document.getElementById(this.options.videoId);
        this.canvas = document.getElementById(this.options.canvasId);
        this.context = this.canvas.getContext('2d');
        this.context.willReadFrequently = true;
    }

    /**
     * Open the scanner modal and start camera
     */
    async open() {
        try {
            // Show modal using Bootstrap
            const modal = new bootstrap.Modal(this.modal);
            modal.show();
            
            // Trigger onOpen callback
            if (this.callbacks.onOpen) {
                this.callbacks.onOpen();
            }
            
            await this.startCamera();
        } catch (error) {
            this.handleError('Failed to start camera', error);
        }
    }

    /**
     * Close the scanner modal and stop camera
     */
    close() {
        // Hide modal using Bootstrap
        const modal = bootstrap.Modal.getInstance(this.modal);
        if (modal) {
            modal.hide();
        }
        
        this.stopScanning();
        this.stopCamera();
        
        // Trigger onClose callback
        if (this.callbacks.onClose) {
            this.callbacks.onClose();
        }
    }

    /**
     * Set callback functions
     */
    on(event, callback) {
        const eventMap = {
            'scan': 'onScan',
            'error': 'onError',
            'open': 'onOpen',
            'close': 'onClose'
        };
        
        const callbackName = eventMap[event];
        if (callbackName && this.callbacks.hasOwnProperty(callbackName)) {
            this.callbacks[callbackName] = callback;
        }
        
        return this;
    }

    /**
     * Handle errors with callback or fallback
     */
    handleError(message, error = null) {
        if (this.callbacks.onError) {
            this.callbacks.onError(message, error);
        } else {
            this.showStatus(message, 'error');
        }
    }

    /**
     * Start camera and initialize scanning
     */
    async startCamera() {
        // Validate QuaggaJS availability
        if (typeof Quagga === 'undefined') {
            throw new Error('QuaggaJS library not available. Please ensure the library is loaded.');
        }
        
        // Check getUserMedia support
        if (!navigator.mediaDevices?.getUserMedia) {
            throw new Error('Camera access not supported in this browser');
        }

        // Stop any existing camera first
        if (this.videoTrack || this.stream) {
            this.stopCamera();
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: this.options.cameraConstraints
            });
            
            this.stream = stream;
            this.video.srcObject = stream;
            this.videoTrack = stream.getVideoTracks()[0];
            this.isScanning = true;
            
            // Wait for video metadata and start scanning
            return new Promise((resolve, reject) => {
                const handleLoadedMetadata = () => {
                    if (this.video.videoWidth > 0 && this.video.videoHeight > 0) {
                        this.startScanning();
                        resolve();
                    } else {
                        reject(new Error('Invalid video dimensions'));
                    }
                };
                
                this.video.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });
                
                const timeout = setTimeout(() => {
                    this.video.removeEventListener('loadedmetadata', handleLoadedMetadata);
                    stream.getTracks().forEach(track => track.stop());
                    reject(new Error('Camera initialization timeout'));
                }, 5000);
                
                this.video.addEventListener('loadedmetadata', () => {
                    clearTimeout(timeout);
                }, { once: true });
            });
            
        } catch (error) {
            throw new Error('Camera access failed: ' + error.message);
        }
    }

    /**
     * Stop camera and cleanup resources
     */
    stopCamera() {
        // Stop Quagga first
        if (typeof Quagga !== 'undefined') {
            try {
                Quagga.stop();
                Quagga.offDetected();
                Quagga.offProcessed();
            } catch (error) {
                // Silent cleanup
            }
        }
        
        // Stop video track
        if (this.videoTrack) {
            try {
                this.videoTrack.stop();
            } catch (error) {
                // Silent cleanup
            }
            this.videoTrack = null;
        }
        
        // Stop all media streams
        if (this.stream) {
            try {
                this.stream.getTracks().forEach(track => track.stop());
            } catch (error) {
                // Silent cleanup
            }
            this.stream = null;
        }
        
        // Clear video element
        if (this.video) {
            try {
                this.video.srcObject = null;
                this.video.pause();
                this.video.currentTime = 0;
            } catch (error) {
                // Silent cleanup
            }
        }
        
        this.isScanning = false;
    }

    /**
     * Start barcode scanning with QuaggaJS
     */
    startScanning() {
        if (typeof Quagga === 'undefined' || !this.isScanning) {
            return;
        }

        // Optimized QuaggaJS configuration for barcode detection
        const quaggaConfig = {
            inputStream: {
                name: "Live",
                type: "LiveStream",
                target: this.video,
                constraints: {
                    width: { min: 640, ideal: 1280, max: 1920 },
                    height: { min: 480, ideal: 720, max: 1080 },
                    facingMode: "environment"
                }
            },
            decoder: {
                readers: [
                    "code_128_reader",
                    "ean_reader", 
                    "ean_8_reader",
                    "code_39_reader",
                    "upc_reader",
                    "upc_e_reader"
                ],
                debug: {
                    showCanvas: false,
                    showPatches: false,
                    showFoundPatches: false,
                    showSkeleton: false,
                    showLabels: false,
                    showPatchLabels: false,
                    showRemainingPatchLabels: false,
                    boxFromPatches: {
                        showTransformed: false,
                        showTransformedBox: false,
                        showBB: false
                    }
                }
            },
            locator: {
                patchSize: "medium",
                halfSample: false
            },
            numOfWorkers: 2,
            frequency: 25,
            locate: true
        };

        Quagga.init(quaggaConfig, (err) => {
            if (err) {
                this.handleError('Scanner initialization failed', err);
                return;
            }
            
            Quagga.start();
            this.setupQuaggaListeners();
        });
    }

    /**
     * Setup QuaggaJS event listeners
     */
    setupQuaggaListeners() {
        // Track detections to avoid duplicates
        let lastDetectionTime = 0;
        let lastCode = null;
        
        Quagga.onDetected((result) => {
            const code = result.codeResult.code;
            const now = Date.now();
            
            // Accept codes and avoid duplicate detections within 1000ms
            if (code && code.length >= 8 && 
                (code !== lastCode || now - lastDetectionTime > 1000)) {
                
                lastCode = code;
                lastDetectionTime = now;
                this.onBarcodeDetected(code, result);
            }
        });
    }

    /**
     * Play success sound when barcode is detected
     */
    playSuccessSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0, audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.01);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
            
        } catch (error) {
            console.log('Barcode detected');
        }
    }

    /**
     * Handle detected barcode
     */
    onBarcodeDetected(code, result = null) {
        // Stop scanning to prevent multiple rapid detections
        this.stopScanning();
        
        // Play success sound
        this.playSuccessSound();
        
        // Trigger callback
        if (this.callbacks.onScan && typeof this.callbacks.onScan === 'function') {
            this.callbacks.onScan(code, result);
        }
    }

    /**
     * Stop scanning
     */
    stopScanning() {
        if (typeof Quagga !== 'undefined') {
            Quagga.stop();
            Quagga.offDetected();
            Quagga.offProcessed();
        }
        this.isScanning = false;
    }

    /**
     * Show status message in the modal
     */
    showStatus(message, type = 'error') {
        const statusElement = document.getElementById('scanner-status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.style.display = 'block';
            
            // Update Bootstrap alert class
            statusElement.className = 'alert alert-' + (type === 'error' ? 'danger' : 
                                                       type === 'warning' ? 'warning' :
                                                       type === 'success' ? 'success' : 'info');
            
            // Hide after 3 seconds for non-permanent messages
            if (type !== 'info') {
                setTimeout(() => {
                    statusElement.style.display = 'none';
                }, 3000);
            }
        }
    }

    /**
     * Restart scanning (useful for invalid codes)
     */
    async restartScanning() {
        this.stopScanning();
        await new Promise(resolve => setTimeout(resolve, 300));
        
        if (this.video && this.video.srcObject && this.video.videoWidth > 0) {
            this.isScanning = true;
            this.startScanning();
        } else {
            try {
                await this.startCamera();
            } catch (error) {
                this.handleError('Failed to restart camera', error);
            }
        }
    }

    /**
     * Destroy scanner instance and cleanup
     */
    destroy() {
        this.stopCamera();
        if (this.modal) {
            this.modal.remove();
        }
        this.callbacks = {};
    }
}

// Initialize global scanner instance when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize on admin pages AND BGG search page
    const currentPath = window.location.pathname;
    const shouldInitialize = currentPath.includes('/admin/') || 
                           currentPath.includes('/bgg/search/') ||
                           currentPath.includes('/catalog/');
    
    if (shouldInitialize) {
        try {
            // Check if QuaggaJS is available
            if (typeof Quagga === 'undefined') {
                console.error('QuaggaJS library not loaded. Barcode scanner will not be available.');
                return;
            }
            
            console.log('Initializing barcode scanner...');
            window.boardGameScanner = new BoardGameBarcodeScanner({
                title: 'Scan Board Game Barcode',
                instruction: 'Position the barcode within the frame to search BoardGameGeek'
            });
            console.log('Barcode scanner initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize barcode scanner:', error);
        }
    }
});