// ================================
// BARCODE SCANNER MODULE
// Enhanced version based on proven working implementation
// ================================

class BarcodeScanner {
    constructor(options = {}) {
        // Configuration options
        this.options = {
            modalId: options.modalId || 'scanner-modal',
            videoId: options.videoId || 'scanner-video',
            title: options.title || 'Scanner de Código de Barras',
            instruction: options.instruction || '📱 Posicione o código de barras no quadro',
            autoClose: options.autoClose !== false, // Default true
            cameraConstraints: options.cameraConstraints || {
                facingMode: "environment",
                width: { min: 1280, ideal: 1920, max: 1920 },
                height: { min: 720, ideal: 1080, max: 1080 },
                focusMode: "continuous",
                exposureMode: "continuous",
                whiteBalanceMode: "continuous"
            },
            supportedFormats: options.supportedFormats || [
                'CODE_128', 'CODE_39', 'EAN_13', 'EAN_8', 'UPC_A', 'UPC_E'
            ],
            ...options
        };

        // Internal state
        this.isScanning = false;
        this.stream = null;
        this.video = null;
        this.modal = null;
        this.videoTrack = null;
        this.lastResult = null;
        
        // Event callbacks
        this.callbacks = {
            onScan: options.onScan || null,
            onError: options.onError || null,
            onOpen: options.onOpen || null,
            onClose: options.onClose || null
        };
    }

    /**
     * Open the scanner modal and start camera
     */
    async open() {
        try {
            this.modal = document.getElementById(this.options.modalId);
            this.video = document.getElementById(this.options.videoId);
            
            if (!this.modal || !this.video) {
                throw new Error('Scanner modal elements not found');
            }
            
            this.modal.classList.add('active');
            
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
     * Start barcode scanning (legacy method for compatibility)
     */
    async startScanning(onDetected) {
        this.callbacks.onScan = onDetected;
        return this.open();
    }

    /**
     * Start camera and initialize scanning
     */
    async startCamera() {
        // Validate QuaggaJS availability
        if (typeof Quagga === 'undefined') {
            throw new Error('QuaggaJS library not available');
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
                        this.startScanning_internal();
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
                }, 3000);
                
                this.video.addEventListener('loadedmetadata', () => {
                    clearTimeout(timeout);
                }, { once: true });
            });
            
        } catch (error) {
            throw new Error('Camera access failed: ' + error.message);
        }
    }

    /**
     * Start barcode scanning with QuaggaJS (internal method)
     */
    startScanning_internal() {
        if (typeof Quagga === 'undefined' || !this.isScanning) {
            return;
        }

        // Optimized QuaggaJS configuration for higher sensitivity and speed
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
                halfSample: false,
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
            
            // Accept codes with length >= 2 and avoid duplicate detections within 500ms
            if (code && code.length >= 2 && 
                (code !== lastCode || now - lastDetectionTime > 500)) {
                
                lastCode = code;
                lastDetectionTime = now;
                this.onBarcodeDetected(code, result);
            }
        });

        // Also listen for processed events to improve detection quality
        Quagga.onProcessed((result) => {
            if (result && result.codeResult) {
                const code = result.codeResult.code;
                const now = Date.now();
                
                // If we have a good quality detection, process it
                if (code && code.length >= 2 && result.codeResult.quality > 75 &&
                    (code !== lastCode || now - lastDetectionTime > 300)) {
                    
                    lastCode = code;
                    lastDetectionTime = now;
                    this.onBarcodeDetected(code, result);
                }
            }
        });
    }

    /**
     * Play success sound when barcode is detected
     */
    playSuccessSound() {
        try {
            // Create audio context and play a success beep
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Configure success sound (higher pitch beep)
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.type = 'sine';
            
            // Configure volume envelope
            gainNode.gain.setValueAtTime(0, audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.01);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            
            // Play sound for 300ms
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
            
        } catch (error) {
            // Fallback: try to use system beep if available
            console.log('Success: Barcode detected');
        }
    }

    /**
     * Handle detected barcode
     */
    onBarcodeDetected(code, result = null) {
        // Always stop scanning first to prevent multiple rapid detections
        this.stopScanning_internal();
        
        // Play success sound
        this.playSuccessSound();
        
        // Update UI to show detection
        this.updateScannerStatus('✅ Código detectado: ' + code, 'success');
        
        // Validate barcode
        if (this.isValidBarcode(code)) {
            console.log('✅ Valid barcode detected:', code);
            
            // Close modal after short delay
            setTimeout(() => {
                if (this.options.autoClose) {
                    this.close();
                }
                
                // Trigger callback
                if (this.callbacks.onScan && typeof this.callbacks.onScan === 'function') {
                    this.callbacks.onScan(code, result);
                }
            }, 800);
            
        } else {
            console.log('❌ Invalid barcode detected, restarting scan:', code);
            
            // Show error status briefly
            this.updateScannerStatus('❌ Código inválido, tentando novamente...', 'error');
            
            // Restart scanning after delay
            setTimeout(() => {
                this.restartScanning();
            }, 1500);
        }
    }
    
    // Update scanner status display
    updateScannerStatus(message, type = '') {
        const statusElement = document.getElementById('scanner-status');
        const hintElement = statusElement?.querySelector('.scanner-hint');
        
        if (hintElement) {
            hintElement.textContent = message;
            hintElement.className = `scanner-hint ${type}`;
        }
    }

    /**
     * Validate barcode (enhanced version)
     */
    isValidBarcode(code) {
        if (!code || typeof code !== 'string') return false;
        
        const cleanCode = code.trim();
        const digitCount = (cleanCode.match(/\d/g) || []).length;
        const totalLength = cleanCode.length;
        
        if (digitCount < totalLength * 0.5) return false;
        if (totalLength < 6 || totalLength > 20) return false;
        
        const patterns = [
            /^\d{8}$/,          // EAN-8
            /^\d{12}$/,         // UPC-A
            /^\d{13}$/,         // EAN-13
            /^[\dA-Z\-\. ]+$/   // Code 39/128
        ];
        
        return patterns.some(pattern => pattern.test(cleanCode));
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
        
        return this; // For chaining
    }

    /**
     * Handle errors with callback or fallback
     */
    handleError(message, error = null) {
        if (this.callbacks.onError) {
            this.callbacks.onError(message, error);
        } else {
            console.error(message, error);
            showToast(message + (error ? ': ' + error.message : ''), 'error');
        }
    }

    /**
     * Show status message in the modal
     */
    showStatus(message, type = 'error') {
        const statusElement = document.getElementById('scanner-status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.style.display = 'block';
            statusElement.style.color = type === 'error' ? '#dc3545' : '#28a745';
            
            // Hide after 3 seconds
            setTimeout(() => {
                statusElement.style.display = 'none';
            }, 3000);
        }
    }

    /**
     * Restart scanning (useful for invalid codes)
     */
    async restartScanning() {
        // First stop any existing scanning
        this.stopScanning_internal();
        
        // Small delay to ensure proper cleanup
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // Check if video stream is still active
        if (this.video && this.video.srcObject && this.video.videoWidth > 0) {
            this.isScanning = true;
            this.startScanning_internal();
        } else {
            try {
                await this.startCamera();
            } catch (error) {
                this.handleError('Failed to restart camera', error);
            }
        }
    }

    /**
     * Close the scanner modal and stop camera
     */
    close() {
        if (this.modal) {
            this.modal.classList.remove('active');
        }
        this.stopCamera();
        
        // Trigger onClose callback
        if (this.callbacks.onClose) {
            this.callbacks.onClose();
        }
    }

    /**
     * Stop camera and cleanup resources
     */
    stopCamera() {
        this.stopScanning_internal();
        
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
     * Stop scanning (internal method)
     */
    stopScanning_internal() {
        if (typeof Quagga !== 'undefined') {
            try {
                Quagga.stop();
                Quagga.offDetected();
                Quagga.offProcessed();
            } catch (error) {
                // Silent cleanup
            }
        }
    }

    /**
     * Stop barcode scanning (legacy method for compatibility)
     */
    stopScanning() {
        this.close();
    }

    // Toggle flashlight (if supported)
    async toggleFlashlight() {
        if (!this.videoStream) {
            console.log('No video stream available for flashlight');
            return false;
        }

        try {
            const track = this.videoStream.getVideoTracks()[0];
            const capabilities = track.getCapabilities();

            if (capabilities.torch) {
                const settings = track.getSettings();
                const newTorchState = !settings.torch;
                
                await track.applyConstraints({
                    advanced: [{ torch: newTorchState }]
                });
                
                console.log('Flashlight toggled:', newTorchState);
                return newTorchState;
            } else {
                console.log('Flashlight not supported on this device');
                return false;
            }
        } catch (error) {
            console.error('Error toggling flashlight:', error);
            return false;
        }
    }

    // Manual barcode input prompt
    promptManualInput() {
        const barcode = prompt('Digite o código de barras manualmente:');
        if (barcode && barcode.trim()) {
            const cleanBarcode = barcode.trim();
            if (this.onBarcodeDetected) {
                this.onBarcodeDetected(cleanBarcode);
            }
            return cleanBarcode;
        }
        return null;
    }

    // Check if camera is available
    static async isCameraAvailable() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                return false;
            }

            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.some(device => device.kind === 'videoinput');
        } catch (error) {
            console.error('Error checking camera availability:', error);
            return false;
        }
    }

    // Get available cameras
    static async getCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.filter(device => device.kind === 'videoinput');
        } catch (error) {
            console.error('Error getting cameras:', error);
            return [];
        }
    }
}

// Global scanner instance
const barcodeScanner = new BarcodeScanner();

// Global functions for HTML event handlers
function startBarcodeScanner() {
    // Use new callback system
    barcodeScanner.on('scan', (barcode) => {
        handleBarcodeResult(barcode);
        showToast('✅ Código escaneado: ' + barcode, 'success');
    });
    
    barcodeScanner.on('error', (message, error) => {
        console.error('Scanner error:', error);
        showToast('❌ Erro no scanner: ' + message, 'error');
    });
    
    barcodeScanner.open().catch(error => {
        console.error('Scanner error:', error);
        showToast('❌ Erro ao abrir scanner: ' + error.message, 'error');
    });
}

function stopBarcodeScanner() {
    barcodeScanner.stopScanning();
}

function toggleFlashlight() {
    barcodeScanner.toggleFlashlight().then(state => {
        if (state !== false) {
            showToast(state ? 'Flash ligado' : 'Flash desligado', 'info');
        } else {
            showToast('Flash não suportado neste dispositivo', 'warning');
        }
    });
}

function manualBarcodeInput() {
    barcodeScanner.stopScanning();
    const barcode = barcodeScanner.promptManualInput();
    if (barcode) {
        handleBarcodeResult(barcode);
    }
}

function showBarcodeHelp() {
    const helpText = `
📱 DICAS PARA SCANNER DE CÓDIGO DE BARRAS:

✅ CÓDIGOS QUE FUNCIONAM:
• EAN-13 (13 dígitos) - mais comum
• EAN-8 (8 dígitos)
• UPC-A (12 dígitos)
• UPC-E (6-8 dígitos)
• Code 128, Code 39

📸 DICAS DE ESCANEAMENTO:
• Use boa iluminação
• Mantenha código reto (sem inclinação)
• Distância: 10-30cm da câmera
• Evite reflexos e sombras
• Limpe a lente da câmera

⚠️ SE NÃO FUNCIONAR:
• Use Chrome ou Safari (recomendado)
• Permita acesso à câmera
• Tente "Digitar Manualmente"
• Verifique se está em HTTPS

💡 Teste com código de barras de livro, produto ou jogo!
    `;
    
    alert(helpText);
}

// Handle barcode result (to be implemented in main app)
function handleBarcodeResult(barcode) {
    // This function will be implemented in app.js
    console.log('Barcode result:', barcode);
}