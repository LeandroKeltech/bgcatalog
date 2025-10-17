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
                                    <div class="scanner-frame border border-warning border-3 bg-transparent" 
                                         style="width: 320px; height: 120px; border-style: solid !important; border-radius: 8px;">
                                        <div class="scanner-line position-absolute top-50 start-0 w-100 bg-warning" 
                                             style="height: 2px; animation: scan 2s linear infinite;"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="scanner-instructions p-3 bg-light">
                                <p class="mb-2 text-center">
                                    <i class="bi bi-info-circle text-primary"></i> 
                                    Position the barcode within the yellow frame.<br>
                                    <small>Look for UPC/EAN barcode on game box (8-13 digits)</small>
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

        // Optimized QuaggaJS configuration for board game barcodes
        const quaggaConfig = {
            inputStream: {
                name: "Live",
                type: "LiveStream",
                target: this.video,
                constraints: {
                    width: { min: 800, ideal: 1280, max: 1920 },
                    height: { min: 600, ideal: 720, max: 1080 },
                    facingMode: "environment",
                    focusMode: "continuous"
                },
                area: { // Focus scanning area to center region
                    top: "20%",
                    right: "20%", 
                    left: "20%",
                    bottom: "20%"
                }
            },
            decoder: {
                readers: [
                    // Primary board game barcode formats (most common first)
                    "ean_reader",        // EAN-13 (most common for board games)
                    "upc_reader",        // UPC-A (common in US board games)
                    "code_128_reader",   // Code 128 (some publishers use this)
                    "ean_8_reader",      // EAN-8 (smaller games)
                    "upc_e_reader",      // UPC-E (compressed UPC)
                    "code_39_reader"     // Code 39 (backup)
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
                },
                multiple: false  // Single barcode detection for better performance
            },
            locator: {
                patchSize: "large",     // Larger patches for better detection
                halfSample: false,      // Use full resolution for better accuracy
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
            },
            numOfWorkers: 4,           // More workers for better performance
            frequency: 10,             // Scan every 100ms (slower but more accurate)
            locate: true
        };

        console.log('Starting barcode scanning with optimized config...');
        Quagga.init(quaggaConfig, (err) => {
            if (err) {
                console.error('QuaggaJS init error:', err);
                this.handleError('Scanner initialization failed', err);
                return;
            }
            
            console.log('QuaggaJS initialized successfully');
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
        let detectionAttempts = 0;
        
        // Show scanning status
        this.showStatus('Scanning... Hold barcode steady in the frame', 'info');
        
        Quagga.onProcessed((result) => {
            detectionAttempts++;
            
            // Give feedback every 50 attempts (about 5 seconds)
            if (detectionAttempts % 50 === 0) {
                console.log(`Scanning attempt ${detectionAttempts}...`);
                this.showStatus('Still scanning... Make sure barcode is clear and well-lit', 'info');
            }
            
            // Check for partial results to give feedback
            if (result && result.codeResult && result.codeResult.code) {
                const code = result.codeResult.code;
                const format = result.codeResult.format;
                
                console.log(`Detected potential code: ${code} (format: ${format})`);
                
                // For board games, we expect 8-13 digit codes
                if (code.length >= 8 && code.length <= 13) {
                    // Check if it looks like a valid UPC/EAN
                    if (/^\d+$/.test(code)) {
                        const now = Date.now();
                        
                        // Avoid duplicate detections within 2000ms
                        if (code !== lastCode || now - lastDetectionTime > 2000) {
                            console.log(`Valid barcode detected: ${code}`);
                            lastCode = code;
                            lastDetectionTime = now;
                            this.onBarcodeDetected(code, result);
                        }
                    }
                }
            }
        });
        
        Quagga.onDetected((result) => {
            const code = result.codeResult.code;
            const format = result.codeResult.format;
            const now = Date.now();
            
            console.log(`Barcode detected: ${code} (format: ${format})`);
            
            // For board games, accept codes between 8-13 digits
            if (code && /^\d{8,13}$/.test(code) && 
                (code !== lastCode || now - lastDetectionTime > 2000)) {
                
                console.log(`Processing valid board game barcode: ${code}`);
                lastCode = code;
                lastDetectionTime = now;
                this.onBarcodeDetected(code, result);
            } else if (code) {
                console.log(`Rejected barcode: ${code} (invalid format or duplicate)`);
                this.showStatus(`Invalid barcode format: ${code}. Please try again.`, 'warning');
                setTimeout(() => {
                    this.showStatus('Scanning... Hold barcode steady in the frame', 'info');
                }, 2000);
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